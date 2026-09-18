"""Content rules from QA wave B: people/events (MIT), science samples (NU), other institutions via categories (Cambridge)."""

from dataclasses import replace

from app.services.pipeline import score
from tests.pipeline.conftest_data import CTX, raw, weights

INSIDE = dict(lat=37.590, lng=127.034)
IN_LIBRARY = dict(lat=37.5885, lng=127.0305)
MIT = replace(CTX, names=["Massachusetts Institute of Technology", "MIT"])


def content_labels(photo) -> list[str]:
    return [e.label for e in photo.evidence if e.type == "content"]


# ---------- P1: people and events ----------


def test_protests_speeches_and_officials_are_capped():
    for title in [
        "File:20240515 MIT pro Palestine and pro Israel protest 02.jpg",
        "File:20240510 MIT pro-Palestinian protests.jpg",
        "File:20240506 Polices at MIT pro-Palestinian protests 02.jpg",
        "File:MIT Rally for Ukraine at Killian Court 20220228.jpg",
        "File:Secretary Kerry Speaks With the State Department's Trudeau Before Delivering a Speech at MIT.jpg",
        "File:Secretary Kerry Delivers a Speech on Climate Change at MIT in Cambridge, Mass..jpg",
        "File:Secretary Kerry Shakes Hands With Business Leaders Before Speaking at MIT.jpg",
        "File:Hanging out with the smart people at MIT tonight.jpg",
        "File:Women in Science.jpg",
        "File:MIT students march for climate justice.jpg",
        "File:Student strike at MIT.jpg",
        "File:MIT sit-in at the president's office.jpg",
    ]:
        p = score(raw(**INSIDE, title=title), MIT)
        assert p.tier == "unconfirmed", title
        assert weights(p)["content"] < 0, title


def test_multilingual_people_and_events():
    for title in [
        "File:Митинг студентов у главного корпуса.jpg", "File:Речь министра в университете.jpg",
        "File:고려대학교 집회.jpg", "File:고려대학교 총학생회 시위.jpg",
        "File:Manifestación en la Facultad.jpg", "File:Visita a la Universidad de Nazarbayev.jpg",
        "File:Grève des étudiants.jpg", "File:Kundgebung vor der Universität.jpg",
    ]:
        assert "content" in weights(score(raw(**INSIDE, title=title), CTX)), title


def test_newsletter_is_not_a_campus_photo():
    assert score(raw(title="Research newsletter issue 50 cover.jpg"), CTX) is None


def test_charts_and_rankings_are_not_campus_photos():
    for title in ["File:KazNU QS 2012-2024.jpg", "File:Enrollment graph 2020.png", "File:Рейтинг университетов.jpg"]:
        assert score(raw(title=title, description="КазНУ им. Аль-Фараби", date_taken="2023-07-31"), CTX) is None, title


def test_event_and_people_categories_count():
    for categories in [
        ["Events at the Massachusetts Institute of Technology"],
        ["Images of people in science from Wiki Science Competition 2025"],
        ["Men at work in Kazakhstan"],
        ["2024 pro-Palestinian protests at MIT campus"],
        ["Photographs by the U.S. Department of State"],
    ]:
        p = score(raw(**INSIDE, title="File:MIT 2019.jpg", source_categories=categories), MIT)
        assert p.tier == "unconfirmed", categories
        assert weights(p)["content"] < 0, categories


def test_places_named_like_events_are_not_people():
    for title, description, categories in [
        ("File:Speech Hall.jpg", "", []),
        ("File:Rally Point building.jpg", "", []),
        ("File:Police station near campus.jpg", "", []),
        ("File:Protestant chapel.jpg", "", []),
        ("File:Demonstration garden.jpg", "", []),
        ("File:Campus in March 2020.jpg", "", []),
        ("File:Speech and Hearing Sciences Building.jpg", "", ["Buildings of MIT"]),
        ("File:MIThenge2.jpg", "There were a ton of people in the 3rd floor corridor", []),
        ("File:ATM.jpg", "The modem for this ATM was hanging out in an unsecure fashion.", []),
        ("File:Jardín Botánico.jpg", "La foto corresponde a una visita guiada del mes de agosto", []),
        ("File:Здание министерства.jpg", "", []),
        ("File:안암 경찰서.jpg", "", []),
        ("File:MIT Police headquarters.jpg", "", ["Massachusetts Institute of Technology Police Department"]),
        ("File:Event venue.jpg", "", ["Event venues in Massachusetts"]),
    ]:
        p = score(raw(**INSIDE, title=title, description=description, source_categories=categories), MIT)
        assert "content" not in weights(p), title


# ---------- P2: science samples ----------


def test_microscopy_is_not_a_place():
    for kwargs in [
        dict(title="File:AFM image of the superhydrophobic surface.png"),
        dict(title="File:SEM micrograph of pollen.jpg"),
        dict(title="File:White eyed drosophila.jpg", description="A mutant strain observed under the light microscope"),
        dict(title="File:Bacteria planet.jpg", source_categories=["Microscopy images from Wiki Science Competition 2025"]),
        dict(title="File:AFM Collagen.jpg", source_categories=["Atomic force micrographs"]),
        dict(title="File:3D Neuroblast.jpg", source_categories=["Non-photographic media from Wiki Science Competition 2025"]),
    ]:
        assert score(raw(**IN_LIBRARY, **kwargs), CTX) is None, kwargs


def test_samples_and_experiments_are_capped_despite_geo_and_building():
    for kwargs in [
        dict(title="File:Superhydrophobic surface.JPG", description="A superhydrophobic property on a copper plate."),
        dict(title="File:Water on copper plate.JPG", description="The copper plate before achieving superhydrophobicity."),
        dict(title="File:Biology laboratory work, bacteria- bacillus subtilies.JPG"),
        dict(title="File:Drosophilla brain.jpg", description="Aligned brains for treatment with nanoparticles"),
        dict(title="File:Lilac.jpg", source_categories=["Nature category images from Russian Science Photo Competition 2022"]),
    ]:
        p = score(raw(**IN_LIBRARY, **kwargs), CTX)
        assert p.tier == "unconfirmed", kwargs
        assert any("sample" in label for label in content_labels(p)), kwargs


def test_food_closeups_are_capped_despite_geo_and_category():
    p = score(raw(**INSIDE, matched_category="Korea University", title="File:Pizza at Korea University cafeteria.jpg"), CTX)
    assert p.tier == "unconfirmed"
    assert any("food" in label for label in content_labels(p))


def test_lab_rooms_and_places_with_science_words_stay_places():
    for title, description in [
        ("File:Renewable Energy Laboratory at Korea University.JPG", "Renewable Energy Laboratory"),
        ("File:Biology laboratory 2026.jpg", "Biology laboratory sample making."),
        ("File:Stage of Cell Observer.JPG", "Part of the microscopy facility of the university"),
        ("File:Molecular Beam Epitaxy System.jpg", ""),
        ("File:Sample Gates.jpg", ""),
        ("File:Crystal Hall.jpg", ""),
        ("File:Old dissecting room.jpg", "The interior of the Department of Anatomy"),
    ]:
        p = score(raw(**INSIDE, title=title, description=description), CTX)
        assert "content" not in weights(p), title
    assert "labs" in score(raw(**INSIDE, title="File:Renewable Energy Laboratory.JPG"), CTX).tags


# ---------- P3: another institution through categories ----------

CAMBRIDGE = replace(CTX, names=["University of Cambridge", "Cambridge University"])


def test_other_institution_through_matched_subcategory():
    for title in ["File:Addenbrooke's smokers - geograph.org.uk - 5308352.jpg",
                  "File:Addenbrooke's Treatment Centre - geograph.org.uk - 8359353.jpg"]:
        p = score(raw(**INSIDE, title=title, matched_category="Addenbrooke's Hospital", matched_subcategory=True),
                  CAMBRIDGE)
        assert p.tier == "unconfirmed", title
        assert any("Addenbrooke's Hospital" in label for label in content_labels(p))


def test_other_institution_through_file_categories():
    p = score(raw(**INSIDE, title="File:Entrance to F and G Block.jpg", matched_category="University of Cambridge",
                  source_categories=["Hospitals in Cambridgeshire"]), CAMBRIDGE)
    assert p.tier == "unconfirmed"
    assert weights(p)["content"] < 0


def test_university_named_categories_and_hospital_universities_are_not_other_institutions():
    # The university's own medical centre category also holds its college of medicine.
    p = score(raw(**INSIDE, title="File:고려대학교 의과대학.jpg", matched_category="Korea University",
                  source_categories=["Korea University Medical Center"]), CTX)
    assert "content" not in weights(p)
    # A university that is itself a hospital-named institution.
    hospital_uni = replace(CTX, names=["Hospital University of Somewhere"])
    p = score(raw(**INSIDE, title="File:Main gate.jpg", matched_category="Hospital University of Somewhere"),
              hospital_uni)
    assert "content" not in weights(p)
