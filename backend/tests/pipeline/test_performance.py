"""Indexed building lookup and dedupe matching behave exactly like the plain loops they replaced."""

import random

import imagehash
import numpy as np
from shapely.geometry import Point, Polygon

from app.services.pipeline import Deduplicator, score
from app.services.pipeline.dedupe import PHASH_MAX_DISTANCE, title_stem
from app.services.pipeline.scoring import building_at
from tests.pipeline.conftest_data import CTX, LIBRARY, raw


def _square(i: int, x: float, y: float, size: float):
    return LIBRARY.model_copy(update={
        "id": f"osm-way-{i}",
        "polygon": [[x, y], [x + size, y], [x + size, y + size], [x, y + size], [x, y]],
    })


def _plain_building_at(lat, lng, buildings):
    point = Point(lng, lat)
    return next((b for b in buildings if len(b.polygon) >= 4 and Polygon(b.polygon).contains(point)), None)


def test_building_at_matches_plain_loop_with_overlaps_and_replaced_lists():
    rng = random.Random(1)
    buildings = [_square(i, 127.03 + rng.random() * 0.01, 37.585 + rng.random() * 0.01, 0.002) for i in range(60)]
    buildings.append(LIBRARY.model_copy(update={"id": "degenerate", "polygon": [[127.03, 37.585], [127.04, 37.595]]}))
    points = [(37.585 + rng.random() * 0.012, 127.03 + rng.random() * 0.012) for _ in range(300)]
    for lat, lng in points:
        assert building_at(lat, lng, buildings) == _plain_building_at(lat, lng, buildings)

    replaced = list(reversed(buildings))  # a new list: the first match in *its* order must win
    for lat, lng in points:
        assert building_at(lat, lng, replaced) == _plain_building_at(lat, lng, replaced)
    assert building_at(None, 127.03, buildings) is None
    assert building_at(37.588, 127.030, []) is None


def _plain_groups(items, hashes):
    """The previous O(n²) grouping: the first group (in creation order) with any matching member."""
    groups: list[list] = []
    for photo, r in items:
        stem, phash = title_stem(r.title), hashes.get(r.id)
        found = None
        for g in groups:
            for m in g:
                other = hashes.get(m.id)
                same_file = bool(r.sha1 and m.sha1 and r.sha1 == m.sha1)
                same_stem = bool(stem and m.source == r.source and title_stem(m.title) == stem)
                close = phash is not None and other is not None and phash - other <= PHASH_MAX_DISTANCE
                if same_file or same_stem or close:
                    found = g
                    break
            if found is not None:
                break
        if found is None:
            groups.append(found := [])
        found.append(r)
    return sorted(sorted(r.id for r in g) for g in groups)


def test_indexed_grouping_matches_plain_loop():
    rng = random.Random(3)
    bases = [np.array([rng.random() < 0.5 for _ in range(64)]) for _ in range(40)]
    items, hashes = [], {}
    for i in range(300):
        source = rng.choice(["wikimedia_commons", "flickr"])
        title = f"File:View {rng.randrange(120)}" + rng.choice([".jpg", " (cropped).jpg"])
        r = raw(id=f"x-{i}", source=source, sha1=rng.choice([None, f"s{rng.randrange(150)}"]), title=title)
        if rng.random() < 0.7:
            bits = bases[rng.randrange(len(bases))].copy()
            for j in rng.sample(range(64), rng.randint(0, 12)):
                bits[j] = not bits[j]
            hashes[r.id] = imagehash.ImageHash(bits.reshape(8, 8))
        items.append((score(r, CTX), r))

    d = Deduplicator()
    for photo_id, value in hashes.items():
        d.set_hash(photo_id, value)
    for photo, r in items:
        d.add(photo, r)
    got = sorted(sorted([p.id, *(x.id for x in p.duplicates)]) for p in d.photos())
    assert got == _plain_groups(items, hashes)
    assert dict(d.hashes()) == hashes


def test_hash_set_after_add_and_rescored_title_are_used_for_later_matches():
    d = Deduplicator()
    h = imagehash.hex_to_hash("ffd8a0c0e0f0f8fc")
    first = raw(id="commons-1", sha1=None, title="File:Old name.jpg")
    d.add(score(first, CTX), first)
    d.set_hash("commons-1", h)  # hash arrives after the photo was placed
    renamed = raw(id="commons-1", sha1=None, title="File:New name.jpg")
    d.add(score(renamed, CTX), renamed)  # re-scored with a new title: the old stem no longer matches

    old_stem = raw(id="commons-2", sha1=None, title="File:Old name (cropped).jpg")
    d.add(score(old_stem, CTX), old_stem)
    new_stem = raw(id="commons-3", sha1=None, title="File:New name (cropped).jpg")
    d.add(score(new_stem, CTX), new_stem)
    d.set_hash("flickr-1", imagehash.hex_to_hash("ffd8a0c0e0f0f8fd"))
    similar = raw(id="flickr-1", source="flickr", sha1=None, title="Somewhere")
    d.add(score(similar, CTX), similar)

    groups = sorted(sorted([p.id, *(x.id for x in p.duplicates)]) for p in d.photos())
    assert groups == [["commons-1", "commons-3", "flickr-1"], ["commons-2"]]
