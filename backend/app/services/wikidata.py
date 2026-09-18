"""Wikidata client: wbsearchentities -> wbgetentities, with a Wikipedia spelling fallback."""

import asyncio
import re
import time
from dataclasses import dataclass, field

import httpx

from app.services.hits import SourceHit
from app.services.sources.base import source_slot
from app.services.text import is_cyrillic

WIKIDATA_API = "https://www.wikidata.org/w/api.php"
WIKIDATA_SPARQL = "https://query.wikidata.org/sparql"
WIKIPEDIA_API = "https://{lang}.wikipedia.org/w/api.php"
SEARCH_LIMIT = 10
ENTITY_TTL_S = 24 * 3600
_ENTITY_CACHE: dict[str, tuple[float, dict]] = {}

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
    for attempt in range(3):
        try:
            async with source_slot("wikidata", 3):
                resp = await client.get(url, params={**params, "format": "json"})
            if resp.status_code != 429 and resp.status_code < 500:
                resp.raise_for_status()
                return resp.json()
        except httpx.TransportError:
            if attempt == 2:
                raise
        if attempt < 2:
            await asyncio.sleep(0.2 * (2 ** attempt))
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
    use_cache = not isinstance(client._transport, httpx.MockTransport)
    required = set(props.split("|"))
    cached: dict[str, dict] = {}
    if use_cache:
        for qid in ids:
            item = _ENTITY_CACHE.get(qid)
            if item and time.monotonic() - item[0] < ENTITY_TTL_S and required.issubset(item[1].keys()):
                cached[qid] = item[1]
    missing = [qid for qid in ids if qid not in cached]
    if not missing:
        return cached
    params = {"action": "wbgetentities", "ids": "|".join(missing), "props": props}
    if languages:
        params["languages"] = languages
    data = await _get(client, WIKIDATA_API, params)
    fetched = data.get("entities", {})
    if use_cache:
        for qid, entity in fetched.items():
            previous = _ENTITY_CACHE.get(qid, (0, {}))[1]
            merged = {**previous, **entity}
            _ENTITY_CACHE[qid] = (time.monotonic(), merged)
            fetched[qid] = merged
    return {**cached, **fetched}


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
    names_by_language: dict[str, str] = field(default_factory=dict)
    entity: dict = field(default_factory=dict, repr=False)


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


async def get_university(
    client: httpx.AsyncClient, qid: str, lang: str = "en", with_places: bool = True
) -> UniversityRecord | None:
    """with_places=False skips city/country labels and the city centre walk (~1.3 s); fill them later with add_places()."""
    entity = (await _entities(client, [qid], "labels|aliases|claims|sitelinks", languages=None)).get(qid)
    if not entity or "missing" in entity:
        return None

    name = _label(entity, lang) or qid
    names = [v["value"] for v in entity.get("labels", {}).values()]
    names += [a["value"] for aliases in entity.get("aliases", {}).values() for a in aliases]

    coords = _claim_value(entity, P_COORDS) or {}
    sitelinks = entity.get("sitelinks", {})

    record = UniversityRecord(
        wikidata_id=qid,
        name=name,
        name_en=_label(entity, "en") or name,
        names=list(dict.fromkeys(n for n in names if n)),
        lat=coords.get("latitude"),
        lng=coords.get("longitude"),
        website=_claim_value(entity, P_WEBSITE),
        commons_category=_claim_value(entity, P_COMMONS_CATEGORY),
        ror_id=_claim_value(entity, P_ROR),
        city=None,
        country=None,
        wikipedia_titles={
            code.removesuffix("wiki"): link["title"]
            for code, link in sitelinks.items()
            if code in ("enwiki", "ruwiki", "kowiki")
        },
        city_center=None,
        names_by_language={code: value["value"] for code, value in entity.get("labels", {}).items()},
        entity=entity,
    )
    if with_places:
        await add_places(client, record, lang)
    return record


async def add_places(client: httpx.AsyncClient, uni: UniversityRecord, lang: str) -> None:
    """Fills city, country and city_center in place."""
    city_ids, country_ids = _item_ids(uni.entity, P_LOCATED_IN), _item_ids(uni.entity, P_COUNTRY)
    places, city_center = await asyncio.gather(
        _entities(client, city_ids[:1] + country_ids[:1], "labels"),
        _find_city_center(client, uni.entity, lang),
    )
    uni.city = _label(places[city_ids[0]], lang) if city_ids and city_ids[0] in places else None
    uni.country = _label(places[country_ids[0]], lang) if country_ids and country_ids[0] in places else None
    uni.city_center = city_center


_COORD = re.compile(r"Point\((-?[\d.]+) (-?[\d.]+)\)")
_BUILDING_TYPES = {
    "Q41176": "academic",      # building
    "Q3914": "academic",       # school
    "Q11303": "academic",      # skyscraper (often named campus buildings)
    "Q847950": "dorm",         # dormitory
    "Q7075": "library",
    "Q483110": "sport",        # stadium
    "Q31855": "lab",           # research institute
}


async def discover_campus_subjects(
    client: httpx.AsyncClient,
    uni: UniversityRecord,
    bbox: tuple[float, float, float, float] | None = None,
) -> list[dict]:
    """Direct P361 members plus coordinate-bearing nearby items; bbox filtering is repeated locally."""
    if bbox is None or uni.lat is None or uni.lng is None:
        around = ""
    else:
        around = f'''UNION {{ SERVICE wikibase:around {{
          ?item wdt:P625 ?coord .
          bd:serviceParam wikibase:center "Point({uni.lng} {uni.lat})"^^geo:wktLiteral ; wikibase:radius "3" .
        }} }}'''
    query = f'''SELECT DISTINCT ?item ?itemLabel ?coord ?image ?commons ?instance ?direct WHERE {{
      {{ ?item wdt:P361 wd:{uni.wikidata_id} . BIND(true AS ?direct) }} {around}
      OPTIONAL {{ ?item wdt:P625 ?coord }}
      OPTIONAL {{ ?item wdt:P18 ?image }}
      OPTIONAL {{ ?item wdt:P373 ?commons }}
      OPTIONAL {{ ?item wdt:P31 ?instance }}
      FILTER(BOUND(?image) || BOUND(?commons))
      SERVICE wikibase:label {{ bd:serviceParam wikibase:language "en,ko,ru,kk". }}
    }} LIMIT 120'''
    async with source_slot("wikidata", 3):
        response = await client.get(WIKIDATA_SPARQL, params={"query": query, "format": "json"}, timeout=3.0)
    response.raise_for_status()
    grouped: dict[str, dict] = {}
    for row in response.json().get("results", {}).get("bindings", []):
        item_url = row.get("item", {}).get("value", "")
        qid = item_url.rsplit("/", 1)[-1]
        if not qid.startswith("Q"):
            continue
        lat = lng = None
        if match := _COORD.search(row.get("coord", {}).get("value", "")):
            lng, lat = float(match.group(1)), float(match.group(2))
        direct = row.get("direct", {}).get("value") == "true"
        inside = False
        if bbox and lat is not None and lng is not None:
            west, south, east, north = bbox
            inside = west <= lng <= east and south <= lat <= north
        if not direct and not inside:
            continue
        subject = grouped.setdefault(qid, {
            "qid": qid, "kind": "building", "names": [], "commons_category": None,
            "image_titles": [], "lat": lat, "lng": lng, "building_type": "other",
        })
        label = row.get("itemLabel", {}).get("value")
        if label and label not in subject["names"]:
            subject["names"].append(label)
        if commons := row.get("commons", {}).get("value"):
            subject["commons_category"] = commons
        if image := row.get("image", {}).get("value"):
            title = image.rsplit("/", 1)[-1].replace("_", " ")
            if title not in subject["image_titles"]:
                subject["image_titles"].append(title)
        instance = row.get("instance", {}).get("value", "").rsplit("/", 1)[-1]
        if instance in _BUILDING_TYPES:
            subject["building_type"] = _BUILDING_TYPES[instance]
    return list(grouped.values())[:20]
