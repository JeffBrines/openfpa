import pytest
from pydantic import ValidationError
from pyfpa.analysis.sku import Sku, sku_profitability, pareto_breakpoint


def _skus():
    return [
        Sku(name="A", units=1000, price=100, unit_cost=40),   # rev 100k, gp 60k, m .6
        Sku(name="B", units=500, price=200, unit_cost=120),   # rev 100k, gp 40k, m .4
        Sku(name="C", units=2000, price=20, unit_cost=15),    # rev 40k,  gp 10k, m .25
    ]


def test_sku_profitability_columns_and_sort():
    df = sku_profitability(_skus())
    assert list(df.columns) == [
        "units", "revenue", "cogs", "gross_profit", "gross_margin",
        "revenue_share", "cumulative_revenue_pct",
    ]
    # sorted by gross_profit desc: A, B, C
    assert df.index.tolist() == ["A", "B", "C"]
    assert round(df.loc["A", "revenue"], 2) == 100000.0
    assert round(df.loc["A", "gross_profit"], 2) == 60000.0
    assert round(df.loc["A", "gross_margin"], 4) == 0.6
    assert round(df.loc["C", "gross_margin"], 4) == 0.25


def test_sku_pareto_cumulative():
    df = sku_profitability(_skus())
    # total rev 240k; shares A .4167 B .4167 C .1667
    assert round(df.loc["A", "revenue_share"], 4) == 0.4167
    # cumulative: A .4167, A+B .8333, +C 1.0
    assert round(df.loc["B", "cumulative_revenue_pct"], 4) == 0.8333
    assert round(df["cumulative_revenue_pct"].iloc[-1], 4) == 1.0


def test_pareto_breakpoint():
    df = sku_profitability(_skus())
    # 2 SKUs (A,B) reach >=80% of revenue
    assert pareto_breakpoint(df, threshold=0.8) == 2


def test_sku_rejects_negative():
    with pytest.raises(ValidationError):
        Sku(name="X", units=-1, price=10, unit_cost=5)


def test_empty_skus_returns_empty_frame():
    df = sku_profitability([])
    assert len(df) == 0
