from dataclasses import replace

from app.services.pipeline import score
from tests.pipeline.conftest_data import CTX, raw, weights

INSIDE = dict(lat=37.590, lng=127.034)


def test_inside_polygon_with_category_and_name_is_verified():
    p = score(raw(**INSIDE, matched_category="Korea University", title="File:Korea University main hall.jpg"), CTX)
    assert (p.tier, p.confidence, p.category) == ("verified", 100, "campus")
    assert weights(p)["geo"] > 0


def test_category_without_geotag_but_named_is_likely():
    p = score(raw(matched_category="Korea University", title="File:Korea University gate.jpg"), CTX)
    assert p.tier == "likely"
    assert weights(p)["missing"] < 0


def test_far_geotag_outweighs_the_category():
    p = score(raw(lat=37.513, lng=127.009, matched_category="Korea University", published_at="1971"), CTX)
    assert p.tier == "unconfirmed"
    assert weights(p)["geo"] < 0 and weights(p)["date"] == 0
    assert p.category == "campus"  # linked to the university: low confidence, but not "city"


def test_just_outside_without_link_goes_to_city():
    p = score(raw(lat=37.5955, lng=127.032, title="File:Anam street cafe.jpg", found_by="geosearch"), CTX)
    assert p.category == "city"
    assert "student_life" in p.tags
    assert "outside campus boundary" in p.evidence[0].label


def test_at_the_edge_with_category_stays_campus():
    # OSM boundaries miss heritage buildings at the edge (Korea_University_0a.jpg, 180 m outside).
    p = score(raw(lat=37.5955, lng=127.032, matched_category="Registered heritages in Korea University",
                  matched_subcategory=True, title="File:Korea University 0a.jpg"), CTX)
    assert p.category == "campus"
    assert p.tier == "verified"


def test_without_polygon_degrades_honestly_instead_of_city():
    ctx = replace(CTX, polygon=None)
    near = score(raw(lat=37.5895, lng=127.0325), ctx)
    spread = score(raw(lat=37.600, lng=127.032, matched_category="Korea University"), ctx)  # ~1.2 km
    far = score(raw(lat=37.62, lng=127.10), ctx)
    far_linked = score(raw(lat=37.62, lng=127.10, matched_category="Korea University"), ctx)
    assert weights(near)["geo"] > 0
    assert 0 < weights(spread)["geo"] < weights(near)["geo"]
    assert "boundary unknown" in spread.evidence[0].label
    assert spread.category == "campus" and spread.tier == "likely"
    assert weights(far)["geo"] < 0 and far.category == "city"
    assert far_linked.category == "campus"


def test_no_geotag_and_no_link_is_unconfirmed():
    p = score(raw(), CTX)
    assert p.tier == "unconfirmed"
    assert p.category == "campus"


def test_only_category_is_not_likely_without_name():
    assert score(raw(matched_category="Korea University"), CTX).tier == "unconfirmed"


def test_name_alone_stays_unconfirmed():
    p = score(raw(title="File:Korea University.jpg"), CTX)
    assert weights(p)["text"] > 0
    assert p.tier == "unconfirmed"


def test_honest_cap_blocks_non_place_evidence():
    # Positive weight from outside geo/category/text must not lift a photo above unconfirmed.
    from app.models import Evidence
    from app.services.pipeline.scoring import finalize

    confidence, tier = finalize([Evidence(type="vision", label="model", weight=40)])
    assert (confidence, tier) == (59, "unconfirmed")


def test_official_site_is_text_evidence():
    p = score(raw(source="official_site", source_domain="www.korea.ac.kr", found_by="site", title="Campus"), CTX)
    assert any(e.type == "text" and "korea.ac.kr" in e.label for e in p.evidence)
    assert p.tier == "likely"
    assert not any("license" in e.label.lower() for e in p.evidence)


def test_web_search_official_domain_can_be_likely_but_random_web_stays_hidden():
    official = score(raw(source="web_search", source_domain="www.korea.ac.kr", found_by="text",
                         title="Korea University campus 2025", license=None), CTX)
    random = score(raw(source="web_search", source_domain="example.com", found_by="text",
                       title="Korea University campus 2025", license=None), CTX)
    assert official.tier == "likely"
    assert random.tier == "unconfirmed"


def test_non_latin_name_glued_to_numbers_counts_as_mention():
    assert weights(score(raw(title="File:2006고려대학교19.jpg"), CTX))["text"] > 0


def test_short_alias_needs_word_boundary_and_upper_case():
    assert "text" not in weights(score(raw(title="File:KUMC hospital view.jpg"), CTX))
    assert "text" not in weights(score(raw(title="File:kudos.jpg"), CTX))
    assert weights(score(raw(title="File:KU Main Building.jpg"), CTX))["text"] > 0


def test_not_a_place_is_dropped():
    for title in [
        "File:Korea University logo.png", "File:Cambridge Antiuniversity event flyer.jpg",
        "File:Documento con las calificaciones.jpg", "File:Magazine cover 1925.jpg", "File:Poster.jpg",
        "File:Certificate of graduation.jpg", "File:Postage stamps.jpg", "File:고려대학교 포스터.jpg",
        "File:Обложка журнала.jpg", "File:Scan of the book page.jpg", "File:The Granite Tower wordmark.jpg",
    ]:
        assert score(raw(title=title), CTX) is None, title
    assert score(raw(source_categories=["Book covers of 1925"]), CTX) is None
    assert score(raw(source_categories=["Student newspapers published by universities"]), CTX) is None
    assert score(raw(title="File:Main Building.jpg"), CTX) is not None


def test_people_and_portraits_never_above_unconfirmed():
    cases = [
        raw(**INSIDE, matched_category="Korea University", title="File:Korea University President Lee.jpg"),
        raw(matched_category="Korea University", title="File:Cho Minhaeng Korea University chemist.jpg",
            source_categories=["Chemists from South Korea", "Alumni of Seoul National University"]),
        raw(**INSIDE, matched_category="Nazarbayev University", title="File:RAs at Nazarbayev University.jpg",
            description="three research assistants working on their research project in laboratory"),
        raw(**INSIDE, title="File:Someone.jpg", source_categories=["1920 births"]),
    ]
    for r in cases:
        p = score(r, CTX)
        assert p.tier == "unconfirmed", r.title
        assert weights(p)["content"] < 0


def test_place_words_do_not_trigger_people_rule():
    p = score(raw(**INSIDE, matched_category="Korea University", title="File:Korea University conference hall.jpg"), CTX)
    assert "content" not in weights(p)


def test_other_institution_is_penalised_and_capped():
    for title in ["File:Korea University High School Front Gate.jpg", "File:KUMC Anam Hospital.jpg",
                  "File:고려대학교 안산병원.jpg"]:
        p = score(raw(**INSIDE, matched_category="Korea University", title=title), CTX)
        assert p.tier == "unconfirmed", title
        assert any(e.type == "content" and "institution" in e.label for e in p.evidence)


def test_missing_license_is_penalised():
    with_license, without = score(raw(), CTX), score(raw(license=None, author=None), CTX)
    assert without.confidence < with_license.confidence or without.confidence == 0
    assert (without.license, without.author) == ("unknown", "unknown")
    assert any("license" in e.label for e in without.evidence)


def test_freshness_does_not_change_verification_tier():
    older = score(raw(matched_category="Korea University", title="File:Korea University.jpg", published_at="2022-07-27"), CTX)
    recent = score(raw(matched_category="Korea University", title="File:Korea University.jpg", published_at="2024-07-27"), CTX)
    assert weights(older)["date"] == 0 and weights(recent)["date"] == 0
    assert older.tier == recent.tier == "likely"
    assert older.freshness == "2020_2023" and recent.freshness == "2024_plus"


def test_unchecked_photo_cannot_be_verified():
    photo = score(raw(**INSIDE, matched_category="Korea University", title="File:Korea University main hall.jpg",
                      vision_checked=False), CTX)
    assert photo.tier == "likely" and photo.confidence == 79
    assert any(e.type == "missing" and "visually checked" in e.label for e in photo.evidence)


def test_labels_follow_language_and_retrieved_at_is_today():
    p = score(raw(**INSIDE), replace(CTX, lang="ru"))
    assert p.evidence[0].label.startswith("Геотег внутри")
    assert p.retrieved_at == "2026-09-17"


def test_photo_keeps_source_id():
    assert score(raw(id="flickr-555"), CTX).id == "flickr-555"
