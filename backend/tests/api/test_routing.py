import asyncio

import httpx

from app.services import routing


def test_center_route_reads_osrm_distance_duration_and_line():
    def handler(request: httpx.Request) -> httpx.Response:
        assert "/driving/71.39944,51.09;71.43333,51.13333" in str(request.url)
        return httpx.Response(200, json={"code": "Ok", "routes": [{
            "distance": 7407.8, "duration": 721.4,
            "geometry": {"type": "LineString", "coordinates": [[71.399441, 51.090001], [71.433331, 51.133332]]},
        }]})

    async def run():
        async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
            return await routing.center_route(client, 51.09, 71.39944, 51.13333, 71.43333)

    route = asyncio.run(run())
    assert (route.road_km, route.drive_min, route.walk_min) == (7.4, 12, 93)
    assert route.geometry == [[71.39944, 51.09], [71.43333, 51.13333]]


def test_center_route_is_none_when_osrm_finds_no_route():
    async def run():
        transport = httpx.MockTransport(lambda r: httpx.Response(200, json={"code": "NoRoute", "routes": []}))
        async with httpx.AsyncClient(transport=transport) as client:
            return await routing.center_route(client, 0, 0, 1, 1)

    assert asyncio.run(run()) is None
