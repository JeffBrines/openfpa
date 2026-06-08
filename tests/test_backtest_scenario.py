from pyfpa.backtest.score import score_forecast
from pyfpa.backtest.learn import persistent_miss


def test_persistent_cash_overstatement_is_flagged():
    # Across three closes the model predicts ending cash above actual every time
    # (a real collections lag the model doesn't capture) -> structural trigger.
    closes = [
        ({"ending_cash": 100.0}, {"ending_cash": 90.0}),
        ({"ending_cash": 120.0}, {"ending_cash": 108.0}),
        ({"ending_cash": 140.0}, {"ending_cash": 126.0}),
    ]
    cash_errors = [score_forecast(p, a).per_line["ending_cash"] for p, a in closes]
    assert all(e > 0 for e in cash_errors)            # always overstated
    assert persistent_miss(cash_errors, k=3, threshold=0.05) is True
