"""Trust-first, freshness-aware selection for a compact profile."""

from collections import defaultdict
from math import fsum

from app.models import Photo

TIER_RANK = {"verified": 2, "likely": 1, "unconfirmed": 0}
FRESHNESS_RANK = {"2024_plus": 4, "2020_2023": 3, "older": 2, "date_unknown": 1, "historic": 0}
DEFAULT_TARGETS = {"campus": 6, "dorms": 3, "classrooms": 2, "libraries": 2, "city": 2}


def rank_key(photo: Photo) -> tuple[int, int, int, int, int]:
    # Confidence bands keep trust dominant while allowing freshness to order near-equal candidates.
    return (
        TIER_RANK[photo.tier],
        photo.confidence // 5,
        FRESHNESS_RANK[photo.freshness],
        photo.confidence,
        (photo.width if hasattr(photo, "width") else 0) or 0,
    )


def rank_photos(photos: list[Photo]) -> list[Photo]:
    return sorted(photos, key=rank_key, reverse=True)


def _similarity(a: tuple[float, ...], b: tuple[float, ...]) -> float:
    return fsum(x * y for x, y in zip(a, b))


def _diverse_top(photos: list[Photo], count: int) -> list[Photo]:
    """MMR tie-break among equally trusted/fresh candidates; stronger evidence always wins first."""
    from app.services.pipeline.vision import embedding_for_url

    remaining = rank_photos(photos)
    selected: list[Photo] = []
    while remaining and len(selected) < count:
        best_key = rank_key(remaining[0])[:4]
        bucket = [photo for photo in remaining if rank_key(photo)[:4] == best_key]
        if selected and len(bucket) > 1:
            selected_embeddings = [embedding_for_url(photo.full_url) for photo in selected]
            selected_embeddings = [value for value in selected_embeddings if value is not None]
            if selected_embeddings:
                bucket.sort(key=lambda photo: max(
                    (_similarity(embedding_for_url(photo.full_url), other)
                     for other in selected_embeddings if embedding_for_url(photo.full_url) is not None),
                    default=0,
                ))
        chosen = bucket[0]
        selected.append(chosen)
        remaining.remove(chosen)
    return selected


def select_targets(photos: list[Photo], targets: dict[str, int] | None = None, include_unconfirmed: bool = False) -> list[Photo]:
    targets = targets or DEFAULT_TARGETS
    selected: list[Photo] = []
    grouped: dict[str, list[Photo]] = defaultdict(list)
    for photo in rank_photos(photos):
        grouped[photo.category].append(photo)
    for category, target in targets.items():
        reliable = [p for p in grouped[category] if p.tier != "unconfirmed"]
        chosen = _diverse_top(reliable, target)
        if include_unconfirmed and len(chosen) < target:
            chosen += _diverse_top(
                [p for p in grouped[category] if p.tier == "unconfirmed"], target - len(chosen)
            )
        selected.extend(chosen)
    return rank_photos(selected)
