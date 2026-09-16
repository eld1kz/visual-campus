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


# ---------- GET /profile/{wikidata_id} (design/README.md "Data contracts → profile") ----------

EvidenceType = Literal["geo", "category", "text", "missing", "date", "content"]
Tier = Literal["verified", "likely", "unconfirmed"]
PhotoCategory = Literal["campus", "dorms", "classrooms", "libraries", "city"]


class Evidence(BaseModel):
    type: EvidenceType
    label: str
    weight: int


class DuplicatePhoto(BaseModel):
    id: str
    thumb_url: str | None
    source_url: str


class Photo(BaseModel):
    id: str
    thumb_url: str | None
    full_url: str
    category: PhotoCategory
    tags: list[str]
    confidence: int = Field(ge=0, le=100)
    tier: Tier
    source_url: str
    source_domain: str
    author: str
    license: str = Field(description="'unknown' when the source states no license")
    published_at: str | None
    retrieved_at: str
    lat: float | None
    lng: float | None
    evidence: list[Evidence]
    duplicates: list[DuplicatePhoto]


class ProfileSourceStatus(BaseModel):
    name: str
    status: SourceState
    count: int


class Citation(BaseModel):
    n: int
    title: str
    url: str


class Summary(BaseModel):
    text: str
    citations: list[Citation]


class Place(BaseModel):
    name: str
    lat: float
    lng: float


class ProfileUniversity(BaseModel):
    id: str
    name: str
    aliases: list[str]
    city: str | None
    country: str | None
    website: str | None
    lat: float | None
    lng: float | None
    campus_polygon: list[list[float]] | None = Field(description="[[lng, lat], ...] from OpenStreetMap")
    campus_area_km2: float | None
    distance_to_center_km: float | None
    city_center: Place | None
    wikidata_id: str
    ror_id: str | None
    commons_category: str | None
    osm_url: str | None


class ProfileStats(BaseModel):
    photos: int
    verified: int
    likely: int
    hidden: int = Field(description="Unconfirmed photos, hidden by default in the UI")
    duplicates: int


class ProfileResponse(BaseModel):
    university: ProfileUniversity
    generated_in_ms: int
    sources_status: list[ProfileSourceStatus]
    summary: Summary
    stats: ProfileStats
    photos: list[Photo]
