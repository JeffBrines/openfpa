import pandas as pd
import pytest
from pyfpa.backtest.score import extract_lines, aggregate_periods, DEFAULT_SCORE_LINES


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
    assert out["ending_cash"] == 90.0
    assert out["gross_margin"] == pytest.approx(0.4)
