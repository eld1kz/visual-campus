"""Flickr: CC-licensed geotagged photos inside the campus bbox (flickr.photos.search). Needs FLICKR_API_KEY.

Written against https://www.flickr.com/services/api/flickr.photos.search.html and flickr.photos.licenses.getInfo;
not verified live (no key available).
"""

import re

import httpx

from app.config import settings
from app.models import RawImage, SourceResult
from app.services.pipeline.dates import normalize_date, text_year, unix_date
from app.services.sources.base import (
    MIN_SIDE_PX, Batches, Deadline, OnBatch, Skip, SourceQuery, query_bbox, request_with_retry, run_collector,
)

FLICKR_REST = "https://api.flickr.com/services/rest/"
PER_PAGE = 250
MAX_PAGES = 2

# flickr.photos.licenses.getInfo: only Creative Commons, CC0 and Public Domain Mark.
LICENSES: dict[str, tuple[str, str]] = {
    "1": ("CC BY-NC-SA 2.0", "https://creativecommons.org/licenses/by-nc-sa/2.0/"),
    "2": ("CC BY-NC 2.0", "https://creativecommons.org/licenses/by-nc/2.0/"),
    "3": ("CC BY-NC-ND 2.0", "https://creativecommons.org/licenses/by-nc-nd/2.0/"),
    "4": ("CC BY 2.0", "https://creativecommons.org/licenses/by/2.0/"),
    "5": ("CC BY-SA 2.0", "https://creativecommons.org/licenses/by-sa/2.0/"),
    "6": ("CC BY-ND 2.0", "https://creativecommons.org/licenses/by-nd/2.0/"),
    "9": ("CC0 1.0", "https://creativecommons.org/publicdomain/zero/1.0/"),
    "10": ("Public Domain Mark 1.0", "https://creativecommons.org/publicdomain/mark/1.0/"),
    "11": ("CC BY 4.0", "https://creativecommons.org/licenses/by/4.0/"),
    "12": ("CC BY-SA 4.0", "https://creativecommons.org/licenses/by-sa/4.0/"),
    "13": ("CC BY-ND 4.0", "https://creativecommons.org/licenses/by-nd/4.0/"),
    "14": ("CC BY-NC 4.0", "https://creativecommons.org/licenses/by-nc/4.0/"),
    "15": ("CC BY-NC-SA 4.0", "https://creativecommons.org/licenses/by-nc-sa/4.0/"),
    "16": ("CC BY-NC-ND 4.0", "https://creativecommons.org/licenses/by-nc-nd/4.0/"),
}
# largest first for full_url, 640/500 px for the thumbnail
FULL_SIZES = ("o", "k", "h", "l", "c", "z")
THUMB_SIZES = ("z", "m")
EXTRAS = "description,license,date_upload,date_taken,owner_name,geo,tags,media," + ",".join(f"url_{s}" for s in FULL_SIZES + ("m",))
_TAGS = re.compile(r"<[^>]+>")


def _float(value) -> float | None:
    try:
        number = float(value)
    except (TypeError, ValueError):
        return None
    return number


def parse_photo(item: dict) -> RawImage | None:
    license_ = LICENSES.get(str(item.get("license")))
    full_size = next((s for s in FULL_SIZES if item.get(f"url_{s}")), None)
    if license_ is None or full_size is None or item.get("media", "photo") != "photo":
        return None
    width, height = _float(item.get(f"width_{full_size}")), _float(item.get(f"height_{full_size}"))
    if width and height and min(width, height) < MIN_SIDE_PX:
        return None
    lat, lng = _float(item.get("latitude")), _float(item.get("longitude"))
    if lat == 0 and lng == 0:  # Flickr returns 0/0 for "no geo"
        lat = lng = None
    uploaded = unix_date(item.get("dateupload"))
    taken = normalize_date(str(item.get("datetaken", ""))[:10])
    # Flickr may synthesize datetaken from upload time when EXIF is absent. Equal values are upload-only.
    if str(item.get("datetakenunknown", "0")) == "1" or taken == uploaded:
        taken = None
    description = item.get("description")
    if isinstance(description, dict):
        description = description.get("_content", "")
    thumb = next((item[f"url_{s}"] for s in THUMB_SIZES if item.get(f"url_{s}")), None)
    owner = item.get("owner", "")
    return RawImage(
        id=f"flickr-{item['id']}",
        source="flickr",
        source_url=f"https://www.flickr.com/photos/{owner}/{item['id']}",
        source_domain="www.flickr.com",
        full_url=item[f"url_{full_size}"],
        thumb_url=thumb,
        title=item.get("title") or "",
        description=re.sub(r"\s+", " ", _TAGS.sub(" ", description or "")).strip(),
        source_categories=(item.get("tags") or "").split(),
        found_by="bbox",
        author=item.get("ownername") or None,
        license=license_[0],
        license_url=license_[1],
        date_taken=taken,
        date_uploaded=uploaded,
        date_source="source_metadata" if taken else "upload_only" if uploaded else "unknown",
        date_hint_year=text_year(item.get("title") or "", description or ""),
        lat=lat,
        lng=lng,
        width=int(width) if width else None,
        height=int(height) if height else None,
    )


async def collect(query: SourceQuery, client: httpx.AsyncClient, on_batch: OnBatch | None = None) -> SourceResult:
    async def work(acc: Batches, deadline: Deadline) -> str | None:
        if not settings.flickr_api_key:
            raise Skip("FLICKR_API_KEY is not set")
        bbox = query_bbox(query)
        if bbox is None:
            raise Skip("no coordinates for a bbox")
        async def search(recent: bool) -> None:
            for page in range(1, MAX_PAGES + 1):
                params = {
                    "method": "flickr.photos.search", "api_key": settings.flickr_api_key,
                    "bbox": ",".join(f"{v:.6f}" for v in bbox), "license": ",".join(LICENSES),
                    "content_type": 1, "media": "photos", "has_geo": 1, "extras": EXTRAS,
                    "sort": "date-taken-desc", "per_page": PER_PAGE, "page": page,
                    "format": "json", "nojsoncallback": 1,
                }
                if recent:
                    params["min_taken_date"] = "2024-01-01"
                resp = await request_with_retry(client, "GET", FLICKR_REST, deadline, "flickr", 2, params=params)
                resp.raise_for_status()
                data = resp.json()
                if data.get("stat") != "ok":
                    raise RuntimeError(f"Flickr {data.get('code')}: {data.get('message')}")
                photos = data.get("photos", {})
                for item in photos.get("photo", []):
                    if raw := parse_photo(item):
                        acc[raw.id] = raw
                acc.flush()
                if page >= int(photos.get("pages") or 0):
                    break

        await search(recent=True)
        if len(acc) < 15:
            await search(recent=False)
        return None

    return await run_collector("flickr", work, on_batch=on_batch)
