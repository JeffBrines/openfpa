from pyfpa.config.schemas import EntityConfig
from pyfpa.models.cashflow import cashflow_from_config


def _base_cfg(**overrides):
    data = {
        "name": "T", "start_month": "2025-01", "horizon_months": 12,
        "tax_rate": 0.0,
        "channels": [{
            "name": "C", "annual_revenue": 1_200_000.0, "growth_rate": 0.0,
            "seasonality": [1.0] * 12, "cogs_pct": 0.5,
        }],
        "opex": [], "debt": [],
        "working_capital": {"dso_days": 0, "dpo_days": 0, "dio_days": 0},
        "opening_balances": {"cash": 0.0},
    }
    data.update(overrides)
    return EntityConfig.model_validate(data)


def test_config_defaults_da_capex_zero():
    cfg = _base_cfg()
    assert cfg.da_monthly == 0.0
    assert cfg.capex_monthly == 0.0


def test_config_accepts_da_capex():
    cfg = _base_cfg(da_monthly=1000.0, capex_monthly=2000.0)
    assert cfg.da_monthly == 1000.0
    assert cfg.capex_monthly == 2000.0


def test_fcf_columns_and_math():
    # revenue 100k/mo, cogs 50%, gross 50k, no opex, no tax, no interest;
    # D&A 1k is expensed (EBIT 49k => net 49k) then added back in OCF (cash-neutral).
    cfg = _base_cfg(da_monthly=1000.0, capex_monthly=2000.0)
    df = cashflow_from_config(cfg)
    for col in ("da", "capex", "operating_cash_flow", "free_cash_flow"):
        assert col in df.columns
    row = df.iloc[0]
    assert row["da"] == 1000.0
    assert row["capex"] == 2000.0
    assert row["net_income"] == 49_000.0          # EBITDA 50k - D&A 1k
    assert row["operating_cash_flow"] == 50_000.0  # net 49k + D&A 1k addback
    assert row["free_cash_flow"] == 48_000.0       # OCF 50k - capex 2k
    assert row["change_in_cash"] == 48_000.0


def test_da_is_cash_neutral_vs_no_da():
    # adding D&A must NOT change operating cash flow (expense and addback cancel)
    base = cashflow_from_config(_base_cfg())
    with_da = cashflow_from_config(_base_cfg(da_monthly=5000.0))
    assert (with_da["operating_cash_flow"] == base["operating_cash_flow"]).all()
    assert (with_da["net_income"] == base["net_income"] - 5000.0).all()


def test_da_capex_default_zero_preserves_change_in_cash():
    cfg = _base_cfg()
    df = cashflow_from_config(cfg)
    assert (df["change_in_cash"] == df["net_income"] + df["wc_cash_impact"] - df["principal"]).all()
