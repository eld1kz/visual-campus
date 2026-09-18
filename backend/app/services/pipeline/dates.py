"""Strict photo-date normalization and presentation labels.

Capture, upload, page, index and retrieval timestamps are deliberately kept
separate. Text years are hints only and never become a displayed capture date.
"""

import re
from datetime import date, datetime, timezone

from app.models import DateSource, Freshness

_DATE = re.compile(r"^\+?(\d{4})(?:-(\d{2})(?:-(\d{2}))?)?(?:[T ].*)?$")
_TEXT_YEAR = re.compile(r"(?<!\d)(18\d{2}|19\d{2}|20\d{2})(?!\d)")


def normalize_date(value: object, today: date | None = None) -> str | None:
    """Return YYYY, YYYY-MM or YYYY-MM-DD; reject malformed and future values."""
    if value is None:
        return None
    text = str(value).strip()
    match = _DATE.match(text)
    if not match:
        return None
    year, month, day = match.groups()
    try:
        if day:
            parsed = date(int(year), int(month), int(day))
            normalized = parsed.isoformat()
        elif month:
            if not 1 <= int(month) <= 12:
                return None
            parsed = date(int(year), int(month), 1)
            normalized = f"{year}-{month}"
        else:
            parsed = date(int(year), 1, 1)
            normalized = year
    except ValueError:
        return None
    if parsed > (today or date.today()):
        return None
    return normalized


def unix_date(value: object, milliseconds: bool = False, today: date | None = None) -> str | None:
    try:
        seconds = int(value) / (1000 if milliseconds else 1)
        parsed = datetime.fromtimestamp(seconds, tz=timezone.utc).date()
    except (TypeError, ValueError, OverflowError, OSError):
        return None
    if parsed > (today or date.today()):
        return None
    return parsed.isoformat()


def text_year(*values: str) -> int | None:
    for value in values:
        if match := _TEXT_YEAR.search(value or ""):
            year = int(match.group(1))
            if year <= date.today().year:
                return year
    return None


def freshness(date_taken: str | None, hint_year: int | None = None, historic: bool = False) -> Freshness:
    if historic:
        return "historic"
    year = int(date_taken[:4]) if date_taken and date_taken[:4].isdigit() else None
    if year is None:
        return "historic" if hint_year is not None and hint_year < 1950 else "date_unknown"
    if year >= 2024:
        return "2024_plus"
    if year >= 2020:
        return "2020_2023"
    return "historic" if year < 1950 else "older"


def effective_date_source(
    date_taken: str | None, date_uploaded: str | None, source: DateSource, hint_year: int | None = None
) -> DateSource:
    if date_taken:
        return source if source in ("exif", "source_metadata", "structured_data") else "source_metadata"
    if date_uploaded:
        return "upload_only"
    if hint_year is not None:
        return "text_hint"
    return "unknown"


def date_evidence_label(
    date_taken: str | None, date_uploaded: str | None, source: DateSource, lang: str = "en"
) -> str | None:
    ru = lang == "ru"
    if date_taken:
        names = {
            "exif": "EXIF",
            "source_metadata": "метаданные источника" if ru else "source metadata",
            "structured_data": "структурированные данные" if ru else "structured data",
        }
        basis = names.get(source, names["source_metadata"])
        return f"Снято {date_taken} ({basis})" if ru else f"Taken {date_taken} ({basis})"
    if date_uploaded:
        return f"Только дата загрузки: {date_uploaded}" if ru else f"Upload date only: {date_uploaded}"
    return None
