"""score(): RawImage → Photo with evidence, confidence, tier, category and tags. Pure, no network."""

import math
import re
from dataclasses import dataclass, field
from datetime import date

import shapely
from shapely.geometry import Point, Polygon
from shapely.geometry.base import BaseGeometry
from shapely.ops import nearest_points
from shapely.strtree import STRtree

from app.models import Building, Evidence, Photo, RawImage
from app.services.pipeline import categories as cat
from app.services.pipeline.dates import date_evidence_label, effective_date_source, freshness
from app.services.pipeline.labels import fmt_distance, labels
from app.services.text import normalize

BASE_CONFIDENCE = 40
VERIFIED_FROM = 80
LIKELY_FROM = 60
UNCONFIRMED_MAX = LIKELY_FROM - 1

# Geotag with a known campus polygon.
W_GEO_INSIDE = 28
W_GEO_EDGE = 12  # ≤ EDGE_M outside: OSM boundaries often miss buildings at the edge
W_GEO_JUST_OUTSIDE = 4  # ≤ 1 km
# Geotag with only the university point: less certain, and big campuses spread far from the point.
W_GEO_NEAR_POINT = 20  # ≤ 500 m
W_GEO_POINT_NEARBY = 6  # ≤ 1.5 km
W_GEO_POINT_UNKNOWN = 0  # ≤ 3 km
# Both.
W_GEO_AWAY = -10  # ≤ 10 km without polygon, ≤ 3 km with it
W_GEO_FAR = -30
W_NO_GEO = -6
W_CATEGORY = 22
W_SUBCATEGORY = 16
W_BUILDING = 6
W_NAME_IN_TEXT = 14
W_OFFICIAL_SITE = 30
W_NO_LICENSE = -12
W_PEOPLE_OR_EVENT = -15
W_SPECIMEN = -15
W_OTHER_INSTITUTION = -20

EDGE_M = 250
# Showcase views named in the title/description; Claude flags the rest (vision_highlight).
HIGHLIGHT_TEXT = re.compile(
    r"main (building|gate|entrance|hall)|clock tower|campus (overview|panorama|view)|aerial|panorama|"
    r"главн\w* (корпус|здани|вход|ворот)|панорам|본관|정문|전경",
    re.IGNORECASE,
)
POSITIVE_TYPES = {"geo", "category", "text"}
BUILDING_TYPE_NAMES = {
    "ru": {"academic": "учебное", "dorm": "общежитие", "library": "библиотека", "sport": "спорт",
           "lab": "лаборатория", "food": "еда", "other": "другое"},
}


@dataclass
class CampusContext:
    names: list[str]
    lat: float | None
    lng: float | None
    polygon: BaseGeometry | None  # shapely, (lng, lat); None until OSM answers
    buildings: list[Building] = field(default_factory=list)
    official_domains: list[str] = field(default_factory=list)
    today: date = field(default_factory=date.today)
    lang: str = "ru"


def distance_m(lat1: float, lng1: float, lat2: float, lng2: float) -> float:
    p1, p2 = math.radians(lat1), math.radians(lat2)
    dp, dl = p2 - p1, math.radians(lng2 - lng1)
    h = math.sin(dp / 2) ** 2 + math.cos(p1) * math.cos(p2) * math.sin(dl / 2) ** 2
    return 6_371_000 * 2 * math.asin(math.sqrt(h))


def _outside_m(polygon: BaseGeometry, lat: float, lng: float) -> float:
    """Metres from the point to the polygon (≈, fine at campus scale)."""
    nearest, _ = nearest_points(polygon, Point(lng, lat))
    return distance_m(lat, lng, nearest.y, nearest.x)


def _ev(type_: str, label: str, weight: int) -> Evidence:
    return Evidence(type=type_, label=label, weight=weight)


def geo_evidence(raw: RawImage, ctx: CampusContext) -> tuple[Evidence, bool | None]:
    """The geo evidence and whether the photo is on campus: True, False, or None when we cannot tell."""
    t = labels(ctx.lang)
    if raw.lat is None or raw.lng is None:
        return _ev("missing", t["no_geo"], W_NO_GEO), None

    if ctx.polygon is not None:
        shapely.prepare(ctx.polygon)  # once: a no-op when already prepared
        if ctx.polygon.contains(Point(raw.lng, raw.lat)):
            center = ctx.polygon.centroid if ctx.lat is None or ctx.lng is None else Point(ctx.lng, ctx.lat)
            d = fmt_distance(distance_m(center.y, center.x, raw.lat, raw.lng), ctx.lang)
            return _ev("geo", t["geo_inside"].format(d=d), W_GEO_INSIDE), True
        away = _outside_m(ctx.polygon, raw.lat, raw.lng)
        d = fmt_distance(away, ctx.lang)
        if away <= EDGE_M:
            return _ev("geo", t["geo_edge"].format(d=d), W_GEO_EDGE), False
        if away <= 1000:
            return _ev("geo", t["geo_just_outside"].format(d=d), W_GEO_JUST_OUTSIDE), False
        weight = W_GEO_AWAY if away <= 3000 else W_GEO_FAR
        return _ev("geo", t["geo_away"].format(d=d), weight), False

    if ctx.lat is None or ctx.lng is None:
        return _ev("missing", t["no_geo"], W_NO_GEO), None
    # No polygon yet (or OSM failed): the point alone. Degrade honestly instead of calling the photo "city".
    away = distance_m(ctx.lat, ctx.lng, raw.lat, raw.lng)
    d = fmt_distance(away, ctx.lang)
    if away <= 500:
        return _ev("geo", t["geo_near_point"].format(d=d), W_GEO_NEAR_POINT), True
    if away <= 1500:
        return _ev("geo", t["geo_point"].format(d=d), W_GEO_POINT_NEARBY), None
    if away <= 3000:
        return _ev("geo", t["geo_point"].format(d=d), W_GEO_POINT_UNKNOWN), None
    weight = W_GEO_AWAY if away <= 10_000 else W_GEO_FAR
    return _ev("geo", t["geo_away"].format(d=d), weight), False


@dataclass
class _BuildingIndex:
    buildings: list[Building]  # the indexed list itself: keeps its id() from being reused while cached
    size: int
    shapes: list[tuple[Building, BaseGeometry]]  # prepared outlines, in list order
    tree: STRtree


_BUILDING_INDEXES: dict[int, _BuildingIndex] = {}
_BUILDING_INDEXES_MAX = 16  # a few profiles being built at once


def _building_index(buildings: list[Building]) -> _BuildingIndex:
    """Outlines are built and prepared once per buildings list (lists are replaced, not mutated, by callers)."""
    index = _BUILDING_INDEXES.get(id(buildings))
    if index is not None and index.buildings is buildings and index.size == len(buildings):
        return index
    shapes = [(b, Polygon(b.polygon)) for b in buildings if len(b.polygon) >= 4]
    for _, shape in shapes:
        shapely.prepare(shape)
    index = _BuildingIndex(buildings, len(buildings), shapes, STRtree([shape for _, shape in shapes]))
    if len(_BUILDING_INDEXES) >= _BUILDING_INDEXES_MAX:
        del _BUILDING_INDEXES[next(iter(_BUILDING_INDEXES))]
    _BUILDING_INDEXES[id(buildings)] = index
    return index


def building_at(lat: float | None, lng: float | None, buildings: list[Building]) -> Building | None:
    """The OSM building whose outline contains the geotag (the first one in list order)."""
    if lat is None or lng is None or not buildings:
        return None
    index = _building_index(buildings)
    point = Point(lng, lat)
    for i in sorted(index.tree.query(point)):  # bounding-box candidates
        building, shape = index.shapes[i]
        if shape.contains(point):
            return building
    return None


def mentioned_name(text: str, names: list[str]) -> str | None:
    haystack = f" {normalize(text)} "
    for name in sorted(names, key=len, reverse=True):
        n = normalize(name)
        if not n:
            continue
        if n.isascii():
            # Latin names must be whole words ("KU" must not match "kumc").
            if len(n) >= 4 and f" {n} " in haystack:
                return name
            # Short acronyms count only in upper case as a separate word: "KU Main Building", "testing at NU".
            if 2 <= len(n) < 4 and name.isupper() and re.search(rf"(?<![A-Za-z0-9]){re.escape(name)}(?![A-Za-z0-9])", text):
                return name
        # Korean/Japanese/Chinese titles often glue words and numbers together: "2006고려대학교19".
        elif len(n) >= 3 and n in haystack:
            return name
    return None


def _official_domain(raw: RawImage, ctx: CampusContext) -> str | None:
    domain = raw.source_domain.lower().removeprefix("www.")
    for official in ctx.official_domains:
        o = official.lower().removeprefix("www.")
        if o and (domain == o or domain.endswith("." + o)):
            return raw.source_domain
    return raw.source_domain if raw.is_official_site else None


def content_evidence(raw: RawImage, ctx: CampusContext) -> Evidence | None:
    """At most one sign that the image shows something other than the campus: another institution, people, a sample."""
    t = labels(ctx.lang)
    institution = cat.other_institution(raw, ctx.names)
    if institution:
        return _ev("content", t["other_institution"].format(m=institution), W_OTHER_INSTITUTION)
    if cat.is_people_or_event(raw):
        return _ev("content", t["people"], W_PEOPLE_OR_EVENT)
    if cat.is_specimen(raw):
        return _ev("content", t["specimen"], W_SPECIMEN)
    if cat.is_food_closeup(raw):
        return _ev("content", t["food_closeup"], W_SPECIMEN)
    return None


def finalize(evidence: list[Evidence]) -> tuple[int, str]:
    """Confidence and tier from evidence, with the honest-uncertainty caps (docs/CONTRACT.md §3)."""
    confidence = max(0, min(100, BASE_CONFIDENCE + sum(e.weight for e in evidence)))
    has_place_evidence = any(e.type in POSITIVE_TYPES and e.weight > 0 for e in evidence)
    not_the_place = any(e.type == "content" for e in evidence)
    if not has_place_evidence or not_the_place:
        confidence = min(confidence, UNCONFIRMED_MAX)
    tier = "verified" if confidence >= VERIFIED_FROM else "likely" if confidence >= LIKELY_FROM else "unconfirmed"
    return confidence, tier


def score(raw: RawImage, ctx: CampusContext) -> Photo | None:
    """None when the image is not a photo of a place (logos, maps, flyers, documents, artworks)."""
    if cat.is_not_a_place(raw):
        return None

    t = labels(ctx.lang)
    geo, on_campus = geo_evidence(raw, ctx)
    evidence = [geo]

    building = building_at(raw.lat, raw.lng, ctx.buildings)
    if building is not None and building.inside_campus:
        type_name = BUILDING_TYPE_NAMES.get(ctx.lang, {}).get(building.type, building.type)
        name = building.name or t["unnamed_building"]
        evidence.append(_ev("category", t["building"].format(b=name, t=type_name), W_BUILDING))

    if raw.subject_kind == "building" and raw.subject_name:
        evidence.append(_ev("category", t["building_subject"].format(b=raw.subject_name), W_BUILDING))

    if raw.matched_category:
        key, weight = ("subcategory", W_SUBCATEGORY) if raw.matched_subcategory else ("category", W_CATEGORY)
        evidence.append(_ev("category", t[key].format(c=raw.matched_category), weight))

    name = mentioned_name(cat.own_text(raw), ctx.names)
    if name:
        evidence.append(_ev("text", t["name"].format(n=name), W_NAME_IN_TEXT))
    official = _official_domain(raw, ctx)
    if official:
        evidence.append(_ev("text", t["official"].format(s=official), W_OFFICIAL_SITE))

    content = content_evidence(raw, ctx)
    if raw.vision_checked and raw.vision_label:
        key = "vision_veto" if raw.vision_veto else f"vision_{raw.vision_label}"
        if raw.vision_source == "claude":
            key = f"claude_{key.removeprefix('vision_')}" if key != "vision_veto" else "claude_vision_veto"
        evidence.append(_ev("vision", t[key], raw.vision_weight))
    if content:
        evidence.append(content)

    if not raw.license and not official:
        evidence.append(_ev("missing", t["no_license"], W_NO_LICENSE))

    date_source = effective_date_source(raw.date_taken, raw.date_uploaded, raw.date_source, raw.date_hint_year)
    if date_label := date_evidence_label(raw.date_taken, raw.date_uploaded, date_source, ctx.lang):
        evidence.append(_ev("date", date_label, 0))
    if not raw.vision_checked:
        evidence.append(_ev("missing", t["not_visually_checked"], 0))

    confidence, tier = finalize(evidence)
    if raw.vision_veto:  # only a wide-margin model call overrides the metadata
        confidence, tier = min(confidence, UNCONFIRMED_MAX), "unconfirmed"
    if not raw.vision_checked and tier == "verified":
        confidence, tier = VERIFIED_FROM - 1, "likely"
    linked = bool(raw.matched_category or name or official)
    # Without a polygon, a geotag beyond the point radius is "unknown"; unlinked, it is not the campus.
    off_campus = on_campus is False or (on_campus is None and raw.lat is not None and not linked)
    category, tags = cat.classify(raw, False if off_campus else on_campus, linked, building)
    if raw.vision_category in ("dorms", "classrooms", "libraries") and not off_campus:
        category = raw.vision_category
    subject_categories = {"dorm": "dorms", "library": "libraries", "academic": "classrooms"}
    if raw.subject_building_type in subject_categories and not off_campus:
        category = subject_categories[raw.subject_building_type]
    return Photo(
        id=raw.id,
        thumb_url=raw.thumb_url,
        full_url=raw.full_url,
        category=category,
        tags=tags,
        confidence=confidence,
        tier=tier,
        source_url=raw.source_url,
        source_domain=raw.source_domain,
        author=raw.author or "unknown",
        license=raw.license or "unknown",
        date_taken=raw.date_taken,
        date_uploaded=raw.date_uploaded,
        date_source=date_source,
        freshness=freshness(raw.date_taken, raw.date_hint_year),
        vision_checked=raw.vision_checked,
        highlight=category == "campus" and tier != "unconfirmed" and (
            raw.vision_highlight or bool(HIGHLIGHT_TEXT.search(cat.own_text(raw)))),
        retrieved_at=ctx.today.isoformat(),
        lat=raw.lat,
        lng=raw.lng,
        heading_deg=raw.heading_deg,
        evidence=evidence,
        duplicates=[],
    )
