import pandas as pd
import pytest
from pyfpa.analysis.divestiture import Carveout, divest, net_debt_to_ebitda


def _base_forecast():
    idx = pd.period_range("2026-01", periods=12, freq="M")
    return pd.DataFrame({
        "revenue": [100.0] * 12,
        "gross_profit": [40.0] * 12,
        "opex": [10.0] * 12,
        "ebitda": [30.0] * 12,
        "da": [5.0] * 12,
        "interest": [4.0] * 12,
        "pretax_income": [26.0] * 12,
        "tax": [0.0] * 12,
        "net_income": [26.0] * 12,
        "wc_cash_impact": [0.0] * 12,
        "operating_cash_flow": [31.0] * 12,
        "capex": [3.0] * 12,
        "principal": [0.0] * 12,
        "free_cash_flow": [28.0] * 12,
        "change_in_cash": [28.0] * 12,
        "ending_cash": list(range(28, 28 * 13, 28)),
    }, index=idx)


def _carveout():
    return Carveout(revenue=20.0, gross_profit=8.0, opex=2.0, da=1.0, capex=0.5)


def test_divest_removes_contribution_after_sale_month():
    base = _base_forecast()
    out = divest(base, _carveout(), sale_month=6, proceeds=0.0, annual_rate=0.0, tax_rate=0.0)
    assert out.iloc[0]["revenue"] == 100.0
    assert out.iloc[6]["revenue"] == 80.0
    assert out.iloc[6]["ebitda"] == 24.0
    assert out.iloc[6]["da"] == 4.0
    assert out.iloc[6]["capex"] == 2.5
    assert base.iloc[6]["revenue"] == 100.0  # input not mutated


def test_divest_proceeds_cut_interest():
    base = _base_forecast()
    out = divest(base, _carveout(), sale_month=6, proceeds=1200.0, annual_rate=0.10, tax_rate=0.0)
    assert out.iloc[5]["interest"] == 4.0
    assert out.iloc[6]["interest"] == pytest.approx(4.0 - 10.0)


def test_net_debt_to_ebitda():
    base = _base_forecast()
    lev = net_debt_to_ebitda(base, debt_balance=360.0, cash=0.0)
    assert lev == pytest.approx(360.0 / (30.0 * 12))
