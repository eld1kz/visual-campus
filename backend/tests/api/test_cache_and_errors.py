import asyncio
import time

import httpx

from app.services import cache, orchestrator
from app.routers.profile import follow
from tests.api.fakes import QID, collector, fake, get, parse_sse, run  # noqa: F401


def test_repeat_request_replays_from_cache(fake):
    async def twice():
        first = await get(f"/profile/{QID}?lang=en")
        second = await get(f"/profile/{QID}?lang=en")
        return first, second

    first, second = run(twice())
    a, b = parse_sse(first.text), parse_sse(second.text)
    assert fake["calls"]["wikidata"] == 1
    assert b[-1][0] == "done" and b[-1][1]["cached"] is True
    assert b[-1][1]["stats"] == a[-1][1]["stats"] and b[-1][1]["partial"] == a[-1][1]["partial"]
    assert all(d["status"] == "pending" for _, d in b[:7])
    final_a = {d["id"]: d for e, d in a if e == "photo"}
    assert {d["id"]: d for e, d in b if e == "photo"} == final_a
    assert [d for e, d in b if e == "summary"] == [d for e, d in a if e == "summary"]


def test_partial_profile_is_cached_for_less_time(fake):
    fake["set"]("flickr", collector("flickr", status="error"))
    run(get(f"/profile/{QID}?lang=en"))
    expires, entry = cache.profiles._items[(QID, "en")]
    assert entry.partial is True
    assert expires - time.monotonic() <= cache.PARTIAL_PROFILE_TTL_S


def test_concurrent_requests_share_one_build(fake):
    fake["set"]("wikimedia_commons", collector("wikimedia_commons", delay=0.2))

    async def both():
        return await asyncio.gather(get(f"/profile/{QID}?lang=en"), get(f"/profile/{QID}?lang=en"))

    r1, r2 = run(both())
    assert fake["calls"]["wikidata"] == 1 and fake["calls"]["osm"] == 1
    e1, e2 = parse_sse(r1.text), parse_sse(r2.text)
    assert e1 == e2 and e1[-1][1]["cached"] is False


def test_cached_campus_shape_skips_osm_on_rebuild(fake):
    async def rebuild():
        await get(f"/profile/{QID}?lang=en")
        return await get(f"/profile/{QID}?lang=ru")  # other lang: a new build, same OSM shape

    events = parse_sse(run(rebuild()).text)
    assert fake["calls"]["osm"] == 1
    osm = [d for e, d in events if e == "source_status" and d["name"] == "openstreetmap" and d["status"] != "pending"]
    assert osm[0]["status"] == "ok" and events[-1][1]["university"]["campus_polygon"]


def test_unknown_id_is_404_json(fake):
    resp = run(get("/profile/Q1?lang=en"))
    assert resp.status_code == 404 and resp.headers["content-type"] == "application/json"


def test_wikidata_down_is_503_json(fake):
    fake["state"]["wikidata_exc"] = httpx.ConnectError("down")
    resp = run(get(f"/profile/{QID}?lang=en"))
    assert resp.status_code == 503
    assert resp.json()["sources_status"] == [{"name": "wikidata", "status": "error"}]
    assert (QID, "en") not in cache.inflight


def test_bad_id_is_422(fake):
    assert run(get("/profile/abc")).status_code == 422


def test_last_client_leaving_cancels_the_build(fake):
    fake["set"]("flickr", collector("flickr", delay=10))

    async def leave():
        build = orchestrator.start_or_join(QID, "en")
        await build.ready
        stream = follow(build)
        await stream.__anext__()
        await stream.aclose()  # what Starlette does when the client disconnects
        await asyncio.sleep(0.05)
        return build

    build = run(leave())
    assert build.task.cancelled()
    assert all(t.done() for t in build._children)
    assert (QID, "en") not in cache.inflight and cache.get_profile(QID, "en") is None
