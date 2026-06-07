from pyfpa.config.schemas import (Channel, EntityConfig, WorkingCapitalConfig)
from pyfpa.models.revenue import revenue_from_config
from pyfpa.models.cogs import cogs_from_config


def test_cogs_applies_per_channel_pct(sample_config):
    rev = revenue_from_config(sample_config)
    df = cogs_from_config(sample_config, rev)
    assert list(df.columns) == ["D2C", "total"]
    # 100 revenue * 0.5 = 50 per month
    assert df["D2C"].round(6).tolist() == [50.0] * 12
    assert df["total"].round(6).tolist() == [50.0] * 12


def test_cogs_total_sums_across_channels():
    cfg = EntityConfig(
        name="M", start_month="2026-01", horizon_months=12,
        channels=[
            Channel(name="A", annual_revenue=1200.0, seasonality=[1.0] * 12, cogs_pct=0.5),
            Channel(name="B", annual_revenue=2400.0, seasonality=[1.0] * 12, cogs_pct=0.25),
        ],
        working_capital=WorkingCapitalConfig(dso_days=0, dpo_days=0, dio_days=0),
    )
    rev = revenue_from_config(cfg)
    df = cogs_from_config(cfg, rev)
    # A: 100*0.5=50, B: 200*0.25=50 -> total 100/mo
    assert df["A"].round(6).tolist() == [50.0] * 12
    assert df["B"].round(6).tolist() == [50.0] * 12
    assert df["total"].round(6).tolist() == [100.0] * 12
