import asyncio
import json
from collections.abc import AsyncIterator
from typing import Literal

from fastapi import APIRouter, Path, Query
from fastapi.responses import JSONResponse, StreamingResponse

from app.models import ErrorResponse, SourceStatus
from app.services import cache
from app.services.orchestrator import ProfileBuild, ProfileUnavailable, UniversityNotFound, replay_events, start_or_join

router = APIRouter(tags=["profile"])

SSE_HEADERS = {"Cache-Control": "no-cache", "X-Accel-Buffering": "no", "Connection": "keep-alive"}


def sse(event: str, data: dict) -> str:
    return f"event: {event}\ndata: {json.dumps(data, ensure_ascii=False)}\n\n"


async def replay(events: list[tuple[str, dict]]) -> AsyncIterator[str]:
    for event, data in events:
        yield sse(event, data)


async def follow(build: ProfileBuild) -> AsyncIterator[str]:
    build.log.followers += 1
    try:
        async for event, data in build.log.follow():
            yield sse(event, data)
    finally:
        build.log.followers -= 1
        if build.log.followers == 0 and not build.log.closed:
            build.cancel()  # the last client disconnected: stop the sources


@router.get(
    "/profile/{wikidata_id}",
    response_class=StreamingResponse,
    responses={
        200: {"content": {"text/event-stream": {}}, "description": "SSE stream, docs/CONTRACT.md §3"},
        404: {"model": ErrorResponse, "description": "No Wikidata item with this ID"},
        503: {"model": ErrorResponse, "description": "Wikidata is unavailable"},
    },
)
async def get_profile(
    wikidata_id: str = Path(pattern=r"^Q\d+$", description="Wikidata ID from /resolve, e.g. Q39997"),
    lang: Literal["ru", "en"] = Query(default="ru", description="Language of labels and evidence"),
):
    cached = cache.get_profile(wikidata_id, lang)
    if cached is not None:
        return StreamingResponse(replay(replay_events(cached)), media_type="text/event-stream", headers=SSE_HEADERS)
    build = start_or_join(wikidata_id, lang)
    try:
        await asyncio.shield(build.ready)  # a cancelled request must not cancel the shared build
    except UniversityNotFound:
        body = ErrorResponse(detail=f"No university found for Wikidata ID {wikidata_id}.")
        return JSONResponse(status_code=404, content=body.model_dump())
    except ProfileUnavailable as exc:
        body = ErrorResponse(
            detail="Wikidata is unavailable right now, so the profile cannot be built. Try again later.",
            sources_status=[SourceStatus(name="wikidata", status=exc.state)],
        )
        return JSONResponse(status_code=503, content=body.model_dump())
    return StreamingResponse(follow(build), media_type="text/event-stream", headers=SSE_HEADERS)
