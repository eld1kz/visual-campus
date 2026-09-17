from app.services.pipeline import score
from tests.pipeline.conftest_data import CTX, raw

IN_LIBRARY = dict(lat=37.5885, lng=127.0305)


def test_osm_building_sets_category_and_evidence():
    p = score(raw(**IN_LIBRARY, title="File:IMG 2041.jpg"), CTX)
    assert p.category == "libraries"
    assert any(e.type == "category" and "Central Library" in e.label for e in p.evidence)


def test_subcategory_name_beats_text():
    p = score(raw(matched_category="Korea University Library", matched_subcategory=True,
                  title="File:Korea University lecture.jpg"), CTX)
    assert p.category == "libraries"


def test_text_keywords_set_category():
    assert score(raw(title="File:고려대학교 중앙도서관.jpg"), CTX).category == "libraries"
    assert score(raw(description="고려대학교 세종학술정보원"), CTX).category == "libraries"
    assert score(raw(title="File:Student dormitory.jpg"), CTX).category == "dorms"
    assert score(raw(title="File:Lecture room 101.jpg"), CTX).category == "classrooms"


def test_labs_only_on_explicit_signs():
    assert "labs" in score(raw(title="File:Renewable Energy Laboratory.jpg"), CTX).tags
    assert "labs" in score(raw(title="File:Clean room", description="Laboratory equipment"), CTX).tags
    people_in_lab = raw(title="File:RAs at Nazarbayev University.jpg",
                        description="three research assistants working on their project in laboratory")
    assert "labs" not in score(people_in_lab, CTX).tags
    assert "labs" not in score(raw(title="File:Young researchers.jpg", description="Researchers at work"), CTX).tags


def test_tags_are_contract_values():
    p = score(raw(title="File:Dormitory gym and student festival lab.jpg"), CTX)
    assert set(p.tags) <= {"sport", "labs", "dorm", "student_life"}
    assert len(p.tags) == len(set(p.tags))
