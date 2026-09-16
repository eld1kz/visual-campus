"""Why do we believe a photo shows this campus? Evidence, confidence, tier, category and tags.

Pure functions: no network, so the rules are unit-tested (tests/test_evidence.py).
"""

import math
import re
from dataclasses import dataclass, field
from datetime import date

from shapely.geometry import Point
from shapely.geometry.base import BaseGeometry

from app.services.commons import CommonsFile
from app.services.osm import KM_PER_DEGREE, distance_m
from app.services.text import normalize

BASE_CONFIDENCE = 40
VERIFIED_FROM = 80
LIKELY_FROM = 60
OLD_PHOTO_YEARS = 15

W_GEO_INSIDE = 28
W_GEO_NEAR_POINT = 20
W_GEO_JUST_OUTSIDE = 6
W_GEO_AWAY = -10
W_GEO_FAR = -30
W_NO_GEO = -10
W_CATEGORY = 22
W_SUBCATEGORY = 16
W_NAME_IN_TEXT = 14
W_NO_LICENSE = -12
W_OLD = -10
W_PEOPLE_OR_EVENT = -15

_NOT_A_PHOTO = re.compile(
    r"\blogo|emblem|\bseal\b|coat of arms|\bicon\b|diagram|floor ?plan|\bmap of\b|\bchart\b|signature|screenshot|"
    r"로고|엠블럼|логотип|герб",
    re.IGNORECASE,
)
_PEOPLE_OR_EVENT = re.compile(
    r"portrait|headshot|delegation|gala|conference|ceremony|meeting|official visit|press|award|"
    r"초상|기자회견|делегац|визит|церемони|конференц",
    re.IGNORECASE,
)
_LIBRARY = re.compile(r"librar|도서관|библиотек|図書館|bibliothek", re.IGNORECASE)
_DORM = re.compile(r"dormitor|\bdorms?\b|residence hall|student housing|기숙사|학생생활관|общежит|wohnheim", re.IGNORECASE)
_CLASSROOM = re.compile(r"classroom|lecture|auditorium|seminar room|강의실|강당|аудитор|hörsaal", re.IGNORECASE)
_SPORT = re.compile(r"stadium|gymnas|\bgym\b|sport|athlet|arena|체육|운동장|стадион|спорт", re.IGNORECASE)
_LAB = re.compile(r"\blabs?\b|laborator|연구실|실험실|лаборатор", re.IGNORECASE)
_STUDENT_LIFE = re.compile(
    r"festival|student|club|concert|cafe|café|edit-a-thon|graduation|축제|동아리|학생|студент|фестивал",
    re.IGNORECASE,
)

LABELS = {
    "ru": {
        "geo_inside": "Геотег внутри границ кампуса, {d} от центра",
        "geo_near_point": "Геотег в {d} от точки университета",
        "geo_just_outside": "Геотег в {d} за границей кампуса",
        "geo_away": "Геотег в {d} от кампуса",
        "no_geo": "Нет геотега",
        "category": "Находится в категории Commons «{c}»",
        "subcategory": "Находится в подкатегории Commons «{c}»",
        "name": "Описание упоминает «{n}»",
        "no_license": "Лицензия не указана на странице источника",
        "old": "Снимок {y} года — кампус мог измениться",
        "people": "Похоже на фото людей или мероприятия, а не места",
    },
    "en": {
        "geo_inside": "Geotag inside campus boundary, {d} from centre",
        "geo_near_point": "Geotag {d} from the university point",
        "geo_just_outside": "Geotag {d} outside campus boundary",
        "geo_away": "Geotag {d} from campus",
        "no_geo": "No geotag",
        "category": "In Commons category “{c}”",
        "subcategory": "In Commons subcategory “{c}”",
        "name": "Description mentions “{n}”",
        "no_license": "No license stated on source page",
        "old": "Taken in {y} — the campus may have changed",
        "people": "Looks like a photo of people or an event, not a place",
    },
}


@dataclass
class CampusContext:
    names: list[str]
    lat: float | None
    lng: float | None
    geometry: BaseGeometry | None
    today: date
    lang: str = "ru"


@dataclass
class Evaluation:
    file: CommonsFile
    evidence: list[dict]
    confidence: int
    tier: str
    category: str
    tags: list[str]
    duplicates: list[CommonsFile] = field(default_factory=list)


def _fmt_distance(meters: float, lang: str) -> str:
    if meters < 1000:
        return f"{round(meters / 10) * 10:.0f} {'м' if lang == 'ru' else 'm'}"
    return f"{meters / 1000:.1f} {'км' if lang == 'ru' else 'km'}"


def _boundary_distance_m(geometry: BaseGeometry, point: Point) -> float:
    degrees = geometry.distance(point)
    return degrees * KM_PER_DEGREE * 1000 * math.cos(math.radians(point.y))


def _geo_evidence(f: CommonsFile, ctx: CampusContext, t: dict) -> tuple[dict, bool | None]:
    """Returns the evidence item and whether the photo is on campus (None if unknown)."""
    if f.lat is None or f.lng is None or ctx.lat is None or ctx.lng is None:
        return {"type": "missing", "label": t["no_geo"], "weight": W_NO_GEO}, None

    from_center = distance_m(ctx.lat, ctx.lng, f.lat, f.lng)
    if ctx.geometry is not None:
        point = Point(f.lng, f.lat)
        if ctx.geometry.contains(point):
            d = _fmt_distance(from_center, ctx.lang)
            return {"type": "geo", "label": t["geo_inside"].format(d=d), "weight": W_GEO_INSIDE}, True
        away = _boundary_distance_m(ctx.geometry, point)
    else:
        if from_center <= 500:
            d = _fmt_distance(from_center, ctx.lang)
            return {"type": "geo", "label": t["geo_near_point"].format(d=d), "weight": W_GEO_NEAR_POINT}, True
        away = from_center

    d = _fmt_distance(away, ctx.lang)
    if away <= 1000:
        return {"type": "geo", "label": t["geo_just_outside"].format(d=d), "weight": W_GEO_JUST_OUTSIDE}, False
    weight = W_GEO_AWAY if away <= 3000 else W_GEO_FAR
    return {"type": "geo", "label": t["geo_away"].format(d=d), "weight": weight}, False


def _mentioned_name(text: str, names: list[str]) -> str | None:
    haystack = f" {normalize(text)} "
    for name in sorted(names, key=len, reverse=True):
        n = normalize(name)
        if n.isascii():
            # Latin names must start at a word boundary ("KU" must not match "kumc").
            if len(n) >= 4 and f" {n}" in haystack:
                return name
        # Korean/Japanese/Chinese titles often glue words and numbers together: "2006고려대학교19".
        elif len(n) >= 3 and n in haystack:
            return name
    return None


def classify(f: CommonsFile, on_campus: bool | None) -> tuple[str, list[str]]:
    text = " ".join([f.title, f.description, *f.categories])
    if _LIBRARY.search(text):
        category = "libraries"
    elif _DORM.search(text):
        category = "dorms"
    elif _CLASSROOM.search(text):
        category = "classrooms"
    elif on_campus is False:
        category = "city"
    else:
        category = "campus"

    tags = []
    if _DORM.search(text):
        tags.append("dorm")
    if _SPORT.search(text):
        tags.append("sport")
    if _LAB.search(text):
        tags.append("labs")
    if _STUDENT_LIFE.search(text):
        tags.append("student_life")
    return category, tags


def evaluate(f: CommonsFile, ctx: CampusContext) -> Evaluation | None:
    """None when the file is not a photo of a place (logos, maps, diagrams)."""
    text = " ".join([f.title, f.description, *f.categories])
    if _NOT_A_PHOTO.search(f"{f.title} {f.description}"):
        return None

    t = LABELS.get(ctx.lang, LABELS["en"])
    evidence = []
    geo, on_campus = _geo_evidence(f, ctx, t)
    evidence.append(geo)

    if f.via_category:
        key, weight = ("subcategory", W_SUBCATEGORY) if f.via_subcategory else ("category", W_CATEGORY)
        evidence.append({"type": "category", "label": t[key].format(c=f.via_category), "weight": weight})

    name = _mentioned_name(f"{f.title} {f.description}", ctx.names)
    if name:
        evidence.append({"type": "text", "label": t["name"].format(n=name), "weight": W_NAME_IN_TEXT})

    if on_campus is not True and _PEOPLE_OR_EVENT.search(text):
        evidence.append({"type": "content", "label": t["people"], "weight": W_PEOPLE_OR_EVENT})

    if not f.license:
        evidence.append({"type": "missing", "label": t["no_license"], "weight": W_NO_LICENSE})

    year = int(f.date_taken[:4]) if f.date_taken else None
    if year and year < ctx.today.year - OLD_PHOTO_YEARS:
        evidence.append({"type": "date", "label": t["old"].format(y=year), "weight": W_OLD})

    confidence = max(0, min(100, BASE_CONFIDENCE + sum(e["weight"] for e in evidence)))
    tier = "verified" if confidence >= VERIFIED_FROM else "likely" if confidence >= LIKELY_FROM else "unconfirmed"
    category, tags = classify(f, on_campus)
    return Evaluation(file=f, evidence=evidence, confidence=confidence, tier=tier, category=category, tags=tags)


_COPY_SUFFIX = re.compile(r"\s*\((cropped|crop|edited|retouched|\d+)\)|\s*-\s*panoramio", re.IGNORECASE)


def _title_stem(title: str) -> str:
    stem = title.removeprefix("File:").rsplit(".", 1)[0]
    return normalize(_COPY_SUFFIX.sub("", stem))


def deduplicate(evaluations: list[Evaluation]) -> list[Evaluation]:
    """Identical files (same SHA-1) or crops/edits of the same title keep only the most confident copy."""
    kept: dict[str, Evaluation] = {}
    stems: dict[str, str] = {}
    for ev in sorted(evaluations, key=lambda e: e.confidence, reverse=True):
        own_key = ev.file.sha1 or f"page:{ev.file.pageid}"
        stem = _title_stem(ev.file.title)
        original = own_key if own_key in kept else stems.get(stem)
        if original:
            kept[original].duplicates.append(ev.file)
            continue
        kept[own_key] = ev
        stems[stem] = own_key
    return list(kept.values())
