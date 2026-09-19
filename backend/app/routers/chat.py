from fastapi import APIRouter
from fastapi.responses import JSONResponse

from app.models import ChatReply, ChatRequest, ErrorResponse
from app.services import cache
from app.services.chat import answer

router = APIRouter(tags=["chat"])


@router.post("/chat", response_model=ChatReply, responses={404: {"model": ErrorResponse}})
async def chat(req: ChatRequest):
    """Kampi answers about a profile that was built in the last 30 minutes, only from its collected data."""
    cached = cache.get_profile(req.wikidata_id, req.lang) or cache.any_profile(req.wikidata_id)
    if cached is None:
        body = ErrorResponse(detail="Build the profile first: the guide answers only from collected data.")
        return JSONResponse(status_code=404, content=body.model_dump())
    return await answer(req, cached.profile)
