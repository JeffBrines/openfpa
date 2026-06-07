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
    # Dips at week 2 but never goes negative, so min_week is a real trough (not week 1).
    cfg = Cash13Config(
        opening_cash=1000.0,
        weeks=3,
        receipts=[WeeklyFlow(name="Sales", amount=10.0, start_week=1, recurrence="weekly")],
        disbursements=[WeeklyFlow(name="OneOff", amount=30.0, start_week=2, recurrence="once")],
    )
    summary = runway_summary(cash13_forecast(cfg))
    # ending cash: 1010, 990, 1000 -> trough 990 at week 2; never negative
    assert summary["first_negative_week"] is None
    assert summary["min_cash"] == 990.0
    assert summary["min_week"] == 2
