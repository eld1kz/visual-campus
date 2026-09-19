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


def test_initials_do_not_end_a_sentence():
    from app.services.text import split_sentences
    from app.services.wikipedia import first_sentences

    text = "Назарбаев Университет — вуз, открытый по инициативе Н. А. Назарбаева. Находится в г. Астана. Кампус большой."
    assert split_sentences(text)[0].endswith("Н. А. Назарбаева.")
    assert not first_sentences(text, 1).endswith(" Н.")


def test_footnote_validation_accepts_initials_and_footnotes_after_the_full_stop():
    from app.models import Citation
    from app.services.summary import is_valid

    cites = [Citation(n=1, title="W", url="https://w")]
    assert is_valid("Вуз открыт по инициативе Н. А. Назарбаева [1]. Кампус большой. [1]", cites)
    assert not is_valid("Вуз открыт [1]. Кампус большой.", cites)
