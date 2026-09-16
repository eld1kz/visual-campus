from typing import Literal

from fastapi import APIRouter, Path, Query
from fastapi.responses import JSONResponse

from app.models import ErrorResponse, ProfileResponse
from app.services.profile import ProfileUnavailable, UniversityNotFound, build_profile

router = APIRouter(tags=["profile"])


@router.get(
    "/profile/{wikidata_id}",
    response_model=ProfileResponse,
    responses={
        404: {"model": ErrorResponse, "description": "No Wikidata item with this ID"},
        503: {"model": ErrorResponse, "description": "Wikidata is unavailable"},
    },
)
async def get_profile(
    wikidata_id: str = Path(pattern=r"^Q\d+$", description="Wikidata ID from /resolve, e.g. Q39997"),
    lang: Literal["ru", "en"] = Query(default="ru", description="Language of labels and evidence"),
):
    try:
        return await build_profile(wikidata_id, lang)
    except UniversityNotFound:
        body = ErrorResponse(detail=f"No university found for Wikidata ID {wikidata_id}.")
        return JSONResponse(status_code=404, content=body.model_dump())
    except ProfileUnavailable:
        body = ErrorResponse(detail="Wikidata is unavailable right now, so the profile cannot be built. Try again later.")
        return JSONResponse(status_code=503, content=body.model_dump())
