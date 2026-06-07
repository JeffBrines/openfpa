import pytest
from pydantic import ValidationError
from pyfpa.config.schemas import (
    EntityConfig, Channel, WorkingCapitalConfig,
)


def _minimal_kwargs():
    return dict(
        name="X",
        start_month="2026-01",
        channels=[Channel(name="D2C", annual_revenue=1200.0,
                          seasonality=[1.0] * 12, cogs_pct=0.5)],
        working_capital=WorkingCapitalConfig(dso_days=30, dpo_days=30, dio_days=0),
    )


def test_entity_config_defaults():
    cfg = EntityConfig(**_minimal_kwargs())
    assert cfg.horizon_months == 12
    assert cfg.tax_rate == 0.21
    assert cfg.opening_balances.cash == 0.0


def test_seasonality_must_be_twelve():
    with pytest.raises(ValidationError):
        Channel(name="D2C", annual_revenue=1.0, seasonality=[1.0] * 11, cogs_pct=0.5)


def test_cogs_pct_bounded():
    with pytest.raises(ValidationError):
        Channel(name="D2C", annual_revenue=1.0, seasonality=[1.0] * 12, cogs_pct=1.5)


def test_bad_start_month_rejected():
    kwargs = _minimal_kwargs() | {"start_month": "not-a-month"}
    with pytest.raises(ValidationError):
        EntityConfig(**kwargs)
