"""Tests never use the real keys from backend/.env: every keyed source starts unconfigured."""

import pytest

from app.config import settings

KEYS = ("flickr_api_key", "mapillary_token", "openverse_client_id", "openverse_client_secret",
        "brave_search_api_key", "kakao_api_key", "llm_api_key")


@pytest.fixture(autouse=True)
def no_real_keys():
    saved = {k: getattr(settings, k) for k in KEYS}
    for k in KEYS:
        object.__setattr__(settings, k, "")  # Settings is frozen; the shared instance is patched in place
    yield
    for k, v in saved.items():
        object.__setattr__(settings, k, v)
