from fastapi import APIRouter, Query
from fastapi.responses import JSONResponse

from app.models import ErrorResponse, ResolveResponse
from app.services.resolver import AllSourcesFailed, resolve

router = APIRouter(tags=["resolve"])


@router.get(
    "/resolve",
    response_model=ResolveResponse,
    responses={503: {"model": ErrorResponse, "description": "Every source failed or timed out"}},
)
async def resolve_university(
    q: str = Query(min_length=2, max_length=200, description="University name, any language"),
):
    try:
        return await resolve(q.strip())
    except AllSourcesFailed as exc:
        body = ErrorResponse(
            detail="University registries are unavailable right now (ROR and Wikidata). Try again later.",
            sources_status=exc.sources_status,
        )
        return JSONResponse(status_code=503, content=body.model_dump())
