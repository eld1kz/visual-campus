"""ROR (Research Organization Registry) client, API v2."""

import httpx

from app.services.hits import SourceHit

ROR_URL = "https://api.ror.org/v2/organizations"
MAX_HITS = 10


def _parse(org: dict, chosen: bool = False) -> SourceHit | None:
    if "education" not in org.get("types", []):
        return None
    names = org.get("names", [])
    display = next((n["value"] for n in names if "ror_display" in n.get("types", [])), None)
    if not display:
        return None
    aliases = [n["value"] for n in names if n["value"] != display]
    geo = (org.get("locations") or [{}])[0].get("geonames_details", {})
    website = next((link["value"] for link in org.get("links", []) if link.get("type") == "website"), None)
    wikidata_ids = next(
        (ext.get("all", []) for ext in org.get("external_ids", []) if ext.get("type") == "wikidata"), []
    )
    return SourceHit(
        source="ror",
        name=display,
        aliases=aliases,
        city=geo.get("name"),
        country=geo.get("country_name"),
        lat=geo.get("lat"),
        lng=geo.get("lng"),
        website=website,
        ror_id=org["id"].rsplit("/", 1)[-1],
        wikidata_ids=wikidata_ids,
        chosen=chosen,
    )


async def search_ror(client: httpx.AsyncClient, query: str) -> list[SourceHit]:
    # The affiliation matcher is tuned for messy affiliation strings and returns a score.
    resp = await client.get(ROR_URL, params={"affiliation": query})
    resp.raise_for_status()
    hits = [
        _parse(item["organization"], chosen=bool(item.get("chosen")))
        for item in resp.json().get("items", [])
    ]
    hits = [h for h in hits if h]
    if hits:
        return hits[:MAX_HITS]

    # Acronyms ("KAIST") and single words ("Cambridge") often get nothing from the
    # affiliation matcher, but the plain search endpoint finds them.
    resp = await client.get(ROR_URL, params={"query": query, "filter": "types:education"})
    resp.raise_for_status()
    hits = [_parse(org) for org in resp.json().get("items", [])]
    return [h for h in hits if h][:MAX_HITS]
