import asyncio

from app.services.pipeline import score
from app.services.pipeline.vision import VisionResult, classify
from tests.pipeline.conftest_data import CTX, raw, weights

INSIDE = dict(lat=37.590, lng=127.034)
CAR = VisionResult(place_prob=0.08, top="car")
BUILDING = VisionResult(place_prob=0.93, top="building")


def test_disabled_vision_gives_no_verdicts():
    assert asyncio.run(classify([b"x", b"y"])) == [None, None]


def test_non_place_is_capped_even_with_geotag_and_category():
    # A parked car geotagged on campus and filed under the university category.
    r = raw(**INSIDE, matched_category="Korea University", title="File:Hyundai Genesis.jpg")
    assert score(r, CTX).tier == "verified"
    p = score(r, CTX, CAR)
    assert p.tier == "unconfirmed"
    assert weights(p)["vision"] < 0
    assert "car" in next(e.label for e in p.evidence if e.type == "vision")


def test_place_verdict_raises_a_geotagged_photo():
    r = raw(**INSIDE, title="File:IMG 2041.jpg", found_by="geosearch")
    assert score(r, CTX).tier == "likely"
    p = score(r, CTX, BUILDING)
    assert p.tier == "verified" and weights(p)["vision"] > 0


def test_vision_alone_does_not_lift_an_unlinked_photo():
    p = score(raw(title="File:IMG 2041.jpg", found_by="geosearch"), CTX, BUILDING)
    assert p.tier == "unconfirmed"


def test_unsure_verdict_adds_nothing():
    r = raw(**INSIDE, title="File:IMG 2041.jpg", found_by="geosearch")
    assert score(r, CTX, VisionResult(place_prob=0.42, top="interior")) == score(r, CTX)


def test_vision_sets_the_category_when_metadata_is_silent():
    p = score(raw(**INSIDE, title="File:IMG 2041.jpg"), CTX, VisionResult(place_prob=0.9, top="library"))
    assert p.category == "libraries"
    p = score(raw(**INSIDE, title="File:IMG 2041.jpg"), CTX, VisionResult(place_prob=0.9, top="classroom"))
    assert p.category == "classrooms"
