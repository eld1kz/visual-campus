import asyncio
from types import SimpleNamespace

import httpx

from app.models import Citation
from app.services import summary
from app.services.wikipedia import first_sentences

WIKI = summary.SourceText(title="Wikipedia — KAIST", url="https://en.wikipedia.org/wiki/KAIST", text="KAIST is in Daejeon.",
                          is_extract=True)
SITE = summary.SourceText(title="kaist.ac.kr — Campus", url="https://kaist.ac.kr/campus", text="A green campus.")


def build(texts, monkeypatch, key="", reply=None):
    monkeypatch.setattr(summary, "settings", SimpleNamespace(llm_api_key=key))
    if reply is not None:
        async def complete(prompt, client):
            if isinstance(reply, Exception):
                raise reply
            return reply
        monkeypatch.setattr(summary, "complete", complete)
    return asyncio.run(summary.build_summary(texts, "en", httpx.AsyncClient()))


def test_without_key_the_wikipedia_extract_is_used_as_is(monkeypatch):
    s = build([SITE, WIKI], monkeypatch)
    assert s.text == WIKI.text and [c.url for c in s.citations] == [WIKI.url]


def test_no_texts_gives_empty_summary(monkeypatch):
    s = build([], monkeypatch, key="k")
    assert (s.text, s.citations) == ("", [])


def test_llm_answer_with_valid_footnotes_is_kept(monkeypatch):
    s = build([WIKI, SITE], monkeypatch, key="k", reply="KAIST is in Daejeon [1]. The campus is green [2].")
    assert s.text.endswith("[2].") and [c.n for c in s.citations] == [1, 2]


def test_llm_answer_with_unknown_footnote_or_error_falls_back(monkeypatch):
    assert build([WIKI, SITE], monkeypatch, key="k", reply="Big campus [3].").text == WIKI.text
    assert build([WIKI, SITE], monkeypatch, key="k", reply="No footnote here.").text == WIKI.text
    assert build([WIKI, SITE], monkeypatch, key="k", reply=RuntimeError("down")).text == WIKI.text


def test_unconfigured_provider_falls_back(monkeypatch):
    assert build([WIKI], monkeypatch, key="k").text == WIKI.text


def test_is_valid_requires_a_footnote_per_sentence():
    cites = [Citation(n=1, title="a", url="u")]
    assert summary.is_valid("One [1]. Two [1].", cites)
    assert not summary.is_valid("One [1]. Two.", cites)


def test_first_sentences_trims_long_extracts():
    assert first_sentences("One. Two! Three? Four. Five.", limit=3) == "One. Two! Three?"
