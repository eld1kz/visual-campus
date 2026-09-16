"""Wikidata client: wbsearchentities -> wbgetentities, with a Wikipedia spelling fallback."""

import asyncio
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


async def _entities(
    client: httpx.AsyncClient, ids: list[str], props: str, languages: str | None = "en|ru"
) -> dict[str, dict]:
    if not ids:
        return {}
    params = {"action": "wbgetentities", "ids": "|".join(ids), "props": props}
    if languages:
        params["languages"] = languages
    data = await _get(client, WIKIDATA_API, params)
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


# ---------- Profile: one university by QID ----------

P_INSTANCE_OF, P_HEADQUARTERS, P_LOCATION = "P31", "P159", "P276"
MAX_ADMIN_LEVELS = 3

# "City"-like classes used to find the city centre by walking up P131 (located in).
CITY_CLASSES = {
    "Q515",  # city
    "Q1549591",  # big city
    "Q5119",  # capital
    "Q200250",  # metropolis
    "Q1637706",  # city with millions of inhabitants
    "Q3181348",  # university town
    "Q7930989",  # city/town
    "Q3957",  # town
}


@dataclass
class Place:
    name: str
    lat: float
    lng: float


@dataclass
class UniversityRecord:
    wikidata_id: str
    name: str
    name_en: str
    names: list[str]
    lat: float | None
    lng: float | None
    website: str | None
    commons_category: str | None
    ror_id: str | None
    city: str | None
    country: str | None
    wikipedia_titles: dict[str, str]
    city_center: Place | None


def _item_ids(entity: dict, prop: str) -> list[str]:
    ids = []
    for claim in entity.get("claims", {}).get(prop, []):
        value = claim.get("mainsnak", {}).get("datavalue", {}).get("value")
        if isinstance(value, dict) and "id" in value:
            ids.append(value["id"])
    return ids


async def _find_city_center(client: httpx.AsyncClient, entity: dict, lang: str) -> Place | None:
    """Headquarters/location first (usually the city itself), then walk up P131 (located in).

    Stops before the country: country entities are huge and never a city centre."""
    countries = set(_item_ids(entity, P_COUNTRY))
    next_ids = (_item_ids(entity, P_HEADQUARTERS) + _item_ids(entity, P_LOCATION) + _item_ids(entity, P_LOCATED_IN))[:1]
    for _ in range(MAX_ADMIN_LEVELS):
        if not next_ids or next_ids[0] in countries:
            return None
        parent = (await _entities(client, next_ids, "labels|claims")).get(next_ids[0])
        if not parent:
            return None
        coords = _claim_value(parent, P_COORDS)
        if set(_item_ids(parent, P_INSTANCE_OF)) & CITY_CLASSES and coords:
            return Place(name=_label(parent, lang) or next_ids[0], lat=coords["latitude"], lng=coords["longitude"])
        next_ids = _item_ids(parent, P_LOCATED_IN)[:1]
    return None


async def get_university(client: httpx.AsyncClient, qid: str, lang: str = "en") -> UniversityRecord | None:
    data = await _get(
        client,
        WIKIDATA_API,
        # sitefilter: big universities have 200+ sitelinks; only these three are used.
        {"action": "wbgetentities", "ids": qid, "props": "labels|aliases|claims|sitelinks", "sitefilter": "enwiki|ruwiki|kowiki"},
    )
    entity = data.get("entities", {}).get(qid)
    if not entity or "missing" in entity:
        return None

    name = _label(entity, lang) or qid
    names = [v["value"] for v in entity.get("labels", {}).values()]
    names += [a["value"] for aliases in entity.get("aliases", {}).values() for a in aliases]

    city_ids, country_ids = _item_ids(entity, P_LOCATED_IN), _item_ids(entity, P_COUNTRY)
    places, city_center = await asyncio.gather(
        _entities(client, city_ids[:1] + country_ids[:1], "labels"),
        _find_city_center(client, entity, lang),
    )
    coords = _claim_value(entity, P_COORDS) or {}
    sitelinks = entity.get("sitelinks", {})

    return UniversityRecord(
        wikidata_id=qid,
        name=name,
        name_en=_label(entity, "en") or name,
        names=list(dict.fromkeys(n for n in names if n)),
        lat=coords.get("latitude"),
        lng=coords.get("longitude"),
        website=_claim_value(entity, P_WEBSITE),
        commons_category=_claim_value(entity, P_COMMONS_CATEGORY),
        ror_id=_claim_value(entity, P_ROR),
        city=_label(places[city_ids[0]], lang) if city_ids and city_ids[0] in places else None,
        country=_label(places[country_ids[0]], lang) if country_ids and country_ids[0] in places else None,
        wikipedia_titles={
            code.removesuffix("wiki"): link["title"]
            for code, link in sitelinks.items()
            if code in ("enwiki", "ruwiki", "kowiki")
        },
        city_center=city_center,
    )
