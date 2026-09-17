"""Wikimedia Commons: files from the university's category (+ one level of subcategories) and geotagged files nearby.

Listing is cheap (ids only), metadata is fetched by page id in parallel chunks, so most files arrive within the budget.
"""

import asyncio
import html
import re
from dataclasses import dataclass

import httpx

from app.models import RawImage, SourceResult
from app.services.sources.base import MIN_SIDE_PX, Deadline, Skip, SourceQuery, run_collector
from app.services.sources.geo import distance_m

COMMONS_API = "https://commons.wikimedia.org/w/api.php"
COMMONS_DOMAIN = "commons.wikimedia.org"
PHOTO_MIMES = {"image/jpeg", "image/png", "image/webp"}
THUMB_WIDTH = 640
MAX_SUBCATEGORIES = 12
MAX_FILES_PER_CATEGORY = 500
MAX_FILES_PER_SUBCATEGORY = 100
GEOSEARCH_LIMIT = 100
NEARBY_RADIUS_M = 1000
CHUNK = 50  # API limit for extmetadata page ids per request
PARALLEL_REQUESTS = 6

# Subcategories about people, symbols or media rather than places.
_NOT_A_PLACE = re.compile(
    r"alumni|people|faculty|staff|president|professor|rector|persons|portrait|logo|seal|emblem|coat of arms|"
    r"\bmaps?\b|document|video|audio|publication|book|signature|award|medal|academic dress|costume",
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
    return "-".join(part for part in match.groups() if part)


def _meta(extmetadata: dict, key: str) -> str | None:
    return (extmetadata.get(key) or {}).get("value")


def parse_page(page: dict) -> CommonsFile | None:
    """One `pages` entry of an imageinfo query → CommonsFile; None for non-photos and tiny files."""
    info = (page.get("imageinfo") or [None])[0]
    if not info or info.get("mime") not in PHOTO_MIMES or "url" not in info:
        return None
    width, height = info.get("width"), info.get("height")
    if width and height and min(width, height) < MIN_SIDE_PX:
        return None
    meta = info.get("extmetadata", {})
    coords = (page.get("coordinates") or [{}])[0]
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
        date_taken=parse_date(_meta(meta, "DateTimeOriginal")),
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
        published_at=f.date_taken or f.uploaded,
        lat=f.lat,
        lng=f.lng,
        width=f.width,
        height=f.height,
        sha1=f.sha1 or None,
    )


class _Harvest:
    """Collects files for one university; `files` is complete-so-far at any moment (safe to read after a timeout)."""

    def __init__(self, client: httpx.AsyncClient, deadline: Deadline, on_file=None) -> None:
        self.client = client
        self.deadline = deadline
        self.on_file = on_file or (lambda f: None)
        self.files: dict[int, CommonsFile] = {}
        self._origin: dict[int, tuple[int, str | None]] = {}  # pageid → (rank, category); 0 main, 1 sub, 2 nearby
        self._requested: set[int] = set()
        self._nearby: set[int] = set()
        self._sem = asyncio.Semaphore(PARALLEL_REQUESTS)

    async def _get(self, params: dict) -> dict:
        async with self._sem:
            resp = await self.client.get(
                COMMONS_API, params={"action": "query", "format": "json", **params}, timeout=self.deadline.left()
            )
        resp.raise_for_status()
        return resp.json()

    async def _members(self, category: str, cmtype: str, limit: int) -> list[dict]:
        members: list[dict] = []
        cont: dict = {}
        while len(members) < limit:
            data = await self._get({"list": "categorymembers", "cmtitle": f"Category:{category}", "cmtype": cmtype,
                                    "cmlimit": min(500, limit - len(members)), **cont})
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
        await asyncio.gather(*(self._chunk(c) for c in chunks))

    async def _chunk(self, pageids: list[int]) -> None:
        params = {
            "pageids": "|".join(map(str, pageids)),
            "prop": "imageinfo|coordinates",
            "iiprop": "url|mime|sha1|timestamp|size|extmetadata",
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

    async def category(self, category: str) -> None:
        async def files_of(cat: str, rank: int, limit: int) -> None:
            members = await self._members(cat, "file", limit)
            await self._details(self._note([m["pageid"] for m in members], rank, cat))

        async def subcategories() -> None:
            subs = [m["title"].removeprefix("Category:") for m in await self._members(category, "subcat", 200)]
            subs = [s for s in subs if not _NOT_A_PLACE.search(s)][:MAX_SUBCATEGORIES]
            await asyncio.gather(*(files_of(s, 1, MAX_FILES_PER_SUBCATEGORY) for s in subs))

        await asyncio.gather(files_of(category, 0, MAX_FILES_PER_CATEGORY), subcategories())

    async def nearby(self, lat: float, lng: float, radius_m: int) -> None:
        data = await self._get({"list": "geosearch", "gscoord": f"{lat}|{lng}", "gsradius": max(10, min(radius_m, 10_000)),
                                "gsnamespace": 6, "gslimit": GEOSEARCH_LIMIT})
        ids = [g["pageid"] for g in data.get("query", {}).get("geosearch", [])]
        await self._details(self._note(ids, 2, None))


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


async def collect(query: SourceQuery, client: httpx.AsyncClient) -> SourceResult:
    async def work(acc: dict[str, RawImage], deadline: Deadline) -> str | None:
        has_point = query.lat is not None and query.lng is not None
        if not query.commons_category and not has_point:
            raise Skip("no Commons category and no coordinates")

        def publish(f: CommonsFile) -> None:
            raw = to_raw(f)
            acc[raw.id] = raw

        harvest = _Harvest(client, deadline, publish)
        await _harvest(harvest, query.commons_category, query.lat, query.lng, _radius_m(query))
        return None

    return await run_collector("wikimedia_commons", work)
