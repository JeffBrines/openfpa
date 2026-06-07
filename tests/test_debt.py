from pyfpa.models.debt import debt_from_config


def test_term_loan_amortization(sample_config):
    df = debt_from_config(sample_config)
    assert list(df.columns) == ["interest", "principal", "ending_debt"]
    # opening 1200 @ 1%/mo: month1 interest 12, principal 100, ending 1100
    assert round(df["interest"].iloc[0], 6) == 12.0
    assert round(df["principal"].iloc[0], 6) == 100.0
    assert round(df["ending_debt"].iloc[0], 6) == 1100.0
    # month2: interest 1100*1% = 11, ending 1000
    assert round(df["interest"].iloc[1], 6) == 11.0
    assert round(df["ending_debt"].iloc[1], 6) == 1000.0


def test_loc_is_interest_only():
    from pyfpa.config.schemas import (DebtInstrument, EntityConfig, Channel,
                                      WorkingCapitalConfig)
    cfg = EntityConfig(
        name="L", start_month="2026-01", horizon_months=3,
        channels=[Channel(name="C", annual_revenue=12.0,
                          seasonality=[1.0] * 12, cogs_pct=0.5)],
        debt=[DebtInstrument(name="LOC", kind="loc", opening_balance=1000.0,
                             annual_rate=0.12)],
        working_capital=WorkingCapitalConfig(dso_days=0, dpo_days=0, dio_days=0),
    )
    df = debt_from_config(cfg)
    assert df["principal"].round(6).tolist() == [0.0, 0.0, 0.0]
    assert df["ending_debt"].round(6).tolist() == [1000.0, 1000.0, 1000.0]
    assert round(df["interest"].iloc[0], 6) == 10.0  # 1000 * 1%
