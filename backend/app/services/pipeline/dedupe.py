"""Deduplicator: one per profile, fed batch by batch as sources arrive.

Copies are matched by file SHA-1, by perceptual hash of the thumbnail (pHash) and, within one source,
by title stem ("X (cropped).jpg" = "X.jpg"). The most confident copy stays; the rest go to its `duplicates`.

Matching is indexed (SHA-1 and stem dictionaries, a numpy array of pHashes), so placing a photo does not walk every
member in Python: a full regroup of ~500 photos stays within tens of milliseconds and does not stall the event loop.
"""

import asyncio
import io
import re
import time
from collections import Counter
from dataclasses import dataclass, field
from types import MappingProxyType

import httpx
import imagehash
import numpy as np
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
_POPCOUNT8 = np.array([bin(i).count("1") for i in range(256)], dtype=np.uint8)


def title_stem(title: str) -> str:
    stem = title.removeprefix("File:").rsplit(".", 1)[0].replace("_", " ")
    stem = normalize(_COPY_SUFFIX.sub("", stem))
    return "" if _CAMERA_NAME.match(stem.replace("_", "")) else stem


@dataclass(eq=False)
class _Group:
    seq: int  # creation order: when several groups match, the earliest wins
    members: list["_Member"] = field(default_factory=list)

    def best(self) -> "_Member":
        return max(self.members, key=lambda m: m.photo.confidence)

    def result(self) -> Photo:
        best = self.best()
        dups = [
            DuplicatePhoto(id=m.photo.id, thumb_url=m.photo.thumb_url, source_url=m.photo.source_url)
            for m in self.members
            if m is not best
        ]
        return best.photo.model_copy(update={"duplicates": dups})


@dataclass(eq=False)
class _Member:
    photo: Photo
    raw: RawImage
    group: _Group
    keys: tuple = ()  # its entries in Deduplicator._keys


def _match_keys(raw: RawImage) -> tuple:
    """Exact-match keys: the file SHA-1 and, within one source, the title stem."""
    stem = title_stem(raw.title)
    keys = (("sha1", raw.sha1) if raw.sha1 else None, ("stem", raw.source, stem) if stem else None)
    return tuple(k for k in keys if k)


def _bits(value: imagehash.ImageHash) -> np.uint64:
    return np.frombuffer(np.packbits(value.hash.flatten()).tobytes().rjust(8, b"\0"), dtype=">u8")[0]


class Deduplicator:
    def __init__(self, hash_budget_s: float = HASH_BUDGET_S) -> None:
        self._groups: list[_Group] = []
        self._by_id: dict[str, _Group] = {}
        self._hashes: dict[str, imagehash.ImageHash] = {}
        self._keys: dict[tuple, Counter[_Group]] = {}  # match key → groups holding it (member counts)
        self._members: dict[str, _Member] = {}
        # pHashes of members, as uint64 bits with their group's seq, filled up to _hashed_count.
        self._hash_bits = np.zeros(64, dtype=np.uint64)
        self._hash_seqs = np.zeros(64, dtype=np.int64)
        self._hash_slot: dict[str, int] = {}
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
                self.set_hash(raw.id, await asyncio.to_thread(_phash, response.content))
            except Exception:  # noqa: BLE001 — a missing hash must never break the profile
                return

    def set_hash(self, photo_id: str, value: imagehash.ImageHash) -> None:
        self._hashes[photo_id] = value
        member = self._members.get(photo_id)
        if member is not None:
            self._index_hash(photo_id, member.group)

    def hashes(self) -> MappingProxyType[str, imagehash.ImageHash]:
        """pHashes computed so far, by photo id (read-only view)."""
        return MappingProxyType(self._hashes)

    # ---------- grouping (pure) ----------

    def add(self, photo: Photo, raw: RawImage) -> list[Photo]:
        """Photos to (re)send as `photo` events: the group's best copy with its duplicates."""
        group = self._by_id.get(photo.id)
        if group is not None:  # re-scored (polygon arrived, vision): replace the member
            for m in group.members:
                if m.photo.id == photo.id:
                    self._unindex(m)
                    m.photo, m.raw = photo, raw
                    self._index(m)
        else:
            group = self._find_group(raw)
            if group is None:
                group = _Group(seq=len(self._groups))
                self._groups.append(group)
            member = _Member(photo, raw, group)
            group.members.append(member)
            self._by_id[photo.id] = group
            self._index(member)
        return [group.result()]

    def photos(self) -> list[Photo]:
        """Final state: one photo per group, most confident first."""
        return sorted((g.result() for g in self._groups), key=lambda p: p.confidence, reverse=True)

    def _find_group(self, raw: RawImage) -> _Group | None:
        """The earliest group with a member of the same SHA-1, same source and title stem, or a close pHash."""
        seqs = [g.seq for key in _match_keys(raw) for g in self._keys.get(key, ())]
        phash = self._hashes.get(raw.id)
        n = len(self._hash_slot)
        if phash is not None and n:
            xor = (self._hash_bits[:n] ^ _bits(phash)).view(np.uint8).reshape(n, 8)
            close = _POPCOUNT8[xor].sum(axis=1, dtype=np.int64) <= PHASH_MAX_DISTANCE
            if close.any():
                seqs.append(int(self._hash_seqs[:n][close].min()))
        return self._groups[min(seqs)] if seqs else None

    def _index(self, member: _Member) -> None:
        member.keys = _match_keys(member.raw)
        for key in member.keys:
            self._keys.setdefault(key, Counter())[member.group] += 1
        self._members[member.raw.id] = member
        if member.raw.id in self._hashes:
            self._index_hash(member.raw.id, member.group)

    def _unindex(self, member: _Member) -> None:
        for key in member.keys:
            groups = self._keys[key]
            groups[member.group] -= 1
            if groups[member.group] <= 0:
                del groups[member.group]
        self._members.pop(member.raw.id, None)

    def _index_hash(self, photo_id: str, group: _Group) -> None:
        slot = self._hash_slot.get(photo_id)
        if slot is None:
            slot = self._hash_slot[photo_id] = len(self._hash_slot)
            if slot == len(self._hash_bits):
                self._hash_bits = np.concatenate([self._hash_bits, np.zeros_like(self._hash_bits)])
                self._hash_seqs = np.concatenate([self._hash_seqs, np.zeros_like(self._hash_seqs)])
        self._hash_bits[slot] = _bits(self._hashes[photo_id])
        self._hash_seqs[slot] = group.seq


def _phash(content: bytes) -> imagehash.ImageHash:
    with Image.open(io.BytesIO(content)) as image:
        return imagehash.phash(image.convert("RGB"))
