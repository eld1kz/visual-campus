"""Mapillary: street-level images inside the campus bbox (Graph API v4 /images). Needs MAPILLARY_TOKEN.

Written against https://www.mapillary.com/developer/api-documentation (Image entity); not verified live (no token).
"""

import math
from datetime import datetime, timezone

import httpx

from app.config import settings
from app.models import RawImage, SourceResult
from app.services.sources.base import Deadline, Skip, SourceQuery, query_bbox, run_collector

GRAPH_IMAGES = "https://graph.mapillary.com/images"
LIMIT = 500
MAX_BBOX_DEG2 = 0.01  # API rejects larger bbox queries
FIELDS = "id,captured_at,compass_angle,computed_compass_angle,geometry,computed_geometry,creator,width,height,is_pano,thumb_1024_url,thumb_original_url"
# Mapillary publishes all imagery under CC BY-SA 4.0 (Mapillary Terms / open data licence).
LICENSE = ("CC BY-SA 4.0", "https://creativecommons.org/licenses/by-sa/4.0/")


def clamp_bbox(bbox: tuple[float, float, float, float]) -> tuple[float, float, float, float]:
    west, south, east, north = bbox
    area = (east - west) * (north - south)
    if area <= MAX_BBOX_DEG2:
        return bbox
    k = math.sqrt(MAX_BBOX_DEG2 / area) * 0.99
    cx, cy = (west + east) / 2, (south + north) / 2
    hw, hh = (east - west) / 2 * k, (north - south) / 2 * k
    return (cx - hw, cy - hh, cx + hw, cy + hh)


def parse_image(item: dict) -> RawImage | None:
    geometry = item.get("computed_geometry") or item.get("geometry") or {}
    coords = geometry.get("coordinates") or [None, None]
    full = item.get("thumb_original_url") or item.get("thumb_1024_url")
    if not full or "id" not in item:
        return None
    heading = item.get("computed_compass_angle", item.get("compass_angle"))
    captured = item.get("captured_at")
    published = (
        datetime.fromtimestamp(int(captured) / 1000, tz=timezone.utc).date().isoformat() if captured is not None else None
    )
    return RawImage(
        id=f"mapillary-{item['id']}",
        source="mapillary",
        source_url=f"https://www.mapillary.com/app/?pKey={item['id']}",
        source_domain="www.mapillary.com",
        full_url=full,
        thumb_url=item.get("thumb_1024_url"),
        found_by="bbox",
        author=(item.get("creator") or {}).get("username") or None,
        license=LICENSE[0],
        license_url=LICENSE[1],
        published_at=published,
        lat=coords[1],
        lng=coords[0],
        heading_deg=round(float(heading) % 360, 1) if heading is not None else None,
        width=item.get("width"),
        height=item.get("height"),
    )


async def collect(query: SourceQuery, client: httpx.AsyncClient) -> SourceResult:
    async def work(acc: dict[str, RawImage], deadline: Deadline) -> str | None:
        if not settings.mapillary_token:
            raise Skip("MAPILLARY_TOKEN is not set")
        bbox = query_bbox(query)
        if bbox is None:
            raise Skip("no coordinates for a bbox")
        resp = await client.get(GRAPH_IMAGES, timeout=deadline.left(), params={
            "access_token": settings.mapillary_token, "fields": FIELDS, "limit": LIMIT,
            "bbox": ",".join(f"{v:.6f}" for v in clamp_bbox(bbox)),
        })
        resp.raise_for_status()
        for item in resp.json().get("data", []):
            if raw := parse_image(item):
                acc[raw.id] = raw
        return None

    return await run_collector("mapillary", work)
