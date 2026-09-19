import dataclasses
import json
from types import SimpleNamespace

import httpx

from app.main import app
from app.models import ChatRequest
from app.services import ai_budget, cache, chat
from tests.api.fakes import QID, fake, get, parse_sse, run  # noqa: F401  (fake is a fixture)


async def post(body: dict) -> httpx.Response:
    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://test") as client:
        return await client.post("/chat", json=body)


def build_profile():
    parse_sse(run(get(f"/profile/{QID}?lang=ru")).text)
    return cache.get_profile(QID, "ru").profile


def test_chat_needs_a_built_profile():
    cache.clear()
    response = run(post({"wikidata_id": QID, "lang": "ru", "message": "Есть ли общежития?"}))
    assert response.status_code == 404


def test_facts_come_only_from_the_profile(fake):
    text, cites = chat.facts(build_profile(), "ru")
    assert "Korea University" in text and "Verified or likely photos found per category" in text
    assert [c.n for c in cites] == list(range(1, len(cites) + 1))


def test_answer_cites_used_facts_and_offers_a_tab(fake, monkeypatch):
    profile = build_profile()
    monkeypatch.setattr(chat, "settings", dataclasses.replace(chat.settings, llm_api_key="k"))
    monkeypatch.setattr(ai_budget, "check", lambda: None)
    monkeypatch.setattr(ai_budget, "record", lambda *a: 0.0)

    class Messages:
        async def create(self, **kwargs):
            assert "Korea University" in kwargs["system"]
            body = {"text": "Фото общежитий есть на вкладке.", "found": True, "sources": [1], "tab": "dorms"}
            return SimpleNamespace(stop_reason="end_turn", usage=SimpleNamespace(input_tokens=10, output_tokens=5),
                                   content=[SimpleNamespace(type="text", text=json.dumps(body))])

    monkeypatch.setattr(chat, "_client", SimpleNamespace(messages=Messages()))
    reply = run(chat.answer(ChatRequest(wikidata_id=QID, message="Общежития?"), profile))
    assert reply.mascot_state == "pointing" and reply.actions[0].tab == "dorms" and [c.n for c in reply.citations] == [1]


def test_budget_reached_gives_an_honest_reply_without_calling_claude(fake, monkeypatch):
    profile = build_profile()
    monkeypatch.setattr(chat, "settings", dataclasses.replace(chat.settings, llm_api_key="k"))

    def exhausted():
        raise ai_budget.BudgetExceeded("spent")

    monkeypatch.setattr(ai_budget, "check", exhausted)
    reply = run(chat.answer(ChatRequest(wikidata_id=QID, message="Общежития?"), profile))
    assert reply.mascot_state == "dont_know" and "лимит" in reply.text
