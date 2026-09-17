import asyncio

import httpx
import imagehash
import numpy as np
from PIL import Image

from app.services.pipeline import Deduplicator, score
from app.services.pipeline.dedupe import _phash
from tests.pipeline.conftest_data import CTX, raw


def scored(**overrides):
    r = raw(**overrides)
    return score(r, CTX), r


def test_same_sha1_keeps_most_confident_copy():
    d = Deduplicator()
    low = scored(id="commons-2", sha1="same", title="File:A.jpg")
    high = scored(id="commons-1", sha1="same", title="File:B.jpg", matched_category="Korea University")
    d.add(*low)
    out = d.add(*high)
    assert [p.id for p in out] == ["commons-1"]
    assert [x.id for x in out[0].duplicates] == ["commons-2"]
    assert [p.id for p in d.photos()] == ["commons-1"]


def test_cropped_title_is_duplicate_within_source_only():
    d = Deduplicator()
    d.add(*scored(id="commons-1", sha1="a", title="File:Campus view.jpg"))
    d.add(*scored(id="commons-3", sha1="b", title="File:Campus view (cropped).jpg"))
    d.add(*scored(id="flickr-9", sha1=None, source="flickr", title="Campus view"))
    d.add(*scored(id="flickr-10", sha1=None, source="flickr", title="IMG_1234"))
    d.add(*scored(id="flickr-11", sha1=None, source="flickr", title="IMG_1234"))
    assert sorted(p.id for p in d.photos()) == ["commons-1", "flickr-10", "flickr-11", "flickr-9"]


def test_perceptual_hash_matches_across_sources():
    d = Deduplicator()
    h = imagehash.hex_to_hash("ffd8a0c0e0f0f8fc")
    d.set_hash("commons-1", h)
    d.set_hash("flickr-7", imagehash.hex_to_hash("ffd8a0c0e0f0f8fd"))  # 1 bit apart
    d.set_hash("flickr-8", imagehash.hex_to_hash("00275f3f1f0f0703"))  # far
    d.add(*scored(id="commons-1", sha1="a", title="File:Main hall.jpg"))
    d.add(*scored(id="flickr-7", sha1=None, source="flickr", title="Main hall at dusk"))
    d.add(*scored(id="flickr-8", sha1=None, source="flickr", title="Other"))
    assert len(d.photos()) == 2


def test_rescored_photo_replaces_member_with_same_id():
    d = Deduplicator()
    first = scored(id="commons-1", title="File:Hall.jpg")
    d.add(*first)
    better = scored(id="commons-1", title="File:Hall.jpg", lat=37.590, lng=127.034)
    out = d.add(*better)
    assert out[0].confidence == better[0].confidence
    assert len(d.photos()) == 1 and d.photos()[0].duplicates == []


def _png(seed: int) -> bytes:
    import io

    rng = np.random.default_rng(seed)
    buf = io.BytesIO()
    Image.fromarray(rng.integers(0, 255, (64, 64, 3), dtype=np.uint8)).save(buf, "PNG")
    return buf.getvalue()


def test_prepare_downloads_thumbs_and_survives_errors():
    image = _png(1)

    def handler(request: httpx.Request) -> httpx.Response:
        if "broken" in request.url.path:
            return httpx.Response(500)
        if "garbage" in request.url.path:
            return httpx.Response(200, content=b"not an image")
        assert "VisualCampus" in request.headers["user-agent"]
        return httpx.Response(200, content=image)

    async def run():
        d = Deduplicator()
        async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
            await d.prepare([
                raw(id="commons-1", thumb_url="https://t/a.png"),
                raw(id="flickr-1", source="flickr", thumb_url="https://t/b.png"),
                raw(id="flickr-2", source="flickr", thumb_url="https://t/broken.png"),
                raw(id="flickr-3", source="flickr", thumb_url="https://t/garbage.png"),
            ], client)
        return d

    d = asyncio.run(run())
    assert set(d._hashes) == {"commons-1", "flickr-1"}
    assert d._hashes["commons-1"] == _phash(image)


def test_prepare_respects_budget_and_stops_on_429():
    calls = 0

    def throttled(request: httpx.Request) -> httpx.Response:
        nonlocal calls
        calls += 1
        return httpx.Response(429)

    async def slow(request: httpx.Request) -> httpx.Response:
        await asyncio.sleep(5)
        return httpx.Response(200, content=_png(2))

    async def run():
        d = Deduplicator()
        async with httpx.AsyncClient(transport=httpx.MockTransport(throttled)) as client:
            await d.prepare([raw(id=f"commons-{i}", thumb_url=f"https://t/{i}.png") for i in range(20)], client)
        assert calls <= 4  # concurrency limit; nothing more after the 429

        d2 = Deduplicator(hash_budget_s=0.2)
        loop = asyncio.get_running_loop()
        started = loop.time()
        async with httpx.AsyncClient(transport=httpx.MockTransport(slow)) as client:
            await d2.prepare([raw(id="commons-1", thumb_url="https://t/x.png")], client)
            await d2.prepare([raw(id="commons-2", thumb_url="https://t/y.png")], client)  # budget spent
        assert loop.time() - started < 1.0
        assert d2._hashes == {}

    asyncio.run(run())
