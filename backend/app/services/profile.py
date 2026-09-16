"""Build a verified campus profile: Wikidata → (OSM campus ∥ Commons photos ∥ Wikipedia) → evidence scoring."""

import asyncio
import time
from datetime import date

import httpx
from shapely.geometry import MultiPolygon
from shapely.geometry.base import BaseGeometry

from app.config import settings
from app.models import (
    Citation, DuplicatePhoto, Evidence, Photo, Place, ProfileResponse, ProfileSourceStatus, ProfileStats,
    ProfileUniversity, Summary,
)
from app.services.commons import collect_files
from app.services.evidence import CampusContext, Evaluation, deduplicate, evaluate
from app.services.osm import Campus, distance_m, find_campus
from app.services.sources import run_source
from app.services.wikidata import UniversityRecord, get_university
from app.services.wikipedia import WikiSummary, summary

WIKIDATA_TIMEOUT_S = 8
OSM_TIMEOUT_S = 10
COMMONS_TIMEOUT_S = 15
WIKIPEDIA_TIMEOUT_S = 6
NEARBY_RADIUS_M = 1000
CACHE_TTL_S = 30 * 60
COMMONS_DOMAIN = "commons.wikimedia.org"

_cache: dict[tuple[str, str], tuple[float, ProfileResponse]] = {}


class UniversityNotFound(Exception):
    pass


class ProfileUnavailable(Exception):
    pass


def polygon_coords(geometry: BaseGeometry | None) -> list[list[float]] | None:
    """Outer ring of the (largest) campus polygon as [[lng, lat], ...]."""
    if geometry is None:
        return None
    if isinstance(geometry, MultiPolygon):
        geometry = max(geometry.geoms, key=lambda g: g.area)
    return [[round(x, 6), round(y, 6)] for x, y in geometry.exterior.coords]


def build_citations(wiki: WikiSummary | None, qid: str, campus: Campus | None) -> list[Citation]:
    sources = []
    if wiki:
        sources.append((f"Wikipedia — {wiki.title}", wiki.url))
    sources.append((f"Wikidata — {qid}", f"https://www.wikidata.org/wiki/{qid}"))
    if campus:
        sources.append((f"OpenStreetMap — {campus.name or 'campus'}", campus.osm_url))
    return [Citation(n=i, title=title, url=url) for i, (title, url) in enumerate(sources, start=1)]


def to_photo(ev: Evaluation, today: date) -> Photo:
    f = ev.file
    return Photo(
        id=f"commons-{f.pageid}",
        thumb_url=f.thumb_url,
        full_url=f.full_url,
        category=ev.category,
        tags=ev.tags,
        confidence=ev.confidence,
        tier=ev.tier,
        source_url=f.page_url,
        source_domain=COMMONS_DOMAIN,
        author=f.author,
        license=f.license or "unknown",
        published_at=f.date_taken or f.uploaded,
        retrieved_at=today.isoformat(),
        lat=f.lat,
        lng=f.lng,
        evidence=[Evidence(**e) for e in ev.evidence],
        duplicates=[DuplicatePhoto(id=f"commons-{d.pageid}", thumb_url=d.thumb_url, source_url=d.page_url) for d in ev.duplicates],
    )


def compute_stats(photos: list[Photo]) -> ProfileStats:
    return ProfileStats(
        photos=len(photos),
        verified=sum(p.tier == "verified" for p in photos),
        likely=sum(p.tier == "likely" for p in photos),
        hidden=sum(p.tier == "unconfirmed" for p in photos),
        duplicates=sum(len(p.duplicates) for p in photos),
    )


def _university(uni: UniversityRecord, campus: Campus | None) -> ProfileUniversity:
    center = uni.city_center
    distance = None
    if center and uni.lat is not None and uni.lng is not None:
        distance = round(distance_m(uni.lat, uni.lng, center.lat, center.lng) / 1000, 1)
    return ProfileUniversity(
        id=uni.wikidata_id,
        name=uni.name,
        aliases=[n for n in uni.names if n != uni.name][:20],
        city=center.name if center else uni.city,
        country=uni.country,
        website=uni.website,
        lat=uni.lat,
        lng=uni.lng,
        campus_polygon=polygon_coords(campus.geometry if campus else None),
        campus_area_km2=campus.area_km2 if campus else None,
        distance_to_center_km=distance,
        city_center=Place(name=center.name, lat=center.lat, lng=center.lng) if center else None,
        wikidata_id=uni.wikidata_id,
        ror_id=uni.ror_id,
        commons_category=uni.commons_category,
        osm_url=campus.osm_url if campus else None,
    )


async def build_profile(qid: str, lang: str) -> ProfileResponse:
    cached = _cache.get((qid, lang))
    if cached and cached[0] > time.monotonic():
        return cached[1]

    started = time.perf_counter()
    today = date.today()
    async with httpx.AsyncClient(
        timeout=COMMONS_TIMEOUT_S, headers={"User-Agent": settings.user_agent}, follow_redirects=True
    ) as client:
        wd_state, uni = await run_source("wikidata", get_university(client, qid, lang), WIKIDATA_TIMEOUT_S)
        if wd_state != "ok":
            raise ProfileUnavailable(f"Wikidata {wd_state}")
        if uni is None:
            raise UniversityNotFound(qid)

        has_point = uni.lat is not None and uni.lng is not None
        (osm_state, campus), (commons_state, files), (wiki_state, wiki) = await asyncio.gather(
            run_source("openstreetmap", find_campus(client, qid, uni.name_en, uni.names, uni.lat, uni.lng), OSM_TIMEOUT_S)
            if has_point else _skipped(),
            run_source(
                "wikimedia_commons",
                collect_files(client, uni.commons_category, uni.lat, uni.lng, NEARBY_RADIUS_M),
                COMMONS_TIMEOUT_S,
            ),
            run_source("wikipedia", summary(client, uni.wikipedia_titles, lang), WIKIPEDIA_TIMEOUT_S),
        )

    ctx = CampusContext(
        names=uni.names, lat=uni.lat, lng=uni.lng, geometry=campus.geometry if campus else None, today=today, lang=lang
    )
    evaluations = [ev for f in files or [] if (ev := evaluate(f, ctx))]
    kept = sorted(deduplicate(evaluations), key=lambda e: e.confidence, reverse=True)
    photos = [to_photo(ev, today) for ev in kept]

    response = ProfileResponse(
        university=_university(uni, campus),
        generated_in_ms=round((time.perf_counter() - started) * 1000),
        sources_status=[
            ProfileSourceStatus(name="wikidata", status=wd_state, count=1),
            ProfileSourceStatus(name="openstreetmap", status=osm_state, count=1 if campus else 0),
            ProfileSourceStatus(name="wikimedia_commons", status=commons_state, count=len(photos)),
            ProfileSourceStatus(name="wikipedia", status=wiki_state, count=1 if wiki else 0),
        ],
        summary=Summary(text=wiki.text if wiki else "", citations=build_citations(wiki, qid, campus)),
        stats=compute_stats(photos),
        photos=photos,
    )
    _cache[(qid, lang)] = (time.monotonic() + CACHE_TTL_S, response)
    return response


async def _skipped() -> tuple[str, None]:
    return "ok", None
