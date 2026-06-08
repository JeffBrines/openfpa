from __future__ import annotations

import pandas as pd
from pydantic import BaseModel, Field

_CASH_COLUMNS = [
    "revenue", "gross_profit", "opex", "ebitda", "da", "interest",
    "pretax_income", "tax", "net_income", "capex",
    "operating_cash_flow", "free_cash_flow", "change_in_cash",
]


class Carveout(BaseModel):
    """Monthly contribution of the unit being divested (positive numbers)."""
    revenue: float = Field(ge=0)
    gross_profit: float = Field(ge=0)
    opex: float = Field(ge=0)
    da: float = Field(default=0.0, ge=0)
    capex: float = Field(default=0.0, ge=0)


def divest(
    forecast: pd.DataFrame,
    carve_out: Carveout,
    *,
    sale_month: int,
    proceeds: float,
    annual_rate: float,
    tax_rate: float,
) -> pd.DataFrame:
    """Return a NEW forecast with ``carve_out`` removed from ``sale_month``
    (1-based) onward and ``proceeds`` used to pay down debt (interest reduced
    by ``proceeds * annual_rate / 12`` in post-sale months).

    The input ``forecast`` is **never mutated** — a deep copy is taken
    immediately and all writes go to that copy.

    Assumptions (documented):
    - Working-capital impact of the carve-out is held constant.
    - One-time proceeds are excluded from FCF.
    - Opening balances (debt principal) unchanged.
    - ``ending_cash`` is rebuilt from cumulative ``change_in_cash``.
    """
    out = forecast.copy(deep=True)
    n = len(out.index)
    monthly_interest_saved = proceeds * annual_rate / 12.0
    opening_cash = (
        float(forecast["ending_cash"].iloc[0])
        - float(forecast["change_in_cash"].iloc[0])
    )

    for i in range(n):
        if i < sale_month:
            continue

        revenue = float(out.at[out.index[i], "revenue"]) - carve_out.revenue
        gross_profit = float(out.at[out.index[i], "gross_profit"]) - carve_out.gross_profit
        opex = float(out.at[out.index[i], "opex"]) - carve_out.opex
        da = float(out.at[out.index[i], "da"]) - carve_out.da
        capex = float(out.at[out.index[i], "capex"]) - carve_out.capex
        ebitda = gross_profit - opex
        interest = float(out.at[out.index[i], "interest"]) - monthly_interest_saved
        pretax = ebitda - interest
        tax = max(0.0, pretax) * tax_rate
        net_income = pretax - tax
        wc = float(out.at[out.index[i], "wc_cash_impact"])
        ocf = net_income + da + wc
        fcf = ocf - capex
        principal = float(out.at[out.index[i], "principal"])
        change_in_cash = fcf - principal

        idx_label = out.index[i]
        out.at[idx_label, "revenue"] = revenue
        out.at[idx_label, "gross_profit"] = gross_profit
        out.at[idx_label, "opex"] = opex
        out.at[idx_label, "da"] = da
        out.at[idx_label, "ebitda"] = ebitda
        out.at[idx_label, "interest"] = interest
        out.at[idx_label, "pretax_income"] = pretax
        out.at[idx_label, "tax"] = tax
        out.at[idx_label, "net_income"] = net_income
        out.at[idx_label, "capex"] = capex
        out.at[idx_label, "operating_cash_flow"] = ocf
        out.at[idx_label, "free_cash_flow"] = fcf
        out.at[idx_label, "change_in_cash"] = change_in_cash

    out["ending_cash"] = out["change_in_cash"].cumsum() + opening_cash
    return out


def net_debt_to_ebitda(
    forecast: pd.DataFrame,
    *,
    debt_balance: float,
    cash: float = 0.0,
) -> float:
    """Net-debt / annualized-EBITDA derived from the forecast's EBITDA column.

    Returns ``inf`` when total EBITDA is zero to avoid silent division by zero.
    """
    ebitda = float(forecast["ebitda"].sum())
    return (debt_balance - cash) / ebitda if ebitda else float("inf")
