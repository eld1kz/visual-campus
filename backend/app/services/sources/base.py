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


async def run_collector(
    name: SourceName,
    work: Callable[[dict[str, RawImage], Deadline], Awaitable[str | None]],
    budget_s: float = SOURCE_BUDGET_S,
) -> SourceResult:
    """Run `work` under the source budget. `work` fills `acc` as results arrive, so a timeout keeps them.

    Partial results at the deadline are reported as `ok` (with a detail), an empty timeout as `timeout`.
    """
    acc: dict[str, RawImage] = {}
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
    result = SourceResult(name=name, status=status, took_ms=elapsed_ms(started), images=list(acc.values()), detail=detail)
    logger.info("source=%s status=%s images=%d in %d ms", name, status, len(acc), result.took_ms)
    return result
