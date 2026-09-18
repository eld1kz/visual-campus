"""Official website: og:image / twitter:image from the home page and obvious campus-life pages."""

import asyncio
import hashlib
import html
import json
import re
import xml.etree.ElementTree as ET
from urllib.parse import unquote, urljoin, urlparse

import httpx

from app.models import RawImage, SourceResult
from app.services.sources.base import Deadline, Skip, SourceQuery, run_collector

MAX_HTML_BYTES = 1_500_000
MAX_CAMPUS_PAGES = 8
MIN_IMAGE_BYTES = 10_000
_META = re.compile(r"<meta\b[^>]*>", re.IGNORECASE)
_ATTR = re.compile(r"""([a-zA-Z:_-]+)\s*=\s*("[^"]*"|'[^']*'|[^\s>]+)""")
_LINK = re.compile(r"""<a\b[^>]*href\s*=\s*["']([^"'#]+)["']""", re.IGNORECASE)
_TITLE = re.compile(r"<title[^>]*>(.*?)</title>", re.IGNORECASE | re.DOTALL)
_IMG = re.compile(r"<img\b[^>]*>", re.IGNORECASE)
_JSON_LD = re.compile(
    r"<script\b[^>]*type=[\"']application/ld\+json[\"'][^>]*>(.*?)</script>", re.IGNORECASE | re.DOTALL
)
_CAMPUS_PATH = re.compile(
    r"campus|housing|dorm|residence|library|sport|athletic|student[-_/]?life|laborator|labs?|research|"
    r"기숙사|도서관|общежитие|библиотека",
    re.IGNORECASE,
)
_IMAGE_KEYS = ("og:image:secure_url", "og:image", "og:image:url", "twitter:image", "twitter:image:src")


def meta_tags(page: str) -> dict[str, list[str]]:
    tags: dict[str, list[str]] = {}
    for tag in _META.findall(page):
        attrs = {k.lower(): html.unescape(v.strip("\"'")) for k, v in _ATTR.findall(tag)}
        key = (attrs.get("property") or attrs.get("name") or "").lower()
        if key and attrs.get("content"):
            tags.setdefault(key, []).append(attrs["content"].strip())
    return tags


def _structured_image_dates(page: str, page_url: str) -> dict[str, tuple[str | None, str | None]]:
    """Dates only from an ImageObject that names the exact image URL."""
    dates: dict[str, tuple[str | None, str | None]] = {}
    for raw in _JSON_LD.findall(page):
        try:
            data = json.loads(html.unescape(raw))
        except (json.JSONDecodeError, TypeError):
            continue
        nodes = data.get("@graph", []) if isinstance(data, dict) else data if isinstance(data, list) else [data]
        for node in nodes:
            if not isinstance(node, dict) or node.get("@type") not in ("ImageObject", ["ImageObject"]):
                continue
            value = node.get("contentUrl") or node.get("url")
            if isinstance(value, dict):
                value = value.get("url")
            if isinstance(value, str):
                dates[urljoin(page_url, value)] = (node.get("dateCreated"), node.get("uploadDate"))
    return dates


def page_images(page: str, page_url: str, found_by: str = "site") -> list[RawImage]:
    """og/twitter images declared by one HTML page, absolute and de-duplicated, SVG excluded."""
    tags = meta_tags(page)
    title_match = _TITLE.search(page)
    title = (tags.get("og:title") or [html.unescape(title_match.group(1)).strip() if title_match else ""])[0]
    description = (tags.get("og:description") or tags.get("description") or [""])[0]
    host = urlparse(page_url).hostname or ""
    structured_dates = _structured_image_dates(page, page_url)
    images, seen = [], set()
    candidates: list[tuple[str, str]] = []
    for key in _IMAGE_KEYS:
        for value in tags.get(key, []):
            candidates.append((value, title))
    for tag in _IMG.findall(page):
        attrs = {k.lower(): html.unescape(v.strip("\"'")) for k, v in _ATTR.findall(tag)}
        src, alt = attrs.get("src") or attrs.get("data-src"), attrs.get("alt", "").strip()
        if src and len(alt) >= 8 and (_CAMPUS_PATH.search(alt) or _CAMPUS_PATH.search(urlparse(src).path)):
            candidates.append((src, alt))
    from app.services.pipeline.dates import normalize_date
    for value, image_title in candidates:
            url = urljoin(page_url, value)
            if url in seen or urlparse(url).scheme not in ("http", "https") or urlparse(url).path.lower().endswith(".svg"):
                continue
            seen.add(url)
            created, uploaded = structured_dates.get(url, (None, None))
            date_taken, date_uploaded = normalize_date(created), normalize_date(uploaded)
            filename = unquote(urlparse(url).path.rsplit("/", 1)[-1]).replace("_", " ")
            images.append(RawImage(
                id=f"site-{hashlib.sha1(url.encode()).hexdigest()[:12]}",
                source="official_site",
                source_url=page_url,
                source_domain=host,
                full_url=url,
                thumb_url=None,
                title=re.sub(r"\s+", " ", f"{image_title or title} {filename}"),
                description=re.sub(r"\s+", " ", description),
                found_by=found_by,
                date_taken=date_taken,
                date_uploaded=date_uploaded,
                date_source="structured_data" if date_taken else "upload_only" if date_uploaded else "unknown",
                is_official_site=True,
            ))
    return images


def campus_links(page: str, page_url: str) -> list[str]:
    """Same-site links whose path suggests visual campus evidence, shortest first."""
    host = (urlparse(page_url).hostname or "").removeprefix("www.")
    links = set()
    for href in _LINK.findall(page):
        url = urljoin(page_url, html.unescape(href))
        parsed = urlparse(url)
        if parsed.scheme in ("http", "https") and (parsed.hostname or "").removeprefix("www.") == host \
                and _CAMPUS_PATH.search(parsed.path):
            links.add(url)
    return sorted(links, key=len)[:MAX_CAMPUS_PAGES]


async def _fetch_html(client: httpx.AsyncClient, url: str, deadline: Deadline) -> tuple[str, str] | None:
    headers = {
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
        "User-Agent": "Mozilla/5.0 (compatible; VisualCampus/0.1; +https://github.com/eld1kz/visual-campus)",
    }
    async with client.stream("GET", url, timeout=deadline.left(), follow_redirects=True, headers=headers) as resp:
        if resp.status_code != 200:
            raise httpx.HTTPStatusError(f"HTTP {resp.status_code}", request=resp.request, response=resp)
        if "html" not in resp.headers.get("content-type", "html"):
            return None
        body = b""
        async for chunk in resp.aiter_bytes():
            body += chunk
            if len(body) > MAX_HTML_BYTES:
                break
        return body.decode(resp.encoding or "utf-8", errors="replace"), str(resp.url)


async def sitemap_links(client: httpx.AsyncClient, website: str, deadline: Deadline) -> list[str]:
    """Recent relevant pages from sitemap lastmod; lastmod never becomes a photo date."""
    root_url = urljoin(website, "/sitemap.xml")
    try:
        response = await client.get(root_url, timeout=min(deadline.left(), 2.5), follow_redirects=True)
        response.raise_for_status()
        root = ET.fromstring(response.content[:MAX_HTML_BYTES])
    except (httpx.HTTPError, ET.ParseError):
        return []
    rows = []
    for node in root.iter():
        if not node.tag.endswith("url"):
            continue
        loc = next((c.text for c in node if c.tag.endswith("loc")), None)
        lastmod = next((c.text for c in node if c.tag.endswith("lastmod")), "")
        if loc and _CAMPUS_PATH.search(urlparse(loc).path):
            rows.append((lastmod or "", loc))
    rows.sort(reverse=True)
    return [url for _, url in rows[:MAX_CAMPUS_PAGES]]


async def _is_photo(client: httpx.AsyncClient, image: RawImage, deadline: Deadline) -> bool:
    """Format-only check: not SVG / not an image / tiny file → drop. If HEAD is not answered, keep it."""
    try:
        resp = await client.head(image.full_url, timeout=min(deadline.left(), 2.0), follow_redirects=True)
    except httpx.HTTPError:
        return True
    if resp.status_code >= 400:
        return resp.status_code in (403, 405)  # HEAD not allowed is not proof of a broken image
    ctype = resp.headers.get("content-type", "")
    if ctype and (not ctype.startswith("image/") or "svg" in ctype):
        return False
    size = resp.headers.get("content-length")
    return not (size and size.isdigit() and int(size) < MIN_IMAGE_BYTES)


async def collect(query: SourceQuery, client: httpx.AsyncClient) -> SourceResult:
    async def work(acc: dict[str, RawImage], deadline: Deadline) -> str | None:
        if not query.website:
            raise Skip("no official website in Wikidata")

        async def take(images: list[RawImage]) -> None:
            checks = await asyncio.gather(*(_is_photo(client, im, deadline) for im in images))
            for image, ok in zip(images, checks):
                if ok:
                    acc.setdefault(image.id, image)  # same URL on several pages: keep the first page

        home = await _fetch_html(client, query.website, deadline)
        if home is None:
            return "home page is not HTML"
        page, url = home
        await take(page_images(page, url))

        async def sub(link: str) -> None:
            try:
                fetched = await _fetch_html(client, link, deadline)
            except httpx.HTTPError:
                return
            if fetched:
                fetched_page, fetched_url = fetched
                await take(page_images(fetched_page, fetched_url, "sitemap" if link in sitemap else "site"))

        sitemap = await sitemap_links(client, url, deadline)
        links = list(dict.fromkeys([*sitemap, *campus_links(page, url)]))[:MAX_CAMPUS_PAGES]
        await asyncio.gather(*(sub(link) for link in links))
        return None if acc else "no og:image on the site"

    return await run_collector("official_site", work)
