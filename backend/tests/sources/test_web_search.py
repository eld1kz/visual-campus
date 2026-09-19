import asyncio
import dataclasses

import httpx

from app.services.sources import web_search
from tests.sources.test_keyed_and_site import QUERY

BRAVE_ITEM = {
    "type": "image_result",
    "title": "Korea University Main Campus 2025",
    "url": "https://www.korea.ac.kr/campus/main",
    "source": "korea.ac.kr",
    "page_fetched": "2026-01-02T03:04:05Z",
    "thumbnail": {"src": "https://imgs.search.brave.com/thumb.jpg", "width": 500, "height": 333},
    "properties": {"url": "https://www.korea.ac.kr/img/main-campus.jpg", "width": 1600, "height": 1000},
}


def run(handler):
    async def go():
        async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
            return await web_search.collect(QUERY, client)
    return asyncio.run(go())


def test_parse_result_keeps_source_page_and_does_not_invent_date():
    raw = web_search.parse_result(BRAVE_ITEM)
    assert raw.id.startswith("web-")
    assert raw.source == "web_search"
    assert raw.source_url == "https://www.korea.ac.kr/campus/main"
    assert raw.full_url == "https://www.korea.ac.kr/img/main-campus.jpg"
    assert raw.thumb_url == "https://imgs.search.brave.com/thumb.jpg"
    assert raw.source_domain == "www.korea.ac.kr"
    assert raw.published_at is None and raw.license is None


def test_collect_skips_without_key_and_reads_brave_results(monkeypatch):
    assert run(lambda request: httpx.Response(500)).status == "skipped"
    monkeypatch.setattr(web_search, "settings", dataclasses.replace(web_search.settings, brave_search_api_key="k"))

    seen = []

    def handler(request: httpx.Request) -> httpx.Response:
        seen.append(request.url.params["q"])
        assert request.headers["X-Subscription-Token"] == "k"
        return httpx.Response(200, json={"type": "images", "results": [BRAVE_ITEM]})

    result = run(handler)
    assert result.status == "ok"
    assert [raw.id for raw in result.images] == [web_search.parse_result(BRAVE_ITEM).id]
    assert seen and all('"Korea University"' in q for q in seen)


def test_search_gaps_runs_narrow_topics_and_ignores_failures(monkeypatch):
    monkeypatch.setattr(web_search, "settings", dataclasses.replace(web_search.settings, brave_search_api_key="k"))
    seen = []

    def handler(request: httpx.Request) -> httpx.Response:
        seen.append(request.url.params["q"])
        if "reading room" in request.url.params["q"]:
            return httpx.Response(500)
        return httpx.Response(200, json={"results": [BRAVE_ITEM]})

    async def run():
        async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
            return await web_search.search_gaps(QUERY, client, ["libraries"], 2.0)

    raws = asyncio.run(run())
    assert len(seen) == 2 and all("library" in q for q in seen)
    assert len(raws) == 1  # the failing topic is skipped, not fatal
