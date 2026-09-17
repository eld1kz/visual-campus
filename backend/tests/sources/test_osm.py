import asyncio

import httpx
from shapely.geometry import MultiPolygon, Polygon

from app.services.sources import osm
from app.services.sources.base import SourceQuery


def ring(x0, y0, x1, y1):
    return [{"lon": x, "lat": y} for x, y in [(x0, y0), (x1, y0), (x1, y1), (x0, y1), (x0, y0)]]


SITE = {  # type=site relation made of closed ways, like University of Cambridge
    "type": "relation", "id": 7, "tags": {"amenity": "university", "type": "site", "wikidata": "Q1", "name": "U"},
    "members": [{"type": "way", "role": "", "geometry": ring(0, 0, 1, 1)},
                {"type": "way", "role": "", "geometry": ring(2, 2, 3, 3)}],
}


def test_pick_campus_prefers_wikidata_and_handles_site_relation():
    other = {"type": "way", "id": 9, "tags": {"amenity": "college"}, "geometry": ring(-5, -5, 5, 5)}
    campus = osm.pick_campus([other, SITE], "Q1", ["U"], 0.5, 0.5)
    assert campus.osm_url == "https://www.openstreetmap.org/relation/7"
    assert campus.geometry.geom_type == "MultiPolygon"
    assert osm.outer_ring(campus.geometry, 0.5, 0.5)[0] in ([0.0, 0.0], [1.0, 0.0], [0.0, 1.0], [1.0, 1.0])


def test_outer_ring_takes_the_part_at_the_university_point_not_the_largest():
    # Cambridge: a large outlying site plus small town-centre parts where the university point is
    site = MultiPolygon([Polygon([(10, 10), (20, 10), (20, 20), (10, 20)]), Polygon([(0, 0), (1, 0), (1, 1), (0, 1)])])
    assert osm.outer_ring(site, 0.5, 0.5)[0] == [0.0, 0.0]
    assert osm.outer_ring(site, 1.5, -0.5)[0] == [0.0, 0.0]  # no part contains it: the nearest one
    assert osm.outer_ring(site, None, None)[0] == [10.0, 10.0]  # no point: the largest


def test_building_type_follows_contract_table():
    assert osm.building_type({"building": "university"}) == "academic"
    assert osm.building_type({"building": "dormitory"}) == "dorm"
    assert osm.building_type({"amenity": "library", "building": "yes"}) == "library"
    assert osm.building_type({"building": "library"}) == "other"
    assert osm.building_type({"leisure": "sports_centre"}) == "sport"
    assert osm.building_type({"amenity": "research_institute"}) == "lab"
    assert osm.building_type({"amenity": "cafe", "building": "yes"}) == "food"
    assert osm.building_type({"building": "yes"}) == "other"


def test_parse_buildings_inside_flag_height_levels_and_far_ones_dropped():
    campus = Polygon([(0, 0), (0.01, 0), (0.01, 0.01), (0, 0.01)])
    elements = [
        {"type": "way", "id": 1, "tags": {"building": "university", "name": "Main", "height": "22.5 m", "building:levels": "5"},
         "geometry": ring(0.002, 0.002, 0.003, 0.003)},
        {"type": "way", "id": 2, "tags": {"building": "yes"}, "geometry": ring(0.0104, 0.005, 0.0105, 0.0051)},
        {"type": "way", "id": 3, "tags": {"building": "yes"}, "geometry": ring(0.05, 0.05, 0.051, 0.051)},
        {"type": "way", "id": 4, "tags": {"highway": "path"}, "geometry": ring(0.002, 0.002, 0.003, 0.003)},
    ]
    buildings = {b.id: b for b in osm.parse_buildings(elements, campus)}
    assert set(buildings) == {"osm-way-1", "osm-way-2"}
    main = buildings["osm-way-1"]
    assert (main.name, main.type, main.height_m, main.levels, main.inside_campus) == ("Main", "academic", 22.5, 5, True)
    assert buildings["osm-way-2"].inside_campus is False and buildings["osm-way-2"].height_m is None


def test_find_campus_nominatim_then_buildings_from_second_mirror():
    def handler(request: httpx.Request) -> httpx.Response:
        if "nominatim" in request.url.host:
            return httpx.Response(200, json=[{
                "osm_type": "way", "osm_id": 5, "category": "amenity", "name": "KAIST", "extratags": {"wikidata": "Q39949"},
                "geojson": {"type": "Polygon", "coordinates": [[[0, 0], [0.01, 0], [0.01, 0.01], [0, 0.01], [0, 0]]]},
            }])
        if request.url.host == "overpass-api.de":
            return httpx.Response(504, text="Gateway Timeout")
        return httpx.Response(200, json={"elements": [
            {"type": "way", "id": 1, "tags": {"building": "dormitory"}, "geometry": ring(0.002, 0.002, 0.003, 0.003)}]})

    async def run():
        async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
            return await osm.find_campus(SourceQuery("Q39949", ["KAIST"], 0.005, 0.005, None, None), client)

    result, shape = asyncio.run(run())
    assert result.status == "ok" and result.name == "openstreetmap"
    assert shape.osm_url == "https://www.openstreetmap.org/way/5" and shape.area_km2 > 0
    assert [b.type for b in shape.buildings] == ["dorm"]


def test_find_campus_keeps_polygon_when_buildings_fail():
    def handler(request: httpx.Request) -> httpx.Response:
        if "nominatim" in request.url.host:
            return httpx.Response(200, json=[])
        if "wikidata" in request.content.decode():  # campus + buildings near the point: no buildings there
            return httpx.Response(200, json={"elements": [SITE]})
        return httpx.Response(429)  # the campus is larger than the point radius → bbox buildings query fails

    async def run():
        async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
            return await osm.find_campus(SourceQuery("Q1", ["U"], 0.5, 0.5, None, None), client)

    result, shape = asyncio.run(run())
    assert result.status == "ok" and "buildings failed" in result.detail
    assert shape.polygon and shape.buildings == []
