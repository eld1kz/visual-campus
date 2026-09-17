"""Deduplicator: one per profile, fed batch by batch as sources arrive.

Copies are matched by file SHA-1, by perceptual hash of the thumbnail (pHash) and, within one source,
by title stem ("X (cropped).jpg" = "X.jpg"). The most confident copy stays; the rest go to its `duplicates`.
"""

import asyncio
import io
import re
import time
from dataclasses import dataclass, field

import httpx
import imagehash
from PIL import Image

from app.config import settings
from app.models import DuplicatePhoto, Photo, RawImage
from app.services.text import normalize

PHASH_MAX_DISTANCE = 6  # of 64 bits
HASH_CONCURRENCY = 4  # upload.wikimedia.org answers 429 to bursts
HASH_REQUEST_TIMEOUT_S = 3.0
HASH_BUDGET_S = 6.0  # total for all thumbnail downloads of one profile

_COPY_SUFFIX = re.compile(r"\s*\((cropped|crop|edited|retouched|\d+)\)|\s*-\s*panoramio", re.IGNORECASE)
_CAMERA_NAME = re.compile(r"^(img|dsc|dscn|dcim|pict|photo|image|p)\s*\d*$")


def title_stem(title: str) -> str:
    stem = title.removeprefix("File:").rsplit(".", 1)[0].replace("_", " ")
    stem = normalize(_COPY_SUFFIX.sub("", stem))
    return "" if _CAMERA_NAME.match(stem.replace("_", "")) else stem


@dataclass
class _Member:
    photo: Photo
    raw: RawImage


@dataclass
class _Group:
    members: list[_Member] = field(default_factory=list)

    def best(self) -> _Member:
        return max(self.members, key=lambda m: m.photo.confidence)

    def result(self) -> Photo:
        best = self.best()
        dups = [
            DuplicatePhoto(id=m.photo.id, thumb_url=m.photo.thumb_url, source_url=m.photo.source_url)
            for m in self.members
            if m is not best
        ]
        return best.photo.model_copy(update={"duplicates": dups})


class Deduplicator:
    def __init__(self, hash_budget_s: float = HASH_BUDGET_S) -> None:
        self._groups: list[_Group] = []
        self._by_id: dict[str, _Group] = {}
        self._hashes: dict[str, imagehash.ImageHash] = {}
        self._semaphore = asyncio.Semaphore(HASH_CONCURRENCY)
        self._budget_s = hash_budget_s
        self._throttled = False

    # ---------- perceptual hashes (network) ----------

    async def prepare(self, raws: list[RawImage], client: httpx.AsyncClient) -> None:
        """Download thumbnails and compute pHash within the shared budget. Failures just leave no hash."""
        todo = [r for r in raws if r.thumb_url and r.id not in self._hashes]
        if not todo or self._budget_s <= 0 or self._throttled:
            return
        started = time.monotonic()
        tasks = [asyncio.create_task(self._hash_one(r, client)) for r in todo]
        try:
            await asyncio.wait(tasks, timeout=self._budget_s)
        finally:
            for task in tasks:
                task.cancel()
            self._budget_s -= time.monotonic() - started

    async def _hash_one(self, raw: RawImage, client: httpx.AsyncClient) -> None:
        async with self._semaphore:
            if self._throttled:
                return
            try:
                response = await client.get(
                    raw.thumb_url, headers={"User-Agent": settings.user_agent}, timeout=HASH_REQUEST_TIMEOUT_S
                )
                if response.status_code == 429:
                    self._throttled = True
                    return
                response.raise_for_status()
                self._hashes[raw.id] = await asyncio.to_thread(_phash, response.content)
            except Exception:  # noqa: BLE001 — a missing hash must never break the profile
                return

    def set_hash(self, photo_id: str, value: imagehash.ImageHash) -> None:
        self._hashes[photo_id] = value

    # ---------- grouping (pure) ----------

    def add(self, photo: Photo, raw: RawImage) -> list[Photo]:
        """Photos to (re)send as `photo` events: the group's best copy with its duplicates."""
        group = self._by_id.get(photo.id)
        if group is not None:  # re-scored (polygon arrived, vision): replace the member
            for m in group.members:
                if m.photo.id == photo.id:
                    m.photo, m.raw = photo, raw
        else:
            group = self._find_group(raw)
            if group is None:
                group = _Group()
                self._groups.append(group)
            group.members.append(_Member(photo, raw))
            self._by_id[photo.id] = group
        return [group.result()]

    def photos(self) -> list[Photo]:
        """Final state: one photo per group, most confident first."""
        return sorted((g.result() for g in self._groups), key=lambda p: p.confidence, reverse=True)

    def _find_group(self, raw: RawImage) -> _Group | None:
        stem = title_stem(raw.title)
        phash = self._hashes.get(raw.id)
        for group in self._groups:
            for m in group.members:
                if raw.sha1 and m.raw.sha1 and raw.sha1 == m.raw.sha1:
                    return group
                if stem and m.raw.source == raw.source and title_stem(m.raw.title) == stem:
                    return group
                other = self._hashes.get(m.raw.id)
                if phash is not None and other is not None and phash - other <= PHASH_MAX_DISTANCE:
                    return group
        return None


def _phash(content: bytes) -> imagehash.ImageHash:
    with Image.open(io.BytesIO(content)) as image:
        return imagehash.phash(image.convert("RGB"))
