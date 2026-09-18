"""Build the shared, source-independent photo query plan."""

import math

from app.models import CampusShape
from app.services.pipeline.ranking import DEFAULT_TARGETS
from app.services.sources.base import SearchSubject, SourceQuery
from app.services.wikidata import UniversityRecord

LOCAL_LANGUAGE_CODES = ("ko", "ru", "kk")
MAX_SEARCH_NAMES = 16
MAX_CENTERS = 9


def _bbox(polygon: list[list[float]] | None) -> tuple[float, float, float, float] | None:
    if not polygon:
        return None
    xs, ys = [point[0] for point in polygon], [point[1] for point in polygon]
    return min(xs), min(ys), max(xs), max(ys)


def polygon_search_centers(
    polygon: list[list[float]] | None, lat: float | None, lng: float | None
) -> list[tuple[float, float, int]]:
    """Cover the campus bbox with up to 9 circles; callers still apply polygon containment."""
    bbox = _bbox(polygon)
    if bbox is None:
        return [(lat, lng, 1000)] if lat is not None and lng is not None else []
    west, south, east, north = bbox
    mid_lat, mid_lng = (south + north) / 2, (west + east) / 2
    height_m = (north - south) * 111_320
    width_m = (east - west) * 111_320 * max(math.cos(math.radians(mid_lat)), 0.01)
    nx = min(3, max(1, math.ceil(width_m / 1500)))
    ny = min(3, max(1, math.ceil(height_m / 1500)))
    radius = max(500, min(10_000, math.ceil(max(width_m / nx, height_m / ny) * 0.8)))
    return [
        (south + (iy + 0.5) * (north - south) / ny, west + (ix + 0.5) * (east - west) / nx, radius)
        for iy in range(ny) for ix in range(nx)
    ][:MAX_CENTERS]


def build_query_plan(uni: UniversityRecord, shape: CampusShape | None = None, discovered: list[dict] | None = None) -> SourceQuery:
    preferred = [uni.names_by_language.get(code) for code in ("en", *LOCAL_LANGUAGE_CODES)]
    names = list(dict.fromkeys(n for n in [uni.name_en, uni.name, *preferred, *uni.names] if n))[:MAX_SEARCH_NAMES]
    polygon = shape.polygon if shape else None
    subjects = [SearchSubject(
        qid=uni.wikidata_id, kind="university", names=names,
        commons_category=uni.commons_category, lat=uni.lat, lng=uni.lng,
    )]
    if shape:
        for building in shape.buildings:
            if not building.inside_campus or not building.name:
                continue
            subjects.append(SearchSubject(
                qid=None, kind="building", names=[building.name], building_type=building.type,
            ))
    for item in discovered or []:
        subjects.append(SearchSubject(**item))
    if uni.city_center:
        subjects.append(SearchSubject(
            qid=None, kind="city", names=[uni.city_center.name],
            lat=uni.city_center.lat, lng=uni.city_center.lng,
        ))
    return SourceQuery(
        wikidata_id=uni.wikidata_id,
        names=names,
        lat=uni.lat,
        lng=uni.lng,
        website=uni.website,
        commons_category=uni.commons_category,
        bbox=_bbox(polygon),
        polygon=polygon,
        geosearch_centers=polygon_search_centers(polygon, uni.lat, uni.lng),
        subjects=subjects,
        category_targets=dict(DEFAULT_TARGETS),
    )
