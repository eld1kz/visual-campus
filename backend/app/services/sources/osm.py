"""OpenStreetMap: campus polygon (Nominatim by Wikidata tag, Overpass fallback) and buildings with contract types."""

import asyncio
import re
import time
from dataclasses import dataclass

import httpx
from shapely.geometry import LineString, Point, Polygon, shape
from shapely.geometry.base import BaseGeometry
from shapely.ops import polygonize, unary_union

from app.models import Building, CampusShape, SourceResult
from app.services.sources.base import SOURCE_BUDGET_S, Deadline, SourceQuery, elapsed_ms
from app.services.sources.geo import KM_PER_DEGREE, area_km2, distance_m
from app.services.text import best_similarity

__all__ = ["KM_PER_DEGREE", "Campus", "distance_m", "pick_campus", "building_type", "parse_buildings"]

NAME_MATCH = 0.8


@dataclass
class Campus:
    geometry: BaseGeometry  # Polygon or MultiPolygon, coordinates are (lng, lat)
    name: str | None
    osm_url: str
    area_km2: float


def _geometry(element: dict) -> BaseGeometry | None:
    if element["type"] == "way":
        coords = [(p["lon"], p["lat"]) for p in element.get("geometry", [])]
        if len(coords) < 4 or coords[0] != coords[-1]:
            return None
        return Polygon(coords)
    if element["type"] == "relation":
        # multipolygon outers and type=site members (closed ways with an empty role)
        lines = [
            LineString([(p["lon"], p["lat"]) for p in m["geometry"]])
            for m in element.get("members", [])
            if m.get("type") == "way" and m.get("role") in ("outer", "", "perimeter") and len(m.get("geometry") or []) >= 2
        ]
        polygons = list(polygonize(lines))
        return unary_union(polygons) if polygons else None
    return None


def best_similarity_any(names: list[str], osm_names: list[str]) -> float:
    return max((best_similarity(name, osm_names) for name in names), default=0.0)


def _campus(element: dict, geometry: BaseGeometry, name: str | None) -> Campus:
    return Campus(
        geometry=geometry,
        name=name,
        osm_url=f"https://www.openstreetmap.org/{element['type']}/{element['id']}",
        area_km2=round(area_km2(geometry), 2),
    )


def pick_campus(elements: list[dict], qid: str, names: list[str], lat: float | None, lng: float | None) -> Campus | None:
    """Prefer the element tagged with the university's Wikidata ID, then one containing its point by name."""
    point = Point(lng, lat) if lat is not None and lng is not None else None
    candidates = []
    for element in elements:
        tags = element.get("tags", {})
        if tags.get("amenity") not in ("university", "college") and tags.get("site") != "university":
            continue
        geometry = _geometry(element)
        if geometry is None or geometry.is_empty or not geometry.is_valid:
            continue
        osm_names = [v for k, v in tags.items() if k == "name" or k.startswith("name:")]
        contains = point is not None and geometry.contains(point)
        if tags.get("wikidata") == qid:
            rank = 0
        elif contains and best_similarity_any(names, osm_names) >= NAME_MATCH:
            rank = 1
        elif contains:
            rank = 2
        else:
            continue
        candidates.append((rank, -geometry.area, element, geometry, tags))
    if not candidates:
        return None
    _, _, element, geometry, tags = min(candidates, key=lambda c: (c[0], c[1]))
    return _campus(element, geometry, tags.get("name:en") or tags.get("name"))


def campus_from_nominatim(items: list[dict], qid: str) -> Campus | None:
    for item in items:
        if (item.get("extratags") or {}).get("wikidata") != qid or item.get("category") != "amenity":
            continue
        geojson = item.get("geojson") or {}
        if geojson.get("type") not in ("Polygon", "MultiPolygon"):
            continue
        geometry = shape(geojson)
        if geometry.is_empty or not geometry.is_valid:
            continue
        return _campus({"type": item["osm_type"], "id": item["osm_id"]}, geometry, item.get("name"))
    return None


# docs/CONTRACT.md §4: OSM values → Building.type, checked in this order.
_TYPE_RULES: list[tuple[str, set[str]]] = [
    ("dorm", {"dormitory"}),
    ("library", {"library"}),
    ("lab", {"laboratory", "research_institute"}),
    ("sport", {"sports_centre", "stadium", "pitch"}),
    ("food", {"restaurant", "cafe", "canteen", "food_court"}),
    ("academic", {"university", "college", "school"}),
]
NEARBY_BUILDING_M = 100  # "around the campus": buildings this close to the polygon are kept


def building_type(tags: dict) -> str:
    values = {tags.get(k) for k in ("amenity", "building", "leisure", "building:use")} - {None}
    for kind, osm_values in _TYPE_RULES:
        if kind == "library" and tags.get("amenity") != "library":
            continue
        if values & osm_values:
            return kind
    return "other"


def _number(value: str | None) -> float | None:
    if not value:
        return None
    try:
        return float(value.strip().removesuffix("m").strip().replace(",", "."))
    except ValueError:
        return None


def parse_buildings(elements: list[dict], campus: BaseGeometry | None) -> list[Building]:
    """Overpass `out geom` ways → contract Buildings; with a campus, keep those inside or within 100 m of it."""
    near = campus.buffer(NEARBY_BUILDING_M / KM_PER_DEGREE / 1000) if campus is not None else None
    buildings, seen = [], set()
    for element in elements:
        tags = element.get("tags", {})
        if element.get("type") != "way" or element["id"] in seen:
            continue
        if "building" not in tags and tags.get("leisure") not in ("sports_centre", "stadium", "pitch"):
            continue
        geometry = _geometry(element)
        if geometry is None or geometry.is_empty or not geometry.is_valid:
            continue
        center = geometry.representative_point()
        if near is not None and not near.contains(center):
            continue
        seen.add(element["id"])
        levels = _number(tags.get("building:levels"))
        buildings.append(Building(
            id=f"osm-way-{element['id']}",
            name=tags.get("name") or "",
            type=building_type(tags),
            polygon=[[round(x, 6), round(y, 6)] for x, y in geometry.exterior.coords],
            height_m=_number(tags.get("height")),
            levels=int(levels) if levels is not None else None,
            photo_ids=[],
            source="OpenStreetMap",
            inside_campus=campus is not None and campus.contains(center),
        ))
    return buildings


# ---------- network ----------

NOMINATIM_URL = "https://nominatim.openstreetmap.org/search"
# Public instances are often overloaded: query two at once and take the first good answer.
OVERPASS_URLS = [
    "https://overpass-api.de/api/interpreter",
    "https://maps.mail.ru/osm/tools/overpass/api/interpreter",
]
WIKIDATA_TAG_RADIUS_M = 20_000
NEARBY_RADIUS_M = 400
BUILDINGS_AROUND_POINT_M = 500
MAX_BUILDINGS = 3000
_LATIN = re.compile(r"^[\x00-\x7F]+$")


async def overpass(client: httpx.AsyncClient, query: str, deadline: Deadline) -> list[dict]:
    """POST to all mirrors in parallel; the first 200 with JSON wins, the rest are cancelled."""
    async def one(url: str) -> list[dict]:
        resp = await client.post(url, data={"data": query}, timeout=deadline.left())
        resp.raise_for_status()
        data = resp.json()
        if "elements" not in data:
            raise ValueError("no elements in Overpass response")
        if data.get("remark", "").startswith("runtime error"):
            raise ValueError(data["remark"])
        return data["elements"]

    tasks = [asyncio.create_task(one(url)) for url in OVERPASS_URLS]
    errors: list[BaseException] = []
    try:
        for next_done in asyncio.as_completed(tasks):
            try:
                return await next_done
            except Exception as exc:  # try the other mirror
                errors.append(exc)
    finally:
        for task in tasks:
            task.cancel()
    if any(isinstance(e, httpx.TimeoutException) for e in errors):
        raise httpx.ReadTimeout("all Overpass mirrors timed out")
    raise errors[0]


def _server_timeout(deadline: Deadline) -> int:
    return max(2, int(deadline.left() - 0.5))


def _search_name(names: list[str]) -> str | None:
    return next((n for n in names if _LATIN.match(n)), names[0] if names else None)


async def nominatim_campus(client: httpx.AsyncClient, qid: str, name: str, deadline: Deadline) -> Campus | None:
    """Fast path (~0.1–1 s): geocode the name and keep the amenity tagged with this Wikidata ID."""
    resp = await client.get(
        NOMINATIM_URL,
        params={"q": name, "format": "jsonv2", "polygon_geojson": 1, "extratags": 1, "limit": 10},
        timeout=min(deadline.left(), 3.0),
    )
    resp.raise_for_status()
    return campus_from_nominatim(resp.json(), qid)


def _campus_query(qid: str, lat: float | None, lng: float | None, timeout_s: int) -> str:
    """Campus candidates; with a point, buildings around it too, so the fallback needs a single round trip."""
    if lat is None or lng is None:
        return f'[out:json][timeout:{timeout_s}];nwr["wikidata"="{qid}"];out geom;'
    around = f"(around:{BUILDINGS_AROUND_POINT_M},{lat},{lng})"
    return f"""[out:json][timeout:{timeout_s}];
(
  nwr["wikidata"="{qid}"](around:{WIKIDATA_TAG_RADIUS_M},{lat},{lng});
  way["amenity"~"^(university|college)$"](around:{NEARBY_RADIUS_M},{lat},{lng});
  relation["amenity"~"^(university|college)$"](around:{NEARBY_RADIUS_M},{lat},{lng});
);
out geom;
(
  way["building"]{around};
  way["leisure"~"^(sports_centre|stadium|pitch)$"]{around};
);
out geom {MAX_BUILDINGS};"""


def _buildings_query(scope: str, timeout_s: int) -> str:
    return f"""[out:json][timeout:{timeout_s}];
(
  way["building"]{scope};
  way["leisure"~"^(sports_centre|stadium|pitch)$"]{scope};
);
out geom {MAX_BUILDINGS};"""


async def locate_campus(
    client: httpx.AsyncClient, qid: str, names: list[str], lat: float | None, lng: float | None, deadline: Deadline
) -> tuple[Campus | None, list[dict] | None]:
    """Nominatim first; Overpass fallback. Returns the campus and, from Overpass, elements around the point."""
    name = _search_name(names)
    if name:
        try:
            campus = await nominatim_campus(client, qid, name, deadline)
            if campus:
                return campus, None
        except (httpx.HTTPError, ValueError):
            pass  # fall back to Overpass
    elements = await overpass(client, _campus_query(qid, lat, lng, _server_timeout(deadline)), deadline)
    return pick_campus(elements, qid, names[:40], lat, lng), elements


def _covers(campus: Campus, lat: float, lng: float) -> bool:
    """True if buildings fetched around the point cover the whole campus."""
    west, south, east, north = campus.geometry.bounds
    return all(distance_m(lat, lng, y, x) <= BUILDINGS_AROUND_POINT_M for x in (west, east) for y in (south, north))


async def find_campus(query: SourceQuery, client: httpx.AsyncClient) -> tuple[SourceResult, CampusShape | None]:
    started = time.perf_counter()
    deadline = Deadline(SOURCE_BUDGET_S)
    state: dict = {"campus": None, "polygon_done": False, "buildings": None}

    def result(status: str, detail: str | None = None) -> tuple[SourceResult, CampusShape | None]:
        campus: Campus | None = state["campus"]
        shape_ = None
        if campus or state["buildings"]:
            shape_ = CampusShape(
                polygon=outer_ring(campus.geometry, query.lat, query.lng) if campus else None,
                area_km2=campus.area_km2 if campus else None,
                osm_url=campus.osm_url if campus else None,
                buildings=state["buildings"] or [],
            )
        return SourceResult(name="openstreetmap", status=status, took_ms=elapsed_ms(started), detail=detail), shape_

    has_point = query.lat is not None and query.lng is not None
    if not has_point and not query.names:
        return result("skipped", "no coordinates and no names")

    async def work() -> None:
        campus, around = await locate_campus(client, query.wikidata_id, query.names, query.lat, query.lng, deadline)
        state["campus"], state["polygon_done"] = campus, True
        geometry = campus.geometry if campus else None
        if around is not None:
            state["buildings"] = parse_buildings(around, geometry)
            if campus is None or _covers(campus, query.lat, query.lng):
                return
        if campus is None:
            if not has_point:
                return
            scope = f"(around:{BUILDINGS_AROUND_POINT_M},{query.lat},{query.lng})"
        else:
            west, south, east, north = campus.geometry.bounds
            scope = f"({south},{west},{north},{east})"
        elements = await overpass(client, _buildings_query(scope, _server_timeout(deadline)), deadline)
        state["buildings"] = parse_buildings(elements, geometry)

    try:
        await asyncio.wait_for(work(), timeout=SOURCE_BUDGET_S)
    except (asyncio.TimeoutError, httpx.TimeoutException):
        if state["polygon_done"]:
            return result("ok", "buildings timed out" + (", only those near the point" if state["buildings"] else ""))
        return result("timeout", f"budget {SOURCE_BUDGET_S:g} s reached")
    except Exception as exc:
        if state["polygon_done"]:
            return result("ok", f"buildings failed: {type(exc).__name__}: {exc}")
        return result("error", f"{type(exc).__name__}: {exc}")
    return result("ok", None if state["campus"] else "no campus polygon in OpenStreetMap")


def outer_ring(geometry: BaseGeometry, lat: float | None, lng: float | None) -> list[list[float]]:
    """Outer ring as [[lng, lat], ...]. A multi-site campus gives the part at (or nearest to) the university point,
    not the largest one: University of Cambridge's largest site lies 4 km from the town-centre colleges."""
    if geometry.geom_type == "MultiPolygon":
        if lat is not None and lng is not None:
            point = Point(lng, lat)
            geometry = min(geometry.geoms, key=lambda g: (g.distance(point), -g.area))
        else:
            geometry = max(geometry.geoms, key=lambda g: g.area)
    return [[round(x, 6), round(y, 6)] for x, y in geometry.exterior.coords]
