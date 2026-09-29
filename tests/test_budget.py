from __future__ import annotations

from datetime import UTC, datetime

import pytest

from lemoria.budget import Budget, format_limit, month_start_ms, parse_limit


def test_parse_human_budget_limits():
    assert parse_limit("500M") == 500_000_000
    assert parse_limit("1.5B") == 1_500_000_000
    assert parse_limit("2_000_000") == 2_000_000
    assert format_limit(500_000_000) == "500M"


@pytest.mark.parametrize("bad", ["0", "-5", "abc", ""])
def test_rejects_non_positive_or_unreadable_limits(bad):
    with pytest.raises(ValueError):
        parse_limit(bad)


def test_budget_state_warns_and_goes_negative_when_over():
    budget = Budget(monthly_tokens=500_000_000)
    assert budget.state(399_999_999)["status"] == "ok"
    assert budget.state(400_000_000)["status"] == "warn"
    assert budget.state(500_000_000)["status"] == "over"
    over = budget.state(600_000_000)
    assert over["remaining"] == -100_000_000
    assert over["percent"] == 120.0


def test_missing_budget_still_reports_usage_without_inventing_a_limit():
    state = Budget().state(123)
    assert state == {
        "funded": None,
        "used": 123,
        "remaining": None,
        "percent": None,
        "status": "unset",
    }
    assert Budget().as_contract(123) is None


def test_month_start_uses_the_local_calendar_month():
    now = datetime(2026, 9, 29, 12, 0, tzinfo=UTC)
    start = datetime.fromtimestamp(month_start_ms(now) / 1000).astimezone()
    assert start.day == 1
    assert start.hour == 0
    assert start.minute == 0
