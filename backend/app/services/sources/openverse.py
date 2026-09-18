"""Openverse enrichment source. Index timestamps are deliberately not photo dates."""

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
        response = await request_with_retry(client, "GET", SEARCH_URL, deadline, "openverse", 1, headers=headers, params={
            "q": f'"{name}" campus',
            "page_size": AUTHENTICATED_PAGE_SIZE if token else ANONYMOUS_PAGE_SIZE,
        })
        response.raise_for_status()
        for item in response.json().get("results", []):
            if raw := parse_image(item):
                acc[raw.id] = raw
        return None

    return await run_collector("openverse", work, on_batch=on_batch)
