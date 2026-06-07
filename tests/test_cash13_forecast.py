import pytest
from pydantic import ValidationError
from pyfpa.cash13.schemas import WeeklyFlow, Cash13Config


def test_weeklyflow_defaults():
    f = WeeklyFlow(name="Payroll", amount=1000.0, start_week=1)
    assert f.recurrence == "once"
    assert f.end_week is None


def test_weeklyflow_rejects_end_before_start():
    with pytest.raises(ValidationError):
        WeeklyFlow(name="x", amount=1.0, start_week=5, recurrence="weekly", end_week=3)


def test_cash13config_defaults():
    cfg = Cash13Config(opening_cash=500.0)
    assert cfg.weeks == 13
    assert cfg.receipts == []
    assert cfg.disbursements == []


def test_weeklyflow_amount_nonnegative():
    with pytest.raises(ValidationError):
        WeeklyFlow(name="x", amount=-5.0, start_week=1)
