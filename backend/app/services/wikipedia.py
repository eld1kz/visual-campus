"""Short campus description from the Wikipedia article summary (REST API)."""

import re
from dataclasses import dataclass
from urllib.parse import quote

import httpx

SUMMARY_URL = "https://{lang}.wikipedia.org/api/rest_v1/page/summary/{title}"
MAX_SENTENCES = 4
_SENTENCE_END = re.compile(r"(?<=[.!?])\s+")


@dataclass
class WikiSummary:
    text: str
    url: str
    title: str
    lang: str


def first_sentences(text: str, limit: int = MAX_SENTENCES) -> str:
    return " ".join(_SENTENCE_END.split(text.strip())[:limit])


async def summary(client: httpx.AsyncClient, titles: dict[str, str], lang: str) -> WikiSummary | None:
    """`titles` maps a language code to the article title (from Wikidata sitelinks)."""
    order = [lang, "en", *titles.keys()]
    for code in dict.fromkeys(c for c in order if c in titles):
        resp = await client.get(SUMMARY_URL.format(lang=code, title=quote(titles[code].replace(" ", "_"), safe="")))
        if resp.status_code == 404:
            continue
        resp.raise_for_status()
        data = resp.json()
        extract = data.get("extract", "").strip()
        if extract:
            url = data.get("content_urls", {}).get("desktop", {}).get("page") or f"https://{code}.wikipedia.org/wiki/{quote(titles[code])}"
            return WikiSummary(text=first_sentences(extract), url=url, title=data.get("title", titles[code]), lang=code)
    return None
