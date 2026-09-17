"""Collectors hand out candidates in batches before they finish; batches (last version per id) add up to the result."""

import asyncio
import dataclasses

import httpx

from app.services.sources import base, commons, flickr
from tests.sources.test_commons import _handler as commons_handler
from tests.sources.test_keyed_and_site import FLICKR_PHOTO, QUERY


def _merge(batches: list[list]) -> dict:
    merged = {}
    for batch in batches:
        merged.update({raw.id: raw for raw in batch})
    return merged


def test_commons_first_batch_arrives_before_geosearch_finishes():
    batches: list[list] = []
    got_batch = asyncio.Event()

    def on_batch(batch):
        batches.append(batch)
        got_batch.set()

    async def handler(request: httpx.Request) -> httpx.Response:
        if request.url.params.get("list") == "geosearch":  # released only by a batch delivered earlier
            await asyncio.wait_for(got_batch.wait(), timeout=2)
        return commons_handler(request)

    async def go():
        async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
            return await commons.collect(QUERY, client, on_batch=on_batch)

    result = asyncio.run(go())
    assert result.status == "ok" and result.detail is None
    assert len(batches) >= 2
    assert _merge(batches) == {raw.id: raw for raw in result.images}
    assert {"commons-43", "commons-44"} <= set(_merge(batches))  # geosearch files came in a later batch


def test_flickr_flushes_each_page(monkeypatch):
    monkeypatch.setattr(flickr, "settings", dataclasses.replace(flickr.settings, flickr_api_key="k"))
    batches: list[list] = []

    def handler(request: httpx.Request) -> httpx.Response:
        page = int(request.url.params["page"])
        assert len(batches) == page - 1  # page 1 was delivered before page 2 was requested
        photo = {**FLICKR_PHOTO, "id": str(page)}
        return httpx.Response(200, json={"photos": {"page": page, "pages": 2, "photo": [photo]}, "stat": "ok"})

    async def go():
        async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
            return await flickr.collect(QUERY, client, on_batch=batches.append)

    result = asyncio.run(go())
    assert [[r.id for r in b] for b in batches] == [["flickr-1"], ["flickr-2"]]
    assert _merge(batches) == {raw.id: raw for raw in result.images}


def test_run_collector_flushes_leftovers_on_timeout_and_survives_callback_errors():
    batches: list[list] = []

    async def work(acc, deadline):
        acc["x"] = flickr.parse_photo(FLICKR_PHOTO)
        await asyncio.sleep(1)

    partial = asyncio.run(base.run_collector("flickr", work, budget_s=0.05, on_batch=batches.append))
    assert partial.status == "ok" and [[r.id for r in b] for b in batches] == [["flickr-5555"]]

    def broken(batch):
        raise RuntimeError("consumer bug")

    async def quick(acc, deadline):
        acc["x"] = flickr.parse_photo(FLICKR_PHOTO)
        acc.flush()

    result = asyncio.run(base.run_collector("flickr", quick, on_batch=broken))
    assert result.status == "ok" and len(result.images) == 1
