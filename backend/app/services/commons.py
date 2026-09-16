"""Wikimedia Commons: files from the university's category tree and geotagged files near the campus."""

import asyncio
import html
import re
from dataclasses import dataclass

import httpx

COMMONS_API = "https://commons.wikimedia.org/w/api.php"
PHOTO_MIMES = {"image/jpeg", "image/png", "image/webp"}
THUMB_WIDTH = 640
MAX_BATCHES = 6
MAX_SUBCATEGORIES = 8

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
    uploaded: str | None  # YYYY-MM-DD
    description: str
    categories: list[str]
    # Which of the university's categories listed this file (None if found only by location).
    via_category: str | None = None
    via_subcategory: bool = False
    found_nearby: bool = False


def clean_text(value: str | None) -> str:
    return re.sub(r"\s+", " ", html.unescape(_TAGS.sub(" ", value or ""))).strip()


def parse_date(value: str | None) -> str | None:
    match = _DATE.search(clean_text(value))
    if not match:
        return None
    return "-".join(part for part in match.groups() if part)


def _meta(extmetadata: dict, key: str) -> str | None:
    return (extmetadata.get(key) or {}).get("value")


def _parse(page: dict) -> CommonsFile | None:
    info = (page.get("imageinfo") or [None])[0]
    if not info or info.get("mime") not in PHOTO_MIMES:
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
    )


async def _query_pages(client: httpx.AsyncClient, params: dict) -> list[dict]:
    """Run a generator query, following `continue` and merging partial page records."""
    base = {
        "action": "query",
        "format": "json",
        "prop": "imageinfo|coordinates",
        "iiprop": "url|mime|sha1|timestamp|extmetadata",
        "iiextmetadatafilter": "Artist|LicenseShortName|DateTimeOriginal|ImageDescription|Categories",
        "iiurlwidth": THUMB_WIDTH,
        **params,
    }
    pages: dict[int, dict] = {}
    cont: dict = {}
    for _ in range(MAX_BATCHES):
        resp = await client.get(COMMONS_API, params={**base, **cont})
        resp.raise_for_status()
        data = resp.json()
        for pageid, page in data.get("query", {}).get("pages", {}).items():
            merged = pages.setdefault(int(pageid), {})
            for key, value in page.items():
                if key in ("imageinfo", "coordinates") and key in merged:
                    continue
                merged[key] = value
        if "continue" not in data:
            break
        cont = data["continue"]
    return list(pages.values())


async def subcategories(client: httpx.AsyncClient, category: str) -> list[str]:
    resp = await client.get(
        COMMONS_API,
        params={"action": "query", "format": "json", "list": "categorymembers", "cmtype": "subcat",
                "cmtitle": f"Category:{category}", "cmlimit": 100},
    )
    resp.raise_for_status()
    titles = [m["title"].removeprefix("Category:") for m in resp.json().get("query", {}).get("categorymembers", [])]
    return [t for t in titles if not _NOT_A_PLACE.search(t)][:MAX_SUBCATEGORIES]


async def category_files(client: httpx.AsyncClient, category: str, limit: int = 50) -> list[CommonsFile]:
    pages = await _query_pages(
        client,
        {"generator": "categorymembers", "gcmtitle": f"Category:{category}", "gcmtype": "file", "gcmlimit": limit},
    )
    files = [f for f in map(_parse, pages) if f]
    for f in files:
        f.via_category = category
    return files


async def nearby_files(client: httpx.AsyncClient, lat: float, lng: float, radius_m: int, limit: int = 50) -> list[CommonsFile]:
    pages = await _query_pages(
        client,
        {"generator": "geosearch", "ggscoord": f"{lat}|{lng}", "ggsradius": min(radius_m, 10_000),
         "ggsnamespace": 6, "ggslimit": limit},
    )
    files = [f for f in map(_parse, pages) if f]
    for f in files:
        f.found_nearby = True
    return files


async def collect_files(
    client: httpx.AsyncClient, category: str | None, lat: float | None, lng: float | None, radius_m: int
) -> list[CommonsFile]:
    """All candidate files, merged by page id (a file can be both in the category and nearby)."""
    tasks = []
    if category:
        subcats = await subcategories(client, category)
        tasks.append(category_files(client, category, limit=100))
        tasks += [category_files(client, sub) for sub in subcats]
    if lat is not None and lng is not None:
        tasks.append(nearby_files(client, lat, lng, radius_m))

    merged: dict[int, CommonsFile] = {}
    # Main category first, then subcategories, then nearby: the first listing of a file keeps its provenance.
    for batch in await asyncio.gather(*tasks):
        for f in batch:
            f.via_subcategory = f.via_category is not None and f.via_category != category
            existing = merged.setdefault(f.pageid, f)
            existing.found_nearby = existing.found_nearby or f.found_nearby
            if existing.via_category is None:
                existing.via_category, existing.via_subcategory = f.via_category, f.via_subcategory
    return list(merged.values())
