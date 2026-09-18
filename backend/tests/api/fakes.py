"""Offline fakes for the orchestrator: Wikidata, collectors, OSM and Wikipedia without network."""

import asyncio
import json

import httpx
import pytest

from app.main import app
from app.models import Building, CampusShape, RawImage, SourceResult
from app.services import cache, orchestrator
from app.services.sources import osm
from app.services.wikidata import Place, UniversityRecord
from app.services.wikipedia import WikiSummary
from app.routers import campus as campus_router

QID = "Q39997"
LAT, LNG = 37.5895, 127.0323
POLYGON = [[127.028, 37.586], [127.037, 37.586], [127.037, 37.593], [127.028, 37.593], [127.028, 37.586]]
HALL = [[127.031, 37.589], [127.033, 37.589], [127.033, 37.590], [127.031, 37.590], [127.031, 37.589]]


def record(**over) -> UniversityRecord:
    base = dict(
        wikidata_id=QID, name="Korea University", name_en="Korea University", names=["Korea University", "고려대학교"],
        lat=LAT, lng=LNG, website="https://www.korea.ac.kr", commons_category="Korea University", ror_id=None,
        city="Seoul", country="South Korea", wikipedia_titles={"en": "Korea University"},
        city_center=Place(name="Seoul", lat=37.5665, lng=126.978),
    )
    return UniversityRecord(**{**base, **over})


def raw(pid: str, source: str = "wikimedia_commons", **over) -> RawImage:
    base = dict(
        id=pid, source=source, source_url=f"https://commons.wikimedia.org/wiki/File:{pid}.jpg",
        source_domain="commons.wikimedia.org", full_url=f"https://upload.wikimedia.org/{pid}.jpg",
        title=f"File:Korea University {pid}.jpg", matched_category="Korea University", found_by="category",
        author="Jane", license="CC BY-SA 4.0", lat=37.5895, lng=127.032,
        vision_checked=True,
    )
    return RawImage(**{**base, **over})


def shape() -> CampusShape:
    hall = Building(id="osm-way-1", name="Main Hall", type="academic", polygon=HALL, height_m=None, levels=5,
                    photo_ids=[], source="OpenStreetMap", inside_campus=True)
    return CampusShape(polygon=POLYGON, area_km2=0.6, osm_url="https://www.openstreetmap.org/way/9", buildings=[hall])


def collector(name, images=(), status="ok", delay=0.0, detail=None, exc=None, batches=()):
    """`batches`: lists of images handed to `on_batch` before the delay, like the real collectors do."""
    async def collect(query, client, on_batch=None):
        for batch in batches:
            if on_batch:
                on_batch(list(batch))
            await asyncio.sleep(0)
        await asyncio.sleep(delay)
        if exc:
            raise exc
        return SourceResult(name=name, status=status, took_ms=int(delay * 1000), images=list(images), detail=detail)
    return collect


@pytest.fixture
def fake(monkeypatch):
    """Default: every source answers quickly; tests override single pieces through the returned dict."""
    cache.clear()
    calls = {"wikidata": 0, "osm": 0}
    state = {"record": record(), "wikidata_exc": None, "osm_delay": 0.0, "shape": shape()}

    async def get_university(client, qid, lang="en", with_places=True):
        calls["wikidata"] += 1
        await asyncio.sleep(0.01)
        if state["wikidata_exc"]:
            raise state["wikidata_exc"]
        return state["record"] if qid == QID else None

    async def find_campus(query, client):
        calls["osm"] += 1
        await asyncio.sleep(state["osm_delay"])
        return SourceResult(name="openstreetmap", status="ok", took_ms=1), state["shape"]

    async def wiki(client, titles, lang):
        return WikiSummary(text="Korea University is in Seoul.", url="https://en.wikipedia.org/wiki/Korea_University",
                           title="Korea University", lang="en")

    async def add_places(client, uni, lang):
        return None

    async def discover_campus_subjects(client, uni, bbox=None):
        return []

    async def center_route(client, lat, lng, c_lat, c_lng, timeout_s=4.0):
        return None

    monkeypatch.setattr(orchestrator, "get_university", get_university)
    monkeypatch.setattr(orchestrator, "add_places", add_places)
    monkeypatch.setattr(orchestrator, "discover_campus_subjects", discover_campus_subjects)
    monkeypatch.setattr(orchestrator, "center_route", center_route)
    monkeypatch.setattr(campus_router, "get_university", get_university)
    monkeypatch.setattr(osm, "find_campus", find_campus)
    monkeypatch.setattr(orchestrator, "wikipedia_summary", wiki)
    monkeypatch.setattr(orchestrator, "PHOTO_COLLECTORS", {
        "wikimedia_commons": collector("wikimedia_commons", [raw("commons-1"), raw("commons-2", lat=37.60, lng=127.05)]),
        "flickr": collector("flickr", status="skipped", detail="no FLICKR_API_KEY"),
        "mapillary": collector("mapillary", status="skipped", detail="no MAPILLARY_TOKEN"),
        "official_site": collector("official_site"),
        "openverse": collector("openverse"),
        "web_search": collector("web_search", status="skipped", detail="no BRAVE_SEARCH_API_KEY"),
    })
    yield {"state": state, "calls": calls, "set": lambda name, fn: orchestrator.PHOTO_COLLECTORS.__setitem__(name, fn)}
    cache.clear()


def parse_sse(text: str) -> list[tuple[str, dict]]:
    events = []
    for block in text.strip().split("\n\n"):
        lines = dict(line.split(": ", 1) for line in block.split("\n"))
        events.append((lines["event"], json.loads(lines["data"])))
    return events


async def get(path: str) -> httpx.Response:
    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://test") as client:
        return await client.get(path)


def run(coro):
    return asyncio.run(coro)
