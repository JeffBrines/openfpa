import pandas as pd
import pytest
from pyfpa.analysis.divestiture import Carveout, divest, net_debt_to_ebitda


def _base_forecast():
    # 12 flat months. Internally consistent with the engine: EBIT = EBITDA - D&A,
    # pretax = EBIT - interest, OCF = net_income + D&A + wc, FCF = OCF - capex.
    # ebitda 30, da 5 => EBIT 25; interest 4 => pretax 21; tax 0 => net 21;
    # OCF = 21 + 5 = 26; FCF = 26 - 3 = 23.
    idx = pd.period_range("2026-01", periods=12, freq="M")
    return pd.DataFrame({
        "revenue": [100.0] * 12,
        "gross_profit": [40.0] * 12,
        "opex": [10.0] * 12,
        "ebitda": [30.0] * 12,
        "da": [5.0] * 12,
        "interest": [4.0] * 12,
        "pretax_income": [21.0] * 12,
        "tax": [0.0] * 12,
        "net_income": [21.0] * 12,
        "wc_cash_impact": [0.0] * 12,
        "operating_cash_flow": [26.0] * 12,
        "capex": [3.0] * 12,
        "principal": [0.0] * 12,
        "free_cash_flow": [23.0] * 12,
        "change_in_cash": [23.0] * 12,
        "ending_cash": [23.0 * (i + 1) for i in range(12)],
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


def test_divest_retains_sale_month_then_divests():
    # sale_month=6 => months 1..6 (index 0..5) retained, divested from index 6.
    base = _base_forecast()
    out = divest(base, _carveout(), sale_month=6, proceeds=0.0, annual_rate=0.0, tax_rate=0.0)
    assert out.iloc[5]["revenue"] == 100.0   # month 6 still full
    assert out.iloc[6]["revenue"] == 80.0    # month 7 divested


def test_divest_proceeds_cut_interest():
    base = _base_forecast()
    out = divest(base, _carveout(), sale_month=6, proceeds=1200.0, annual_rate=0.10, tax_rate=0.0)
    assert out.iloc[5]["interest"] == 4.0
    assert out.iloc[6]["interest"] == pytest.approx(4.0 - 10.0)


def test_divest_cascades_cash_lines_with_tax():
    base = _base_forecast()
    out = divest(base, _carveout(), sale_month=6, proceeds=0.0, annual_rate=0.0, tax_rate=0.25)
    row = out.iloc[6]
    # post-sale: gross 32, opex 8 => ebitda 24; da 4 => EBIT 20; interest 4 => pretax 16
    assert row["ebitda"] == 24.0
    assert row["da"] == 4.0
    assert row["pretax_income"] == 16.0
    assert row["tax"] == pytest.approx(4.0)         # 16 * 0.25
    assert row["net_income"] == pytest.approx(12.0)
    # OCF = net 12 + da 4 + wc 0 = 16; FCF = 16 - capex 2.5 = 13.5
    assert row["operating_cash_flow"] == pytest.approx(16.0)
    assert row["free_cash_flow"] == pytest.approx(13.5)
    assert row["change_in_cash"] == pytest.approx(13.5)
    # ending_cash rebuilt from cumulative change_in_cash (opening 0):
    # months 1-6 add 23 each => 138 at index 5; index 6 adds 13.5 => 151.5
    assert out.iloc[5]["ending_cash"] == pytest.approx(138.0)
    assert out.iloc[6]["ending_cash"] == pytest.approx(151.5)
    assert base.iloc[6]["net_income"] == 21.0  # input untouched


def test_divest_reduces_fcf_when_unit_is_cash_generative():
    # Selling a profitable, lightly-levered unit should LOWER total FCF
    # (you give up its cash) even after the interest saved on debt paydown.
    base = _base_forecast()
    held = float(base["free_cash_flow"].sum())
    sold = float(
        divest(base, _carveout(), sale_month=0, proceeds=100.0,
               annual_rate=0.08, tax_rate=0.25)["free_cash_flow"].sum()
    )
    assert sold < held


def test_net_debt_to_ebitda():
    base = _base_forecast()
    lev = net_debt_to_ebitda(base, debt_balance=360.0, cash=0.0)
    assert lev == pytest.approx(360.0 / (30.0 * 12))


def test_net_debt_to_ebitda_zero_ebitda_is_inf():
    base = _base_forecast()
    base["ebitda"] = 0.0
    assert net_debt_to_ebitda(base, debt_balance=100.0) == float("inf")
