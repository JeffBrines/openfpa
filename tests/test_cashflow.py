from pyfpa.models.cashflow import cashflow_from_config


def test_cashflow_full_forecast(sample_config):
    df = cashflow_from_config(sample_config)
    assert len(df) == 12
    for col in ["revenue", "cogs", "gross_profit", "opex", "ebitda", "interest",
                "pretax_income", "tax", "net_income", "wc_cash_impact",
                "principal", "change_in_cash", "ending_cash"]:
        assert col in df.columns
    assert not df.isna().any().any(), "output DataFrame must contain no NaN values"

    assert round(df["gross_profit"].iloc[0], 6) == 50.0
    assert round(df["ebitda"].iloc[0], 6) == -50.0
    assert round(df["pretax_income"].iloc[0], 6) == -62.0
    assert round(df["net_income"].iloc[0], 6) == -62.0
    assert round(df["change_in_cash"].iloc[0], 6) == -212.0
    assert round(df["ending_cash"].iloc[0], 6) == 288.0
    assert round(df["ending_cash"].iloc[1], 6) == 127.0


def test_nol_shelters_tax():
    from pyfpa.config.schemas import (Channel, EntityConfig, OpeningBalances,
                                      WorkingCapitalConfig)
    cfg = EntityConfig(
        name="P", start_month="2026-01", horizon_months=12, tax_rate=0.25,
        channels=[Channel(name="C", annual_revenue=2400.0,
                          seasonality=[1.0] * 12, cogs_pct=0.0)],
        working_capital=WorkingCapitalConfig(dso_days=0, dpo_days=0, dio_days=0),
        opening_balances=OpeningBalances(nol=100.0),
    )
    df = cashflow_from_config(cfg)
    # Month 1 pretax = 200 (rev 200, no cogs/opex/interest). NOL 100 shelters
    # 100 -> taxable 100 -> tax 25.
    assert round(df["pretax_income"].iloc[0], 6) == 200.0
    assert round(df["tax"].iloc[0], 6) == 25.0
    # Month 2: NOL exhausted -> taxable 200 -> tax 50.
    assert round(df["tax"].iloc[1], 6) == 50.0


def test_ridgeline_config_runs_end_to_end():
    from pathlib import Path
    from pyfpa.config.loader import load_config
    repo_root = Path(__file__).resolve().parents[1]
    cfg = load_config(repo_root / "examples/ridgeline/config.yaml")
    df = cashflow_from_config(cfg)
    assert len(df) == 12
    assert df["ending_cash"].notna().all()
    assert df["revenue"].iloc[0] > 0
