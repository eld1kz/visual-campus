"""Official website: og:image / twitter:image of the home page and of up to two obvious "campus" pages."""

import asyncio
import hashlib
import html
import re
from urllib.parse import urljoin, urlparse

import httpx

from app.models import RawImage, SourceResult
from app.services.sources.base import Deadline, Skip, SourceQuery, run_collector

MAX_HTML_BYTES = 1_500_000
MAX_CAMPUS_PAGES = 2
MIN_IMAGE_BYTES = 10_000
_META = re.compile(r"<meta\b[^>]*>", re.IGNORECASE)
_ATTR = re.compile(r"""([a-zA-Z:_-]+)\s*=\s*("[^"]*"|'[^']*'|[^\s>]+)""")
_LINK = re.compile(r"""<a\b[^>]*href\s*=\s*["']([^"'#]+)["']""", re.IGNORECASE)
_TITLE = re.compile(r"<title[^>]*>(.*?)</title>", re.IGNORECASE | re.DOTALL)
_CAMPUS_PATH = re.compile(r"campus", re.IGNORECASE)
_IMAGE_KEYS = ("og:image:secure_url", "og:image", "og:image:url", "twitter:image", "twitter:image:src")


def meta_tags(page: str) -> dict[str, list[str]]:
    tags: dict[str, list[str]] = {}
    for tag in _META.findall(page):
        attrs = {k.lower(): html.unescape(v.strip("\"'")) for k, v in _ATTR.findall(tag)}
        key = (attrs.get("property") or attrs.get("name") or "").lower()
        if key and attrs.get("content"):
            tags.setdefault(key, []).append(attrs["content"].strip())
    return tags


def page_images(page: str, page_url: str) -> list[RawImage]:
    """og/twitter images declared by one HTML page, absolute and de-duplicated, SVG excluded."""
    tags = meta_tags(page)
    title_match = _TITLE.search(page)
    title = (tags.get("og:title") or [html.unescape(title_match.group(1)).strip() if title_match else ""])[0]
    description = (tags.get("og:description") or tags.get("description") or [""])[0]
    host = urlparse(page_url).hostname or ""
    images, seen = [], set()
    for key in _IMAGE_KEYS:
        for value in tags.get(key, []):
            url = urljoin(page_url, value)
            if url in seen or urlparse(url).scheme not in ("http", "https") or urlparse(url).path.lower().endswith(".svg"):
                continue
            seen.add(url)
            images.append(RawImage(
                id=f"site-{hashlib.sha1(url.encode()).hexdigest()[:12]}",
                source="official_site",
                source_url=page_url,
                source_domain=host,
                full_url=url,
                thumb_url=None,
                title=re.sub(r"\s+", " ", title),
                description=re.sub(r"\s+", " ", description),
                found_by="site",
                is_official_site=True,
            ))
    return images


def campus_links(page: str, page_url: str) -> list[str]:
    """Same-site links whose path mentions "campus", shortest first."""
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
    async with client.stream("GET", url, timeout=deadline.left(), follow_redirects=True) as resp:
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
                await take(page_images(*fetched))

        await asyncio.gather(*(sub(link) for link in campus_links(page, url)))
        return None if acc else "no og:image on the site"

    return await run_collector("official_site", work)
