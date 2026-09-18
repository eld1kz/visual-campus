import asyncio

import httpx

from app.services.sources import openverse
from app.services.sources.base import SourceQuery


def test_openverse_keeps_original_page_and_does_not_use_index_date(monkeypatch):
    monkeypatch.setattr(openverse, "settings", type("S", (), {"openverse_client_id": "", "openverse_client_secret": ""})())
    monkeypatch.setattr(openverse, "ANONYMOUS_GAP_S", 0)
    seen = {}
    queries = []

    def handler(request: httpx.Request) -> httpx.Response:
        seen.update(request.url.params)
        queries.append(request.url.params["q"])
        return httpx.Response(200, json={"result_count": 1, "results": [{
            "id": "abc", "url": "https://images.example/campus.jpg",
            "thumbnail": "https://images.example/thumb.jpg",
            "foreign_landing_url": "https://commons.wikimedia.org/wiki/File:Campus.jpg",
            "title": "Campus view", "creator": "Jane", "license": "by-sa", "license_version": "4.0",
            "license_url": "https://creativecommons.org/licenses/by-sa/4.0/", "indexed_on": "2026-01-01",
            "width": 1200, "height": 800,
        }]})

    async def run():
        query = SourceQuery("Q1", ["Example University"], 1, 2, None, None)
        async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
            return await openverse.collect(query, client)

    result = asyncio.run(run())
    assert result.status == "ok" and seen["page_size"] == "20"
    # unquoted "<name> campus" first, bare name as the fallback when the first search is thin
    assert queries == ["Example University campus", "Example University"]
    raw = result.images[0]
    assert raw.source_url.startswith("https://commons.wikimedia.org/")
    assert raw.date_taken is None and raw.date_uploaded is None and raw.date_source == "unknown"


def test_openverse_reports_rejected_page_size_as_a_source_error(monkeypatch):
    monkeypatch.setattr(openverse, "settings", type("S", (), {"openverse_client_id": "", "openverse_client_secret": ""})())

    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(401, json={"detail": "page_size may not exceed 20 for anonymous requests"},
                              headers={"x-ratelimit-available-anon_burst": "19"})

    async def run():
        query = SourceQuery("Q1", ["Example University"], 1, 2, None, None)
        async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
            return await openverse.collect(query, client)

    result = asyncio.run(run())
    assert result.status == "error" and result.images == [] and "401" in (result.detail or "")
