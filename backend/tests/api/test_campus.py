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
    assert body["panoramas"] == {"provider": None, "available": False, "checked_providers": [], "start": None}


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
