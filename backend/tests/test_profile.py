from datetime import date

from shapely.geometry import MultiPolygon, Polygon

from app.services.evidence import CampusContext, evaluate
from app.services.osm import Campus
from app.services.profile import build_citations, compute_stats, polygon_coords, to_photo
from app.services.wikipedia import WikiSummary, first_sentences
from tests.test_evidence import CAMPUS, CTX, make_file

TODAY = date(2026, 9, 17)


def test_polygon_coords_uses_largest_part_of_multipolygon():
    small = Polygon([(0, 0), (1, 0), (1, 1), (0, 1)])
    big = Polygon([(10, 10), (13, 10), (13, 13), (10, 13)])
    coords = polygon_coords(MultiPolygon([small, big]))
    assert coords[0] == [10.0, 10.0]
    assert len(coords) == 5
    assert polygon_coords(None) is None


def test_citations_are_numbered_and_skip_missing_sources():
    wiki = WikiSummary(text="…", url="https://en.wikipedia.org/wiki/KAIST", title="KAIST", lang="en")
    campus = Campus(geometry=CAMPUS, name="KAIST", osm_url="https://www.openstreetmap.org/way/1", area_km2=1.1)
    full = build_citations(wiki, "Q39949", campus)
    assert [c.n for c in full] == [1, 2, 3]
    assert "Wikipedia" in full[0].title

    only_wikidata = build_citations(None, "Q39949", None)
    assert [(c.n, c.url) for c in only_wikidata] == [(1, "https://www.wikidata.org/wiki/Q39949")]


def test_to_photo_maps_contract_fields():
    ev = evaluate(make_file(pageid=42, license=None, date_taken=None, uploaded="2025-01-02"), CTX)
    photo = to_photo(ev, TODAY)
    assert photo.id == "commons-42"
    assert photo.license == "unknown"
    assert photo.published_at == "2025-01-02"
    assert photo.retrieved_at == "2026-09-17"
    assert photo.source_domain == "commons.wikimedia.org"


def test_compute_stats_counts_tiers_and_duplicates():
    ctx = CampusContext(names=["Korea University"], lat=37.589, lng=127.032, geometry=CAMPUS, today=TODAY, lang="en")
    verified = evaluate(make_file(pageid=1, lat=37.590, lng=127.031, via_category="Korea University",
                                  title="File:Korea University hall.jpg"), ctx)
    unconfirmed = evaluate(make_file(pageid=2), ctx)
    verified.duplicates.append(make_file(pageid=3))
    stats = compute_stats([to_photo(verified, TODAY), to_photo(unconfirmed, TODAY)])
    assert (stats.photos, stats.verified, stats.likely, stats.hidden, stats.duplicates) == (2, 1, 0, 1, 1)


def test_first_sentences_trims_long_extracts():
    assert first_sentences("One. Two! Three? Four. Five.", limit=3) == "One. Two! Three?"
