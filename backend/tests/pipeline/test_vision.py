import asyncio

from app.services.pipeline import score, vision_check
from app.services.pipeline.vision import (
    INCONCLUSIVE_MARGIN, VETO_MARGIN, W_VISION_NEGATIVE, W_VISION_POSITIVE, verdict,
)
from tests.pipeline.conftest_data import CTX, raw, weights


def test_vision_without_model_returns_photo_unchanged():
    r = raw()
    photo = score(r, CTX)
    assert asyncio.run(vision_check(r, photo)) == photo


def _row(positive: float, negative: float, positive_slot: int = 0) -> list[float]:
    row = [0.0] * 9
    row[positive_slot] = positive
    row[4] = negative
    return row


def test_small_margin_is_inconclusive_not_a_verdict():
    assert verdict(_row(0.25, 0.25 + 0.015)) == ("inconclusive", 0, None, False)
    assert verdict(_row(0.25 + 0.015, 0.25)) == ("inconclusive", 0, None, False)


def test_soft_negative_between_thresholds_is_a_penalty_without_veto():
    label, weight, _, veto = verdict(_row(0.25, 0.25 + INCONCLUSIVE_MARGIN + 0.01))
    assert (label, weight, veto) == ("not_campus_place", W_VISION_NEGATIVE, False)


def test_wide_negative_margin_is_a_veto():
    assert verdict(_row(0.25, 0.25 + VETO_MARGIN)) == ("not_campus_place", W_VISION_NEGATIVE, None, True)


def test_positive_verdict_carries_the_room_category():
    assert verdict(_row(0.30, 0.25, positive_slot=1)) == ("campus_place", W_VISION_POSITIVE, "libraries", False)
    assert verdict(_row(0.30, 0.25, positive_slot=0)) == ("campus_place", W_VISION_POSITIVE, None, False)


STRONG_METADATA = dict(lat=37.59, lng=127.034, matched_category="Korea University",
                       description="Main building of Korea University")


def test_soft_negative_verdict_is_outweighed_by_strong_metadata():
    photo = score(raw(**STRONG_METADATA, vision_label="not_campus_place", vision_weight=W_VISION_NEGATIVE), CTX)
    assert photo.tier == "verified"
    assert weights(photo)["vision"] == W_VISION_NEGATIVE


def test_people_or_event_text_still_caps_the_tier_alongside_a_soft_verdict():
    photo = score(raw(**STRONG_METADATA, title="File:Graduation ceremony.jpg",
                      vision_label="not_campus_place", vision_weight=W_VISION_NEGATIVE), CTX)
    assert weights(photo)["content"] < 0 and weights(photo)["vision"] == W_VISION_NEGATIVE
    assert photo.tier == "unconfirmed"


def test_confident_veto_keeps_the_photo_unconfirmed_whatever_the_metadata():
    photo = score(raw(**STRONG_METADATA, vision_label="not_campus_place", vision_weight=W_VISION_NEGATIVE,
                      vision_veto=True), CTX)
    assert photo.tier == "unconfirmed"
    assert any(e.type == "vision" and "confidently" in e.label for e in photo.evidence)


def test_inconclusive_verdict_changes_nothing_but_leaves_a_trace():
    photo = score(raw(**STRONG_METADATA, vision_label="inconclusive", vision_weight=0), CTX)
    assert photo.tier == "verified"
    assert any(e.label == "Visual check inconclusive" and e.weight == 0 for e in photo.evidence)


def test_unchecked_photo_is_capped_at_likely():
    photo = score(raw(**STRONG_METADATA, vision_checked=False), CTX)
    assert photo.tier == "likely"
    assert any(e.label == "Not visually checked (time limit)" for e in photo.evidence)
