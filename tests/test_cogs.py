from pyfpa.models.revenue import revenue_from_config
from pyfpa.models.cogs import cogs_from_config


def test_cogs_applies_per_channel_pct(sample_config):
    rev = revenue_from_config(sample_config)
    df = cogs_from_config(sample_config, rev)
    assert list(df.columns) == ["D2C", "total"]
    # 100 revenue * 0.5 = 50 per month
    assert df["D2C"].round(6).tolist() == [50.0] * 12
    assert df["total"].round(6).tolist() == [50.0] * 12
