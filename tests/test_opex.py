from pyfpa.config.schemas import (Channel, EntityConfig, OpexLine,
                                  WorkingCapitalConfig)
from pyfpa.models.revenue import revenue_from_config
from pyfpa.models.opex import opex_from_config


def test_fixed_opex_constant(sample_config):
    rev = revenue_from_config(sample_config)
    df = opex_from_config(sample_config, rev)
    assert df["Rent"].round(6).tolist() == [100.0] * 12
    assert df["total"].round(6).tolist() == [100.0] * 12


def test_variable_opex_scales_with_revenue():
    cfg = EntityConfig(
        name="V", start_month="2026-01",
        channels=[Channel(name="C", annual_revenue=1200.0,
                          seasonality=[1.0] * 12, cogs_pct=0.5)],
        opex=[OpexLine(name="Ads", kind="variable", pct_of_revenue=0.10)],
        working_capital=WorkingCapitalConfig(dso_days=0, dpo_days=0, dio_days=0),
    )
    rev = revenue_from_config(cfg)
    df = opex_from_config(cfg, rev)
    # 100 revenue * 0.10 = 10 per month
    assert df["Ads"].round(6).tolist() == [10.0] * 12
    assert df["total"].round(6).tolist() == [10.0] * 12
