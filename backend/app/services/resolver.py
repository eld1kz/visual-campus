"""Resolve a free-text university name via ROR + Wikidata in parallel."""

import asyncio
import math
import time
from dataclasses import dataclass, field

import httpx

from app.config import settings
from app.models import ResolveResponse, SourceStatus, UniversityCandidate
from app.services.hits import SourceHit
from app.services.ror import search_ror
from app.services.sources import run_source
from app.services.text import best_similarity, normalize
from app.services.wikidata import WikidataResult, search_wikidata

MAX_CANDIDATES = 5
MIN_NAME_SIMILARITY = 0.6
RESOLVE_MIN_NAME_SIMILARITY = 0.9
RESOLVE_MIN_SCORE = 0.7
RESOLVE_MIN_GAP = 0.1
# Below this the best candidate only shares generic words ("Technical University of …"): say not found.
NOT_FOUND_BELOW_SCORE = 0.55
SAME_PLACE_KM = 15


class AllSourcesFailed(Exception):
    def __init__(self, sources_status: list[SourceStatus]):
        super().__init__("All sources failed")
        self.sources_status = sources_status


@dataclass
class Merged:
    ror: SourceHit | None = None
    wikidata: SourceHit | None = None
    name_similarity: float = 0.0
    score: float = 0.0
    wikidata_ids: list[str] = field(default_factory=list)

    @property
    def hits(self) -> list[SourceHit]:
        return [h for h in (self.ror, self.wikidata) if h]

    @property
    def ror_id(self) -> str | None:
        return (self.ror and self.ror.ror_id) or (self.wikidata and self.wikidata.ror_id)

    def to_candidate(self) -> UniversityCandidate:
        primary = self.ror or self.wikidata
        wd = self.wikidata
        names = [h.name for h in self.hits] + [a for h in self.hits for a in h.aliases]
        aliases = [n for n in dict.fromkeys(names) if n != primary.name]
        wikidata_id = (wd and wd.wikidata_ids[0]) or next(iter(self.wikidata_ids), None)
        # Wikidata P625 is the campus point; ROR coordinates are the city centroid.
        coords_from = wd if wd and wd.lat is not None else primary
        return UniversityCandidate(
            id=self.ror_id or wikidata_id or normalize(primary.name).replace(" ", "-"),
            name=primary.name,
            aliases=aliases[:12],
            city=(self.ror and self.ror.city) or (wd and wd.city),
            country=(self.ror and self.ror.country) or (wd and wd.country),
            lat=coords_from.lat,
            lng=coords_from.lng,
            website=(self.ror and self.ror.website) or (wd and wd.website),
            wikidata_id=wikidata_id,
            ror_id=self.ror_id,
            commons_category=wd.commons_category if wd else None,
            match_score=round(min(self.score, 1.0), 3),
        )


def _distance_km(a: SourceHit, b: SourceHit) -> float | None:
    if None in (a.lat, a.lng, b.lat, b.lng):
        return None
    lat1, lng1, lat2, lng2 = map(math.radians, (a.lat, a.lng, b.lat, b.lng))
    h = math.sin((lat2 - lat1) / 2) ** 2 + math.cos(lat1) * math.cos(lat2) * math.sin((lng2 - lng1) / 2) ** 2
    return 6371 * 2 * math.asin(math.sqrt(h))


def _same_org(group: Merged, wd: SourceHit) -> bool:
    ror = group.ror
    if ror is None:
        return False
    if wd.ror_id and wd.ror_id == ror.ror_id:
        return True
    if set(wd.wikidata_ids) & set(ror.wikidata_ids):
        return True
    ror_names = {normalize(n) for n in [ror.name, *ror.aliases]}
    if normalize(wd.name) in ror_names:
        distance = _distance_km(ror, wd)
        return distance is not None and distance <= SAME_PLACE_KM
    return False


def merge(ror_hits: list[SourceHit], wd_hits: list[SourceHit]) -> list[Merged]:
    groups = [Merged(ror=h, wikidata_ids=list(h.wikidata_ids)) for h in ror_hits]
    for wd in wd_hits:
        target = next((g for g in groups if g.wikidata is None and _same_org(g, wd)), None)
        if target:
            target.wikidata = wd
        else:
            groups.append(Merged(wikidata=wd, wikidata_ids=list(wd.wikidata_ids)))
    return groups


def score(group: Merged, query: str, corrected_query: str | None) -> None:
    names = [n for h in group.hits for n in [h.name, *h.aliases]]
    similarity = best_similarity(query, names)
    if corrected_query:
        similarity = max(similarity, 0.95 * best_similarity(corrected_query, names))
    if group.ror and group.ror.chosen:
        similarity = max(similarity, 0.95)
    group.name_similarity = similarity

    sitelinks = group.wikidata.sitelinks if group.wikidata else 0
    popularity = min(1.0, math.log1p(sitelinks) / math.log1p(150))
    both_sources = 1.0 if group.ror and group.wikidata else 0.0
    group.score = 0.55 * similarity + 0.15 * both_sources + 0.3 * popularity


def _query_is_a_city(query: str, groups: list[Merged]) -> bool:
    q = normalize(query)
    return any(h.city and normalize(h.city) == q for g in groups for h in g.hits)


def decide(groups: list[Merged], query: str) -> tuple[str, list[Merged]]:
    ranked = sorted(
        (g for g in groups if g.name_similarity >= MIN_NAME_SIMILARITY),
        key=lambda g: g.score,
        reverse=True,
    )
    if not ranked or ranked[0].score < NOT_FOUND_BELOW_SCORE:
        return "not_found", []
    best = ranked[0]
    gap = best.score - ranked[1].score if len(ranked) > 1 else 1.0
    # "Cambridge" names a city with many institutions, even if one of them has it as an alias.
    names_a_city = _query_is_a_city(query, ranked) and normalize(query) != normalize(best.hits[0].name)
    if (
        not names_a_city
        and best.name_similarity >= RESOLVE_MIN_NAME_SIMILARITY
        and best.score >= RESOLVE_MIN_SCORE
        and gap >= RESOLVE_MIN_GAP
    ):
        return "resolved", ranked[:MAX_CANDIDATES]
    return "ambiguous", ranked[:MAX_CANDIDATES]


async def _run_source(name: str, coro) -> tuple[SourceStatus, object]:
    state, result = await run_source(name, coro, settings.source_timeout_s)
    return SourceStatus(name=name, status=state), result


async def resolve(query: str) -> ResolveResponse:
    started = time.perf_counter()
    async with httpx.AsyncClient(
        timeout=settings.source_timeout_s,
        headers={"User-Agent": settings.user_agent},
        follow_redirects=True,
    ) as client:
        (ror_status, ror_hits), (wd_status, wd_result) = await asyncio.gather(
            _run_source("ror", search_ror(client, query)),
            _run_source("wikidata", search_wikidata(client, query)),
        )
        ror_hits = ror_hits or []
        wd_result = wd_result or WikidataResult()
        corrected = wd_result.corrected_query

        # ROR is not typo-tolerant: retry it with Wikipedia's spelling suggestion.
        if corrected and ror_status.status == "ok" and not ror_hits:
            ror_status, retry_hits = await _run_source("ror", search_ror(client, corrected))
            ror_hits = retry_hits or []

    sources_status = [ror_status, wd_status]
    if all(s.status != "ok" for s in sources_status):
        raise AllSourcesFailed(sources_status)

    groups = merge(ror_hits, wd_result.hits)
    for group in groups:
        score(group, query, corrected)
    status, ranked = decide(groups, query)
    candidates = [g.to_candidate() for g in ranked]

    return ResolveResponse(
        query=query,
        corrected_query=corrected,
        status=status,
        university=candidates[0] if status == "resolved" else None,
        candidates=candidates,
        sources_status=sources_status,
        took_ms=round((time.perf_counter() - started) * 1000),
    )
