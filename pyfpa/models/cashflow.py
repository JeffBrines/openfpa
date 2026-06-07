from __future__ import annotations

import pandas as pd

from pyfpa.config.schemas import EntityConfig
from pyfpa.models.cogs import cogs_from_config
from pyfpa.models.debt import debt_from_config
from pyfpa.models.opex import opex_from_config
from pyfpa.models.revenue import revenue_from_config
from pyfpa.models.working_capital import working_capital_from_config


def _tax_series(pretax: pd.Series, opening_nol: float, tax_rate: float) -> pd.Series:
    """Apply tax_rate to positive pre-tax income after consuming NOL carryforward."""
    nol = opening_nol
    out = []
    for value in pretax:
        positive = max(0.0, value)
        used = min(nol, positive)
        nol -= used
        taxable = positive - used
        out.append(taxable * tax_rate)
    return pd.Series(out, index=pretax.index)


def cashflow_from_config(cfg: EntityConfig) -> pd.DataFrame:
    """Compose all model layers into the full monthly forecast (P&L + cash)."""
    revenue = revenue_from_config(cfg)
    cogs = cogs_from_config(cfg, revenue)
    opex = opex_from_config(cfg, revenue)
    wc = working_capital_from_config(cfg, revenue, cogs)
    debt = debt_from_config(cfg)

    gross_profit = revenue["total"] - cogs["total"]
    ebitda = gross_profit - opex["total"]
    interest = debt["interest"]
    pretax = ebitda - interest
    tax = _tax_series(pretax, cfg.opening_balances.nol, cfg.tax_rate)
    net_income = pretax - tax

    change_in_cash = net_income + wc["wc_cash_impact"] - debt["principal"]
    ending_cash = change_in_cash.cumsum() + cfg.opening_balances.cash

    return pd.DataFrame(
        {
            "revenue": revenue["total"],
            "cogs": cogs["total"],
            "gross_profit": gross_profit,
            "opex": opex["total"],
            "ebitda": ebitda,
            "interest": interest,
            "pretax_income": pretax,
            "tax": tax,
            "net_income": net_income,
            "wc_cash_impact": wc["wc_cash_impact"],
            "principal": debt["principal"],
            "change_in_cash": change_in_cash,
            "ending_cash": ending_cash,
        },
        index=revenue.index,
    )
