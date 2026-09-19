from typing import Literal

from pydantic import AliasChoices, BaseModel, Field

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


# ---------- GET /profile/{wikidata_id} (docs/CONTRACT.md §3) ----------

EvidenceType = Literal["geo", "category", "text", "vision", "missing", "date", "content"]
Tier = Literal["verified", "likely", "unconfirmed"]
PhotoCategory = Literal["campus", "dorms", "classrooms", "libraries", "city"]
PhotoTag = Literal["sport", "labs", "dorm", "student_life"]
DateSource = Literal["exif", "source_metadata", "structured_data", "upload_only", "text_hint", "unknown"]
Freshness = Literal["2024_plus", "2020_2023", "older", "date_unknown", "historic"]
ProfileSourceState = Literal["pending", "ok", "timeout", "error", "skipped"]


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
    tags: list[PhotoTag]
    confidence: int = Field(ge=0, le=100)
    tier: Tier
    source_url: str
    source_domain: str
    author: str
    license: str = Field(description="'unknown' when the source states no license")
    date_taken: str | None = Field(default=None, validation_alias=AliasChoices("date_taken", "published_at"))
    date_uploaded: str | None = None
    date_source: DateSource = "unknown"
    freshness: Freshness = "date_unknown"
    vision_checked: bool = False
    highlight: bool = Field(default=False, description="Main building, main gate or campus overview: shown first")
    retrieved_at: str
    lat: float | None
    lng: float | None
    heading_deg: float | None = Field(default=None, description="Camera direction, 0 = north, clockwise")
    evidence: list[Evidence]
    duplicates: list[DuplicatePhoto]

    @property
    def published_at(self) -> str | None:
        """Compatibility accessor; omitted from serialized API output."""
        return self.date_taken or self.date_uploaded


class ProfileSourceStatus(BaseModel):
    name: str
    status: ProfileSourceState
    count: int
    took_ms: int | None = None


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


class CenterRoute(BaseModel):
    """Road route campus → city centre from OSRM (car). walk_min is estimated from road_km, not routed."""

    road_km: float
    drive_min: int
    walk_min: int
    geometry: list[list[float]] = Field(description="[[lng, lat], ...] simplified road line")


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
    center_route: CenterRoute | None = None
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


class ProfileDone(BaseModel):
    """Payload of the final SSE event `done`."""

    university: ProfileUniversity
    stats: ProfileStats
    generated_in_ms: int
    cached: bool
    partial: bool = Field(description="A source timed out or failed, or the 30 s deadline hit")
    photo_ids: list[str] = Field(default_factory=list, description="Final ranked ids; discard provisional photos not listed")


# ---------- GET /campus/{wikidata_id} (docs/CONTRACT.md §4) ----------

BuildingType = Literal["academic", "dorm", "library", "sport", "lab", "food", "other"]
PanoramaProvider = Literal["mapillary", "kakao", "google"]


class LatLng(BaseModel):
    lat: float
    lng: float


class TransitStop(BaseModel):
    type: Literal["metro", "bus"]
    name: str
    lat: float
    lng: float
    walk_min: int


class CampusInfo(BaseModel):
    center: LatLng
    polygon: list[list[float]] | None = Field(description="[[lng, lat], ...]")
    area_km2: float | None
    city_center: Place | None
    distance_to_center_km: float | None
    transit: list[TransitStop]


class Building(BaseModel):
    id: str
    name: str
    type: BuildingType
    polygon: list[list[float]] = Field(description="[[lng, lat], ...]")
    height_m: float | None
    levels: int | None
    photo_ids: list[str]
    source: str
    inside_campus: bool


class PhotoPin(BaseModel):
    photo_id: str
    lat: float
    lng: float
    heading_deg: float | None
    tier: Tier
    confidence: int = Field(ge=0, le=100)
    thumb_url: str | None
    building_id: str | None


class PanoramaStart(BaseModel):
    lat: float
    lng: float
    captured_at: str | None
    image_id: str | None = Field(default=None, description="Provider image id, e.g. the Mapillary image key")


class Panoramas(BaseModel):
    provider: PanoramaProvider | None
    available: bool
    checked_providers: list[PanoramaProvider]
    start: PanoramaStart | None
    points: list[PanoramaStart] = Field(default_factory=list, description="Street-level images around the campus")


class CampusMapResponse(BaseModel):
    campus: CampusInfo
    buildings: list[Building]
    photo_pins: list[PhotoPin]
    panoramas: Panoramas


# ---------- POST /chat (docs/CONTRACT.md §5) ----------

MascotState = Literal["talking", "pointing", "dont_know"]


class ChatTurn(BaseModel):
    role: Literal["user", "assistant"]
    text: str


class ChatRequest(BaseModel):
    wikidata_id: str = Field(pattern=r"^Q\d+$")
    lang: Literal["ru", "en"] = "ru"
    messages: list[ChatTurn] = Field(min_length=1)


class ChatAction(BaseModel):
    type: Literal["photos", "map", "tab"]
    photo_ids: list[str] | None = None
    building_id: str | None = None
    tab: PhotoCategory | None = None


class ChatMessage(BaseModel):
    role: Literal["assistant"] = "assistant"
    text: str
    mascot_state: MascotState
    citations: list[Citation]
    actions: list[ChatAction] = []
    checked: str | None = Field(default=None, description="Set with dont_know: where the answer was looked for")


# ---------- Internal: source collectors → verification pipeline (docs/CONTRACT.md §6) ----------

SourceName = Literal[
    "wikidata", "openstreetmap", "wikimedia_commons", "wikipedia", "flickr", "mapillary", "official_site",
    "openverse", "web_search",
]


class RawImage(BaseModel):
    """An unverified image candidate exactly as a source returned it. Collectors never score or categorize."""

    id: str = Field(description="'commons-<pageid>', 'flickr-<id>', 'mapillary-<id>', 'site-<sha1(url)[:12]>'")
    source: SourceName
    source_url: str
    source_domain: str
    full_url: str
    thumb_url: str | None = None
    title: str = ""
    description: str = ""
    source_categories: list[str] = []
    matched_category: str | None = None
    matched_subcategory: bool = False
    found_by: Literal[
        "category", "geosearch", "bbox", "site", "text", "depicts", "wikidata_image", "sitemap", "openverse"
    ]
    author: str | None = None
    license: str | None = None
    license_url: str | None = None
    date_taken: str | None = Field(default=None, validation_alias=AliasChoices("date_taken", "published_at"))
    date_uploaded: str | None = None
    date_source: DateSource = "unknown"
    date_hint_year: int | None = None
    vision_checked: bool = False
    vision_label: Literal["campus_place", "not_campus_place", "inconclusive"] | None = None
    vision_weight: int = 0
    vision_veto: bool = Field(default=False, description="Model is confident by a wide margin: never above unconfirmed")
    vision_category: PhotoCategory | None = None
    vision_source: Literal["openclip", "claude"] | None = None
    vision_highlight: bool = False
    subject_id: str | None = None
    subject_name: str | None = None
    subject_kind: Literal["university", "building", "city"] | None = None
    subject_building_type: BuildingType | None = None
    lat: float | None = None
    lng: float | None = None
    heading_deg: float | None = None
    width: int | None = None
    height: int | None = None
    sha1: str | None = None
    is_official_site: bool = False

    @property
    def published_at(self) -> str | None:
        """Compatibility accessor for older internal callers and tests."""
        return self.date_taken or self.date_uploaded


class SourceResult(BaseModel):
    name: SourceName
    status: Literal["ok", "timeout", "error", "skipped"]
    took_ms: int
    images: list[RawImage] = []
    detail: str | None = Field(default=None, description="Reason for error/skipped, for logs only")


class CampusShape(BaseModel):
    polygon: list[list[float]] | None = Field(description="[[lng, lat], ...]")
    area_km2: float | None
    osm_url: str | None
    buildings: list[Building]


# ---------- Guide chat (POST /chat) ----------


class ChatTurn(BaseModel):
    role: Literal["user", "assistant"]
    text: str = Field(max_length=2000)


class ChatRequest(BaseModel):
    wikidata_id: str = Field(pattern=r"^Q\d+$")
    lang: Literal["ru", "en"] = "ru"
    message: str = Field(min_length=1, max_length=500)
    history: list[ChatTurn] = Field(default_factory=list, max_length=12)


class ChatAction(BaseModel):
    type: Literal["tab"] = "tab"
    tab: PhotoCategory


class ChatReply(BaseModel):
    role: Literal["assistant"] = "assistant"
    text: str
    mascot_state: Literal["talking", "pointing", "dont_know"]
    citations: list[Citation] = Field(default_factory=list)
    actions: list[ChatAction] = Field(default_factory=list)
    checked: str | None = Field(default=None, description="When the answer is not in the sources: what was checked")
    from_web: bool = Field(default=False, description="Answered by a web search, not from the collected profile")
