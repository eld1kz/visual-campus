import asyncio

import httpx

from app.services.sources import openverse
from app.services.sources.base import SourceQuery


def test_openverse_keeps_original_page_and_does_not_use_index_date(monkeypatch):
    monkeypatch.setattr(openverse, "settings", type("S", (), {"openverse_client_id": "", "openverse_client_secret": ""})())
    seen = {}

    def handler(request: httpx.Request) -> httpx.Response:
        seen.update(request.url.params)
        return httpx.Response(200, json={"results": [{
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
    raw = result.images[0]
    assert raw.source_url.startswith("https://commons.wikimedia.org/")
    assert raw.date_taken is None and raw.date_uploaded is None and raw.date_source == "unknown"
