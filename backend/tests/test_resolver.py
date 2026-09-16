from app.services.hits import SourceHit
from app.services.resolver import decide, merge, score
from app.services.text import similarity


def test_similarity_bands():
    assert similarity("KAIST", "KAIST") == 1.0
    assert similarity("Koera Univrsity", "Korea University") >= 0.9
    # Containment never reaches the "exact" band.
    assert 0.6 <= similarity("Cambridge", "University of Cambridge") < 0.9
    # Sharing only a generic word is not a match.
    assert similarity("Xyzzqq Blorft Institute", "Cockcroft Institute") <= 0.5


def _ror(name, city, **kw):
    return SourceHit(source="ror", name=name, city=city, ror_id=kw.pop("ror_id", name.lower()), **kw)


def _wd(name, city, **kw):
    return SourceHit(source="wikidata", name=name, city=city, **kw)


def test_merge_joins_sources_by_wikidata_id():
    groups = merge(
        [_ror("Korea University", "Seoul", wikidata_ids=["Q39997"])],
        [_wd("Korea University", "Seoul", wikidata_ids=["Q39997"], sitelinks=60)],
    )
    assert len(groups) == 1
    assert groups[0].ror and groups[0].wikidata


def test_well_known_exact_match_is_resolved():
    groups = merge(
        [_ror("Korea University", "Seoul", wikidata_ids=["Q39997"]), _ror("Korea University", "Tokyo")],
        [_wd("Korea University", "Seoul", wikidata_ids=["Q39997"], sitelinks=60)],
    )
    for g in groups:
        score(g, "Korea University", None)
    status, ranked = decide(groups, "Korea University")
    assert status == "resolved"
    assert ranked[0].ror.city == "Seoul"


def test_query_that_names_a_city_stays_ambiguous():
    groups = merge(
        [_ror("University of Cambridge", "Cambridge", aliases=["Cambridge"], wikidata_ids=["Q35794"])],
        [_wd("University of Cambridge", "Cambridge", aliases=["Cambridge"], wikidata_ids=["Q35794"], sitelinks=200)],
    )
    for g in groups:
        score(g, "Cambridge", None)
    status, _ = decide(groups, "Cambridge")
    assert status == "ambiguous"


def test_nothing_similar_is_not_found():
    groups = merge([_ror("Cockcroft Institute", "Daresbury")], [])
    for g in groups:
        score(g, "Xyzzqq Blorft Institute", None)
    assert decide(groups, "Xyzzqq Blorft Institute")[0] == "not_found"
