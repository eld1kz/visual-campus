"""Road route from the campus to the city centre (public OSRM demo server, car profile, no key)."""

import httpx

from app.models import CenterRoute

OSRM_ROUTE = "https://router.project-osrm.org/route/v1/driving/{a_lng},{a_lat};{b_lng},{b_lat}"
WALK_KMH = 4.8  # walking time is an estimate from the road distance, not a walking route


async def center_route(client: httpx.AsyncClient, lat: float, lng: float, c_lat: float, c_lng: float,
                       timeout_s: float = 4.0) -> CenterRoute | None:
    response = await client.get(
        OSRM_ROUTE.format(a_lng=lng, a_lat=lat, b_lng=c_lng, b_lat=c_lat),
        params={"overview": "simplified", "geometries": "geojson"}, timeout=timeout_s,
    )
    response.raise_for_status()
    data = response.json()
    if data.get("code") != "Ok" or not data.get("routes"):
        return None
    route = data["routes"][0]
    road_km = route["distance"] / 1000
    return CenterRoute(
        road_km=round(road_km, 1),
        drive_min=max(1, round(route["duration"] / 60)),
        walk_min=max(1, round(road_km / WALK_KMH * 60)),
        geometry=[[round(x, 5), round(y, 5)] for x, y in route["geometry"]["coordinates"]],
    )
