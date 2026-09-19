import dataclasses

import pytest

from app.services import ai_budget


@pytest.fixture
def budget(tmp_path, monkeypatch):
    monkeypatch.setattr(ai_budget, "USAGE_FILE", tmp_path / "usage.json")
    monkeypatch.setattr(ai_budget, "settings", dataclasses.replace(ai_budget.settings, ai_daily_budget_usd=0.01))
    return ai_budget


def test_cost_is_computed_from_tokens_and_persisted(budget):
    cost = budget.record("claude-haiku-4-5", 2000, 400)  # 2000 * $1/M + 400 * $5/M
    assert cost == pytest.approx(0.004)
    assert budget.usage()["usd"] == pytest.approx(0.004) and budget.usage()["calls"] == 1
    assert budget.USAGE_FILE.exists()


def test_calls_stop_once_the_daily_budget_is_spent(budget):
    budget.check()  # nothing spent yet
    budget.record("claude-opus-5", 2000, 0)  # $0.01
    with pytest.raises(budget.BudgetExceeded):
        budget.check()
    assert budget.usage()["remaining_usd"] == 0


def test_a_new_day_starts_from_zero(budget):
    budget.USAGE_FILE.write_text('{"date": "2000-01-01", "usd": 99, "calls": 5, "input_tokens": 1, "output_tokens": 1}')
    budget.check()
    assert budget.usage()["usd"] == 0
