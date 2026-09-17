"""Text patterns: what is not a place, people/events, other institutions, category and tags.

Multilingual (en/ru/ko + common European words), matched case-insensitively.
"""

import re

from app.models import Building, RawImage

_I = re.IGNORECASE

# Not a photo of a place at all: symbols, maps, printed matter, artworks. Checked on title + description.
NOT_A_PHOTO = re.compile(
    r"\blogo|emblem|\bseal\b|coat of arms|\bicons?\b|diagram|floor ?plan|\bmap of\b|\bchart\b|signature|screenshot|"
    r"\bflyers?\b|\bleaflet|brochure|\bposters?\b|\bcovers?\b|\bdocument|certificate|diploma|\bstamps?\b|"
    r"banknote|\bbook page|page of the book|\bscan(ned)?\b|magazine|newspaper|\bpainting|artwork|lithograph|"
    r"engraving|calligraph|manuscript|book-?plates?|ex libris|\bsymbol\b|\.(pdf|djvu|svg)$|"
    r"revista|peri[oó]dico|edici[oó]n \d|portada|cartel\b|affiche|couverture|plakat|urkunde|zertifikat|briefmarke|"
    r"로고|엠블럼|포스터|전단|표지|문서|증명서|상장|우표|지폐|"
    r"логотип|герб|афиш|плакат|листовк|буклет|обложк|документ|диплом|сертификат|грамот|почтов\w* марк|банкнот|"
    r"\bскан|журнал|газет|картин",
    _I,
)
# Same idea for the file's own Commons categories, but only when the category *is* such a collection.
NOT_A_PHOTO_CATEGORY = re.compile(
    r"^(logos?|maps?|diagrams?|posters?|flyers?|documents?|scans?|scanned|certificates?|diplomas?|stamps?|"
    r"banknotes?|book covers?|magazine covers?|covers?|coats? of arms|seals?|signatures?|screenshots?|paintings?)\b",
    _I,
)

# People, portraits and events: a photo of who was there, not of the place.
PEOPLE_OR_EVENT = re.compile(
    r"portrait|headshot|selfie|delegation|\bgala\b|conference(?!\s*(hall|room|cent|building))|ceremony|"
    r"meeting(?!\s*(hall|room|house|point))|official visit|\bvisit (by|of|to)\b|\bpress\b|\bawards?\b|celebration|"
    r"graduation|\bteam\b|research assistants?|\bRAs\b|researchers?\b|professor|chemist|physicist|scientist|"
    r"biologist|\bpresident\b|\brector\b|\bdean\b|minister|ambassador|supervisor|\bgirl\b|\bprime minister|"
    r"\bdelivering\b|\bspeech\b|\bspeaking\b|\bseminar\b(?!\s*(room|hall))|\bsigning\b|visitors?'? book|handshake|"
    r"초상|기자회견|총장|교수|졸업식|시상식|"
    r"портрет|делегац|визит|церемони|конференц|встреч|выпускн|награжд|профессор|ректор",
    _I,
)
# Commons categories that are about a person: "1920 births", "Chemists from South Korea", "Alumni of …".
PERSON_CATEGORY = re.compile(
    r"\b\d{3,4}s? (births|deaths)\b|^(alumni|faculty|people|men|women|politicians|scientists|chemists|physicists|"
    r"professors|presidents|rectors|writers|poets|actors|singers|athletes)\b|^portrait|portraits? of\b",
    _I,
)
# A different institution that shares the university's name: school, hospital, clinic.
OTHER_INSTITUTION = re.compile(
    r"high school|middle school|secondary school|elementary school|primary school|kindergarten|"
    r"hospital|medical cent(er|re)|\bclinic\b|"
    r"고등학교|중학교|초등학교|유치원|병원|의료원|"
    r"больниц|госпитал|клиник|лицей|гимнази|детский сад|"
    r"krankenhaus|klinikum|hôpital|hospital",
    _I,
)

LIBRARY = re.compile(r"librar|도서관|학술정보원|библиотек|図書館|bibliothek|biblioth[eè]que|biblioteca", _I)
DORM = re.compile(r"dormitor|\bdorms?\b|residence hall|student housing|기숙사|학생생활관|общежит|wohnheim", _I)
CLASSROOM = re.compile(r"classroom|lecture|auditorium|seminar room|강의실|강당|аудитор|hörsaal", _I)
SPORT = re.compile(r"stadium|gymnas|\bgym\b|sport|athlet|arena|체육|운동장|стадион|спорт", _I)
LAB = re.compile(r"\blabs?\b|laborator|연구실|실험실|лаборатор", _I)
STUDENT_LIFE = re.compile(
    r"festival|student|club|concert|cafe|café|edit-a-thon|graduation|축제|동아리|학생|студент|фестивал", _I
)

BUILDING_CATEGORY = {"library": "libraries", "dorm": "dorms"}
BUILDING_TAG = {"dorm": "dorm", "sport": "sport", "lab": "labs"}


def own_text(raw: RawImage) -> str:
    return f"{raw.title} {raw.description}"


def all_text(raw: RawImage) -> str:
    return " ".join([raw.title, raw.description, *raw.source_categories])


def is_not_a_place(raw: RawImage) -> bool:
    return bool(NOT_A_PHOTO.search(own_text(raw)) or any(NOT_A_PHOTO_CATEGORY.search(c) for c in raw.source_categories))


def is_people_or_event(raw: RawImage) -> bool:
    return bool(PEOPLE_OR_EVENT.search(all_text(raw)) or any(PERSON_CATEGORY.search(c) for c in raw.source_categories))


def other_institution(raw: RawImage, names: list[str]) -> str | None:
    """The matched word, unless the university itself is named that way (e.g. a medical university's hospital)."""
    match = OTHER_INSTITUTION.search(own_text(raw))
    if not match:
        return None
    if any(OTHER_INSTITUTION.search(n) for n in names):
        return None
    return match.group(0)


def classify(
    raw: RawImage, on_campus: bool | None, linked: bool, building: Building | None, seen: str | None = None
) -> tuple[str, list[str]]:
    """One category and contract tags, from the most reliable signal down (docs/CONTRACT.md §6)."""
    tags: list[str] = []
    category = None

    # 1. Metadata: the university subcategory the file came from, the OSM building the geotag falls into.
    sub = raw.matched_category if raw.matched_subcategory else ""
    if sub and LIBRARY.search(sub):
        category = "libraries"
    elif sub and DORM.search(sub):
        category = "dorms"
    elif building is not None and building.type in BUILDING_CATEGORY:
        category = BUILDING_CATEGORY[building.type]
    if building is not None and building.type in BUILDING_TAG:
        tags.append(BUILDING_TAG[building.type])

    # 2. Text of the title, description and the file's own categories.
    text = all_text(raw)
    if category is None:
        if LIBRARY.search(text):
            category = "libraries"
        elif DORM.search(text):
            category = "dorms"
        elif CLASSROOM.search(text):
            category = "classrooms"

    # 3. What the CLIP model sees (library reading room, lecture hall, dorm), when it is sure it is a place.
    if category is None and seen:
        category = seen
    # 4. Fallback: city only on positive signs that the photo is off campus and unrelated to the university.
    if category is None:
        category = "city" if on_campus is False and not linked else "campus"

    people = is_people_or_event(raw)
    if DORM.search(text):
        tags.append("dorm")
    if SPORT.search(text):
        tags.append("sport")
    # Labs only on explicit signs: the title or a category says lab; a description counts unless it is about people.
    if LAB.search(raw.title) or (
        not people and (LAB.search(raw.description) or any(LAB.search(c) for c in raw.source_categories))
    ):
        tags.append("labs")
    if STUDENT_LIFE.search(text):
        tags.append("student_life")
    return category, list(dict.fromkeys(tags))
