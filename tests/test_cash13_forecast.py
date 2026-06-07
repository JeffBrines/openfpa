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


# --- append to tests/test_cash13_forecast.py ---
from pyfpa.cash13.schemas import WeeklyFlow as WF  # noqa: E402
from pyfpa.cash13.forecast import cash13_forecast  # noqa: E402


def test_forecast_weekly_trajectory():
    cfg = Cash13Config(
        opening_cash=100.0,
        weeks=4,
        receipts=[WF(name="Sales", amount=50.0, start_week=1, recurrence="weekly")],
        disbursements=[
            WF(name="Opex", amount=40.0, start_week=1, recurrence="weekly"),
            WF(name="Rent", amount=200.0, start_week=3, recurrence="once"),
        ],
    )
    df = cash13_forecast(cfg)
    assert list(df.columns) == ["receipts", "disbursements", "net_cash", "ending_cash"]
    assert df.index.tolist() == [1, 2, 3, 4]
    # receipts 50 each week; disb 40,40,240,40
    assert df["receipts"].tolist() == [50.0, 50.0, 50.0, 50.0]
    assert df["disbursements"].tolist() == [40.0, 40.0, 240.0, 40.0]
    # net 10,10,-190,10 ; ending 110,120,-70,-60
    assert df["net_cash"].tolist() == [10.0, 10.0, -190.0, 10.0]
    assert df["ending_cash"].tolist() == [110.0, 120.0, -70.0, -60.0]


def test_forecast_empty_flows_holds_opening_cash():
    cfg = Cash13Config(opening_cash=500.0, weeks=3)
    df = cash13_forecast(cfg)
    assert df["ending_cash"].tolist() == [500.0, 500.0, 500.0]
    assert df["receipts"].sum() == 0.0
