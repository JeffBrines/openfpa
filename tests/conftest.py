import pytest

from pyfpa.config.schemas import (
    Channel, DebtInstrument, EntityConfig, OpeningBalances, OpexLine,
    WorkingCapitalConfig,
)


@pytest.fixture
def sample_config() -> EntityConfig:
    return EntityConfig(
        name="Test Co",
        start_month="2026-01",
        horizon_months=12,
        tax_rate=0.0,
        channels=[
            Channel(name="D2C", annual_revenue=1200.0, growth_rate=0.0,
                    seasonality=[1.0] * 12, cogs_pct=0.5),
        ],
        opex=[OpexLine(name="Rent", kind="fixed", monthly_amount=100.0)],
        debt=[DebtInstrument(name="Term", kind="term_loan", opening_balance=1200.0,
                             annual_rate=0.12, monthly_principal=100.0)],
        working_capital=WorkingCapitalConfig(dso_days=30, dpo_days=30, dio_days=0),
        opening_balances=OpeningBalances(cash=500.0, ar=0.0, ap=0.0, inventory=0.0),
    )
