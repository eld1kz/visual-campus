"""Shared pieces of the image collectors (docs/CONTRACT.md §6)."""

import asyncio
import logging
import math
import time
from collections.abc import Awaitable, Callable
from contextlib import asynccontextmanager
from dataclasses import dataclass

import httpx

from app.models import BuildingType, RawImage, SourceName, SourceResult

logger = logging.getLogger("visual_campus.sources")

# Contract: ≤ 8 s per source. Stop a little earlier so an outer 8 s wrapper never cuts us first.
SOURCE_BUDGET_S = 7.5
MIN_SIDE_PX = 200  # smaller files are icons/thumbnails, not photos of a place


@dataclass
class SearchSubject:
    qid: str | None
    kind: str
    names: list[str]
    commons_category: str | None = None
    image_titles: list[str] | None = None
    lat: float | None = None
    lng: float | None = None
    building_type: BuildingType | None = None


@dataclass
class SourceQuery:
    wikidata_id: str
    names: list[str]
    lat: float | None
    lng: float | None
    website: str | None
    commons_category: str | None
    bbox: tuple[float, float, float, float] | None = None  # (west, south, east, north)
    polygon: list[list[float]] | None = None
    geosearch_centers: list[tuple[float, float, int]] | None = None  # lat, lng, radius metres
    subjects: list[SearchSubject] | None = None
    category_targets: dict[str, int] | None = None


_SOURCE_SEMAPHORES: dict[str, asyncio.Semaphore] = {}


@asynccontextmanager
async def source_slot(name: str, limit: int):
    """A process-wide source concurrency limit shared by every profile build."""
    semaphore = _SOURCE_SEMAPHORES.setdefault(name, asyncio.Semaphore(limit))
    async with semaphore:
        yield


async def request_with_retry(
    client: httpx.AsyncClient,
    method: str,
    url: str,
    deadline: "Deadline",
    source: str,
    limit: int,
    **kwargs,
) -> httpx.Response:
    """Bounded 429/5xx retry that honors Retry-After and the collector deadline."""
    response: httpx.Response | None = None
    for attempt in range(3):
        try:
            async with source_slot(source, limit):
                response = await client.request(method, url, timeout=deadline.left(), **kwargs)
        except httpx.TransportError:
            if attempt == 2:
                raise
            await asyncio.sleep(0.2 * (2 ** attempt))
            continue
        if response.status_code != 429 and response.status_code < 500:
            return response
        if attempt == 2:
            return response
        retry_after = response.headers.get("retry-after", "")
        try:
            delay = min(float(retry_after), 2.0)
        except ValueError:
            delay = 0.2 * (2 ** attempt)
        await asyncio.sleep(min(delay, max(0.0, deadline.end - time.monotonic() - 0.25)))
    return response  # pragma: no cover


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


def padded_bbox(bbox: tuple[float, float, float, float], pad_m: float = 250) -> tuple[float, float, float, float]:
    """Expand a campus bbox a little so street-level photos on bordering roads are still considered."""
    west, south, east, north = bbox
    lat = (south + north) / 2
    dlat = (pad_m / 1000) / 111.32
    dlng = (pad_m / 1000) / (111.32 * max(math.cos(math.radians(lat)), 0.01))
    return (west - dlng, south - dlat, east + dlng, north + dlat)


def query_bbox(query: SourceQuery, half_km: float = 0.6) -> tuple[float, float, float, float] | None:
    if query.bbox:
        return padded_bbox(query.bbox)
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
