from pyfpa.models.revenue import revenue_from_config
from pyfpa.models.cogs import cogs_from_config
from pyfpa.models.working_capital import working_capital_from_config


def test_working_capital_balances_and_cash_impact(sample_config):
    rev = revenue_from_config(sample_config)
    cogs = cogs_from_config(sample_config, rev)
    df = working_capital_from_config(sample_config, rev, cogs)

    # dso=30 -> AR = revenue(100) * 30/30 = 100 every month
    assert df["ar"].round(6).tolist() == [100.0] * 12
    # dpo=30 -> AP = cogs(50) * 30/30 = 50 every month
    assert df["ap"].round(6).tolist() == [50.0] * 12
    # dio=0 -> inventory 0
    assert df["inventory"].round(6).tolist() == [0.0] * 12

    # Month 1 deltas vs opening (all opening = 0): d_ar=100, d_ap=50, d_inv=0
    assert round(df["d_ar"].iloc[0], 6) == 100.0
    assert round(df["d_ap"].iloc[0], 6) == 50.0
    # cash impact month 1 = -100 + 50 - 0 = -50
    assert round(df["wc_cash_impact"].iloc[0], 6) == -50.0
    # month 2 balances flat -> deltas 0 -> cash impact 0
    assert round(df["wc_cash_impact"].iloc[1], 6) == 0.0
