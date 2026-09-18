"""Shared fixtures for pipeline tests: a ~1 km square campus around (37.589, 127.032)."""

from datetime import date

from shapely.geometry import Polygon

from app.models import Building, RawImage
from app.services.pipeline import CampusContext

CAMPUS = Polygon([(127.027, 37.584), (127.037, 37.584), (127.037, 37.594), (127.027, 37.594)])
LIBRARY = Building(
    id="osm-way-1", name="Central Library", type="library",
    polygon=[[127.030, 37.588], [127.031, 37.588], [127.031, 37.589], [127.030, 37.589], [127.030, 37.588]],
    height_m=None, levels=None, photo_ids=[], source="OpenStreetMap", inside_campus=True,
)
CTX = CampusContext(
    names=["Korea University", "고려대학교", "KU"],
    lat=37.589,
    lng=127.032,
    polygon=CAMPUS,
    buildings=[LIBRARY],
    official_domains=["korea.ac.kr"],
    today=date(2026, 9, 17),
    lang="en",
)


def raw(**overrides) -> RawImage:
    base = dict(
        id="commons-1",
        source="wikimedia_commons",
        source_url="https://commons.wikimedia.org/wiki/File:Campus_view.jpg",
        source_domain="commons.wikimedia.org",
        full_url="https://upload.wikimedia.org/campus.jpg",
        title="File:Campus view.jpg",
        found_by="category",
        author="Someone",
        license="CC BY-SA 4.0",
        published_at="2024-05-01",
        vision_checked=True,
        sha1="aaa",
    )
    return RawImage(**{**base, **overrides})


def weights(photo) -> dict[str, int]:
    out: dict[str, int] = {}
    for e in photo.evidence:
        out[e.type] = out.get(e.type, 0) + e.weight
    return out
