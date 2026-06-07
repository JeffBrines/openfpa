import pandas as pd
from pyfpa.models.revenue import revenue_from_config


def test_revenue_flat_seasonality(sample_config):
    df = revenue_from_config(sample_config)
    assert len(df) == 12
    assert list(df.columns) == ["D2C", "total"]
    # 1200 / 12 = 100 per month with flat seasonality
    assert df["D2C"].round(6).tolist() == [100.0] * 12
    assert df["total"].sum().round(6) == 1200.0


def test_revenue_growth_compounds_in_year_two():
    from pyfpa.config.schemas import (Channel, EntityConfig, WorkingCapitalConfig)
    cfg = EntityConfig(
        name="G", start_month="2026-01", horizon_months=24,
        channels=[Channel(name="C", annual_revenue=1200.0, growth_rate=0.10,
                          seasonality=[1.0] * 12, cogs_pct=0.5)],
        working_capital=WorkingCapitalConfig(dso_days=0, dpo_days=0, dio_days=0),
    )
    df = revenue_from_config(cfg)
    # year 1 month = 100; year 2 month = 100 * 1.10 = 110
    assert round(df["C"].iloc[0], 6) == 100.0
    assert round(df["C"].iloc[12], 6) == 110.0
