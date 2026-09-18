"""Brave Image Search fallback.

This source is intentionally low-trust: image search gives broad, fresh coverage, but it does not prove that a photo
belongs to the university. The scoring pipeline must keep these results unconfirmed unless another strong signal exists.
"""

import asyncio
import hashlib
from urllib.parse import urlparse

import httpx

from app.config import settings
from app.models import RawImage, SourceResult
from app.services.sources.base import MIN_SIDE_PX, Batches, Deadline, OnBatch, Skip, SourceQuery, run_collector

BRAVE_IMAGES = "https://api.search.brave.com/res/v1/images/search"
COUNT_PER_QUERY = 25
MAX_QUERIES = 6

TOPICS = (
    "campus building 2024 2025",
    "library campus 2024 2025",
    "student housing dormitory 2024 2025",
    "laboratory campus 2024 2025",
    "sports center campus 2024 2025",
    "student life campus 2024 2025",
)


def _site_domain(website: str | None) -> str | None:
    if not website:
        return None
    host = urlparse(website).hostname or ""
    return host.removeprefix("www.") or None


def _query_text(query: SourceQuery, topic: str) -> str:
    name = query.names[0] if query.names else query.wikidata_id
    site = _site_domain(query.website)
    # Prefer the official site when there is one, but keep the university name in the query for copied media pages.
    suffix = f" site:{site}" if site else ""
    return f'"{name}" {topic}{suffix}'[:400]


def parse_result(item: dict) -> RawImage | None:
    props = item.get("properties") or {}
    thumb = item.get("thumbnail") or {}
    page_url = item.get("url")
    image_url = props.get("url") or thumb.get("src")
    if not page_url or not image_url:
        return None
    parsed = urlparse(page_url)
    if parsed.scheme not in ("http", "https"):
        return None
    width, height = props.get("width"), props.get("height")
    if width and height and min(int(width), int(height)) < MIN_SIDE_PX:
        return None
    key = hashlib.sha1(f"{page_url}|{image_url}".encode()).hexdigest()[:12]
    return RawImage(
        id=f"web-{key}",
        source="web_search",
        source_url=page_url,
        source_domain=parsed.hostname or item.get("source") or "unknown",
        full_url=image_url,
        thumb_url=thumb.get("src") or props.get("placeholder"),
        title=item.get("title") or "",
        description=item.get("description") or "",
        found_by="text",
        author=None,
        license=None,
        # Brave exposes page_fetched, not the photo capture/upload date. Keep the photo date unknown.
        date_source="unknown",
        width=int(width) if width else None,
        height=int(height) if height else None,
    )


async def collect(query: SourceQuery, client: httpx.AsyncClient, on_batch: OnBatch | None = None) -> SourceResult:
    async def work(acc: Batches, deadline: Deadline) -> str | None:
        if not settings.brave_search_api_key:
            raise Skip("BRAVE_SEARCH_API_KEY is not set")
        if not query.names:
            raise Skip("no university name for web search")

        async def one(topic: str) -> None:
            resp = await client.get(
                BRAVE_IMAGES,
                headers={
                    "Accept": "application/json",
                    "Accept-Encoding": "gzip",
                    "X-Subscription-Token": settings.brave_search_api_key,
                },
                params={
                    "q": _query_text(query, topic),
                    "count": COUNT_PER_QUERY,
                    "country": "ALL",
                    "search_lang": "en",
                    "safesearch": "strict",
                    "spellcheck": 1,
                },
                timeout=deadline.left(),
            )
            resp.raise_for_status()
            for item in resp.json().get("results", []):
                if raw := parse_result(item):
                    acc[raw.id] = raw
            acc.flush()

        await asyncio.gather(*(one(topic) for topic in TOPICS[:MAX_QUERIES]))
        return None if acc else "no image search results"

    return await run_collector("web_search", work, on_batch=on_batch)
