import asyncio

from app.models import SourceResult
from app.services import orchestrator
from tests.api.fakes import QID, collector, fake, get, parse_sse, raw, run  # noqa: F401


def final_statuses(events):
    return {d["name"]: d for e, d in events if e == "source_status" and d["status"] != "pending"}


def test_stream_order_pending_first_done_last(fake):
    resp = run(get(f"/profile/{QID}?lang=en"))
    assert resp.status_code == 200
    assert resp.headers["content-type"].startswith("text/event-stream")
    assert resp.headers["cache-control"] == "no-cache" and resp.headers["x-accel-buffering"] == "no"
    events = parse_sse(resp.text)
    pending = events[:len(orchestrator.SOURCE_NAMES)]
    assert [e for e, _ in pending] == ["source_status"] * len(orchestrator.SOURCE_NAMES)
    assert {d["name"] for _, d in pending} == set(orchestrator.SOURCE_NAMES)
    assert all(d["status"] == "pending" and d["took_ms"] is None for _, d in pending)
    assert events[-1][0] == "done" and [e for e, _ in events].count("done") == 1
    assert [e for e, _ in events].count("summary") == 1

    statuses = final_statuses(events)
    assert statuses["flickr"]["status"] == "skipped"
    assert statuses["wikimedia_commons"]["count"] == 2
    assert statuses["openstreetmap"]["count"] == 1
    done = events[-1][1]
    assert done["cached"] is False and done["partial"] is False
    assert done["stats"]["photos"] == 2
    assert done["university"]["campus_polygon"] is not None


def test_photos_are_rescored_when_the_polygon_arrives(fake):
    fake["state"]["osm_delay"] = 0.2  # Commons answers first
    events = parse_sse(run(get(f"/profile/{QID}?lang=en")).text)
    photo_events = [d for e, d in events if e == "photo" and d["id"] == "commons-1"]
    assert len(photo_events) == 2  # first by the point, then re-sent with the polygon (same id)
    first_photo = next(i for i, (e, _) in enumerate(events) if e == "photo")
    osm_done = next(i for i, (e, d) in enumerate(events) if e == "source_status" and d["name"] == "openstreetmap"
                    and d["status"] != "pending")
    assert first_photo < osm_done
    assert photo_events[0]["evidence"] != photo_events[1]["evidence"]


def test_failed_and_crashed_sources_do_not_break_the_stream(fake):
    fake["set"]("flickr", collector("flickr", status="error", detail="HTTP 500"))
    fake["set"]("mapillary", collector("mapillary", exc=RuntimeError("bug")))
    events = parse_sse(run(get(f"/profile/{QID}?lang=en")).text)
    statuses = final_statuses(events)
    assert statuses["flickr"]["status"] == "error"
    assert statuses["mapillary"]["status"] == "error"
    assert statuses["wikimedia_commons"]["status"] == "ok"
    assert events[-1][0] == "done" and events[-1][1]["partial"] is True


def test_source_timeout_becomes_timeout_status(fake, monkeypatch):
    monkeypatch.setattr(orchestrator, "SOURCE_TIMEOUT_S", 0.1)
    fake["set"]("official_site", collector("official_site", delay=1.0))
    events = parse_sse(run(get(f"/profile/{QID}?lang=en")).text)
    assert final_statuses(events)["official_site"]["status"] == "timeout"
    assert events[-1][1]["partial"] is True


def test_global_deadline_ends_the_stream_with_done(fake, monkeypatch):
    monkeypatch.setattr(orchestrator, "PROFILE_DEADLINE_S", 0.5)
    monkeypatch.setattr(orchestrator, "DONE_MARGIN_S", 0.1)
    fake["set"]("flickr", collector("flickr", delay=5.0))
    took, text = asyncio.run(_timed(f"/profile/{QID}?lang=en"))
    events = parse_sse(text)
    assert took < 2.0
    assert final_statuses(events)["flickr"]["status"] == "timeout"
    assert events[-1][0] == "done" and events[-1][1]["partial"] is True
    assert events[-1][1]["stats"]["photos"] == 2


async def _timed(path):
    loop = asyncio.get_running_loop()
    t0 = loop.time()
    resp = await get(path)
    return loop.time() - t0, resp.text


def test_partial_rules():
    ok_partial = SourceResult(name="flickr", status="ok", took_ms=1, detail="budget 7.5 s reached, partial: 3 images")
    skipped = SourceResult(name="mapillary", status="skipped", took_ms=0)
    site_403 = SourceResult(name="official_site", status="error", took_ms=1, detail="HTTPStatusError: HTTP 403")
    assert orchestrator.is_partial([ok_partial, skipped], deadline_hit=False) is False
    assert orchestrator.is_partial([ok_partial], deadline_hit=True) is True
    assert orchestrator.is_partial([site_403], deadline_hit=False) is True


def test_official_site_403_can_be_ignored(monkeypatch):
    monkeypatch.setattr(orchestrator, "IGNORE_OFFICIAL_SITE_403", True)
    site_403 = SourceResult(name="official_site", status="error", took_ms=1, detail="HTTPStatusError: HTTP 403")
    site_500 = SourceResult(name="official_site", status="error", took_ms=1, detail="HTTPStatusError: HTTP 500")
    assert orchestrator.is_partial([site_403], deadline_hit=False) is False
    assert orchestrator.is_partial([site_500], deadline_hit=False) is True


def test_more_confident_copy_takes_over_and_lists_the_earlier_one(fake):
    weak = raw("commons-7", sha1="same", matched_category=None, title="File:IMG 1.jpg")
    strong = raw("flickr-7", source="flickr", sha1="same")
    fake["set"]("wikimedia_commons", collector("wikimedia_commons", [weak]))
    fake["set"]("flickr", collector("flickr", [strong], delay=0.1))
    events = parse_sse(run(get(f"/profile/{QID}?lang=en")).text)
    sent_ids = [d["id"] for e, d in events if e == "photo"]
    assert "commons-7" in sent_ids and "flickr-7" in sent_ids
    last = [d for e, d in events if e == "photo" and d["id"] == "flickr-7"][-1]
    assert [dup["id"] for dup in last["duplicates"]] == ["commons-7"]
    assert events[-1][1]["stats"]["photos"] == 1 and events[-1][1]["stats"]["duplicates"] == 1


def test_first_photo_is_sent_before_the_collector_finishes(fake):
    first = raw("commons-1")
    fake["set"]("wikimedia_commons", collector("wikimedia_commons", [first, raw("commons-2")], delay=0.3,
                                               batches=[[first]]))
    fake["set"]("flickr", collector("flickr", delay=0.1))
    events = parse_sse(run(get(f"/profile/{QID}?lang=en")).text)
    first_photo = next(i for i, (e, d) in enumerate(events) if e == "photo" and d["id"] == "commons-1")
    flickr_done = next(i for i, (e, d) in enumerate(events) if e == "source_status" and d["name"] == "flickr"
                       and d["status"] != "pending")
    commons_done = next(i for i, (e, d) in enumerate(events) if e == "source_status"
                        and d["name"] == "wikimedia_commons" and d["status"] != "pending")
    assert first_photo < flickr_done < commons_done
    assert final_statuses(events)["wikimedia_commons"]["count"] == 2
    assert events[-1][1]["stats"]["photos"] == 2


def test_bbox_photo_sources_wait_briefly_for_campus_shape(fake):
    seen = {}

    async def mapillary(query, client, on_batch=None):
        seen["bbox"] = query.bbox
        return SourceResult(name="mapillary", status="skipped", took_ms=0, detail="no key")

    fake["set"]("mapillary", mapillary)
    parse_sse(run(get(f"/profile/{QID}?lang=en")).text)
    assert seen["bbox"] == (127.028, 37.586, 127.037, 37.593)


def test_repeated_batches_resend_a_photo_only_when_it_changed(fake):
    fake["state"]["osm_delay"] = 0.3  # the polygon arrives after Commons is done
    weak = raw("commons-1", matched_category=None, found_by="text")
    strong = raw("commons-1")
    fake["set"]("wikimedia_commons", collector("wikimedia_commons", [strong],
                                               batches=[[weak], [weak], [weak.model_copy()], [strong], [strong]]))
    events = parse_sse(run(get(f"/profile/{QID}?lang=en")).text)
    commons_done = next(i for i, (e, d) in enumerate(events) if e == "source_status"
                        and d["name"] == "wikimedia_commons" and d["status"] != "pending")
    before = [d for e, d in events[:commons_done] if e == "photo" and d["id"] == "commons-1"]
    assert len(before) == 2  # weak once, strong once — not once per repeat
    assert before[0] != before[1]
    assert events[-1][1]["stats"]["photos"] == 1


def test_search_names_drop_a_lone_toponym_but_keep_acronyms_and_other_scripts():
    from app.services.orchestrator import search_names
    from tests.api.fakes import record

    uni = record(name="University of Cambridge", name_en="University of Cambridge", city=None,
                 names=["University of Cambridge", "Cambridge", "Cambridge University", "KAIST", "고려대"])
    assert search_names(uni) == ["University of Cambridge", "Cambridge University", "KAIST", "고려대"]


def test_stage_events_announce_what_the_build_is_doing_before_done(fake):
    events = parse_sse(run(get(f"/profile/{QID}?lang=en")).text)
    stages = [d["stage"] for e, d in events if e == "stage"]
    assert stages[0] == "sources" and stages[-1] == "finalizing"
    assert "vision" in stages
    last_stage = max(i for i, (e, _) in enumerate(events) if e == "stage")
    assert events[-1][0] == "done" and last_stage < len(events) - 1
