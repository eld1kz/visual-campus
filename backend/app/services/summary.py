"""Profile summary (docs/CONTRACT.md §3 `summary`): only from texts collected for this profile.

Without LLM_API_KEY: the Wikipedia extract as is. With a key: an LLM rewrite with [n] footnotes, validated;
any failure falls back to the extract. The provider is not chosen yet — wire it in `complete()` only.
"""

import asyncio
import logging
import re
from dataclasses import dataclass

import httpx

from app.config import settings
from app.models import Citation, Summary

logger = logging.getLogger("visual_campus.summary")

LLM_TIMEOUT_S = 8.0
MAX_TEXT_CHARS = 2000
_FOOTNOTE = re.compile(r"\[(\d+)\]")


@dataclass
class SourceText:
    title: str  # "Wikipedia — Korea University"
    url: str
    text: str
    is_extract: bool = False  # True for the Wikipedia extract used without an LLM


async def complete(prompt: str, client: httpx.AsyncClient) -> str:
    """The one place to connect an LLM provider (uses settings.llm_api_key)."""
    raise NotImplementedError("LLM provider is not configured")


def build_prompt(texts: list[SourceText], lang: str) -> str:
    language = "Russian" if lang == "ru" else "English"
    sources = "\n\n".join(f"[{i}] {t.title}\n{t.text[:MAX_TEXT_CHARS]}" for i, t in enumerate(texts, start=1))
    return (
        f"Write 3-5 sentences in {language} about the university campus using ONLY the numbered sources below. "
        "End every sentence with the footnote [n] of the source it relies on. Do not add facts that are not "
        "in the sources. If the sources say nothing about the campus, answer with an empty string.\n\n" + sources
    )


def is_valid(text: str, citations: list[Citation]) -> bool:
    """Every footnote exists in citations and every non-empty sentence carries one."""
    known = {c.n for c in citations}
    used = {int(n) for n in _FOOTNOTE.findall(text)}
    if not used or not used <= known:
        return False
    sentences = [s for s in re.split(r"(?<=[.!?])\s+(?=[^\[])", text.strip()) if s.strip()]
    return all(_FOOTNOTE.search(s) for s in sentences)


def extract_summary(texts: list[SourceText]) -> Summary:
    wiki = next((t for t in texts if t.is_extract and t.text), None)
    if wiki is None:
        return Summary(text="", citations=[])
    return Summary(text=wiki.text, citations=[Citation(n=1, title=wiki.title, url=wiki.url)])


async def build_summary(
    texts: list[SourceText], lang: str, client: httpx.AsyncClient, timeout_s: float = LLM_TIMEOUT_S
) -> Summary:
    texts = [t for t in texts if t.text.strip()]
    if not texts:
        return Summary(text="", citations=[])
    if not settings.llm_api_key or timeout_s <= 0:
        return extract_summary(texts)
    citations = [Citation(n=i, title=t.title, url=t.url) for i, t in enumerate(texts, start=1)]
    try:
        text = (await asyncio.wait_for(complete(build_prompt(texts, lang), client), timeout=timeout_s)).strip()
    except Exception as exc:  # noqa: BLE001 — the extract is always a valid answer
        logger.warning("LLM summary failed, using the extract: %s", exc)
        return extract_summary(texts)
    if not is_valid(text, citations):
        logger.warning("LLM summary failed footnote validation, using the extract")
        return extract_summary(texts)
    used = {int(n) for n in _FOOTNOTE.findall(text)}
    return Summary(text=text, citations=[c for c in citations if c.n in used])
