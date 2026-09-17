"""Image and campus-shape collectors (docs/CONTRACT.md §6), plus the generic `run_source` wrapper."""

import asyncio
import logging
import time
from collections.abc import Awaitable
from typing import Literal, TypeVar

import httpx

from app.services.sources.base import SourceQuery

__all__ = ["SourceQuery", "run_source"]

logger = logging.getLogger("visual_campus.sources")

T = TypeVar("T")
SourceOutcome = Literal["ok", "timeout", "error"]


async def run_source(name: str, coro: Awaitable[T], timeout_s: float) -> tuple[SourceOutcome, T | None]:
    """Run one external source with its own timeout; failures become a status, never an exception."""
    started = time.perf_counter()
    try:
        result = await asyncio.wait_for(coro, timeout=timeout_s)
        state: SourceOutcome = "ok"
    except (asyncio.TimeoutError, httpx.TimeoutException):
        result, state = None, "timeout"
    except Exception:
        logger.exception("Source %s failed", name)
        result, state = None, "error"
    logger.info("source=%s status=%s in %.0f ms", name, state, (time.perf_counter() - started) * 1000)
    return state, result
