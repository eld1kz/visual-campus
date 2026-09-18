"""Wikimedia Commons: files from the university's category (+ one level of subcategories) and geotagged files nearby.

Listing is cheap (ids only), metadata is fetched by page id in parallel chunks, so most files arrive within the budget.
"""

import asyncio
import html
import re
from dataclasses import dataclass

import httpx

from app.models import RawImage, SourceResult
from app.services.pipeline.dates import normalize_date, text_year
from app.services.sources.base import (
    MIN_SIDE_PX, Batches, Deadline, OnBatch, Skip, SourceQuery, request_with_retry, run_collector,
)
from app.services.sources.geo import distance_m

COMMONS_API = "https://commons.wikimedia.org/w/api.php"
COMMONS_DOMAIN = "commons.wikimedia.org"
PHOTO_MIMES = {"image/jpeg", "image/png", "image/webp"}
THUMB_WIDTH = 250
MAX_SUBCATEGORIES = 12
MAX_FILES_PER_CATEGORY = 500
FAST_FILES_PER_CATEGORY = 120
MAX_FILES_PER_SUBCATEGORY = 100
GEOSEARCH_LIMIT = 100
NEARBY_RADIUS_M = 1000
CHUNK = 50  # API limit for extmetadata page ids per request
PARALLEL_REQUESTS = 3

# Subcategories about people, symbols or media rather than places.
_NOT_A_PLACE = re.compile(
    r"alumni|people|faculty|staff|president|professor|rector|persons|portrait|logo|seal|emblem|coat of arms|"
    r"\bmaps?\b|document|video|audio|publication|book|signature|award|medal",
    re.IGNORECASE,
)
_TAGS = re.compile(r"<[^>]+>")
_DATE = re.compile(r"(\d{4})(?:-(\d{2}))?(?:-(\d{2}))?")


@dataclass
class CommonsFile:
    pageid: int
    title: str
    page_url: str
    thumb_url: str | None
    full_url: str
    sha1: str
    lat: float | None
    lng: float | None
    author: str
    license: str | None
    date_taken: str | None  # YYYY, YYYY-MM or YYYY-MM-DD
    date_source: str
    uploaded: str | None  # YYYY-MM-DD
    description: str
    categories: list[str]
    # Which of the university's categories listed this file (None if found only by location).
    via_category: str | None = None
    via_subcategory: bool = False
    found_nearby: bool = False
    license_url: str | None = None
    width: int | None = None
    height: int | None = None


def clean_text(value: str | None) -> str:
    return re.sub(r"\s+", " ", html.unescape(_TAGS.sub(" ", value or ""))).strip()


def parse_date(value: str | None) -> str | None:
    match = _DATE.search(clean_text(value))
    if not match:
        return None
    return normalize_date("-".join(part for part in match.groups() if part))


def _meta(extmetadata: dict, key: str) -> str | None:
    return (extmetadata.get(key) or {}).get("value")


def parse_page(page: dict, structured_date: str | None = None) -> CommonsFile | None:
    """One `pages` entry of an imageinfo query → CommonsFile; None for non-photos and tiny files."""
    info = (page.get("imageinfo") or [None])[0]
    if not info or info.get("mime") not in PHOTO_MIMES or "url" not in info:
        return None
    width, height = info.get("width"), info.get("height")
    if width and height and min(width, height) < MIN_SIDE_PX:
        return None
    meta = info.get("extmetadata", {})
    raw_meta = {entry.get("name"): entry.get("value") for entry in info.get("metadata", []) if entry.get("name")}
    coords = (page.get("coordinates") or [{}])[0]
    exif_date = parse_date(raw_meta.get("DateTimeOriginal") or raw_meta.get("DateTimeDigitized"))
    source_date = parse_date(_meta(meta, "DateTimeOriginal"))
    date_taken = exif_date or structured_date or source_date
    date_source = "exif" if exif_date else "structured_data" if structured_date else "source_metadata" if source_date else "unknown"
    return CommonsFile(
        pageid=page["pageid"],
        title=page["title"],
        page_url=info.get("descriptionurl") or f"https://commons.wikimedia.org/?curid={page['pageid']}",
        thumb_url=info.get("thumburl"),
        full_url=info["url"],
        sha1=info.get("sha1", ""),
        lat=coords.get("lat"),
        lng=coords.get("lon"),
        author=clean_text(_meta(meta, "Artist")) or "—",
        license=clean_text(_meta(meta, "LicenseShortName")) or None,
        date_taken=date_taken,
        date_source=date_source,
        uploaded=parse_date(info.get("timestamp")),
        description=clean_text(_meta(meta, "ImageDescription")),
        categories=[c for c in (_meta(meta, "Categories") or "").split("|") if c],
        license_url=clean_text(_meta(meta, "LicenseUrl")) or None,
        width=width,
        height=height,
    )


def to_raw(f: CommonsFile) -> RawImage:
    return RawImage(
        id=f"commons-{f.pageid}",
        source="wikimedia_commons",
        source_url=f.page_url,
        source_domain=COMMONS_DOMAIN,
        full_url=f.full_url,
        thumb_url=f.thumb_url,
        title=f.title,
        description=f.description,
        source_categories=f.categories,
        matched_category=f.via_category,
        matched_subcategory=f.via_subcategory,
        found_by="category" if f.via_category else "geosearch",
        author=None if f.author == "—" else f.author,
        license=f.license,
        license_url=f.license_url,
        date_taken=f.date_taken,
        date_uploaded=f.uploaded,
        date_source=f.date_source if f.date_taken else "upload_only" if f.uploaded else "unknown",
        date_hint_year=text_year(f.title, f.description),
        lat=f.lat,
        lng=f.lng,
        width=f.width,
        height=f.height,
        sha1=f.sha1 or None,
    )


class _Harvest:
    """Collects files for one university; `files` is complete-so-far at any moment (safe to read after a timeout)."""

    def __init__(self, client: httpx.AsyncClient, deadline: Deadline, on_file=None, on_batch_end=None) -> None:
        self.client = client
        self.deadline = deadline
        self.on_file = on_file or (lambda f: None)
        self.on_batch_end = on_batch_end or (lambda: None)  # called after each metadata chunk / provenance update
        self.files: dict[int, CommonsFile] = {}
        self._origin: dict[int, tuple[int, str | None]] = {}  # pageid → (rank, category); 0 main, 1 sub, 2 nearby
        self._requested: set[int] = set()
        self._nearby: set[int] = set()

    async def _get(self, params: dict) -> dict:
        resp = await request_with_retry(
            self.client, "GET", COMMONS_API, self.deadline, "wikimedia", PARALLEL_REQUESTS,
            params={"action": "query", "format": "json", **params},
        )
        resp.raise_for_status()
        return resp.json()

    async def _members(self, category: str, cmtype: str, limit: int) -> list[dict]:
        members: list[dict] = []
        cont: dict = {}
        while len(members) < limit:
            # Files: newest additions to the category first, so recent photos survive the per-category limits.
            order = {"cmsort": "timestamp", "cmdir": "desc"} if cmtype == "file" else {}
            data = await self._get({"list": "categorymembers", "cmtitle": f"Category:{category}", "cmtype": cmtype,
                                    "cmlimit": min(500, limit - len(members)), **order, **cont})
            members += data.get("query", {}).get("categorymembers", [])
            if "continue" not in data:
                break
            cont = data["continue"]
        return members[:limit]

    def _apply(self, f: CommonsFile) -> None:
        rank, category = self._origin[f.pageid]
        f.via_category = category
        f.via_subcategory = rank == 1
        f.found_nearby = f.pageid in self._nearby

    def _note(self, pageids: list[int], rank: int, category: str | None) -> list[int]:
        """Record where ids were found (main category > subcategory > nearby); returns ids not yet requested."""
        new = []
        for pid in pageids:
            if rank == 2:
                self._nearby.add(pid)
            if pid not in self._origin or rank < self._origin[pid][0]:
                self._origin[pid] = (rank, category)
            if pid in self.files:
                self._apply(self.files[pid])
                self.on_file(self.files[pid])
            if pid not in self._requested:
                self._requested.add(pid)
                new.append(pid)
        return new

    async def _details(self, pageids: list[int]) -> None:
        chunks = [pageids[i:i + CHUNK] for i in range(0, len(pageids), CHUNK)]
        if not chunks:
            return
        # Fetch one chunk first so every concurrent profile can stream photos before its bulk metadata work.
        await self._chunk(chunks[0])
        await asyncio.gather(*(self._chunk(c) for c in chunks[1:]))

    async def _chunk(self, pageids: list[int]) -> None:
        params = {
            "pageids": "|".join(map(str, pageids)),
            "prop": "imageinfo|coordinates",
            "iiprop": "url|mime|sha1|timestamp|size|metadata|extmetadata",
            "iiextmetadatafilter": "Artist|LicenseShortName|LicenseUrl|DateTimeOriginal|ImageDescription|Categories",
            "iiurlwidth": THUMB_WIDTH,
            "colimit": "max",
        }
        pages: dict[int, dict] = {}
        cont: dict = {}
        for _ in range(3):
            data = await self._get({**params, **cont})
            for pid, page in data.get("query", {}).get("pages", {}).items():
                merged = pages.setdefault(int(pid), {})
                for key, value in page.items():
                    if key in ("imageinfo", "coordinates") and key in merged:
                        continue
                    merged[key] = value
            if "continue" not in data:
                break
            cont = data["continue"]
        for page in pages.values():
            f = parse_page(page) if "pageid" in page else None
            if f is None or f.pageid not in self._origin:
                continue
            self._apply(f)
            self.files[f.pageid] = f
            self.on_file(f)
        self.on_batch_end()
        structured = await self._structured_dates(pageids)
        for page in pages.values():
            pid = int(page.get("pageid", 0))
            if pid not in structured or pid not in self._origin:
                continue
            updated = parse_page(page, structured[pid])
            if updated is not None and self.files.get(pid) != updated:
                self._apply(updated)
                self.files[pid] = updated
                self.on_file(updated)
        self.on_batch_end()

    async def _structured_dates(self, pageids: list[int]) -> dict[int, str]:
        """Structured Data on Commons inception (P571), preserving claim precision."""
        if not pageids:
            return {}
        try:
            data = await self._get({"action": "wbgetentities", "ids": "|".join(f"M{pid}" for pid in pageids), "props": "claims"})
        except Exception:  # a metadata extension/mock may not implement MediaInfo; dates remain unknown
            return {}
        result: dict[int, str] = {}
        for entity_id, entity in data.get("entities", {}).items():
            claims = entity.get("claims", {}).get("P571", [])
            if not claims:
                continue
            value = claims[0].get("mainsnak", {}).get("datavalue", {}).get("value", {})
            raw, precision = value.get("time"), value.get("precision", 11)
            if not raw:
                continue
            candidate = raw.lstrip("+").split("T", 1)[0]
            if precision <= 9:
                candidate = candidate[:4]
            elif precision == 10:
                candidate = candidate[:7]
            if normalized := normalize_date(candidate):
                result[int(entity_id.removeprefix("M"))] = normalized
        return result

    async def files_of(self, category: str, rank: int, limit: int) -> None:
        members = await self._members(category, "file", limit)
        new = self._note([m["pageid"] for m in members], rank, category)
        self.on_batch_end()
        await self._details(new)

    async def subcategories(self, category: str) -> None:
        subs = [m["title"].removeprefix("Category:") for m in await self._members(category, "subcat", 200)]
        subs = [s for s in subs if not _NOT_A_PLACE.search(s)]
        # Recent year categories are discovered from the tree, never hardcoded by university.
        subs.sort(key=lambda s: (not bool(re.search(r"\b20(?:2[4-9]|[3-9]\d)\b", s)), s.casefold()))
        await asyncio.gather(*(self.files_of(s, 1, MAX_FILES_PER_SUBCATEGORY) for s in subs[:MAX_SUBCATEGORIES]))

    async def category(self, category: str) -> None:
        await asyncio.gather(self.files_of(category, 0, MAX_FILES_PER_CATEGORY), self.subcategories(category))

    async def nearby(self, lat: float, lng: float, radius_m: int) -> None:
        data = await self._get({"list": "geosearch", "gscoord": f"{lat}|{lng}", "gsradius": max(10, min(radius_m, 10_000)),
                                "gsnamespace": 6, "gslimit": GEOSEARCH_LIMIT})
        ids = [g["pageid"] for g in data.get("query", {}).get("geosearch", [])]
        new = self._note(ids, 2, None)
        self.on_batch_end()
        await self._details(new)

    async def search(self, query: str, found_by: str, subject_id: str | None = None) -> None:
        data = await self._get({
            "list": "search", "srsearch": query, "srnamespace": 6,
            "srlimit": 80, "srsort": "create_timestamp_desc",
        })
        ids = [item["pageid"] for item in data.get("query", {}).get("search", [])]
        new = self._note(ids, 2, None)
        await self._details(new)
        for pid in ids:
            if pid in self.files:
                raw = self.files[pid]
                self.on_file(raw)

    async def titles(self, titles: list[str], category: str | None = None) -> None:
        if not titles:
            return
        normalized = [title if title.startswith("File:") else f"File:{title}" for title in titles[:50]]
        data = await self._get({"titles": "|".join(normalized), "prop": "info"})
        ids = [int(pid) for pid, page in data.get("query", {}).get("pages", {}).items() if "missing" not in page]
        new = self._note(ids, 0 if category else 2, category)
        await self._details(new)


async def _harvest(harvest: _Harvest, category: str | None, lat: float | None, lng: float | None, radius_m: int) -> None:
    tasks = []
    if category:
        tasks.append(harvest.category(category))
    if lat is not None and lng is not None:
        tasks.append(harvest.nearby(lat, lng, radius_m))
    await asyncio.gather(*tasks)


def _radius_m(query: SourceQuery) -> int:
    if not query.bbox:
        return NEARBY_RADIUS_M
    west, south, east, north = query.bbox
    return int(max(NEARBY_RADIUS_M, distance_m(south, west, north, east) / 2))


async def collect(query: SourceQuery, client: httpx.AsyncClient, on_batch: OnBatch | None = None) -> SourceResult:
    async def work(acc: Batches, deadline: Deadline) -> str | None:
        has_point = query.lat is not None and query.lng is not None
        if not query.commons_category and not has_point:
            raise Skip("no Commons category and no coordinates")

        def publish(f: CommonsFile) -> None:
            raw = to_raw(f)
            subject = category_subjects.get(f.via_category or "")
            if subject:
                raw = raw.model_copy(update={
                    "subject_id": subject.qid,
                    "subject_name": subject.names[0] if subject.names else None,
                    "subject_kind": subject.kind,
                    "subject_building_type": subject.building_type,
                })
            acc[raw.id] = raw

        category_subjects = {
            subject.commons_category: subject
            for subject in (query.subjects or [])
            if subject.commons_category
        }
        harvest = _Harvest(client, deadline, publish, acc.flush)
        centers = query.geosearch_centers or (
            [(query.lat, query.lng, _radius_m(query))] if query.lat is not None and query.lng is not None else []
        )
        # Fair fast stage: every concurrent profile queues only its main category/centre before enrichment fans out.
        if query.commons_category:
            await harvest.files_of(query.commons_category, 0, FAST_FILES_PER_CATEGORY)
        elif centers:
            lat, lng, radius = centers[0]
            await harvest.nearby(lat, lng, radius)

        enrichment = []
        if query.commons_category:
            enrichment.append(harvest.subcategories(query.commons_category))
        for lat, lng, radius in (centers if query.commons_category else centers[1:]):
            enrichment.append(harvest.nearby(lat, lng, radius))
        for subject in [s for s in (query.subjects or []) if s.kind == "building"][:8]:
            if subject.commons_category and subject.commons_category != query.commons_category:
                enrichment.append(harvest.category(subject.commons_category))
            if subject.image_titles:
                enrichment.append(harvest.titles(subject.image_titles, subject.commons_category or subject.names[0]))

        # Enrichment: structured depicts statements, then a few useful local-language names.
        qids = [query.wikidata_id, *[s.qid for s in (query.subjects or []) if s.qid and s.kind == "building"][:8]]
        enrichment.extend(harvest.search(f"haswbstatement:P180={qid}", "depicts", qid) for qid in qids)
        for name in [n for n in query.names if len(n.strip()) >= 4][:4]:
            enrichment.append(harvest.search(f'"{name}" filetype:bitmap', "text"))
        await asyncio.gather(*enrichment, return_exceptions=True)
        return None

    return await run_collector("wikimedia_commons", work, on_batch=on_batch)
