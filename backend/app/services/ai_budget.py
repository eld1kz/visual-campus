"""Daily Claude spending caps: one per user and a global safety ceiling.

Every Claude call (photo check, summary, guide chat) calls `check()` first and `record()` after. The user is
taken from a context variable that a middleware sets per request (anonymous browser id from the X-Client-Id
header, else the client IP). A profile build runs in a task created inside the request that started it, so the
build is charged to that user; someone who opens the cached profile pays nothing. Costs come from the token
counts of each response and are kept in a small JSON file, so a restart does not reset them.
"""

import json
import logging
import threading
from contextvars import ContextVar
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
current_user: ContextVar[str] = ContextVar("ai_user", default="anonymous")
_lock = threading.Lock()


class BudgetExceeded(Exception):
    """Raised instead of calling Claude once the user's (or the global) budget for today is spent."""

    def __init__(self, message: str, scope: str) -> None:
        super().__init__(message)
        self.scope = scope  # "user" | "global"


def _load() -> dict:
    today = date.today().isoformat()
    try:
        data = json.loads(USAGE_FILE.read_text())
    except (OSError, ValueError):
        data = {}
    if data.get("date") != today:
        data = {"date": today, "usd": 0.0, "calls": 0, "input_tokens": 0, "output_tokens": 0, "users": {}}
    data.setdefault("users", {})
    return data


def usage(user: str | None = None) -> dict:
    user = user or current_user.get()
    with _lock:
        data = _load()
    spent = data["users"].get(user, 0.0)
    return {
        "date": data["date"],
        "user_usd": round(spent, 4),
        "user_budget_usd": settings.ai_user_daily_budget_usd,
        "user_remaining_usd": round(max(0.0, settings.ai_user_daily_budget_usd - spent), 4),
        "total_usd": round(data["usd"], 4),
        "global_budget_usd": settings.ai_daily_budget_usd,
        "users_today": len(data["users"]),
        "calls": data["calls"],
    }


def check() -> None:
    """Call before every Claude request."""
    user = current_user.get()
    with _lock:
        data = _load()
    spent = data["users"].get(user, 0.0)
    if spent >= settings.ai_user_daily_budget_usd:
        raise BudgetExceeded(f"user daily AI budget ${settings.ai_user_daily_budget_usd:g} reached", "user")
    if data["usd"] >= settings.ai_daily_budget_usd:
        raise BudgetExceeded(f"global daily AI budget ${settings.ai_daily_budget_usd:g} reached", "global")


def record(model: str, input_tokens: int, output_tokens: int) -> float:
    """Add one response's cost to the current user and the day total; returns it in USD."""
    price_in, price_out = PRICES.get(model, PRICES["claude-opus-5"])  # unknown model: count it as the dearest
    cost = (input_tokens * price_in + output_tokens * price_out) / 1_000_000
    user = current_user.get()
    with _lock:
        data = _load()
        data["usd"] += cost
        data["users"][user] = data["users"].get(user, 0.0) + cost
        data["calls"] += 1
        data["input_tokens"] += input_tokens
        data["output_tokens"] += output_tokens
        try:
            USAGE_FILE.write_text(json.dumps(data))
        except OSError:
            logger.warning("Could not write %s", USAGE_FILE)
    return cost
