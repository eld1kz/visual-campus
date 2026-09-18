"""Openverse enrichment source. Index timestamps are deliberately not photo dates.

Verified live (2026-09): anonymous access allows ~1 request/s (20/min burst, 200/day) and `page_size` ≤ 20; a larger
page size is rejected with 401. A quoted name is too strict (1 hit for "Nazarbayev University" campus), so the
search asks for `<name> campus` first and falls back to the bare name when that returns too little.
"""

import asyncio
import logging
from urllib.parse import urlparse

import httpx

from app.config import settings
from app.models import RawImage, SourceResult
from app.services.pipeline.dates import text_year
from app.services.sources.base import Batches, Deadline, OnBatch, SourceQuery, request_with_retry, run_collector

SEARCH_URL = "https://api.openverse.org/v1/images/"
TOKEN_URL = "https://api.openverse.org/v1/auth_tokens/token/"
ANONYMOUS_PAGE_SIZE = 20
AUTHENTICATED_PAGE_SIZE = 50
ANONYMOUS_GAP_S = 1.05  # anonymous burst limit is ~1 request per second
FALLBACK_BELOW = 10  # results from "<name> campus" below which the bare name is also searched

logger = logging.getLogger("visual_campus.sources.openverse")


async def _token(client: httpx.AsyncClient, deadline: Deadline) -> str | None:
    if not settings.openverse_client_id or not settings.openverse_client_secret:
        return None
    response = await client.post(TOKEN_URL, timeout=deadline.left(), data={
        "client_id": settings.openverse_client_id,
        "client_secret": settings.openverse_client_secret,
        "grant_type": "client_credentials",
    })
    response.raise_for_status()
    return response.json().get("access_token")


def parse_image(item: dict) -> RawImage | None:
    full = item.get("url")
    source_url = item.get("foreign_landing_url")
    if not full or not source_url or not item.get("id"):
        return None
    license_name = (item.get("license") or "").upper()
    if version := item.get("license_version"):
        license_name = f"{license_name} {version}"
    title = item.get("title") or ""
    hint = text_year(title)
    return RawImage(
        id=f"openverse-{item['id']}",
        source="openverse",
        source_url=source_url,
        source_domain=urlparse(source_url).hostname or "openverse.org",
        full_url=full,
        thumb_url=item.get("thumbnail"),
        title=title,
        description=item.get("attribution") or "",
        found_by="openverse",
        author=item.get("creator") or None,
        license=license_name or None,
        license_url=item.get("license_url") or None,
        date_source="text_hint" if hint else "unknown",
        date_hint_year=hint,
        width=item.get("width"),
        height=item.get("height"),
    )


async def collect(query: SourceQuery, client: httpx.AsyncClient, on_batch: OnBatch | None = None) -> SourceResult:
    async def work(acc: Batches, deadline: Deadline) -> str | None:
        name = next((name for name in query.names if len(name) >= 4), query.wikidata_id)
        token = await _token(client, deadline)
        headers = {"Authorization": f"Bearer {token}"} if token else {}
        page_size = AUTHENTICATED_PAGE_SIZE if token else ANONYMOUS_PAGE_SIZE

        async def search(text: str) -> int:
            params = {"q": text, "page_size": page_size}
            response = await request_with_retry(client, "GET", SEARCH_URL, deadline, "openverse", 1, headers=headers, params=params)
            if response.status_code != 200:
                limits = {k: v for k, v in response.headers.items() if k.lower().startswith("x-ratelimit")}
                detail = response.json().get("detail") if "json" in response.headers.get("content-type", "") else response.text[:200]
                logger.warning("openverse q=%r page_size=%s status=%s detail=%r ratelimit=%s",
                               text, page_size, response.status_code, detail, limits)
                response.raise_for_status()
            results = response.json().get("results", [])
            for item in results:
                if raw := parse_image(item):
                    acc[raw.id] = raw
            acc.flush()
            logger.info("openverse q=%r results=%d total=%s", text, len(results), response.json().get("result_count"))
            return len(results)

        found = await search(f"{name} campus")
        if found < FALLBACK_BELOW and deadline.left() > ANONYMOUS_GAP_S + 1:
            if not token:
                await asyncio.sleep(ANONYMOUS_GAP_S)
            await search(name)
        return None

    return await run_collector("openverse", work, on_batch=on_batch)
