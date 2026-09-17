"""Shared pieces of the image collectors (docs/CONTRACT.md §6)."""

import asyncio
import logging
import math
import time
from collections.abc import Awaitable, Callable
from dataclasses import dataclass

import httpx

from app.models import RawImage, SourceName, SourceResult

logger = logging.getLogger("visual_campus.sources")

# Contract: ≤ 8 s per source. Stop a little earlier so an outer 8 s wrapper never cuts us first.
SOURCE_BUDGET_S = 7.5
MIN_SIDE_PX = 200  # smaller files are icons/thumbnails, not photos of a place


@dataclass
class SourceQuery:
    wikidata_id: str
    names: list[str]
    lat: float | None
    lng: float | None
    website: str | None
    commons_category: str | None
    bbox: tuple[float, float, float, float] | None = None  # (west, south, east, north)


class Skip(Exception):
    """Raised by a collector that honestly cannot run (no API key, no coordinates)."""


class Deadline:
    def __init__(self, budget_s: float) -> None:
        self.end = time.monotonic() + budget_s

    def left(self, floor: float = 0.5) -> float:
        return max(self.end - time.monotonic(), floor)


def elapsed_ms(started: float) -> int:
    return round((time.perf_counter() - started) * 1000)


def point_bbox(lat: float, lng: float, half_km: float) -> tuple[float, float, float, float]:
    dlat = half_km / 111.32
    dlng = half_km / (111.32 * max(math.cos(math.radians(lat)), 0.01))
    return (lng - dlng, lat - dlat, lng + dlng, lat + dlat)


def query_bbox(query: SourceQuery, half_km: float = 0.6) -> tuple[float, float, float, float] | None:
    if query.bbox:
        return query.bbox
    if query.lat is not None and query.lng is not None:
        return point_bbox(query.lat, query.lng, half_km)
    return None


OnBatch = Callable[[list[RawImage]], None]


class Batches(dict[str, RawImage]):
    """Results so far, keyed by id. `flush()` hands the images added or replaced since the last flush to `on_batch`."""

    def __init__(self, name: str, on_batch: OnBatch | None) -> None:
        super().__init__()
        self._name = name
        self._on_batch = on_batch
        self._pending: dict[str, None] = {}  # ordered set of ids

    def __setitem__(self, key: str, value: RawImage) -> None:
        super().__setitem__(key, value)
        self._pending[key] = None

    def setdefault(self, key: str, default: RawImage) -> RawImage:  # dict.setdefault bypasses __setitem__
        if key not in self:
            self[key] = default
        return self[key]

    def flush(self) -> None:
        if not self._pending:
            return
        batch = [self[key] for key in self._pending]
        self._pending = {}
        if self._on_batch is None:
            return
        try:
            self._on_batch(batch)
        except Exception:  # a consumer bug must not turn the source into an error
            logger.exception("on_batch callback of %s failed", self._name)


async def run_collector(
    name: SourceName,
    work: Callable[[Batches, Deadline], Awaitable[str | None]],
    budget_s: float = SOURCE_BUDGET_S,
    on_batch: OnBatch | None = None,
) -> SourceResult:
    """Run `work` under the source budget. `work` fills `acc` as results arrive, so a timeout keeps them.

    `work` calls `acc.flush()` whenever a batch is ready; whatever is left unflushed is flushed here before returning,
    so the batches (last version per id) always add up to `SourceResult.images`.
    Partial results at the deadline are reported as `ok` (with a detail), an empty timeout as `timeout`.
    """
    acc = Batches(name, on_batch)
    started = time.perf_counter()
    detail: str | None = None
    try:
        detail = await asyncio.wait_for(work(acc, Deadline(budget_s)), timeout=budget_s)
        status = "ok"
    except Skip as exc:
        status, detail = "skipped", str(exc)
    except (asyncio.TimeoutError, httpx.TimeoutException):
        status = "ok" if acc else "timeout"
        detail = f"budget {budget_s:g} s reached" + (f", partial: {len(acc)} images" if acc else "")
    except Exception as exc:  # a collector never raises
        logger.exception("Source %s failed", name)
        status, detail = "error", f"{type(exc).__name__}: {exc}"
    acc.flush()
    result = SourceResult(name=name, status=status, took_ms=elapsed_ms(started), images=list(acc.values()), detail=detail)
    logger.info("source=%s status=%s images=%d in %d ms", name, status, len(acc), result.took_ms)
    return result
