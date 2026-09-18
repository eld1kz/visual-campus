from datetime import date

from app.services.pipeline.dates import effective_date_source, freshness, normalize_date, text_year, unix_date
from app.services.pipeline.ranking import parse_targets, rank_photos, select_targets
from tests.pipeline.conftest_data import CTX, raw
from app.services.pipeline import score


def test_date_parser_preserves_precision_and_rejects_invalid_or_future():
    today = date(2026, 9, 18)
    assert normalize_date("2024", today) == "2024"
    assert normalize_date("2024-05", today) == "2024-05"
    assert normalize_date("2024-05-02T10:20:30Z", today) == "2024-05-02"
    assert normalize_date("2024-02-31", today) is None
    assert normalize_date("2027-01-01", today) is None
    assert unix_date(0, today=today) == "1970-01-01"


def test_upload_and_text_hints_never_become_capture_dates():
    assert effective_date_source(None, "2025-02-01", "unknown") == "upload_only"
    assert effective_date_source(None, None, "unknown", 1815) == "text_hint"
    assert freshness(None, 1815) == "historic"
    assert freshness(None) == "date_unknown"
    assert text_year("Main hall in 2019") == 2019


def test_ranking_keeps_tier_and_confidence_ahead_of_freshness():
    verified_old = score(raw(id="old", lat=37.59, lng=127.034, date_taken="2019-01-01",
                             matched_category="Korea University", title="Korea University"), CTX)
    recent_likely = score(raw(id="new", lat=37.59, lng=127.034, vision_checked=False, date_taken="2025-01-01",
                              matched_category="Korea University", title="Korea University"), CTX)
    assert rank_photos([recent_likely, verified_old])[0].tier == "verified"


def test_selection_keeps_unconfirmed_photos_after_reliable_ones():
    reliable = score(raw(id="reliable", lat=37.59, lng=127.034, vision_checked=True,
                         matched_category="Korea University", title="Korea University"), CTX)
    unrelated = score(raw(id="unrelated", title="Central Asia"), CTX)
    assert unrelated.tier == "unconfirmed"

    selected = select_targets([unrelated, reliable], {"campus": 2})

    assert [photo.id for photo in selected] == ["reliable", "unrelated"]


def test_selection_caps_reliable_photos_per_category_but_not_unconfirmed():
    reliable = [
        score(raw(id=f"reliable-{i}", lat=37.59, lng=127.034, vision_checked=True,
                  matched_category="Korea University", title="Korea University"), CTX)
        for i in range(4)
    ]
    unconfirmed = [score(raw(id=f"weak-{i}", title="Central Asia"), CTX) for i in range(3)]

    selected = select_targets([*unconfirmed, *reliable], {"campus": 2})

    assert sum(p.tier != "unconfirmed" for p in selected) == 2
    assert sum(p.tier == "unconfirmed" for p in selected) == 3
    assert [p.tier for p in selected] == ["verified", "verified", "unconfirmed", "unconfirmed", "unconfirmed"]


def test_targets_are_parsed_from_settings_format():
    assert parse_targets("campus=12, dorms=6,bad,city=x") == {"campus": 12, "dorms": 6}
