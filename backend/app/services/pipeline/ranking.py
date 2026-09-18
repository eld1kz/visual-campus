"""Trust-first, freshness-aware selection for a compact profile."""

from collections import defaultdict
from math import fsum

from app.config import settings
from app.models import Photo

TIER_RANK = {"verified": 2, "likely": 1, "unconfirmed": 0}
# Added to confidence for ordering only (never to the tier): a recent likely photo can precede a 2011 verified one.
FRESHNESS_BONUS = {"2024_plus": 20, "2020_2023": 10, "older": -5, "date_unknown": -5, "historic": -10}


def parse_targets(value: str) -> dict[str, int]:
    """`campus=12,dorms=6,…` → per-category count of reliable photos to keep."""
    targets: dict[str, int] = {}
    for part in value.split(","):
        name, _, count = part.strip().partition("=")
        if name and count.strip().isdigit():
            targets[name.strip()] = int(count)
    return targets


DEFAULT_TARGETS = parse_targets(settings.photo_targets)


def rank_key(photo: Photo) -> tuple[int, int, int]:
    """Reliable photos first; within them confidence plus a freshness bonus; unconfirmed always last."""
    return (
        int(photo.tier != "unconfirmed"),
        photo.confidence + FRESHNESS_BONUS[photo.freshness],
        photo.confidence,
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
        best_key = rank_key(remaining[0])[:2]
        bucket = [photo for photo in remaining if rank_key(photo)[:2] == best_key]
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
    targets = DEFAULT_TARGETS if targets is None else targets
    selected: list[Photo] = []
    grouped: dict[str, list[Photo]] = defaultdict(list)
    for photo in rank_photos(photos):
        grouped[photo.category].append(photo)
    for category, group in grouped.items():
        reliable = [p for p in group if p.tier != "unconfirmed"]
        target = targets.get(category)
        # No target: every reliable photo is kept (the client pages the grid with "Show more").
        selected.extend(reliable if target is None else _diverse_top(reliable, target))
        selected.extend(p for p in group if p.tier == "unconfirmed")
    return showcase_order(selected)


SHOWCASE_CATEGORIES = ["campus", "dorms", "classrooms", "libraries", "city"]
MAX_HIGHLIGHTS = 4


def showcase_order(photos: list[Photo]) -> list[Photo]:
    """Order for the default view: a few showcase views first (main building, gate, overview), then the reliable
    photos round-robin across categories so the grid is not 30 campus shots in a row, then unconfirmed ones.

    Within a category the rank order holds; a photo from the same source page as the previous one waits a turn.
    """
    ranked = rank_photos(photos)
    reliable = [p for p in ranked if p.tier != "unconfirmed"]
    highlights: list[Photo] = []
    # Dashcam street-level frames are real but poor showcase shots: ordinary photos come first.
    for photo in sorted(reliable, key=lambda p: p.source_domain == "www.mapillary.com"):
        if photo.highlight and len(highlights) < MAX_HIGHLIGHTS and \
                all(photo.source_url != h.source_url for h in highlights):
            highlights.append(photo)
    chosen = {p.id for p in highlights}
    queues = {c: [p for p in reliable if p.category == c and p.id not in chosen] for c in SHOWCASE_CATEGORIES}
    queues.update({c: [p for p in reliable if p.category == c]
                   for c in {p.category for p in reliable} - set(SHOWCASE_CATEGORIES)})
    ordered = list(highlights)
    while any(queues.values()):
        for queue in queues.values():
            if not queue:
                continue
            last = ordered[-1].source_url if ordered else None
            index = next((i for i, p in enumerate(queue) if p.source_url != last), 0)
            ordered.append(queue.pop(index))
    return ordered + [p for p in ranked if p.tier == "unconfirmed"]
