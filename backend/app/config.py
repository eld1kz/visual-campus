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
    kakao_api_key: str = os.getenv("KAKAO_API_KEY", "")
    llm_api_key: str = os.getenv("LLM_API_KEY", "")
    frontend_url: str = os.getenv("FRONTEND_URL", "")
    source_timeout_s: float = float(os.getenv("SOURCE_TIMEOUT_S", "5"))
    # Local CLIP check of what a photo shows (pipeline/vision.py); 0 turns it off.
    vision_enabled: bool = os.getenv("VISION_ENABLED", "1") != "0"
    user_agent: str = "VisualCampus/0.1 (LOCUS hackathon; https://github.com/eld1kz/visual-campus)"
    cors_origins: list[str] = field(default_factory=list)

    def __post_init__(self) -> None:
        origins = [LOCAL_FRONTEND, "http://127.0.0.1:3000"]
        if self.frontend_url:
            origins.append(self.frontend_url.rstrip("/"))
        object.__setattr__(self, "cors_origins", origins)


settings = Settings()
