from app.services.pipeline import score
from app.services.pipeline import claude_vision as cv
from tests.pipeline.conftest_data import CTX, raw

EDGE_STREET = dict(lat=37.59, lng=127.034, title="Street view", license="CC BY-SA 4.0")  # geotag inside, no name


def verdict(label, sure=90, category="campus"):
    return {"i": 1, "label": label, "confidence": sure, "category": category}


def test_confident_campus_verdict_lifts_a_borderline_photo_and_counts_as_checked():
    base = raw(**EDGE_STREET, vision_checked=False)
    before = score(base, CTX)
    after = score(cv.apply(base, verdict("campus_place")), CTX)
    assert after.confidence == before.confidence + cv.W_POSITIVE
    assert after.vision_checked and any(e.label == "Claude check: shows a campus place" for e in after.evidence)


def test_low_model_confidence_is_inconclusive():
    checked = cv.apply(raw(**EDGE_STREET), verdict("campus_place", sure=50))
    assert (checked.vision_label, checked.vision_weight, checked.vision_veto) == ("inconclusive", 0, False)


def test_only_a_sure_not_a_photo_is_a_veto_and_people_are_a_soft_penalty():
    people = cv.apply(raw(**EDGE_STREET), verdict("people_or_event", sure=95))
    chart = cv.apply(raw(**EDGE_STREET), verdict("not_a_photo", sure=95))
    assert (people.vision_weight, people.vision_veto) == (cv.W_NEGATIVE, False)
    assert chart.vision_veto and score(chart, CTX).tier == "unconfirmed"


def test_interior_counts_as_a_place_and_keeps_the_room_category():
    checked = cv.apply(raw(**EDGE_STREET), verdict("building_interior", category="libraries"))
    assert (checked.vision_label, checked.vision_category) == ("campus_place", "libraries")


def test_candidates_skip_hopeless_signal_free_and_already_verified_photos():
    strong = raw(id="strong", **EDGE_STREET)
    weak = raw(id="weak", title="Central Asia")  # no place signal
    items = [(r, score(r, CTX)) for r in (strong, weak)]
    assert [r.id for r, _ in cv.candidates(items, 10)] == ["strong"]
