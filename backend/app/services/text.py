"""Name normalisation and fuzzy similarity for university names."""

import re
import unicodedata
from difflib import SequenceMatcher

_STOP_WORDS = {"the", "of", "and", "at", "de", "der", "für", "fur"}
_CYRILLIC = re.compile(r"[Ѐ-ӿ]")


def is_cyrillic(text: str) -> bool:
    return bool(_CYRILLIC.search(text))


def normalize(text: str) -> str:
    text = unicodedata.normalize("NFKC", text).casefold()
    text = re.sub(r"[^\w\s]", " ", text)
    return re.sub(r"\s+", " ", text).strip()


def _tokens(text: str) -> list[str]:
    return [t for t in normalize(text).split() if t not in _STOP_WORDS]


def _ratio(a: str, b: str) -> float:
    return SequenceMatcher(None, a, b).ratio()


def similarity(query: str, name: str) -> float:
    """0..1: 1.0 for an exact (normalised) match, ~0.9 for small typos,
    0.6-0.9 when every query word appears in a longer name."""
    q, n = normalize(query), normalize(name)
    if not q or not n:
        return 0.0
    if q == n:
        return 1.0
    score = _ratio(q, n)

    q_tokens, n_tokens = _tokens(query), _tokens(name)
    if q_tokens and n_tokens:
        matched = sum(1 for qt in q_tokens if any(_ratio(qt, nt) >= 0.8 for nt in n_tokens))
        if matched == len(q_tokens):
            coverage = len(q_tokens) / len(n_tokens)
            # Never reach the "exact" band just by containment: "Cambridge" must stay ambiguous.
            score = max(score, 0.6 + 0.28 * min(coverage, 1.0))
    return round(score, 4)


def best_similarity(query: str, names: list[str]) -> float:
    return max((similarity(query, n) for n in names if n), default=0.0)
