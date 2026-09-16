"""Campus boundary from OpenStreetMap via the Overpass API."""

import asyncio
import math
from dataclasses import dataclass

import httpx
from shapely.geometry import LineString, Point, Polygon, shape
from shapely.geometry.base import BaseGeometry
from shapely.ops import polygonize, unary_union

from app.services.text import best_similarity

NOMINATIM_URL = "https://nominatim.openstreetmap.org/search"
OVERPASS_URL = "https://overpass-api.de/api/interpreter"
WIKIDATA_TAG_RADIUS_M = 5000
NEARBY_RADIUS_M = 400
NAME_MATCH = 0.8
KM_PER_DEGREE = 111.32


@dataclass
class Campus:
    geometry: BaseGeometry  # Polygon or MultiPolygon, coordinates are (lng, lat)
    name: str | None
    osm_url: str
    area_km2: float


def distance_m(lat1: float, lng1: float, lat2: float, lng2: float) -> float:
    p1, p2 = math.radians(lat1), math.radians(lat2)
    dp, dl = p2 - p1, math.radians(lng2 - lng1)
    h = math.sin(dp / 2) ** 2 + math.cos(p1) * math.cos(p2) * math.sin(dl / 2) ** 2
    return 6_371_000 * 2 * math.asin(math.sqrt(h))


def _area_km2(geometry: BaseGeometry) -> float:
    lat = geometry.centroid.y
    return geometry.area * KM_PER_DEGREE**2 * math.cos(math.radians(lat))


def _geometry(element: dict) -> BaseGeometry | None:
    if element["type"] == "way":
        coords = [(p["lon"], p["lat"]) for p in element.get("geometry", [])]
        return Polygon(coords) if len(coords) >= 4 else None
    if element["type"] == "relation":
        lines = [
            LineString([(p["lon"], p["lat"]) for p in m["geometry"]])
            for m in element.get("members", [])
            if m.get("type") == "way" and m.get("role") in ("outer", "") and len(m.get("geometry", [])) >= 2
        ]
        polygons = list(polygonize(lines))
        return unary_union(polygons) if polygons else None
    return None


def pick_campus(elements: list[dict], qid: str, names: list[str], lat: float, lng: float) -> Campus | None:
    """Prefer the element tagged with the university's Wikidata ID, then one containing its point by name."""
    point = Point(lng, lat)
    candidates = []
    for element in elements:
        geometry = _geometry(element)
        if geometry is None or geometry.is_empty or not geometry.is_valid:
            continue
        tags = element.get("tags", {})
        osm_names = [v for k, v in tags.items() if k == "name" or k.startswith("name:")]
        if tags.get("wikidata") == qid:
            rank = 0
        elif geometry.contains(point) and best_similarity_any(names, osm_names) >= NAME_MATCH:
            rank = 1
        elif geometry.contains(point):
            rank = 2
        else:
            continue
        candidates.append((rank, -geometry.area, element, geometry, tags))
    if not candidates:
        return None
    _, _, element, geometry, tags = min(candidates, key=lambda c: (c[0], c[1]))
    return Campus(
        geometry=geometry,
        name=tags.get("name:en") or tags.get("name"),
        osm_url=f"https://www.openstreetmap.org/{element['type']}/{element['id']}",
        area_km2=round(_area_km2(geometry), 2),
    )


def best_similarity_any(names: list[str], osm_names: list[str]) -> float:
    return max((best_similarity(name, osm_names) for name in names), default=0.0)


def _from_geojson(item: dict) -> Campus | None:
    geojson = item.get("geojson", {})
    if geojson.get("type") not in ("Polygon", "MultiPolygon"):
        return None
    geometry = shape(geojson)
    if geometry.is_empty or not geometry.is_valid:
        return None
    return Campus(
        geometry=geometry,
        name=item.get("name"),
        osm_url=f"https://www.openstreetmap.org/{item['osm_type']}/{item['osm_id']}",
        area_km2=round(_area_km2(geometry), 2),
    )


async def _nominatim(client: httpx.AsyncClient, qid: str, name: str) -> Campus | None:
    """Fast path (~1 s): geocode the name and keep the result tagged with this Wikidata ID."""
    resp = await client.get(
        NOMINATIM_URL,
        params={"q": name, "format": "jsonv2", "polygon_geojson": 1, "extratags": 1, "limit": 10},
    )
    resp.raise_for_status()
    for item in resp.json():
        if (item.get("extratags") or {}).get("wikidata") == qid and item.get("category") == "amenity":
            campus = _from_geojson(item)
            if campus:
                return campus
    return None


async def find_campus(
    client: httpx.AsyncClient, qid: str, name: str, names: list[str], lat: float, lng: float
) -> Campus | None:
    campus = await _nominatim(client, qid, name)
    return campus or await _overpass(client, qid, names, lat, lng)


async def _overpass(client: httpx.AsyncClient, qid: str, names: list[str], lat: float, lng: float) -> Campus | None:
    """Slow path (2–15 s, rate-limited): university areas around the point, incl. multipolygon relations."""
    query = f"""
[out:json][timeout:12];
(
  way["amenity"="university"]["wikidata"="{qid}"](around:{WIKIDATA_TAG_RADIUS_M},{lat},{lng});
  relation["amenity"="university"]["wikidata"="{qid}"](around:{WIKIDATA_TAG_RADIUS_M},{lat},{lng});
  way["amenity"~"university|college"](around:{NEARBY_RADIUS_M},{lat},{lng});
  relation["amenity"~"university|college"](around:{NEARBY_RADIUS_M},{lat},{lng});
);
out geom;
"""
    for attempt in range(2):
        resp = await client.post(OVERPASS_URL, data={"data": query})
        # The public instance rate-limits (429) or times out (504) under load: retry once.
        if resp.status_code in (429, 502, 503, 504) and attempt == 0:
            await asyncio.sleep(1)
            continue
        resp.raise_for_status()
        return pick_campus(resp.json().get("elements", []), qid, names[:40], lat, lng)
    return None
