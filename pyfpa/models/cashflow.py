from __future__ import annotations

import pandas as pd

from pyfpa.config.schemas import EntityConfig
from pyfpa.models.cogs import cogs_from_config
from pyfpa.models.debt import debt_from_config
from pyfpa.models.opex import opex_from_config
from pyfpa.models.revenue import revenue_from_config
from pyfpa.models.working_capital import working_capital_from_config


def _tax_series(pretax: pd.Series, opening_nol: float, tax_rate: float) -> pd.Series:
    """Apply tax_rate to positive pre-tax income after consuming NOL carryforward.

    In-period losses do not generate new NOL for future months; only the
    opening_nol passed in is consumed.
    """
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

    n = len(revenue.index)
    da = pd.Series([cfg.da_monthly] * n, index=revenue.index)
    capex = pd.Series([cfg.capex_monthly] * n, index=revenue.index)

    gross_profit = revenue["total"] - cogs["total"]
    ebitda = gross_profit - opex["total"]
    ebit = ebitda - da                 # D&A is a real (non-cash) expense in the P&L...
    interest = debt["interest"]
    pretax = ebit - interest
    tax = _tax_series(pretax, cfg.opening_balances.nol, cfg.tax_rate)
    net_income = pretax - tax

    operating_cash_flow = net_income + da + wc["wc_cash_impact"]  # ...and added back here
    free_cash_flow = operating_cash_flow - capex
    change_in_cash = free_cash_flow - debt["principal"]
    ending_cash = change_in_cash.cumsum() + cfg.opening_balances.cash

    return pd.DataFrame(
        {
            "revenue": revenue["total"],
            "cogs": cogs["total"],
            "gross_profit": gross_profit,
            "opex": opex["total"],
            "ebitda": ebitda,
            "da": da,
            "interest": interest,
            "pretax_income": pretax,
            "tax": tax,
            "net_income": net_income,
            "wc_cash_impact": wc["wc_cash_impact"],
            "operating_cash_flow": operating_cash_flow,
            "capex": capex,
            "principal": debt["principal"],
            "free_cash_flow": free_cash_flow,
            "change_in_cash": change_in_cash,
            "ending_cash": ending_cash,
        },
        index=revenue.index,
    )
