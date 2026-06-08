import pytest
from pyfpa.config.schemas import EntityConfig
from pyfpa.backtest.holdout import holdout_backtest


def _actuals():
    out = {}
    cash = 0.0
    for i in range(6):
        cash += 20.0
        out[f"2026-{i+1:02d}"] = {"revenue": 100.0, "gross_profit": 40.0,
                                  "ebitda": 30.0, "ending_cash": cash}
    return out


def _build_cfg(growth):
    def _fn(fit_actuals):
        n = len(fit_actuals)
        last_rev = list(fit_actuals.values())[-1]["revenue"]
        annual = last_rev * 12 * (1 + growth)
        return EntityConfig.model_validate({
            "name": "h", "start_month": f"2026-{n+1:02d}", "horizon_months": 3,
            "tax_rate": 0.0,
            "channels": [{"name": "C", "annual_revenue": annual, "growth_rate": 0.0,
                          "seasonality": [1.0] * 12, "cogs_pct": 0.6}],
            "opex": [], "debt": [],
            "working_capital": {"dso_days": 0, "dpo_days": 0, "dio_days": 0},
            "opening_balances": {"cash": 80.0},
        })
    return _fn


def test_holdout_backtest_scores_holdout():
    res = holdout_backtest(_actuals(), _build_cfg(0.0), holdout=3,
                           score_lines=["revenue", "ebitda"])
    assert "revenue" in res.per_line
    assert res.fitness >= 0.0


def test_holdout_discriminates_better_assumption():
    good = holdout_backtest(_actuals(), _build_cfg(0.0), holdout=3, score_lines=["revenue"])
    bad = holdout_backtest(_actuals(), _build_cfg(0.5), holdout=3, score_lines=["revenue"])
    assert good.fitness < bad.fitness


def test_holdout_rejects_too_few_periods():
    with pytest.raises(ValueError):
        holdout_backtest({"2026-01": {"revenue": 1.0}}, _build_cfg(0.0), holdout=3,
                         score_lines=["revenue"])
