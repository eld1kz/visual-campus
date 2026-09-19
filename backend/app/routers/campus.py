"""GET /campus/{wikidata_id} — map data (docs/CONTRACT.md §4)."""

from typing import Literal

import httpx
from fastapi import APIRouter, Path, Query
from fastapi.responses import JSONResponse

from app.config import settings
from app.models import (
    Building, CampusInfo, CampusMapResponse, CampusShape, ErrorResponse, LatLng, PanoramaStart, Panoramas, Photo, PhotoPin,
    SourceStatus,
)
from app.services import cache
from app.services.orchestrator import (
    SOURCE_TIMEOUT_S, WIKIDATA_TIMEOUT_S, search_names, to_university,
)
from app.services.pipeline.scoring import building_at, distance_m
from app.services.sources import osm, run_source
from app.services.sources.base import SourceQuery
from app.services.wikidata import get_university

router = APIRouter(tags=["campus"])


def no_panoramas() -> Panoramas:
    """No panorama provider is checked yet (no MAPILLARY_TOKEN / KAKAO_API_KEY): say so, do not guess."""
    return Panoramas(provider=None, available=False, checked_providers=[], start=None)


MAX_WALK_POINTS = 300


def mapillary_panoramas(photos: list[Photo], lat: float, lng: float) -> Panoramas:
    """Walk mode from the Mapillary images the profile already collected; start at the one nearest the centre."""
    if not settings.mapillary_token:
        return no_panoramas()
    points = [
        PanoramaStart(lat=p.lat, lng=p.lng, captured_at=p.date_taken, image_id=p.id.removeprefix("mapillary-"))
        for p in photos if p.id.startswith("mapillary-") and p.lat is not None and p.lng is not None
    ][:MAX_WALK_POINTS]
    if not points:
        return Panoramas(provider=None, available=False, checked_providers=["mapillary"], start=None)
    start = min(points, key=lambda s: distance_m(lat, lng, s.lat, s.lng))
    return Panoramas(provider="mapillary", available=True, checked_providers=["mapillary"], start=start, points=points)


def link_photos(buildings: list[Building], photos: list[Photo]) -> tuple[list[Building], list[PhotoPin]]:
    """Pins for geotagged photos; each pin gets the building its point falls into, buildings get photo_ids."""
    photo_ids: dict[str, list[str]] = {b.id: [] for b in buildings}
    pins = []
    for p in photos:
        if p.lat is None or p.lng is None:
            continue
        building = building_at(p.lat, p.lng, buildings)
        if building is not None:
            photo_ids[building.id].append(p.id)
        pins.append(PhotoPin(
            photo_id=p.id, lat=p.lat, lng=p.lng, heading_deg=p.heading_deg, tier=p.tier,
            confidence=p.confidence, thumb_url=p.thumb_url, building_id=building.id if building else None,
        ))
    linked = [b.model_copy(update={"photo_ids": photo_ids[b.id]}) for b in buildings]
    return linked, pins


def error(status: int, detail: str, state: str | None = None) -> JSONResponse:
    sources = [SourceStatus(name="wikidata", status=state)] if state else []
    return JSONResponse(status_code=status, content=ErrorResponse(detail=detail, sources_status=sources).model_dump())


@router.get(
    "/campus/{wikidata_id}",
    response_model=CampusMapResponse,
    responses={
        404: {"model": ErrorResponse, "description": "No Wikidata item with this ID, or it has no coordinates"},
        503: {"model": ErrorResponse, "description": "Wikidata is unavailable"},
    },
)
async def get_campus(
    wikidata_id: str = Path(pattern=r"^Q\d+$", description="Wikidata ID from /resolve, e.g. Q39997"),
    lang: Literal["ru", "en"] = Query(default="ru", description="Language of the city centre name"),
):
    cached = cache.get_profile(wikidata_id, lang) or cache.any_profile(wikidata_id)
    shape: CampusShape | None = cache.get_shape(wikidata_id)
    university = cached.profile.university if cached else None

    if university is None or shape is None:
        async with httpx.AsyncClient(
            timeout=SOURCE_TIMEOUT_S, headers={"User-Agent": settings.user_agent}, follow_redirects=True
        ) as client:
            state, record = await run_source("wikidata", get_university(client, wikidata_id, lang), WIKIDATA_TIMEOUT_S)
            if state != "ok":
                return error(503, "Wikidata is unavailable right now, so the campus map cannot be built. Try again later.", state)
            if record is None:
                return error(404, f"No university found for Wikidata ID {wikidata_id}.")
            if record.lat is None or record.lng is None:
                return error(404, f"Wikidata item {wikidata_id} has no coordinates, so there is no campus map.")
            if shape is None:
                query = SourceQuery(
                    wikidata_id=wikidata_id, names=search_names(record), lat=record.lat, lng=record.lng,
                    website=record.website, commons_category=record.commons_category,
                )
                result, shape = await osm.find_campus(query, client)
                if shape is not None:
                    cache.put_shape(wikidata_id, shape, complete=result.status == "ok" and result.detail is None)
        if university is None:
            university = to_university(record, shape)

    if university.lat is None or university.lng is None:
        return error(404, f"Wikidata item {wikidata_id} has no coordinates, so there is no campus map.")
    buildings, pins = link_photos(shape.buildings if shape else [], cached.profile.photos if cached else [])
    return CampusMapResponse(
        campus=CampusInfo(
            center=LatLng(lat=university.lat, lng=university.lng),
            polygon=shape.polygon if shape else None,
            area_km2=shape.area_km2 if shape else None,
            city_center=university.city_center,
            distance_to_center_km=university.distance_to_center_km,
            transit=[],
        ),
        buildings=buildings,
        photo_pins=pins,
        panoramas=mapillary_panoramas(cached.profile.photos if cached else [], university.lat, university.lng),
    )
