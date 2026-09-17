"""Legacy shim: moved to app.services.sources.commons. Kept while profile.py/evidence.py/tests import it."""

from app.services.sources.commons import (  # noqa: F401
    COMMONS_API, PHOTO_MIMES, THUMB_WIDTH, CommonsFile, clean_text, collect_files, parse_date, parse_page,
)
