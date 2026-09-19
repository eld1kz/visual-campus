"""Profile orchestrator (docs/CONTRACT.md §1, §3): Wikidata → all sources in parallel → verify → SSE events.

One `ProfileBuild` per (qid, lang) at a time (single-flight via cache.inflight); followers read its EventLog.
"""

import asyncio
from collections import Counter
import inspect
import logging
import time
from datetime import date
from dataclasses import replace

import httpx
from shapely.geometry import Polygon

from app.config import settings
from app.models import (
    CampusShape, CenterRoute, Photo, Place, ProfileDone, ProfileResponse, ProfileSourceStatus, ProfileStats, ProfileUniversity,
    RawImage, SourceResult, Summary,
)
from app.services import cache
from app.services.pipeline import CampusContext, Deduplicator, batch_vision_check, score
from app.services.pipeline.claude_vision import claude_vision_check
from app.services.pipeline.dedupe import _phash
from app.services.pipeline.ranking import select_targets
from app.services.query_planner import build_query_plan
from app.services.sources import commons, mapillary, official_site, openverse, osm, run_source, web_search
from app.services.sources.base import SourceQuery
from app.services.sources.geo import distance_m
from app.services.summary import SourceText, build_summary, extract_summary
from app.services.wikidata import UniversityRecord, add_places, discover_campus_subjects, get_university
from app.services.routing import center_route
from app.services.wikipedia import summary as wikipedia_summary

logger = logging.getLogger("visual_campus.orchestrator")

PROFILE_DEADLINE_S = 30.0
DONE_MARGIN_S = 1.0  # stop sources this much before the deadline so `done` still fits
WIKIDATA_TIMEOUT_S = 8.0
SOURCE_TIMEOUT_S = 8.0  # outer guard; collectors stop themselves at 7.5 s
WIKIPEDIA_TIMEOUT_S = 6.0
HTTP_TIMEOUT_S = 8.0
SHAPE_WAIT_S = 1.5
GAP_FILL_S = 3.0  # targeted searches for empty categories
GAP_CATEGORIES = ("dorms", "libraries", "classrooms")
GAP_MIN_RELIABLE = 3
CLAUDE_VISION_S = 14.0  # budget of the batched Claude check, which runs in parallel with OpenCLIP  # short head-start for OSM so bbox-based photo sources can use the campus outline on cold cache

# Flickr is off: its API needs a paid Pro account. The collector stays in sources/flickr.py; add "flickr" here
# and to PHOTO_COLLECTORS to turn it back on.
SOURCE_NAMES = [
    "wikidata", "openstreetmap", "wikimedia_commons", "wikipedia", "mapillary", "official_site",
    "openverse", "web_search",
]
PHOTO_COLLECTORS = {
    "wikimedia_commons": commons.collect,
    "mapillary": mapillary.collect,
    "official_site": official_site.collect,
    "openverse": openverse.collect,
    "web_search": web_search.collect,
}

# ---------- Decisions waiting for the user: (a) and (b) ----------

# (a) Only these statuses make a profile partial. `ok` with a "partial" detail (a collector hit its own budget
#     but kept images) does NOT count.
PARTIAL_STATUSES = ("timeout", "error")
# (b) cam.ac.uk and others answer 403 to bots: with False this is an `error` and the profile is partial
#     (as the contract says). Set True to not count an official site 403 as partial.
IGNORE_OFFICIAL_SITE_403 = False


def is_partial(results: list[SourceResult], deadline_hit: bool) -> bool:
    if deadline_hit:
        return True
    for r in results:
        if r.status not in PARTIAL_STATUSES:
            continue
        if IGNORE_OFFICIAL_SITE_403 and r.name == "official_site" and "403" in (r.detail or ""):
            continue
        return True
    return False


class UniversityNotFound(Exception):
    pass


class ProfileUnavailable(Exception):
    def __init__(self, state: str = "error") -> None:
        super().__init__(f"Wikidata {state}")
        self.state = state if state in ("timeout", "error") else "error"


# ---------- Pure helpers ----------


def compute_stats(photos: list[Photo]) -> ProfileStats:
    return ProfileStats(
        photos=len(photos),
        verified=sum(p.tier == "verified" for p in photos),
        likely=sum(p.tier == "likely" for p in photos),
        hidden=sum(p.tier == "unconfirmed" for p in photos),
        duplicates=sum(len(p.duplicates) for p in photos),
    )


def search_names(uni: UniversityRecord) -> list[str]:
    """English name first: the OSM collector searches Nominatim by the first name.

    A single Latin word that is not an acronym ("Cambridge" for the University of Cambridge) is dropped: as an alias
    it would credit any photo taken in that town, such as Harvard or MIT, with a mention of the university.
    """
    names = list(dict.fromkeys([uni.name_en, uni.name, *uni.names]))
    return [n for n in names if not (n.isascii() and len(n.split()) == 1 and not n.isupper())]


def distance_to_center_km(uni: UniversityRecord) -> float | None:
    center = uni.city_center
    if center is None or uni.lat is None or uni.lng is None:
        return None
    return round(distance_m(uni.lat, uni.lng, center.lat, center.lng) / 1000, 1)


def to_university(uni: UniversityRecord, shape: CampusShape | None, route: CenterRoute | None = None) -> ProfileUniversity:
    center = uni.city_center
    return ProfileUniversity(
        id=uni.wikidata_id,
        name=uni.name,
        aliases=[n for n in uni.names if n != uni.name][:20],
        city=center.name if center else uni.city,
        country=uni.country,
        website=uni.website,
        lat=uni.lat,
        lng=uni.lng,
        campus_polygon=shape.polygon if shape else None,
        campus_area_km2=shape.area_km2 if shape else None,
        distance_to_center_km=distance_to_center_km(uni),
        city_center=Place(name=center.name, lat=center.lat, lng=center.lng) if center else None,
        center_route=route if center else None,
        wikidata_id=uni.wikidata_id,
        ror_id=uni.ror_id,
        commons_category=uni.commons_category,
        osm_url=shape.osm_url if shape else None,
    )


def official_domains(website: str | None) -> list[str]:
    if not website:
        return []
    host = httpx.URL(website).host
    return [host] if host else []


def shape_bbox(shape: CampusShape | None) -> tuple[float, float, float, float] | None:
    if shape is None or not shape.polygon:
        return None
    xs, ys = [p[0] for p in shape.polygon], [p[1] for p in shape.polygon]
    return (min(xs), min(ys), max(xs), max(ys))


def status_event(name: str, status: str, count: int = 0, took_ms: int | None = None) -> tuple[str, dict]:
    return "source_status", ProfileSourceStatus(name=name, status=status, count=count, took_ms=took_ms).model_dump()


def replay_events(cached: cache.CachedProfile) -> list[tuple[str, dict]]:
    """A cached profile as the same kinds of events, in contract order, ending with done(cached=true)."""
    p = cached.profile
    events = [status_event(name, "pending") for name in SOURCE_NAMES]
    events += [("source_status", s.model_dump()) for s in p.sources_status]
    events += [("photo", photo.model_dump()) for photo in p.photos]
    events.append(("summary", p.summary.model_dump()))
    done = ProfileDone(university=p.university, stats=p.stats, generated_in_ms=p.generated_in_ms,
                       cached=True, partial=cached.partial, photo_ids=[photo.id for photo in p.photos])
    events.append(("done", done.model_dump()))
    return events


# ---------- One build ----------


def _ms(started: float) -> int:
    return round((time.perf_counter() - started) * 1000)


class ProfileBuild:
    def __init__(self, qid: str, lang: str) -> None:
        self.qid, self.lang = qid, lang
        self.log = cache.EventLog()
        self.ready: asyncio.Future = asyncio.get_running_loop().create_future()  # UniversityRecord or error
        self.started = time.perf_counter()
        self.deadline = time.monotonic() + PROFILE_DEADLINE_S
        self.task: asyncio.Task | None = None
        self.ctx: CampusContext | None = None
        self.shape: CampusShape | None = None
        self.wiki = None
        self.results: dict[str, SourceResult] = {}
        self.raws: dict[str, RawImage] = {}
        self.scored: dict[str, tuple[Photo, RawImage]] = {}
        self.sent: dict[str, Photo] = {}
        self.final: list[Photo] = []
        self.counts: dict[str, int] = {}
        self.hasher = Deduplicator()  # only its pHash cache is used; groups are rebuilt in _refresh
        self.dedup = Deduplicator()  # current groups: new batches are added incrementally, _refresh rebuilds
        self.summary: Summary | None = None
        self.center_route: CenterRoute | None = None
        self.deadline_hit = False
        self._children: set[asyncio.Task] = set()
        self._hash_tasks: set[asyncio.Task] = set()
        self._to_hash: list[RawImage] = []
        self._hashes_grouped = 0  # pHashes known at the last full regroup

    def start(self) -> None:
        self.task = asyncio.create_task(self._run())

    def cancel(self) -> None:
        if self.task and not self.task.done():
            self.task.cancel()

    def _left(self) -> float:
        return self.deadline - DONE_MARGIN_S - time.monotonic()

    def _spawn(self, coro) -> asyncio.Task:
        task = asyncio.create_task(coro)
        self._children.add(task)
        return task

    async def _run(self) -> None:
        key = (self.qid, self.lang)
        try:
            async with httpx.AsyncClient(
                timeout=HTTP_TIMEOUT_S, headers={"User-Agent": settings.user_agent}, follow_redirects=True
            ) as client:
                uni = await self._wikidata(client)
                if uni is not None:
                    await self._collect(uni, client)
        except asyncio.CancelledError:
            raise
        except Exception:  # noqa: BLE001 — never leave followers hanging: the log is closed below
            logger.exception("Profile build %s failed", key)
        finally:
            for task in self._children | self._hash_tasks:
                task.cancel()
            if not self.ready.done():
                self.ready.set_exception(ProfileUnavailable("error"))
            if cache.inflight.get(key) is self:
                del cache.inflight[key]
            self.log.close()

    async def _wikidata(self, client: httpx.AsyncClient) -> UniversityRecord | None:
        started = time.perf_counter()
        state, uni = await run_source("wikidata", get_university(client, self.qid, self.lang, with_places=False), WIKIDATA_TIMEOUT_S)
        if state != "ok":
            self.ready.set_exception(ProfileUnavailable(state))
            return None
        if uni is None:
            self.ready.set_exception(UniversityNotFound(self.qid))
            return None
        for name in SOURCE_NAMES:
            self.log.emit(*status_event(name, "pending"))
        self._finish(SourceResult(name="wikidata", status="ok", took_ms=_ms(started)))
        self.ready.set_result(uni)
        return uni

    async def _collect(self, uni: UniversityRecord, client: httpx.AsyncClient) -> None:
        names = search_names(uni)
        places_task = self._spawn(self._places(uni, client))  # city centre is only needed for `done`
        shape = cache.get_shape(self.qid)
        try:
            discovered = await asyncio.wait_for(
                discover_campus_subjects(client, uni, shape_bbox(shape)), timeout=min(0.6, max(self._left(), 0.1))
            )
        except (asyncio.TimeoutError, httpx.HTTPError, ValueError):
            discovered = []
        self.ctx = CampusContext(
            names=names, lat=uni.lat, lng=uni.lng, polygon=None, buildings=[],
            official_domains=official_domains(uni.website), today=date.today(), lang=self.lang,
        )
        query = build_query_plan(uni, shape, discovered)
        sources_started = time.perf_counter()
        self._stage("sources")
        tasks: dict[str, asyncio.Task] = {}
        if shape is not None:
            self._apply_shape(shape)
            self._finish(SourceResult(name="openstreetmap", status="ok", took_ms=0, detail="cached shape"))
        else:
            tasks["openstreetmap"] = self._spawn(self._guard("openstreetmap", self._osm(query, client)))
        deferred = {"mapillary", "openverse", "web_search"}
        if not query.commons_category:
            deferred.add("wikimedia_commons")
        for name, collect in PHOTO_COLLECTORS.items():
            if name in deferred:
                continue
            tasks[name] = self._spawn(self._guard(name, self._photos(name, collect, query, client)))
        tasks["wikipedia"] = self._spawn(self._guard("wikipedia", self._wikipedia(uni, client)))
        if deferred:
            await self._wait_for_shape(tasks.get("openstreetmap"))
            photo_query = build_query_plan(uni, self.shape, discovered) if self.shape else query
            for name in deferred:
                if name in PHOTO_COLLECTORS:
                    tasks[name] = self._spawn(self._guard(name, self._photos(name, PHOTO_COLLECTORS[name], photo_query, client)))
        summary_task = self._spawn(self._summary(tasks, client))

        _, pending = await asyncio.wait([*tasks.values(), summary_task], timeout=max(self._left(), 0))
        if pending:
            self.deadline_hit = True
            for task in pending:
                task.cancel()
            await asyncio.gather(*pending, return_exceptions=True)
            for name, task in tasks.items():
                if task in pending:
                    self._finish(SourceResult(name=name, status="timeout", took_ms=_ms(sources_started)))

        # The Claude check adapts to the time left; it needs ~8 s for a useful pass after the gap searches.
        if self._left() > GAP_FILL_S + 8:
            await self._fill_gaps(photo_query if deferred else query, client)
        if self._left() > 1.5:
            await self._vision(client)
        self._stage("finalizing")

        if self._hash_tasks:
            _, hash_pending = await asyncio.wait(self._hash_tasks, timeout=max(self._left(), 0))
            for task in hash_pending:
                task.cancel()
        if len(self.hasher.hashes()) != self._hashes_grouped:
            self._refresh()
        for name in SOURCE_NAMES:  # counts may change after late duplicates were found
            result = self.results.get(name)
            if result is not None and self._count(name) != self.counts.get(name):
                self._finish(result)
        if self.summary is None:
            self.summary = extract_wiki(self.wiki)
            self.log.emit("summary", self.summary.model_dump())
        await asyncio.wait([places_task], timeout=max(self._left(), 0))
        self._done(uni)

    async def _places(self, uni: UniversityRecord, client: httpx.AsyncClient) -> None:
        """City, country and city centre; on failure the profile just has no distance to the centre."""
        try:
            await add_places(client, uni, self.lang)
        except asyncio.CancelledError:
            raise
        except Exception:  # noqa: BLE001
            logger.exception("City centre lookup failed for %s", self.qid)
            return
        center = uni.city_center
        if center is None or uni.lat is None or uni.lng is None:
            return
        try:
            self.center_route = await center_route(client, uni.lat, uni.lng, center.lat, center.lng)
        except asyncio.CancelledError:
            raise
        except Exception as exc:  # noqa: BLE001 — the straight-line distance is still shown
            logger.warning("Route to the city centre failed for %s: %s", self.qid, exc)

    async def _guard(self, name: str, coro) -> None:
        """A bug in one source must not break the stream: it becomes that source's `error`."""
        started = time.perf_counter()
        try:
            await coro
        except asyncio.CancelledError:
            raise
        except Exception as exc:  # noqa: BLE001
            logger.exception("Source %s crashed in the orchestrator", name)
            self._finish(SourceResult(name=name, status="error", took_ms=_ms(started), detail=repr(exc)))

    async def _wait_for_shape(self, task: asyncio.Task | None) -> None:
        """Give OSM a brief chance to provide a campus bbox before bbox-only photo APIs start."""
        if self.shape is not None or task is None or task.done():
            return
        until = time.monotonic() + min(SHAPE_WAIT_S, max(self._left(), 0))
        while self.shape is None and not task.done() and time.monotonic() < until:
            await asyncio.sleep(0.05)

    async def _osm(self, query: SourceQuery, client: httpx.AsyncClient) -> None:
        started = time.perf_counter()
        try:
            result, shape = await asyncio.wait_for(osm.find_campus(query, client), timeout=SOURCE_TIMEOUT_S)
        except asyncio.TimeoutError:
            result, shape = SourceResult(name="openstreetmap", status="timeout", took_ms=_ms(started)), None
        if shape is not None:
            cache.put_shape(self.qid, shape, complete=result.detail is None)
            self._apply_shape(shape)
        self._finish(result)

    async def _photos(self, name: str, collect, query: SourceQuery, client: httpx.AsyncClient) -> None:
        """Photos are scored and sent batch by batch as the collector hands them out; the result gives the status."""
        started = time.perf_counter()

        cached = cache.get_source(name, query)
        if cached is not None:
            self._ingest(cached.images, client)
            self._finish(cached.model_copy(update={"took_ms": 0, "detail": "cached source response"}))
            return

        def on_batch(raws: list[RawImage]) -> None:
            self._ingest(raws, client)

        call = collect(query, client, on_batch=on_batch) if "on_batch" in inspect.signature(collect).parameters \
            else collect(query, client)
        try:
            result = await asyncio.wait_for(call, timeout=SOURCE_TIMEOUT_S)
        except asyncio.TimeoutError:  # batches that already arrived stay in the profile
            result = SourceResult(name=name, status="timeout", took_ms=_ms(started))
        self._ingest(result.images, client)  # no-op for images that came in batches
        cache.put_source(name, query, result)
        self._finish(result)

    async def _hash(self, client: httpx.AsyncClient) -> None:
        """One worker per build: hashes new photos in turn, so the shared hash budget is spent sequentially."""
        while self._to_hash:
            raws, self._to_hash = self._to_hash, []
            await self.hasher.prepare(raws, client)
            if len(self.hasher.hashes()) == self._hashes_grouped:  # nothing new to group by
                continue
            self._refresh()
            for name in PHOTO_COLLECTORS:
                result = self.results.get(name)
                if result is not None and self._count(name) != self.counts.get(name):
                    self._finish(result)

    async def _fill_gaps(self, query: SourceQuery, client: httpx.AsyncClient) -> None:
        """A category with no reliable photo gets narrow searches ("<name> library") before the visual check."""
        # Counted before the visual check, so one borderline photo must not hide a gap: fewer than 3 is a gap.
        reliable = Counter(photo.category for photo, _ in self.scored.values() if photo.tier != "unconfirmed")
        empty = [c for c in GAP_CATEGORIES if reliable[c] < GAP_MIN_RELIABLE]
        if not empty:
            return
        self._stage("gap_fill", categories=empty)
        try:
            raws = await asyncio.wait_for(web_search.search_gaps(query, client, empty, GAP_FILL_S), GAP_FILL_S + 0.5)
        except Exception:  # noqa: BLE001 — nothing extra found
            return
        logger.info("gap_fill %s categories=%s found=%d", self.qid, ",".join(empty), len(raws))
        self._ingest(raws, client)

    async def _vision(self, client: httpx.AsyncClient) -> None:
        """OpenCLIP on the candidates most likely to be shown first, then Claude on the borderline ones; one refresh each."""
        prioritized = sorted(
            ((raw, photo) for photo, raw in self.scored.values() if not raw.vision_checked),
            key=lambda pair: (pair[1].tier != "unconfirmed", pair[1].confidence, pair[1].freshness == "2024_plus"),
            reverse=True,
        )
        self._stage("vision", checked=0, total=None)
        claude_task = None
        if settings.llm_api_key and settings.claude_vision_max > 0 and self._left() > 3:
            # Claude runs next to OpenCLIP (network vs local CPU); its verdicts are applied last and win.
            items = [(raw, photo) for photo, raw in self.scored.values()]
            claude_task = asyncio.create_task(claude_vision_check(
                items, self.ctx.names[0], client, budget_s=min(CLAUDE_VISION_S, self._left() - 0.5),
                limit=settings.claude_vision_max,
                on_progress=lambda checked, total: self._stage("vision", checked=checked, total=total),
                on_image=self._hash_bytes))
        try:
            self._apply_vision(await batch_vision_check(prioritized, client, budget_s=min(12.0, max(0.0, self._left())),
                                                        on_image=self._hash_bytes))
        except Exception:  # missing model/runtime failure leaves the explicit unchecked cap in place
            logger.exception("Visual check failed for %s", self.qid)
        if claude_task is None:
            return
        try:
            claude = await claude_task
        except Exception:
            logger.exception("Claude visual check failed for %s", self.qid)
            return
        # An unsure Claude answer must not erase a verdict OpenCLIP already gave the same photo.
        self._apply_vision({
            photo_id: raw for photo_id, raw in claude.items()
            if raw.vision_label != "inconclusive" or self.raws.get(photo_id, raw).vision_source != "openclip"
        })

    def _stage(self, stage: str, **details) -> None:
        """What the build is doing now, for the loading screen (docs/CONTRACT.md §3 `stage`)."""
        self.log.emit("stage", {"stage": stage, **details})

    def _hash_bytes(self, raw: RawImage, content: bytes) -> None:
        """Thumbnails downloaded for the visual checks also give the pHash: duplicates beyond the hash budget."""
        if raw.id in self.hasher.hashes():
            return
        try:
            self.hasher.set_hash(raw.id, _phash(content))
        except Exception:  # noqa: BLE001 — not an image the hasher can read
            pass

    def _apply_vision(self, updated: dict[str, RawImage]) -> None:
        if len(self.hasher.hashes()) != self._hashes_grouped and not updated:
            self._refresh()  # new hashes from the visual checks: regroup duplicates
            return
        if not updated:
            return
        for photo_id, raw in updated.items():
            self.raws[photo_id] = raw
            if photo := score(raw, self.ctx):
                self.scored[photo_id] = (photo, raw)
            else:
                self.scored.pop(photo_id, None)
        self._refresh()

    async def _wikipedia(self, uni: UniversityRecord, client: httpx.AsyncClient) -> None:
        started = time.perf_counter()
        if not uni.wikipedia_titles:
            self._finish(SourceResult(name="wikipedia", status="skipped", took_ms=0, detail="no Wikipedia article"))
            return
        state, wiki = await run_source(
            "wikipedia", wikipedia_summary(client, uni.wikipedia_titles, self.lang), WIKIPEDIA_TIMEOUT_S
        )
        self.wiki = wiki
        self._finish(SourceResult(name="wikipedia", status=state, took_ms=_ms(started)))

    async def _summary(self, tasks: dict[str, asyncio.Task], client: httpx.AsyncClient) -> None:
        # Without an LLM only the Wikipedia extract is used, so do not wait for the official site.
        needed = ["wikipedia", "official_site"] if settings.llm_api_key else ["wikipedia"]
        await asyncio.wait([tasks[n] for n in needed if n in tasks])
        texts = [wiki_text(self.wiki)] if self.wiki else []
        seen = set()
        for raw in self.raws.values():
            if raw.source == "official_site" and raw.description and raw.description not in seen:
                seen.add(raw.description)
                texts.append(SourceText(title=f"{raw.source_domain} — {raw.title or raw.source_domain}",
                                        url=raw.source_url, text=raw.description))
        self.summary = await build_summary(texts, self.lang, client, timeout_s=self._left() - 0.5)
        self.log.emit("summary", self.summary.model_dump())

    # ---------- state updates (synchronous: no awaits, so no races) ----------

    def _apply_shape(self, shape: CampusShape) -> None:
        self.shape = shape
        polygon = Polygon(shape.polygon) if shape.polygon and len(shape.polygon) >= 4 else None
        if polygon is None and not shape.buildings:
            return
        self.ctx.polygon, self.ctx.buildings = polygon, shape.buildings
        rescored = {rid: (p, raw) for rid, raw in self.raws.items() if (p := score(raw, self.ctx))}
        if rescored.keys() != self.scored.keys():
            self.scored = rescored
            self._refresh()
            return
        self.scored = rescored  # same photos, new scores: groups do not depend on scores, update them in place
        self._send(p for photo, raw in rescored.values() for p in self.dedup.add(photo, raw))
        self.final = self.dedup.photos()

    def _ingest(self, raws: list[RawImage], client: httpx.AsyncClient) -> None:
        """Upsert images by id: an unchanged repeat is ignored, a changed one is re-scored."""
        added, regroup = [], False
        for raw in raws:
            known = self.raws.get(raw.id)
            if known == raw:
                continue
            self.raws[raw.id] = raw
            photo = score(raw, self.ctx)
            if photo is None:
                regroup = regroup or self.scored.pop(raw.id, None) is not None
                continue
            self.scored[raw.id] = (photo, raw)
            added.append((photo, raw))
            if known is None:
                self._to_hash.append(raw)
        if regroup:
            self._refresh()
        elif added:  # a full regroup is O(n²): per batch only the new/changed photos are placed into groups
            self._send(p for photo, raw in added for p in self.dedup.add(photo, raw))
            self.final = self.dedup.photos()
        if self._to_hash and not any(not t.done() for t in self._hash_tasks):
            # photos are already sent; perceptual duplicates are found in the background
            self._hash_tasks.add(asyncio.create_task(self._hash(client)))

    def _refresh(self) -> None:
        """Regroup all scored photos with every pHash known so far and send the photos that changed.

        Decision (c): when a more confident copy arrives later, the earlier main photo (already sent) is not
        withdrawn — the new main photo is sent with the earlier id in its `duplicates`; no new event type.
        """
        dedup = Deduplicator()
        self._hashes_grouped = len(self.hasher.hashes())
        for photo_id, value in self.hasher.hashes().items():
            dedup.set_hash(photo_id, value)
        for photo, raw in self.scored.values():
            dedup.add(photo, raw)
        self.dedup = dedup
        self.final = dedup.photos()
        self._send(self.final)

    def _send(self, photos) -> None:
        """Send only photos whose event differs from what the client already has."""
        for photo in photos:
            if self.sent.get(photo.id) != photo:
                self.sent[photo.id] = photo
                self.log.emit("photo", photo.model_dump())

    def _count(self, name: str) -> int:
        if name == "wikidata":
            return 1
        if name == "openstreetmap":
            return 1 if self.shape and self.shape.polygon else 0
        if name == "wikipedia":
            return 1 if self.wiki else 0
        return sum(self.raws[p.id].source == name for p in self.final)

    def _finish(self, result: SourceResult) -> None:
        self.results[result.name] = result
        count = self._count(result.name)
        self.counts[result.name] = count
        source_raws = [raw for raw in self.raws.values() if raw.source == result.name]
        hidden_vision = sum(raw.vision_veto for raw in source_raws)
        duplicate_or_unshown = max(0, len(source_raws) - count - hidden_vision)
        logger.info(
            "source_metrics source=%s candidates=%d shown=%d hidden_vision=%d hidden_duplicate_or_rank=%d "
            "took_ms=%d status=%s error=%s",
            result.name, len(result.images), count, hidden_vision, duplicate_or_unshown,
            result.took_ms, result.status, result.detail or "",
        )
        self.log.emit(*status_event(result.name, result.status, count, result.took_ms))

    def _statuses(self) -> list[ProfileSourceStatus]:
        return [
            ProfileSourceStatus(name=n, status=r.status, count=self.counts.get(n, 0), took_ms=r.took_ms)
            for n in SOURCE_NAMES if (r := self.results.get(n))
        ]

    def _done(self, uni: UniversityRecord) -> None:
        self.final = select_targets(self.final)
        for name, result in self.results.items():
            count = self._count(name)
            if self.counts.get(name) != count:
                self.counts[name] = count
                self.log.emit(*status_event(name, result.status, count, result.took_ms))
        partial = is_partial(list(self.results.values()), self.deadline_hit)
        university = to_university(uni, self.shape, self.center_route)
        stats = compute_stats(self.final)
        generated = _ms(self.started)
        profile = ProfileResponse(
            university=university, generated_in_ms=generated, sources_status=self._statuses(),
            summary=self.summary, stats=stats, photos=self.final,
        )
        cache.put_profile(self.qid, self.lang, profile, partial)
        done = ProfileDone(
            university=university, stats=stats, generated_in_ms=generated, cached=False, partial=partial,
            photo_ids=[photo.id for photo in self.final],
        )
        self.log.emit("done", done.model_dump())


def wiki_text(wiki) -> SourceText:
    return SourceText(title=f"Wikipedia — {wiki.title}", url=wiki.url, text=wiki.text, is_extract=True)


def extract_wiki(wiki) -> Summary:
    return extract_summary([wiki_text(wiki)] if wiki else [])


def start_or_join(qid: str, lang: str) -> ProfileBuild:
    """Single-flight: a second request for a profile being built follows the same build."""
    build = cache.inflight.get((qid, lang))
    if build is None:
        build = ProfileBuild(qid, lang)
        cache.inflight[(qid, lang)] = build
        build.start()
    return build
