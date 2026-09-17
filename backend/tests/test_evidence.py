"""Fixtures of the legacy CommonsFile API, still imported by tests/test_profile.py.

The evidence rules are tested in tests/pipeline/ (test_scoring.py, test_legacy_evidence.py).
Delete this file once test_profile.py moves to the new pipeline API.
"""

from dataclasses import replace
from datetime import date

from shapely.geometry import Polygon

from app.services.commons import CommonsFile, parse_date
from app.services.evidence import CampusContext

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



# Commons date parsing (sources zone); kept here until sources tests cover it.
def test_parse_date_handles_commons_formats():
    assert parse_date("2012-05-20 14:03:22") == "2012-05-20"
    assert parse_date('1970s<div style="display: none;">date QS:P,+1970</div>') == "1970"
    assert parse_date(None) is None
