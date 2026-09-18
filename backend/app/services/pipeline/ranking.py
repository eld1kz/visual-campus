"""Trust-first, freshness-aware selection for a compact profile."""

from collections import defaultdict
from math import fsum

from app.config import settings
from app.models import Photo

TIER_RANK = {"verified": 2, "likely": 1, "unconfirmed": 0}
FRESHNESS_RANK = {"2024_plus": 4, "2020_2023": 3, "older": 2, "date_unknown": 1, "historic": 0}


def parse_targets(value: str) -> dict[str, int]:
    """`campus=12,dorms=6,…` → per-category count of reliable photos to keep."""
    targets: dict[str, int] = {}
    for part in value.split(","):
        name, _, count = part.strip().partition("=")
        if name and count.strip().isdigit():
            targets[name.strip()] = int(count)
    return targets


DEFAULT_TARGETS = parse_targets(settings.photo_targets)


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


def select_targets(photos: list[Photo], targets: dict[str, int] | None = None) -> list[Photo]:
    """Keep the `target` best reliable photos per category; unconfirmed photos are never dropped here.

    The contract (docs/CONTRACT.md §3) sends unconfirmed photos to the client, which hides them by default.
    Dropping them server-side would also throw away the recent photos that only lack strong metadata.
    """
    targets = targets or DEFAULT_TARGETS
    selected: list[Photo] = []
    grouped: dict[str, list[Photo]] = defaultdict(list)
    for photo in rank_photos(photos):
        grouped[photo.category].append(photo)
    for category, group in grouped.items():
        reliable = [p for p in group if p.tier != "unconfirmed"]
        target = targets.get(category, len(reliable))
        selected.extend(_diverse_top(reliable, target))
        selected.extend(p for p in group if p.tier == "unconfirmed")
    return rank_photos(selected)
