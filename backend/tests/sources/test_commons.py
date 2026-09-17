import asyncio

import httpx

from app.services.sources import commons
from app.services.sources.base import SourceQuery

PAGE = {
    "pageid": 42, "title": "File:Main hall.jpg",
    "coordinates": [{"lat": 37.59, "lon": 127.03}],
    "imageinfo": [{
        "url": "https://upload.wikimedia.org/a/Main_hall.jpg", "thumburl": "https://upload.wikimedia.org/640px-Main_hall.jpg",
        "descriptionurl": "https://commons.wikimedia.org/wiki/File:Main_hall.jpg", "mime": "image/jpeg",
        "sha1": "abc", "timestamp": "2020-01-02T03:04:05Z", "width": 4000, "height": 3000,
        "extmetadata": {
            "Artist": {"value": "<a href='//x'>Jane Doe</a>"}, "LicenseShortName": {"value": "CC BY-SA 4.0"},
            "LicenseUrl": {"value": "https://creativecommons.org/licenses/by-sa/4.0"},
            "DateTimeOriginal": {"value": "2019-05-02 10:00:00"}, "ImageDescription": {"value": "<b>Main</b> hall"},
            "Categories": {"value": "Korea University|Buildings"},
        },
    }],
}


def test_parse_page_and_to_raw_keep_author_license_and_provenance():
    f = commons.parse_page(PAGE)
    f.via_category, f.via_subcategory = "Korea University", False
    raw = commons.to_raw(f)
    assert raw.id == "commons-42"
    assert raw.author == "Jane Doe" and raw.license == "CC BY-SA 4.0"
    assert raw.license_url.startswith("https://creativecommons.org")
    assert raw.published_at == "2019-05-02"
    assert (raw.lat, raw.lng, raw.width, raw.sha1) == (37.59, 127.03, 4000, "abc")
    assert raw.description == "Main hall"
    assert raw.found_by == "category" and raw.matched_category == "Korea University"


def test_parse_page_drops_svg_and_tiny_files():
    svg = {**PAGE, "imageinfo": [{**PAGE["imageinfo"][0], "mime": "image/svg+xml"}]}
    tiny = {**PAGE, "imageinfo": [{**PAGE["imageinfo"][0], "width": 120}]}
    assert commons.parse_page(svg) is None
    assert commons.parse_page(tiny) is None


def _handler(request: httpx.Request) -> httpx.Response:
    p = request.url.params
    if p.get("list") == "categorymembers" and p["cmtype"] == "subcat":
        subs = [{"title": "Category:Korea University buildings"}, {"title": "Category:Korea University alumni"}]
        return httpx.Response(200, json={"query": {"categorymembers": subs if p["cmtitle"] == "Category:Korea University" else []}})
    if p.get("list") == "categorymembers":
        ids = {"Category:Korea University": [42], "Category:Korea University buildings": [42, 43]}[p["cmtitle"]]
        return httpx.Response(200, json={"query": {"categorymembers": [{"pageid": i} for i in ids]}})
    if p.get("list") == "geosearch":
        return httpx.Response(200, json={"query": {"geosearch": [{"pageid": 43}, {"pageid": 44}]}})
    assert "alumni" not in str(request.url)
    pages = {pid: {**PAGE, "pageid": int(pid), "title": f"File:{pid}.jpg"} for pid in p["pageids"].split("|")}
    return httpx.Response(200, json={"query": {"pages": pages}})


def test_collect_merges_category_subcategory_and_geosearch():
    query = SourceQuery("Q39997", ["Korea University"], 37.59, 127.03, None, "Korea University")

    async def run():
        async with httpx.AsyncClient(transport=httpx.MockTransport(_handler)) as client:
            return await commons.collect(query, client)

    result = asyncio.run(run())
    assert result.status == "ok"
    by_id = {r.id: r for r in result.images}
    assert set(by_id) == {"commons-42", "commons-43", "commons-44"}
    assert by_id["commons-42"].matched_category == "Korea University" and not by_id["commons-42"].matched_subcategory
    assert by_id["commons-43"].matched_subcategory and by_id["commons-43"].found_by == "category"
    assert by_id["commons-44"].found_by == "geosearch" and by_id["commons-44"].matched_category is None


def test_collect_skips_without_category_and_point():
    async def run():
        async with httpx.AsyncClient(transport=httpx.MockTransport(_handler)) as client:
            return await commons.collect(SourceQuery("Q1", [], None, None, None, None), client)

    assert asyncio.run(run()).status == "skipped"


def test_parse_date_handles_commons_formats():
    assert commons.parse_date("2012-05-20 14:03:22") == "2012-05-20"
    assert commons.parse_date('1970s<div style="display: none;">date QS:P,+1970</div>') == "1970"
    assert commons.parse_date(None) is None


def test_costume_subcategories_are_not_places():
    assert commons._NOT_A_PLACE.search("Academic dress of the University of Cambridge")
    assert not commons._NOT_A_PLACE.search("Buildings of the University of Cambridge")
