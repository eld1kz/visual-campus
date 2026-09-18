"""Flickr and Mapillary fixtures follow the official API docs (not verified live: no keys)."""

import asyncio
import dataclasses

import httpx

from app.services.sources import base, flickr, mapillary, official_site
from app.services.sources.base import SourceQuery

QUERY = SourceQuery("Q39997", ["Korea University"], 37.59, 127.03, "https://www.korea.ac.kr/", "Korea University")

FLICKR_PHOTO = {  # flickr.photos.search with extras, format=json&nojsoncallback=1
    "id": "5555", "owner": "12345@N00", "secret": "s", "server": "1", "farm": 1, "title": "Main hall",
    "ispublic": 1, "license": "4", "description": {"_content": "Spring <b>campus</b>"},
    "dateupload": "1557000000", "datetaken": "2019-05-02 10:11:12", "datetakenunknown": "0",
    "ownername": "Jane", "latitude": "37.5891", "longitude": "127.0318", "accuracy": "16", "tags": "korea campus",
    "media": "photo", "url_l": "https://live.staticflickr.com/1/5555_s_b.jpg", "height_l": 768, "width_l": 1024,
    "url_z": "https://live.staticflickr.com/1/5555_s_z.jpg", "height_z": 480, "width_z": 640,
}


def run(coro_fn, handler):
    async def go():
        async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
            return await coro_fn(QUERY, client)
    return asyncio.run(go())


def test_flickr_parse_photo():
    raw = flickr.parse_photo(FLICKR_PHOTO)
    assert raw.id == "flickr-5555" and raw.source_url == "https://www.flickr.com/photos/12345@N00/5555"
    assert (raw.license, raw.author, raw.published_at) == ("CC BY 2.0", "Jane", "2019-05-02")
    assert (raw.lat, raw.lng, raw.width) == (37.5891, 127.0318, 1024)
    assert raw.full_url.endswith("_b.jpg") and raw.thumb_url.endswith("_z.jpg")
    assert raw.description == "Spring campus" and raw.source_categories == ["korea", "campus"]
    assert flickr.parse_photo({**FLICKR_PHOTO, "license": "0"}) is None  # all rights reserved
    no_geo = flickr.parse_photo({**FLICKR_PHOTO, "latitude": 0, "longitude": 0, "datetakenunknown": "1"})
    assert no_geo.lat is None and no_geo.published_at == "2019-05-04"


def test_flickr_skipped_without_key_and_api_error(monkeypatch):
    assert run(flickr.collect, lambda r: httpx.Response(500)).status == "skipped"
    monkeypatch.setattr(flickr, "settings", dataclasses.replace(flickr.settings, flickr_api_key="k"))
    ok = run(flickr.collect, lambda r: httpx.Response(200, json={"photos": {"page": 1, "pages": 1, "photo": [FLICKR_PHOTO]}, "stat": "ok"}))
    assert ok.status == "ok" and [i.id for i in ok.images] == ["flickr-5555"]
    bad = run(flickr.collect, lambda r: httpx.Response(200, json={"stat": "fail", "code": 100, "message": "Invalid API Key"}))
    assert bad.status == "error" and "Invalid API Key" in bad.detail


MAPILLARY_IMAGE = {  # GET graph.mapillary.com/images?fields=...
    "id": "1234567890", "captured_at": 1614556800000, "compass_angle": 370.5, "geometry": {"type": "Point", "coordinates": [127.03, 37.59]},
    "creator": {"username": "mapper", "id": "1"}, "width": 2048, "height": 1536, "is_pano": False,
    "thumb_1024_url": "https://scontent.example/1024.jpg", "thumb_original_url": "https://scontent.example/orig.jpg",
}


def test_mapillary_parse_and_skip(monkeypatch):
    raw = mapillary.parse_image(MAPILLARY_IMAGE)
    assert raw.id == "mapillary-1234567890" and (raw.lat, raw.lng) == (37.59, 127.03)
    assert (raw.heading_deg, raw.published_at, raw.author) == (10.5, "2021-03-01", "mapper")
    assert run(mapillary.collect, lambda r: httpx.Response(500)).status == "skipped"
    monkeypatch.setattr(mapillary, "settings", dataclasses.replace(mapillary.settings, mapillary_token="t"))
    ok = run(mapillary.collect, lambda r: httpx.Response(200, json={"data": [MAPILLARY_IMAGE]}))
    assert ok.status == "ok" and len(ok.images) == 1


def test_mapillary_clamps_large_bbox():
    w, s, e, n = mapillary.clamp_bbox((0, 0, 1, 1))
    assert (e - w) * (n - s) <= mapillary.MAX_BBOX_DEG2


HOME = """<html><head><title>Korea University</title>
<meta property="og:image" content="/img/campus.jpg"><meta content='https://cdn.korea.ac.kr/logo.svg' property='og:image'>
<meta name="twitter:image" content="https://www.korea.ac.kr/img/campus.jpg"></head>
<body><a href="/campus/life">Campus</a><a href="/library/main">Library</a>
<a href="/research/labs">Labs</a><a href="https://other.org/campus">x</a></body></html>"""


def test_official_site_og_images_and_campus_pages():
    def handler(request: httpx.Request) -> httpx.Response:
        if request.method == "HEAD":
            return httpx.Response(200, headers={"content-type": "image/jpeg", "content-length": "250000"})
        if request.url.path == "/campus/life":
            return httpx.Response(200, headers={"content-type": "text/html"}, text='<meta property="og:image" content="/img/tour.jpg">')
        if request.url.path == "/library/main":
            return httpx.Response(200, headers={"content-type": "text/html"}, text='<meta property="og:image" content="/img/library.jpg">')
        if request.url.path == "/research/labs":
            return httpx.Response(200, headers={"content-type": "text/html"}, text='<meta property="og:image" content="/img/lab.jpg">')
        return httpx.Response(200, headers={"content-type": "text/html; charset=utf-8"}, text=HOME)

    result = run(official_site.collect, handler)
    assert result.status == "ok"
    urls = sorted(i.full_url for i in result.images)
    assert urls == [
        "https://www.korea.ac.kr/img/campus.jpg",
        "https://www.korea.ac.kr/img/lab.jpg",
        "https://www.korea.ac.kr/img/library.jpg",
        "https://www.korea.ac.kr/img/tour.jpg",
    ]
    image = next(i for i in result.images if i.full_url.endswith("campus.jpg"))
    assert image.is_official_site and image.found_by == "site" and image.license is None and image.author is None
    assert image.title == "Korea University campus.jpg"
    assert image.id.startswith("site-") and len(image.id) == 17 and image.source_domain == "www.korea.ac.kr"


def test_official_site_drops_svg_by_mime():
    def handler(request: httpx.Request) -> httpx.Response:
        if request.method == "HEAD":
            return httpx.Response(200, headers={"content-type": "image/svg+xml"})
        return httpx.Response(200, headers={"content-type": "text/html"}, text=HOME)

    assert run(official_site.collect, handler).images == []


def test_run_collector_timeout_keeps_partial_results_as_ok():
    async def work(acc, deadline):
        acc["x"] = flickr.parse_photo(FLICKR_PHOTO)
        await asyncio.sleep(1)

    async def empty(acc, deadline):
        await asyncio.sleep(1)

    partial = asyncio.run(base.run_collector("flickr", work, budget_s=0.05))
    assert partial.status == "ok" and len(partial.images) == 1 and "partial" in partial.detail
    assert asyncio.run(base.run_collector("flickr", empty, budget_s=0.05)).status == "timeout"
