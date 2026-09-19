"""Daily spending cap for every Claude call (photo check, summary, guide chat).

Cost is computed from the token counts in each response and kept in a small JSON file, so a restart does not
reset it. When the day's budget is used up, callers skip Claude and fall back (OpenCLIP verdicts, Wikipedia
extract, a "limit reached" chat reply). The day follows the server's local date.
"""

import json
import logging
import threading
from datetime import date
from pathlib import Path

from app.config import settings

logger = logging.getLogger("visual_campus.ai_budget")

USAGE_FILE = Path(__file__).resolve().parents[2] / ".ai_usage.json"
# USD per million tokens (input, output), Anthropic list prices.
PRICES = {
    "claude-haiku-4-5": (1.0, 5.0),
    "claude-sonnet-5": (2.0, 10.0),
    "claude-opus-5": (5.0, 25.0),
}
_lock = threading.Lock()


class BudgetExceeded(Exception):
    """Raised instead of calling Claude once today's budget is spent."""


def _load() -> dict:
    today = date.today().isoformat()
    try:
        data = json.loads(USAGE_FILE.read_text())
    except (OSError, ValueError):
        data = {}
    if data.get("date") != today:
        data = {"date": today, "usd": 0.0, "calls": 0, "input_tokens": 0, "output_tokens": 0}
    return data


def usage() -> dict:
    with _lock:
        data = _load()
    budget = settings.ai_daily_budget_usd
    return {**data, "usd": round(data["usd"], 4), "budget_usd": budget,
            "remaining_usd": round(max(0.0, budget - data["usd"]), 4)}


def check() -> None:
    """Call before every Claude request."""
    with _lock:
        spent = _load()["usd"]
    if spent >= settings.ai_daily_budget_usd:
        raise BudgetExceeded(f"daily AI budget ${settings.ai_daily_budget_usd:g} reached (spent ${spent:.2f})")


def record(model: str, input_tokens: int, output_tokens: int) -> float:
    """Add one response's cost; returns it in USD."""
    price_in, price_out = PRICES.get(model, PRICES["claude-opus-5"])  # unknown model: count it as the dearest
    cost = (input_tokens * price_in + output_tokens * price_out) / 1_000_000
    with _lock:
        data = _load()
        data["usd"] += cost
        data["calls"] += 1
        data["input_tokens"] += input_tokens
        data["output_tokens"] += output_tokens
        try:
            USAGE_FILE.write_text(json.dumps(data))
        except OSError:
            logger.warning("Could not write %s", USAGE_FILE)
    return cost
