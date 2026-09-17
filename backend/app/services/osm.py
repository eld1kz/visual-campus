"""Legacy shim: moved to app.services.sources.osm. Kept while profile.py/evidence.py/tests import it."""

import httpx

from app.services.sources.base import SOURCE_BUDGET_S, Deadline
from app.services.sources.osm import KM_PER_DEGREE, Campus, distance_m, locate_campus, pick_campus  # noqa: F401


async def find_campus(
    client: httpx.AsyncClient, qid: str, name: str, names: list[str], lat: float, lng: float
) -> Campus | None:
    """Old signature used by services/profile.py; the new collector is sources.osm.find_campus(query, client)."""
    campus, _ = await locate_campus(client, qid, [name, *names], lat, lng, Deadline(SOURCE_BUDGET_S))
    return campus
