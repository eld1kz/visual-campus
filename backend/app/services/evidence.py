"""Legacy adapter: the old CommonsFile API used by services/profile.py, on top of the new pipeline.

CommonsFile → RawImage → pipeline.score / pipeline.Deduplicator. Remove once profile.py moves to the orchestrator.
"""

from dataclasses import dataclass, field
from datetime import date

from shapely.geometry.base import BaseGeometry

from app.models import Photo, RawImage
from app.services import pipeline
from app.services.commons import CommonsFile

COMMONS_DOMAIN = "commons.wikimedia.org"


@dataclass
class CampusContext:
    names: list[str]
    lat: float | None
    lng: float | None
    geometry: BaseGeometry | None
    today: date
    lang: str = "ru"


@dataclass
class Evaluation:
    file: CommonsFile
    evidence: list[dict]
    confidence: int
    tier: str
    category: str
    tags: list[str]
    duplicates: list[CommonsFile] = field(default_factory=list)


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
        found_by="geosearch" if f.found_nearby and not f.via_category else "category",
        author=f.author if f.author and f.author != "—" else None,
        license=f.license,
        published_at=f.date_taken or f.uploaded,
        lat=f.lat,
        lng=f.lng,
        sha1=f.sha1 or None,
    )


def evaluate(f: CommonsFile, ctx: CampusContext) -> Evaluation | None:
    """None when the file is not a photo of a place."""
    new_ctx = pipeline.CampusContext(
        names=ctx.names, lat=ctx.lat, lng=ctx.lng, polygon=ctx.geometry, today=ctx.today, lang=ctx.lang
    )
    raw = to_raw(f)
    # The old API dated photos by date_taken only; uploads are not "old snapshots".
    photo = pipeline.score(raw.model_copy(update={"published_at": f.date_taken}), new_ctx)
    if photo is None:
        return None
    return Evaluation(
        file=f,
        evidence=[e.model_dump() for e in photo.evidence],
        confidence=photo.confidence,
        tier=photo.tier,
        category=photo.category,
        tags=list(photo.tags),
    )


def deduplicate(evaluations: list[Evaluation]) -> list[Evaluation]:
    """Identical files (same SHA-1) or crops/edits of the same title keep only the most confident copy."""
    by_id = {f"commons-{ev.file.pageid}": ev for ev in evaluations}
    dedup = pipeline.Deduplicator()
    for photo_id, ev in by_id.items():
        raw = to_raw(ev.file)
        placeholder = _placeholder(photo_id, ev, raw)
        dedup.add(placeholder, raw)
    kept = []
    for photo in dedup.photos():
        ev = by_id[photo.id]
        ev.duplicates.extend(by_id[d.id].file for d in photo.duplicates)
        kept.append(ev)
    return kept


def _placeholder(photo_id: str, ev: Evaluation, raw: RawImage) -> Photo:
    return Photo(
        id=photo_id, thumb_url=raw.thumb_url, full_url=raw.full_url, category=ev.category, tags=ev.tags,
        confidence=ev.confidence, tier=ev.tier, source_url=raw.source_url, source_domain=raw.source_domain,
        author=raw.author or "unknown", license=raw.license or "unknown", published_at=raw.published_at,
        retrieved_at="", lat=raw.lat, lng=raw.lng, evidence=[], duplicates=[],
    )
