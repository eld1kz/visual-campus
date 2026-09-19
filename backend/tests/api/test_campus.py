from dataclasses import replace

import httpx

from tests.api.fakes import QID, fake, get, run  # noqa: F401


def test_campus_without_profile_has_shape_and_no_pins(fake):
    resp = run(get(f"/campus/{QID}"))
    assert resp.status_code == 200
    body = resp.json()
    assert body["campus"]["polygon"] and body["campus"]["center"] == {"lat": 37.5895, "lng": 127.0323}
    assert body["campus"]["city_center"]["name"] == "Seoul"
    assert body["campus"]["distance_to_center_km"] > 0 and body["campus"]["transit"] == []
    assert len(body["buildings"]) == 1 and body["photo_pins"] == []
    assert body["panoramas"] == {"provider": None, "available": False, "checked_providers": [], "start": None, "points": []}


def test_campus_pins_come_from_the_cached_profile(fake):
    async def flow():
        await get(f"/profile/{QID}?lang=en")
        return await get(f"/campus/{QID}")

    body = run(flow()).json()
    assert fake["calls"]["osm"] == 1  # shape reused from the cache
    pins = {p["photo_id"]: p for p in body["photo_pins"]}
    assert set(pins) == {"commons-1", "commons-2"}
    assert pins["commons-1"]["building_id"] == "osm-way-1" and pins["commons-2"]["building_id"] is None
    assert body["buildings"][0]["photo_ids"] == ["commons-1"]


def test_campus_errors(fake):
    assert run(get("/campus/Q1")).status_code == 404
    fake["state"]["record"] = replace(fake["state"]["record"], lat=None, lng=None)
    assert run(get(f"/campus/{QID}")).status_code == 404
    fake["state"]["wikidata_exc"] = httpx.ConnectTimeout("slow")
    assert run(get(f"/campus/{QID}")).json()["sources_status"] == [{"name": "wikidata", "status": "timeout"}]


def test_walk_points_come_from_the_profile_mapillary_images(monkeypatch):
    import dataclasses

    from app.routers import campus as campus_router
    from app.services.pipeline import score
    from tests.pipeline.conftest_data import CTX, raw

    monkeypatch.setattr(campus_router, "settings", dataclasses.replace(campus_router.settings, mapillary_token="t"))
    near = score(raw(id="mapillary-111", source="mapillary", lat=37.5896, lng=127.0324, date_taken="2025-05-01"), CTX)
    far = score(raw(id="mapillary-222", source="mapillary", lat=37.60, lng=127.05), CTX)
    commons = score(raw(id="commons-1", lat=37.59, lng=127.03), CTX)
    pano = campus_router.mapillary_panoramas([far, commons, near], 37.5895, 127.0323)
    assert pano.provider == "mapillary" and pano.available
    assert [p.image_id for p in pano.points] == ["222", "111"]
    assert pano.start.image_id == "111" and pano.start.captured_at == "2025-05-01"


def test_map_refetches_buildings_when_the_cached_outline_has_none(fake):
    from app.models import CampusShape
    from app.services import cache

    cache.put_shape(QID, CampusShape(polygon=[[127.03, 37.59], [127.04, 37.59], [127.04, 37.6]], area_km2=0.5,
                                     osm_url=None, buildings=[]), complete=False)
    body = run(get(f"/campus/{QID}?lang=en")).json()
    assert len(body["buildings"]) == 1  # the fake OSM answer, fetched again on the map tab
    assert cache.get_shape(QID).buildings
