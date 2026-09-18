import os
from dataclasses import dataclass, field
from pathlib import Path

from dotenv import load_dotenv

load_dotenv(Path(__file__).resolve().parent.parent / ".env")

LOCAL_FRONTEND = "http://localhost:3000"


@dataclass(frozen=True)
class Settings:
    flickr_api_key: str = os.getenv("FLICKR_API_KEY", "")
    mapillary_token: str = os.getenv("MAPILLARY_TOKEN", "")
    openverse_client_id: str = os.getenv("OPENVERSE_CLIENT_ID", "")
    openverse_client_secret: str = os.getenv("OPENVERSE_CLIENT_SECRET", "")
    brave_search_api_key: str = os.getenv("BRAVE_SEARCH_API_KEY", "")
    kakao_api_key: str = os.getenv("KAKAO_API_KEY", "")
    llm_api_key: str = os.getenv("LLM_API_KEY", "")
    vision_enabled: bool = os.getenv("VISION_ENABLED", "1").lower() not in ("0", "false", "no")
    vision_max_candidates: int = int(os.getenv("VISION_MAX_CANDIDATES", "140"))
    # Borderline photos checked by Claude per profile (needs LLM_API_KEY); 0 turns the Claude check off.
    claude_vision_max: int = int(os.getenv("CLAUDE_VISION_MAX", "200"))
    # Optional cap on reliable photos per category ("campus=60,dorms=20"); empty = keep them all.
    photo_targets: str = os.getenv("PHOTO_TARGETS", "")
    frontend_url: str = os.getenv("FRONTEND_URL", "")
    source_timeout_s: float = float(os.getenv("SOURCE_TIMEOUT_S", "5"))
    user_agent: str = "VisualCampus/0.1 (LOCUS hackathon; https://github.com/eld1kz/visual-campus)"
    cors_origins: list[str] = field(default_factory=list)

    def __post_init__(self) -> None:
        origins = [LOCAL_FRONTEND, "http://127.0.0.1:3000"]
        if self.frontend_url:
            origins.append(self.frontend_url.rstrip("/"))
        object.__setattr__(self, "cors_origins", origins)


settings = Settings()
