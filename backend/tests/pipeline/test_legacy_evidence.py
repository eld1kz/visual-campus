"""The legacy CommonsFile adapter used by services/profile.py keeps its old rules."""

from dataclasses import replace

from app.services.evidence import deduplicate, evaluate
from tests.test_evidence import CTX, make_file


def weights(evaluation) -> dict[str, int]:
    return {e["type"]: e["weight"] for e in evaluation.evidence}


def test_inside_with_category_and_name_is_verified():
    f = make_file(lat=37.590, lng=127.031, via_category="Korea University", title="File:Korea University main hall.jpg")
    ev = evaluate(f, CTX)
    assert (ev.tier, ev.confidence) == ("verified", 100)


def test_category_and_name_without_geotag_is_likely():
    ev = evaluate(make_file(via_category="Korea University", title="File:Korea University gate.jpg"), CTX)
    assert ev.tier == "likely" and weights(ev)["missing"] < 0


def test_far_geotag_outweighs_category():
    ev = evaluate(make_file(lat=37.513, lng=127.009, via_category="Korea University", date_taken="1971"), CTX)
    assert ev.tier == "unconfirmed" and weights(ev)["geo"] < 0 and weights(ev)["date"] < 0


def test_nearby_unlinked_photo_goes_to_city():
    ev = evaluate(make_file(lat=37.5955, lng=127.032, title="File:Anam street cafe.jpg", found_nearby=True), CTX)
    assert ev.category == "city" and "student_life" in ev.tags


def test_logos_and_people():
    assert evaluate(make_file(title="File:Korea University logo.png"), CTX) is None
    f = make_file(via_category="Korea University", description="Official visit of the delegation")
    assert weights(evaluate(f, CTX))["content"] < 0


def test_without_polygon_distance_from_point_is_used():
    ctx = replace(CTX, geometry=None)
    assert weights(evaluate(make_file(lat=37.5895, lng=127.0325), ctx))["geo"] > 0
    assert weights(evaluate(make_file(lat=37.62, lng=127.10), ctx))["geo"] < 0


def test_deduplicate_keeps_most_confident_copy():
    a = evaluate(make_file(pageid=1, sha1="same", via_category="Korea University"), CTX)
    b = evaluate(make_file(pageid=2, sha1="same"), CTX)
    c = evaluate(make_file(pageid=3, sha1="other", title="File:Campus view (cropped).jpg"), CTX)
    d = evaluate(make_file(pageid=4, sha1="unique", title="File:Library.jpg"), CTX)
    kept = deduplicate([b, c, a, d])
    assert {e.file.pageid for e in kept} == {1, 4}
    assert {f.pageid for f in next(e for e in kept if e.file.pageid == 1).duplicates} == {2, 3}
