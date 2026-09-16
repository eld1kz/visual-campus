"""Wikidata client: wbsearchentities -> wbgetentities, with a Wikipedia spelling fallback."""

import re
from dataclasses import dataclass, field

import httpx

from app.services.hits import SourceHit
from app.services.text import is_cyrillic

WIKIDATA_API = "https://www.wikidata.org/w/api.php"
WIKIPEDIA_API = "https://{lang}.wikipedia.org/w/api.php"
SEARCH_LIMIT = 10

P_COUNTRY, P_LOCATED_IN, P_COORDS = "P17", "P131", "P625"
P_WEBSITE, P_COMMONS_CATEGORY, P_ROR = "P856", "P373", "P6782"

_EDUCATION = re.compile(
    r"universit|college|institut|school|academ|polytechnic|conservator|университет|институт|академ",
    re.IGNORECASE,
)


@dataclass
class WikidataResult:
    hits: list[SourceHit] = field(default_factory=list)
    corrected_query: str | None = None


def _claim_value(entity: dict, prop: str):
    for claim in entity.get("claims", {}).get(prop, []):
        value = claim.get("mainsnak", {}).get("datavalue", {}).get("value")
        if value is not None:
            return value
    return None


def _label(entity: dict, lang: str = "en") -> str | None:
    labels = entity.get("labels", {})
    for code in (lang, "en", "ru"):
        if code in labels:
            return labels[code]["value"]
    return next((v["value"] for v in labels.values()), None)


async def _get(client: httpx.AsyncClient, url: str, params: dict) -> dict:
    resp = await client.get(url, params={**params, "format": "json"})
    resp.raise_for_status()
    return resp.json()


async def _search_ids(client: httpx.AsyncClient, query: str, lang: str) -> list[str]:
    data = await _get(
        client,
        WIKIDATA_API,
        {"action": "wbsearchentities", "search": query, "language": lang, "uselang": lang,
         "type": "item", "limit": SEARCH_LIMIT},
    )
    return [item["id"] for item in data.get("search", [])]


async def _spelling_suggestion(client: httpx.AsyncClient, query: str, lang: str) -> str | None:
    data = await _get(
        client,
        WIKIPEDIA_API.format(lang=lang),
        {"action": "query", "list": "search", "srsearch": query, "srinfo": "suggestion", "srlimit": 1},
    )
    return data.get("query", {}).get("searchinfo", {}).get("suggestion")


async def _entities(client: httpx.AsyncClient, ids: list[str], props: str) -> dict[str, dict]:
    if not ids:
        return {}
    data = await _get(
        client,
        WIKIDATA_API,
        {"action": "wbgetentities", "ids": "|".join(ids), "props": props, "languages": "en|ru"},
    )
    return data.get("entities", {})


def _is_education(entity: dict) -> bool:
    if _claim_value(entity, P_ROR):
        return True
    # Only the English description: Russian ones for cities often mention their universities.
    descriptions = entity.get("descriptions", {})
    description = (descriptions.get("en") or next(iter(descriptions.values()), {})).get("value", "")
    return bool(_EDUCATION.search(description))


async def search_wikidata(client: httpx.AsyncClient, query: str) -> WikidataResult:
    lang = "ru" if is_cyrillic(query) else "en"
    result = WikidataResult()

    ids = await _search_ids(client, query, lang)
    if not ids:
        suggestion = await _spelling_suggestion(client, query, lang)
        if suggestion and suggestion.casefold() != query.casefold():
            result.corrected_query = suggestion
            ids = await _search_ids(client, suggestion, lang)
    if not ids:
        return result

    entities = await _entities(client, ids, "labels|aliases|descriptions|claims|sitelinks")
    found = [entities[i] for i in ids if i in entities and _is_education(entities[i])]

    place_ids = set()
    for entity in found:
        for prop in (P_COUNTRY, P_LOCATED_IN):
            value = _claim_value(entity, prop)
            if isinstance(value, dict) and "id" in value:
                place_ids.add(value["id"])
    places = await _entities(client, sorted(place_ids), "labels")

    for entity in found:
        name = _label(entity, lang)
        if not name:
            continue
        aliases = [a["value"] for code in ("en", "ru") for a in entity.get("aliases", {}).get(code, [])]
        aliases += [v["value"] for v in entity.get("labels", {}).values() if v["value"] != name]
        coords = _claim_value(entity, P_COORDS) or {}
        country = _claim_value(entity, P_COUNTRY) or {}
        city = _claim_value(entity, P_LOCATED_IN) or {}
        ror_id = _claim_value(entity, P_ROR)
        result.hits.append(
            SourceHit(
                source="wikidata",
                name=name,
                aliases=list(dict.fromkeys(aliases)),
                city=_label(places[city["id"]], lang) if city.get("id") in places else None,
                country=_label(places[country["id"]], lang) if country.get("id") in places else None,
                lat=coords.get("latitude"),
                lng=coords.get("longitude"),
                website=_claim_value(entity, P_WEBSITE),
                ror_id=ror_id,
                wikidata_ids=[entity["id"]],
                commons_category=_claim_value(entity, P_COMMONS_CATEGORY),
                sitelinks=len(entity.get("sitelinks", {})),
            )
        )
    return result
