import asyncio

from app.services.pipeline import score, vision_check
from tests.pipeline.conftest_data import CTX, raw


def test_vision_without_model_returns_photo_unchanged():
    r = raw(lat=37.590, lng=127.034)
    photo = score(r, CTX)
    assert asyncio.run(vision_check(r, photo)) == photo
