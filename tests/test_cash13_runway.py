from pyfpa.cash13.schemas import Cash13Config, WeeklyFlow
from pyfpa.cash13.forecast import cash13_forecast
from pyfpa.cash13.runway import runway_summary


def test_runway_identifies_trough_and_first_negative():
    cfg = Cash13Config(
        opening_cash=100.0,
        weeks=4,
        receipts=[WeeklyFlow(name="Sales", amount=50.0, start_week=1, recurrence="weekly")],
        disbursements=[
            WeeklyFlow(name="Opex", amount=40.0, start_week=1, recurrence="weekly"),
            WeeklyFlow(name="Rent", amount=200.0, start_week=3, recurrence="once"),
        ],
    )
    summary = runway_summary(cash13_forecast(cfg))
    # ending cash: 110,120,-70,-60 -> trough -70 at week 3; first negative week 3
    assert summary["min_cash"] == -70.0
    assert summary["min_week"] == 3
    assert summary["first_negative_week"] == 3


def test_runway_none_when_always_positive():
    cfg = Cash13Config(
        opening_cash=1000.0,
        weeks=3,
        receipts=[WeeklyFlow(name="Sales", amount=10.0, start_week=1, recurrence="weekly")],
    )
    summary = runway_summary(cash13_forecast(cfg))
    assert summary["first_negative_week"] is None
    assert summary["min_cash"] == 1010.0
    assert summary["min_week"] == 1
