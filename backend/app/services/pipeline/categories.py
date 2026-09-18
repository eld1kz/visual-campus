"""Text patterns: what is not a place, people/events, other institutions, category and tags.

Multilingual (en/ru/ko + common European words), matched case-insensitively.
"""

import re
from functools import lru_cache

from app.models import Building, RawImage

_I = re.IGNORECASE

# Not a photo of a place at all: symbols, maps, printed matter, artworks. Checked on title + description.
NOT_A_PHOTO = re.compile(
    r"\blogo|emblem|\bseal\b|coat of arms|\bicons?\b|diagram|floor ?plan|\bmap of\b|\bchart\b|signature|screenshot|"
    r"wordmark|masthead|nameplate|text-?only|typographic|newspaper title|"
    r"\bflyers?\b|\bleaflet|brochure|\bposters?\b|\bcovers?\b|\bnewsletter|\bdocument|certificate|diploma|\bstamps?\b|"
    r"banknote|\bbook page|page of the book|\bscan(ned)?\b|magazine|newspaper|\bpainting|artwork|lithograph|"
    r"engraving|calligraph|manuscript|book-?plates?|ex libris|\bsymbol\b|\.(pdf|djvu|svg)$|"
    r"revista|peri[oó]dico|edici[oó]n \d|portada|cartel\b|affiche|couverture|plakat|urkunde|zertifikat|briefmarke|"
    r"로고|엠블럼|포스터|전단|표지|문서|증명서|상장|우표|지폐|"
    r"логотип|герб|афиш|плакат|листовк|буклет|обложк|документ|диплом|сертификат|грамот|почтов\w* марк|банкнот|"
    r"\bскан|журнал|газет|картин|"
    # Charts and rankings: "KazNU QS 2012-2024.jpg" is a line chart that OpenCLIP took for a campus place.
    r"\brankings?\b|\bqs (world|university|rankings?|\d{4})|\bgraph\b|infographic|statistics?\b|рейтинг|график|инфографик|статистик|"
    # Microscopy: an image of a specimen, not of any place.
    r"micrograph|\b(afm|sem|tem|stm|confocal|fluorescence|atomic force|electron)( microscop(e|y))? (images?|scans?)\b|"
    r"under (an? |the )?(\w+ )?microscope|микрофотограф|под микроскопом|현미경 사진",
    _I,
)
# Same idea for the file's own Commons categories, but only when the category *is* such a collection.
NOT_A_PHOTO_CATEGORY = re.compile(
    r"^(logos?|maps?|diagrams?|posters?|flyers?|documents?|scans?|scanned|certificates?|diplomas?|stamps?|"
    r"banknotes?|book covers?|magazine covers?|covers?|coats? of arms|seals?|signatures?|screenshots?|paintings?|"
    r"newspapers?|student newspapers?|periodicals?|publications?|mastheads?|wordmarks?|"
    r"micrographs?|microscop(y|ic) images|microscopy category images|"
    r"(atomic force|scanning electron|transmission electron|confocal) micro\w+|"
    r"non-photographic media)\b|\bmicrographs\b",
    _I,
)

# People, portraits and events: a photo of who was there, not of the place.
PEOPLE_OR_EVENT = re.compile(
    r"portrait|headshot|selfie|delegation|\bgala\b|conference(?!\s*(hall|room|cent|building))|ceremony|"
    r"meeting(?!\s*(hall|room|house|point))|official visit|\bvisit (by|of|to)\b|\bpress\b|\bawards?\b|celebration|"
    r"graduation|\bteam\b|research assistants?|\bRAs\b|researchers?\b|professor|chemist|physicist|scientist|"
    r"biologist|\bpresident\b|\brector\b|\bdean\b|minister|ambassador|supervisor|\bgirl\b|\bprime minister|"
    r"초상|기자회견|총장|교수|졸업식|시상식|"
    r"портрет|делегац|визит|церемони|конференц|встреч|выпускн|награжд|профессор|ректор|"
    # Protests, rallies, speeches, officials, police, groups of people. Place names are excluded explicitly:
    # "Protestant church", "Rally Point", "speech hall", "demonstration garden", "police station".
    r"\bprotest(?!ant)|\brall(y|ies)\b(?!\s*(point|hall|room|cent|building|house))|"
    r"\bmarch(es|ed|ing)? (for|against|on|through|in support)\b|\bprotest march|"
    r"\bdemonstrat(ion|ions|or|ors)\b(?!\s*(garden|farm|plant|site|house|building|school|reactor|forest|cent|room|lab))|"
    r"\bstrik(e|es|ers?)\b|\bsit-?ins?\b|\bencampment|\bvigil\b|\bcommencement\b|"
    r"\bspeech(es)?\b(?!\s*(hall|room|cent|building|lab|and hearing|therap|science))|\bspeak(s|ing)\b|"
    r"\bdeliver(s|ing|ed)? (a |an |the |his |her |their )?(speech|address|remarks|lecture|talk|keynote)|"
    r"\bremarks\b|\bkeynote\b|\binterview|shak(e|es|ing) hands|handshake|\bsecretary\b|"
    r"\bpolice(s|man|men|woman|women| officers?)?\b(?!\s*(station|department|headquarters|hq|box|post|academy|"
    r"building|precinct|cars?|vehicles?))|hanging out with|\bpos(e|es|ed|ing)\b|"
    r"시위|집회|행진|파업|농성|연설|경찰(?!서)|셀카|악수|인터뷰|"
    r"протест|митинг|демонстрант|демонстраци(?!онн)|забастовк|пикет|шестви|\bречь\b|выступлени|полицейские|"
    r"министр(?!ерств)|\bпосол\b|госсекретар|селфи|рукопожат|интервью|"
    r"\bprotestas?\b|manifestaci[oó]n|manifestantes|\bmarcha\b|huelga|discurso|polic[ií]as\b|\bministr[oa]\b|"
    r"embajador|\bvisita (a|al|oficial)\b|entrevista|"
    r"\bmanifestation|\bmanifestants|\bgr[eè]ve\b|\bdiscours\b|rassemblement|\bpoliciers\b|\bministre\b|ambassadeur|"
    r"kundgebung|demonstranten|\bstreik|\brede (von|des|der)\b|polizisten|\bbotschafter|staatsbesuch",
    _I,
)
# Groups of people named in a title or category ("Women in Science", "People of Astana"). Not checked on descriptions,
# which mention people around a place: "a ton of people in the corridor".
GROUP_OF_PEOPLE = re.compile(r"\b(people|women|men|girls|boys|children|kids|crowds?) (in|at|of|with|during|from|on)\b", _I)
# Commons categories that group events or people rather than places: "Events in Astana", "Visits by …",
# "Images of people in science from Wiki Science Competition 2025", "Men at work in Kazakhstan".
EVENT_CATEGORY = re.compile(
    r"^(events?|visits?|speeches|rallies|demonstrations|strikes|interviews|press conferences|meetings) (in|at|of|by|to)\b|"
    r"^images of people\b|\b(men|women|people|scientists|chemists|biologists|physicists|engineers|students) at work\b|"
    r"^photographs by the u\.s\. department of state",
    _I,
)
# A sample or experiment in close-up (science photo contests): not a view of the campus. Lab rooms stay places.
SPECIMEN = re.compile(
    r"bacteri(a|as|al|um)\b|bacill|\bmicroscop(e|es|y|ic)\b(?!\s*(lab|facilit|cent|room|core|suite|unit))|"
    r"\bspecimens?\b|\bsamples\b|cell cultures?|petri dish|hydrophob|nanoparticle|\bmolecules?\b|"
    r"\bcrystals\b|\bsynthesi[sz]|"
    r"бактери|микроскоп|пробирк|박테리아|세균|현미경|시료|표본|muestras\b|bactéries|échantillons|bakterien",
    _I,
)
SPECIMEN_CATEGORY = re.compile(r"^nature category images\b", _I)
FOOD_CLOSEUP = re.compile(
    r"\bpizza|sandwich|burger|cake|cookie|coffee|latte|meal|dish|snack|plate of|food tray|lunch\b|"
    r"피자|샌드위치|커피|케이크|점심|음식|간식|"
    r"пицц|сэндвич|бургер|кофе|торт|еда|обед|блюдо|тарелк",
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

# Text verdicts are cached by (title, description, categories): the same image is re-scored when the campus polygon
# arrives, and these big patterns are most of score()'s time. Several profiles at ~500-1000 images each fit.
TEXT_CACHE_SIZE = 8192
_Text = tuple[str, str, tuple[str, ...]]


def _key(raw: RawImage) -> _Text:
    return raw.title, raw.description, tuple(raw.source_categories)


def own_text(raw: RawImage) -> str:
    return f"{raw.title} {raw.description}"


def all_text(raw: RawImage) -> str:
    return " ".join([raw.title, raw.description, *raw.source_categories])


def is_not_a_place(raw: RawImage) -> bool:
    return _not_a_place(*_key(raw))


def is_people_or_event(raw: RawImage) -> bool:
    return _people_or_event(*_key(raw))


def is_specimen(raw: RawImage) -> bool:
    return _specimen(*_key(raw))


def is_food_closeup(raw: RawImage) -> bool:
    return _food_closeup(*_key(raw))


@lru_cache(maxsize=TEXT_CACHE_SIZE)
def _not_a_place(title: str, description: str, categories: tuple[str, ...]) -> bool:
    return bool(NOT_A_PHOTO.search(f"{title} {description}") or any(NOT_A_PHOTO_CATEGORY.search(c) for c in categories))


@lru_cache(maxsize=TEXT_CACHE_SIZE)
def _people_or_event(title: str, description: str, categories: tuple[str, ...]) -> bool:
    return bool(
        PEOPLE_OR_EVENT.search(" ".join([title, description, *categories]))
        or GROUP_OF_PEOPLE.search(title)
        or any(GROUP_OF_PEOPLE.search(c) or PERSON_CATEGORY.search(c) or EVENT_CATEGORY.search(c) for c in categories)
    )


@lru_cache(maxsize=TEXT_CACHE_SIZE)
def _specimen(title: str, description: str, categories: tuple[str, ...]) -> bool:
    return bool(
        SPECIMEN.search(" ".join([title, description, *categories])) or any(SPECIMEN_CATEGORY.search(c) for c in categories)
    )


@lru_cache(maxsize=TEXT_CACHE_SIZE)
def _food_closeup(title: str, description: str, categories: tuple[str, ...]) -> bool:
    return bool(FOOD_CLOSEUP.search(" ".join([title, description, *categories])))


@lru_cache(maxsize=TEXT_CACHE_SIZE)
def _institution_in_text(title: str, description: str) -> str | None:
    match = OTHER_INSTITUTION.search(f"{title} {description}")
    return match.group(0) if match else None


@lru_cache(maxsize=TEXT_CACHE_SIZE)
def _text_classes(title: str, description: str, categories: tuple[str, ...]) -> tuple[str | None, tuple[str, ...]]:
    """Category and tags from the text alone (step 2 of classify), in classify's tag order."""
    text = " ".join([title, description, *categories])
    dorm = bool(DORM.search(text))
    category = "libraries" if LIBRARY.search(text) else "dorms" if dorm else "classrooms" if CLASSROOM.search(text) else None
    tags: list[str] = []
    if dorm:
        tags.append("dorm")
    if SPORT.search(text):
        tags.append("sport")
    # Labs only on explicit signs: the title or a category says lab; a description counts unless it is about people.
    if LAB.search(title) or (
        not _people_or_event(title, description, categories)
        and (LAB.search(description) or any(LAB.search(c) for c in categories))
    ):
        tags.append("labs")
    if STUDENT_LIFE.search(text):
        tags.append("student_life")
    return category, tuple(tags)


def other_institution(raw: RawImage, names: list[str]) -> str | None:
    """The matched word or category, unless the university itself is named that way (a medical university's hospital).

    Checks the title and description, then the category the file was found through and the file's own categories
    ("Addenbrooke's Hospital" as a subcategory of the University of Cambridge). A category named after the university
    itself ("Korea University Medical Center") is part of it and also holds its medical school buildings; those files
    count only when their own title or description names the other institution.
    """
    if any(OTHER_INSTITUTION.search(n) for n in names):
        return None
    match = _institution_in_text(raw.title, raw.description)
    if match:
        return match
    categories = [raw.matched_category, *raw.source_categories] if raw.matched_category else raw.source_categories
    own = [n.lower() for n in names if len(n) >= 4]
    return next((c for c in categories if OTHER_INSTITUTION.search(c) and not any(n in c.lower() for n in own)), None)


def classify(raw: RawImage, on_campus: bool | None, linked: bool, building: Building | None) -> tuple[str, list[str]]:
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
    text_category, text_tags = _text_classes(*_key(raw))
    if category is None:
        category = text_category

    # 3. Vision model — not available without LLM_API_KEY (see vision.py).
    # 4. Fallback: city only on positive signs that the photo is off campus and unrelated to the university.
    if category is None:
        category = "city" if on_campus is False and not linked else "campus"

    return category, list(dict.fromkeys([*tags, *text_tags]))
