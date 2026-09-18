from app.models import Building, CampusShape
from app.services.pipeline.ranking import DEFAULT_TARGETS
from app.services.query_planner import build_query_plan, polygon_search_centers
from app.services.wikidata import UniversityRecord


def test_query_plan_carries_names_polygon_subjects_and_targets():
    uni = UniversityRecord(
        wikidata_id="Q1", name="Test University", name_en="Test University",
        names=["Test University", "Тест университеті", "테스트대학교"],
        lat=51.1, lng=71.4, website="https://example.edu", commons_category="Test University",
        ror_id=None, city=None, country=None, wikipedia_titles={}, city_center=None,
    )
    polygon = [[71.39, 51.09], [71.41, 51.09], [71.41, 51.11], [71.39, 51.11], [71.39, 51.09]]
    building = Building(id="b1", name="Central Library", type="library", polygon=polygon,
                        height_m=None, levels=None, photo_ids=[], source="OSM", inside_campus=True)
    plan = build_query_plan(uni, CampusShape(polygon=polygon, area_km2=1, osm_url=None, buildings=[building]))
    assert plan.polygon == polygon and plan.bbox == (71.39, 51.09, 71.41, 51.11)
    assert plan.geosearch_centers and len(plan.geosearch_centers) <= 9
    assert [subject.kind for subject in plan.subjects] == ["university", "building"]
    assert plan.category_targets == DEFAULT_TARGETS and sum(plan.category_targets.values()) > 0


def test_point_only_plan_has_one_kilometre_search_circle():
    assert polygon_search_centers(None, 1.0, 2.0) == [(1.0, 2.0, 1000)]
