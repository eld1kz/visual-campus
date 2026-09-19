import dataclasses

import pytest

from app.services import ai_budget


@pytest.fixture
def budget(tmp_path, monkeypatch):
    monkeypatch.setattr(ai_budget, "USAGE_FILE", tmp_path / "usage.json")
    monkeypatch.setattr(ai_budget, "settings", dataclasses.replace(
        ai_budget.settings, ai_user_daily_budget_usd=0.01, ai_daily_budget_usd=0.025))
    return ai_budget


def as_user(name):
    return ai_budget.current_user.set(name)


def test_cost_is_computed_from_tokens_and_charged_to_the_current_user(budget):
    token = as_user("id:alice")
    cost = budget.record("claude-haiku-4-5", 2000, 400)  # 2000 * $1/M + 400 * $5/M
    assert cost == pytest.approx(0.004)
    u = budget.usage()
    assert u["user_usd"] == pytest.approx(0.004) and u["total_usd"] == pytest.approx(0.004) and u["users_today"] == 1
    assert budget.usage("id:bob")["user_usd"] == 0
    budget.current_user.reset(token)


def test_one_user_hitting_the_cap_does_not_block_another(budget):
    token = as_user("id:alice")
    budget.record("claude-opus-5", 2000, 0)  # $0.01: Alice's whole budget
    with pytest.raises(budget.BudgetExceeded) as exc:
        budget.check()
    assert exc.value.scope == "user"
    budget.current_user.reset(token)
    token = as_user("id:bob")
    budget.check()  # Bob still has his own budget
    budget.current_user.reset(token)


def test_the_global_ceiling_stops_everyone(budget):
    for name in ("id:a", "id:b", "id:c"):
        token = as_user(name)
        budget.record("claude-opus-5", 1800, 0)  # $0.009 each, $0.027 in total
        budget.current_user.reset(token)
    token = as_user("id:new")
    with pytest.raises(budget.BudgetExceeded) as exc:
        budget.check()
    assert exc.value.scope == "global"
    budget.current_user.reset(token)


def test_a_new_day_starts_from_zero(budget):
    budget.USAGE_FILE.write_text('{"date": "2000-01-01", "usd": 99, "calls": 5, "input_tokens": 1, '
                                 '"output_tokens": 1, "users": {"ip:x": 99}}')
    budget.check()
    assert budget.usage()["total_usd"] == 0
