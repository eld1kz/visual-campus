from dataclasses import replace
from datetime import date

from shapely.geometry import Polygon

from app.services.commons import CommonsFile, parse_date
from app.services.evidence import CampusContext, deduplicate, evaluate

# A ~1 km square campus around (37.5890, 127.0320).
CAMPUS = Polygon([(127.027, 37.584), (127.037, 37.584), (127.037, 37.594), (127.027, 37.594)])
CTX = CampusContext(
    names=["Korea University", "고려대학교", "KU"],
    lat=37.589,
    lng=127.032,
    geometry=CAMPUS,
    today=date(2026, 9, 17),
    lang="en",
)


def make_file(**overrides) -> CommonsFile:
    base = CommonsFile(
        pageid=1,
        title="File:Campus view.jpg",
        page_url="https://commons.wikimedia.org/wiki/File:Campus_view.jpg",
        thumb_url=None,
        full_url="https://upload.wikimedia.org/campus.jpg",
        sha1="aaa",
        lat=None,
        lng=None,
        author="Someone",
        license="CC BY-SA 4.0",
        date_taken="2024-05-01",
        uploaded="2024-05-02",
        description="",
        categories=[],
    )
    return replace(base, **overrides)


def weights(evaluation) -> dict[str, int]:
    return {e["type"]: e["weight"] for e in evaluation.evidence}


def test_geotag_inside_campus_with_category_and_name_is_verified():
    f = make_file(lat=37.590, lng=127.031, via_category="Korea University", title="File:Korea University main hall.jpg")
    ev = evaluate(f, CTX)
    assert ev.tier == "verified"
    assert ev.confidence == 100
    assert weights(ev)["geo"] > 0


def test_category_without_geotag_but_named_is_likely():
    f = make_file(via_category="Korea University", title="File:Korea University gate.jpg")
    ev = evaluate(f, CTX)
    assert ev.tier == "likely"
    assert weights(ev)["missing"] < 0


def test_geotag_far_away_outweighs_the_category():
    # Archive scans are often geotagged at the archive, kilometres away.
    f = make_file(lat=37.513, lng=127.009, via_category="Korea University", date_taken="1971")
    ev = evaluate(f, CTX)
    assert ev.tier == "unconfirmed"
    assert weights(ev)["geo"] < 0
    assert weights(ev)["date"] < 0


def test_nearby_photo_outside_boundary_goes_to_city():
    f = make_file(lat=37.5955, lng=127.032, title="File:Anam street cafe.jpg", found_nearby=True)
    ev = evaluate(f, CTX)
    assert ev.category == "city"
    assert "student_life" in ev.tags


def test_library_keyword_sets_category():
    f = make_file(lat=37.589, lng=127.033, title="File:고려대학교 중앙도서관.jpg")
    assert evaluate(f, CTX).category == "libraries"


def test_non_latin_name_glued_to_numbers_counts_as_mention():
    ev = evaluate(make_file(title="File:2006고려대학교19.jpg"), CTX)
    assert weights(ev)["text"] > 0


def test_short_latin_alias_needs_word_boundary():
    ev = evaluate(make_file(title="File:KUMC hospital.jpg"), CTX)
    assert "text" not in weights(ev)


def test_logos_are_not_photos():
    assert evaluate(make_file(title="File:Korea University logo.png"), CTX) is None


def test_people_photos_off_campus_are_penalised():
    f = make_file(via_category="Korea University", description="Official visit of the delegation")
    assert weights(evaluate(f, CTX))["content"] < 0


def test_missing_license_is_penalised():
    with_license = evaluate(make_file(), CTX)
    without_license = evaluate(make_file(license=None), CTX)
    assert without_license.confidence < with_license.confidence
    assert any("license" in e["label"] for e in without_license.evidence)


def test_without_polygon_distance_from_point_is_used():
    ctx = replace(CTX, geometry=None)
    near = evaluate(make_file(lat=37.5895, lng=127.0325), ctx)
    far = evaluate(make_file(lat=37.62, lng=127.10), ctx)
    assert weights(near)["geo"] > 0
    assert weights(far)["geo"] < 0


def test_deduplicate_keeps_most_confident_copy():
    a = evaluate(make_file(pageid=1, sha1="same", via_category="Korea University"), CTX)
    b = evaluate(make_file(pageid=2, sha1="same"), CTX)
    c = evaluate(make_file(pageid=3, sha1="other", title="File:Campus view (cropped).jpg"), CTX)
    d = evaluate(make_file(pageid=4, sha1="unique", title="File:Library.jpg"), CTX)
    kept = deduplicate([b, c, a, d])
    assert {e.file.pageid for e in kept} == {1, 4}
    assert {f.pageid for f in next(e for e in kept if e.file.pageid == 1).duplicates} == {2, 3}


def test_parse_date_handles_commons_formats():
    assert parse_date("2012-05-20 14:03:22") == "2012-05-20"
    assert parse_date('1970s<div style="display: none;">date QS:P,+1970</div>') == "1970"
    assert parse_date(None) is None
