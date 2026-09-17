"""In-memory caches: finished profiles by (qid, lang), OSM campus shapes by qid, and in-flight builds.

One process, no persistence — enough for the hackathon deployment (docs/CONTRACT.md §3 «Кэш»).
"""

import asyncio
import time
from collections.abc import AsyncIterator
from dataclasses import dataclass

from app.models import CampusShape, ProfileResponse

PROFILE_TTL_S = 30 * 60
PARTIAL_PROFILE_TTL_S = 5 * 60
SHAPE_TTL_S = 6 * 60 * 60
PARTIAL_SHAPE_TTL_S = 5 * 60  # OSM answered, but buildings timed out: retry soon

Event = tuple[str, dict]


@dataclass
class CachedProfile:
    profile: ProfileResponse
    partial: bool


class EventLog:
    """Events of one build. Any number of followers replay what was emitted so far, then follow live."""

    def __init__(self) -> None:
        self.events: list[Event] = []
        self.closed = False
        self.followers = 0
        self._changed = asyncio.Event()

    def emit(self, event: str, data: dict) -> None:
        self.events.append((event, data))
        self._wake()

    def close(self) -> None:
        self.closed = True
        self._wake()

    def _wake(self) -> None:
        self._changed.set()
        self._changed = asyncio.Event()

    async def follow(self) -> AsyncIterator[Event]:
        i = 0
        while True:
            changed = self._changed
            while i < len(self.events):
                yield self.events[i]
                i += 1
            if self.closed:
                return
            await changed.wait()


class _Ttl:
    def __init__(self) -> None:
        self._items: dict = {}

    def get(self, key):
        item = self._items.get(key)
        if item is None:
            return None
        expires, value = item
        if expires <= time.monotonic():
            del self._items[key]
            return None
        return value

    def put(self, key, value, ttl_s: float) -> None:
        self._items[key] = (time.monotonic() + ttl_s, value)

    def clear(self) -> None:
        self._items.clear()


profiles = _Ttl()  # (qid, lang) -> CachedProfile
shapes = _Ttl()  # qid -> CampusShape
inflight: dict[tuple[str, str], object] = {}  # (qid, lang) -> orchestrator.ProfileBuild


def get_profile(qid: str, lang: str) -> CachedProfile | None:
    return profiles.get((qid, lang))


def put_profile(qid: str, lang: str, profile: ProfileResponse, partial: bool) -> None:
    profiles.put((qid, lang), CachedProfile(profile, partial), PARTIAL_PROFILE_TTL_S if partial else PROFILE_TTL_S)


def any_profile(qid: str) -> CachedProfile | None:
    """Photos and university data do not depend much on lang: /campus takes whichever is cached."""
    return get_profile(qid, "ru") or get_profile(qid, "en")


def get_shape(qid: str) -> CampusShape | None:
    return shapes.get(qid)


def put_shape(qid: str, shape: CampusShape, complete: bool) -> None:
    shapes.put(qid, shape, SHAPE_TTL_S if complete else PARTIAL_SHAPE_TTL_S)


def clear() -> None:
    profiles.clear()
    shapes.clear()
    inflight.clear()
