from pyfpa.config.schemas import EntityConfig


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
