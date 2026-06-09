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


# --- append to tests/test_loader.py ---
from pathlib import Path
from pyfpa.config.loader import load_config

REPO_ROOT = Path(__file__).resolve().parents[1]


def test_load_ridgeline_config():
    cfg = load_config(REPO_ROOT / "examples/ridgeline/config.yaml")
    assert cfg.name == "Ridgeline Chair Co."
    assert len(cfg.channels) == 3
    assert cfg.horizon_months == 12


def test_load_missing_file_raises():
    with pytest.raises(FileNotFoundError):
        load_config(REPO_ROOT / "examples/does_not_exist.yaml")


def test_channel_name_total_rejected():
    with pytest.raises(ValidationError):
        Channel(name="total", annual_revenue=1.0, seasonality=[1.0] * 12, cogs_pct=0.5)


def test_opex_name_total_rejected():
    from pyfpa.config.schemas import OpexLine
    with pytest.raises(ValidationError):
        OpexLine(name="Total", kind="fixed", monthly_amount=1.0)


def test_duplicate_channel_names_rejected():
    kwargs = _minimal_kwargs()
    kwargs["channels"] = [
        Channel(name="D2C", annual_revenue=1.0, seasonality=[1.0] * 12, cogs_pct=0.5),
        Channel(name="d2c", annual_revenue=2.0, seasonality=[1.0] * 12, cogs_pct=0.5),
    ]
    with pytest.raises(ValidationError, match="channels names must be unique"):
        EntityConfig(**kwargs)


def test_growth_cannot_reduce_revenue_below_zero():
    with pytest.raises(ValidationError):
        Channel(
            name="D2C",
            annual_revenue=1.0,
            growth_rate=-1.0,
            seasonality=[1.0] * 12,
            cogs_pct=0.5,
        )
