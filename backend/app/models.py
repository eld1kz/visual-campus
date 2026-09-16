from typing import Literal

from pydantic import BaseModel, Field

SourceState = Literal["ok", "timeout", "error"]
ResolveStatus = Literal["resolved", "ambiguous", "not_found"]


class SourceStatus(BaseModel):
    name: str = Field(description="Source identifier, e.g. 'ror' or 'wikidata'")
    status: SourceState


class UniversityCandidate(BaseModel):
    id: str = Field(description="ROR ID if known, otherwise Wikidata QID")
    name: str
    aliases: list[str] = []
    city: str | None = None
    country: str | None = None
    lat: float | None = None
    lng: float | None = None
    website: str | None = None
    wikidata_id: str | None = None
    ror_id: str | None = None
    commons_category: str | None = None
    match_score: float = Field(ge=0, le=1)


class ResolveResponse(BaseModel):
    query: str
    corrected_query: str | None = Field(
        default=None, description="Spelling suggestion used when the raw query found nothing"
    )
    status: ResolveStatus
    university: UniversityCandidate | None = Field(default=None, description="Set only when status is 'resolved'")
    candidates: list[UniversityCandidate] = Field(default=[], description="Best matches, at most 5")
    sources_status: list[SourceStatus]
    took_ms: int


class ErrorResponse(BaseModel):
    detail: str
    sources_status: list[SourceStatus] = []
