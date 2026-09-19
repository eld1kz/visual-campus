"""Kampi the guide: answers questions about one built profile, only from what that profile collected."""

import json
import logging

import anthropic

from app.config import settings
from app.models import ChatAction, ChatReply, ChatRequest, Citation, ProfileResponse
from app.services import ai_budget

logger = logging.getLogger("visual_campus.chat")

MODEL = "claude-haiku-4-5"
CATEGORIES = ["campus", "dorms", "classrooms", "libraries", "city"]
SCHEMA = {
    "type": "object",
    "properties": {
        "text": {"type": "string"},
        "found": {"type": "boolean"},
        "sources": {"type": "array", "items": {"type": "integer"}},
        "tab": {"type": "string", "enum": [*CATEGORIES, "none"]},
    },
    "required": ["text", "found", "sources", "tab"],
    "additionalProperties": False,
}
SYSTEM = (
    "You are Kampi, a friendly campus guide inside Visual Campus. Answer the student's question about {name} "
    "in {language}, in 1-3 short sentences, using ONLY the numbered facts below. Never invent facts, prices, "
    "rankings or dates. If the facts do not answer the question, set found=false and say briefly that the "
    "collected sources do not say it. sources: the fact numbers you used. tab: the photo category that best "
    "illustrates the answer (dorms, libraries, classrooms, campus, city) or none.\n\n{facts}"
)
_client: anthropic.AsyncAnthropic | None = None


def facts(profile: ProfileResponse, lang: str) -> tuple[str, list[Citation]]:
    """Numbered facts for the prompt and the citation for each number."""
    u, lines, cites = profile.university, [], []

    def add(text: str, title: str, url: str) -> None:
        cites.append(Citation(n=len(cites) + 1, title=title, url=url))
        lines.append(f"[{len(cites)}] {text}")

    wikidata = f"https://www.wikidata.org/wiki/{u.wikidata_id}"
    add(f"{u.name}; city: {u.city or 'unknown'}; country: {u.country or 'unknown'}; website: {u.website or 'unknown'}",
        f"Wikidata — {u.name}", wikidata)
    if profile.summary.text:
        source = profile.summary.citations[0] if profile.summary.citations else None
        add(profile.summary.text, source.title if source else "Summary", source.url if source else wikidata)
    if u.distance_to_center_km is not None and u.city_center:
        route = u.center_route
        by_road = (f"; by road {route.road_km} km, about {route.drive_min} min by car, about {route.walk_min} min "
                   "on foot (walking time is an estimate)") if route else ""
        add(f"Distance from the campus to the centre of {u.city_center.name}: {u.distance_to_center_km} km in a "
            f"straight line{by_road}. No public transport data.", "OpenStreetMap / OSRM", u.osm_url or wikidata)
    if u.campus_area_km2:
        add(f"Campus area from the OpenStreetMap outline: {u.campus_area_km2} km²", "OpenStreetMap", u.osm_url or wikidata)
    reliable = [p for p in profile.photos if p.tier != "unconfirmed"]
    counts = {c: sum(p.category == c for p in reliable) for c in CATEGORIES}
    recent = sum(p.freshness == "2024_plus" for p in reliable)
    add("Verified or likely photos found per category: " + ", ".join(f"{c} {n}" for c, n in counts.items())
        + f"; {recent} of them taken in 2024 or later. A category with 0 means no reliable photo was found, "
        "not that the place does not exist.", "Visual Campus", wikidata)
    return "\n".join(lines), cites


def not_available(req: ChatRequest, reason: str) -> ChatReply:
    text = {
        "ru": "Сейчас я не могу ответить: лимит ИИ на сегодня исчерпан. Всё собранное можно посмотреть в профиле.",
        "en": "I can't answer right now: today's AI limit is used up. Everything collected is in the profile.",
    }[req.lang] if reason == "budget" else {
        "ru": "Не получилось ответить. Попробуйте ещё раз чуть позже.",
        "en": "I couldn't answer. Please try again a bit later.",
    }[req.lang]
    return ChatReply(text=text, mascot_state="dont_know")


async def answer(req: ChatRequest, profile: ProfileResponse) -> ChatReply:
    global _client
    if not settings.llm_api_key:
        return not_available(req, "error")
    try:
        ai_budget.check()
    except ai_budget.BudgetExceeded:
        return not_available(req, "budget")
    _client = _client or anthropic.AsyncAnthropic(api_key=settings.llm_api_key, max_retries=1)
    fact_text, cites = facts(profile, req.lang)
    system = SYSTEM.format(name=profile.university.name, language="Russian" if req.lang == "ru" else "English",
                           facts=fact_text)
    messages = [{"role": t.role, "content": t.text} for t in req.history[-10:] if t.text.strip()]
    while messages and messages[0]["role"] != "user":
        messages.pop(0)
    messages.append({"role": "user", "content": req.message})
    try:
        response = await _client.messages.create(
            model=MODEL, max_tokens=600, system=system, messages=messages,
            output_config={"format": {"type": "json_schema", "schema": SCHEMA}}, timeout=15,
        )
    except anthropic.APIError as exc:
        logger.warning("Chat failed for %s: %s", req.wikidata_id, exc)
        return not_available(req, "error")
    ai_budget.record(MODEL, response.usage.input_tokens, response.usage.output_tokens)
    if response.stop_reason != "end_turn":
        return not_available(req, "error")
    data = json.loads(next(b.text for b in response.content if b.type == "text"))
    used = [c for c in cites if c.n in set(data["sources"])]
    tab = data["tab"] if data["tab"] in CATEGORIES else None
    if not data["found"]:
        checked = ", ".join(dict.fromkeys(c.title for c in cites))
        return ChatReply(text=data["text"], mascot_state="dont_know", checked=checked)
    return ChatReply(text=data["text"], mascot_state="pointing" if tab else "talking", citations=used,
                     actions=[ChatAction(tab=tab)] if tab else [])
