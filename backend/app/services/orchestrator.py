"""Profile orchestrator (docs/CONTRACT.md §1, §3): Wikidata → all sources in parallel → verify → SSE events.

One `ProfileBuild` per (qid, lang) at a time (single-flight via cache.inflight); followers read its EventLog.
"""

import asyncio
import logging
import time
from datetime import date

import httpx
from shapely.geometry import Polygon

from app.config import settings
from app.models import (
    CampusShape, Photo, Place, ProfileDone, ProfileResponse, ProfileSourceStatus, ProfileStats, ProfileUniversity,
    RawImage, SourceResult, Summary,
)
from app.services import cache
from app.services.pipeline import CampusContext, Deduplicator, VisionResult, classify, score
from app.services.sources import commons, flickr, mapillary, official_site, osm, run_source
from app.services.sources.base import SourceQuery
from app.services.sources.geo import distance_m
from app.services.summary import SourceText, build_summary, extract_summary
from app.services.wikidata import UniversityRecord, add_places, get_university
from app.services.wikipedia import summary as wikipedia_summary

logger = logging.getLogger("visual_campus.orchestrator")

PROFILE_DEADLINE_S = 30.0
DONE_MARGIN_S = 1.0  # stop sources this much before the deadline so `done` still fits
WIKIDATA_TIMEOUT_S = 8.0
SOURCE_TIMEOUT_S = 8.0  # outer guard; collectors stop themselves at 7.5 s
WIKIPEDIA_TIMEOUT_S = 6.0
HTTP_TIMEOUT_S = 8.0

SOURCE_NAMES = [
    "wikidata", "openstreetmap", "wikimedia_commons", "wikipedia", "flickr", "mapillary", "official_site",
]
PHOTO_COLLECTORS = {
    "wikimedia_commons": commons.collect,
    "flickr": flickr.collect,
    "mapillary": mapillary.collect,
    "official_site": official_site.collect,
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
    """English name first: the OSM collector searches Nominatim by the first name."""
    return list(dict.fromkeys([uni.name_en, uni.name, *uni.names]))


def distance_to_center_km(uni: UniversityRecord) -> float | None:
    center = uni.city_center
    if center is None or uni.lat is None or uni.lng is None:
        return None
    return round(distance_m(uni.lat, uni.lng, center.lat, center.lng) / 1000, 1)


def to_university(uni: UniversityRecord, shape: CampusShape | None) -> ProfileUniversity:
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
                       cached=True, partial=cached.partial)
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
        self.vision: dict[str, VisionResult] = {}  # CLIP verdicts by photo id
        self.summary: Summary | None = None
        self.deadline_hit = False
        self._children: set[asyncio.Task] = set()
        self._hash_tasks: set[asyncio.Task] = set()

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
        self.ctx = CampusContext(
            names=names, lat=uni.lat, lng=uni.lng, polygon=None, buildings=[],
            official_domains=official_domains(uni.website), today=date.today(), lang=self.lang,
        )
        query = SourceQuery(
            wikidata_id=self.qid, names=names, lat=uni.lat, lng=uni.lng, website=uni.website,
            commons_category=uni.commons_category, bbox=shape_bbox(shape),
        )
        sources_started = time.perf_counter()
        tasks: dict[str, asyncio.Task] = {}
        if shape is not None:
            self._apply_shape(shape)
            self._finish(SourceResult(name="openstreetmap", status="ok", took_ms=0, detail="cached shape"))
        else:
            tasks["openstreetmap"] = self._spawn(self._guard("openstreetmap", self._osm(query, client)))
        for name, collect in PHOTO_COLLECTORS.items():
            tasks[name] = self._spawn(self._guard(name, self._photos(name, collect, query, client)))
        tasks["wikipedia"] = self._spawn(self._guard("wikipedia", self._wikipedia(uni, client)))
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

        if self._hash_tasks:
            _, hash_pending = await asyncio.wait(self._hash_tasks, timeout=max(self._left(), 0))
            for task in hash_pending:
                task.cancel()
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
        started = time.perf_counter()
        try:
            result = await asyncio.wait_for(collect(query, client), timeout=SOURCE_TIMEOUT_S)
        except asyncio.TimeoutError:
            result = SourceResult(name=name, status="timeout", took_ms=_ms(started))
        new = self._ingest(result.images)
        self._finish(result)
        if new:  # photos are already sent; duplicates and the visual check follow in the background
            self._hash_tasks.add(asyncio.create_task(self._analyze(new, client)))

    async def _analyze(self, raws: list[RawImage], client: httpx.AsyncClient) -> None:
        """Download thumbnails once: pHash for duplicates, CLIP for what the photo shows; re-send what changed.

        Most confident first: if the budget runs out, the photos people see by default are the checked ones.
        """
        raws = sorted(raws, key=lambda r: -(self.scored[r.id][0].confidence if r.id in self.scored else 0))
        started = time.perf_counter()
        contents = await self.hasher.prepare(raws, client)
        downloaded_ms = _ms(started)
        ids = list(contents)
        verdicts = await classify([contents[i] for i in ids])
        logger.info("%s: %d photos, %d thumbnails in %d ms, %d judged by vision in %d ms", self.qid, len(raws),
                    len(ids), downloaded_ms, sum(v is not None for v in verdicts), _ms(started) - downloaded_ms)
        for photo_id, verdict in zip(ids, verdicts):
            if verdict is None:
                continue
            self.vision[photo_id] = verdict
            raw = self.raws[photo_id]
            if (photo := self._score(raw)) is not None:
                self.scored[photo_id] = (photo, raw)
        self._refresh()
        for name in PHOTO_COLLECTORS:
            result = self.results.get(name)
            if result is not None and self._count(name) != self.counts.get(name):
                self._finish(result)

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
        self.scored = {rid: (p, raw) for rid, raw in self.raws.items() if (p := self._score(raw))}
        self._refresh()

    def _ingest(self, raws: list[RawImage]) -> list[RawImage]:
        new = []
        for raw in raws:
            if raw.id in self.raws:
                continue
            self.raws[raw.id] = raw
            photo = self._score(raw)
            if photo is not None:
                self.scored[raw.id] = (photo, raw)
                new.append(raw)
        if new:
            self._refresh()
        return new

    def _score(self, raw: RawImage) -> Photo | None:
        return score(raw, self.ctx, self.vision.get(raw.id))

    def _refresh(self) -> None:
        """Regroup all scored photos with every pHash known so far and send the photos that changed.

        Decision (c): when a more confident copy arrives later, the earlier main photo (already sent) is not
        withdrawn — the new main photo is sent with the earlier id in its `duplicates`; no new event type.
        """
        dedup = Deduplicator()
        for photo_id, value in self.hasher._hashes.items():  # noqa: SLF001 — no public getter yet
            dedup.set_hash(photo_id, value)
        for photo, raw in self.scored.values():
            dedup.add(photo, raw)
        self.final = dedup.photos()
        for photo in self.final:
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
        self.log.emit(*status_event(result.name, result.status, count, result.took_ms))

    def _statuses(self) -> list[ProfileSourceStatus]:
        return [
            ProfileSourceStatus(name=n, status=r.status, count=self.counts.get(n, 0), took_ms=r.took_ms)
            for n in SOURCE_NAMES if (r := self.results.get(n))
        ]

    def _done(self, uni: UniversityRecord) -> None:
        partial = is_partial(list(self.results.values()), self.deadline_hit)
        university = to_university(uni, self.shape)
        stats = compute_stats(self.final)
        generated = _ms(self.started)
        profile = ProfileResponse(
            university=university, generated_in_ms=generated, sources_status=self._statuses(),
            summary=self.summary, stats=stats, photos=self.final,
        )
        cache.put_profile(self.qid, self.lang, profile, partial)
        done = ProfileDone(university=university, stats=stats, generated_in_ms=generated, cached=False, partial=partial)
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
