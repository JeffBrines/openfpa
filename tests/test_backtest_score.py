import pandas as pd
import pytest
from pyfpa.backtest.score import extract_lines, aggregate_periods, DEFAULT_SCORE_LINES
from pyfpa.backtest.score import ScoreResult, score_forecast, DEFAULT_WEIGHTS


def _forecast():
    idx = pd.period_range("2026-01", periods=3, freq="M")
    return pd.DataFrame({
        "revenue": [100.0, 100.0, 100.0],
        "gross_profit": [40.0, 40.0, 40.0],
        "ebitda": [30.0, 30.0, 30.0],
        "ending_cash": [50.0, 70.0, 90.0],
    }, index=idx)


def test_extract_lines_flow_stock_ratio():
    out = extract_lines(_forecast(), DEFAULT_SCORE_LINES)
    assert out["revenue"] == 300.0
    assert out["ebitda"] == 90.0
    assert out["ending_cash"] == 90.0
    assert out["gross_margin"] == pytest.approx(120.0 / 300.0)


def test_aggregate_periods_matches_extract():
    periods = [
        {"revenue": 100.0, "gross_profit": 40.0, "ebitda": 30.0, "ending_cash": 50.0},
        {"revenue": 100.0, "gross_profit": 40.0, "ebitda": 30.0, "ending_cash": 70.0},
        {"revenue": 100.0, "gross_profit": 40.0, "ebitda": 30.0, "ending_cash": 90.0},
    ]
    out = aggregate_periods(periods, DEFAULT_SCORE_LINES)
    assert out["revenue"] == 300.0
    assert out["ebitda"] == 90.0
    assert out["ending_cash"] == 90.0
    assert out["gross_margin"] == pytest.approx(0.4)


def test_aggregate_periods_empty_is_zero_filled():
    out = aggregate_periods([], DEFAULT_SCORE_LINES)
    assert out == {line: 0.0 for line in DEFAULT_SCORE_LINES}


def test_score_forecast_weighted_mape():
    predicted = {"ending_cash": 110.0, "ebitda": 90.0, "revenue": 300.0, "gross_margin": 0.40}
    actual = {"ending_cash": 100.0, "ebitda": 100.0, "revenue": 300.0, "gross_margin": 0.40}
    res = score_forecast(predicted, actual)
    assert res.per_line["ending_cash"] == pytest.approx(0.10)
    assert res.per_line["ebitda"] == pytest.approx(-0.10)
    assert res.per_line["revenue"] == pytest.approx(0.0)
    assert res.fitness == pytest.approx(0.07)


def test_score_forecast_skips_absent_and_zero_actual_lines():
    res = score_forecast(
        {"ending_cash": 90.0, "ebitda": 30.0},
        {"ending_cash": 100.0, "ebitda": 0.0},
    )
    assert set(res.per_line) == {"ending_cash"}
    assert res.weights == {"ending_cash": pytest.approx(1.0)}  # renormalized to the one line
    assert res.fitness == pytest.approx(0.10)
