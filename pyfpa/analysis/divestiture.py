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
    """Return a NEW forecast with ``carve_out`` divested after ``sale_month``
    full months, using ``proceeds`` to pay down debt.

    ``sale_month`` is the number of months the unit is **retained** before the
    sale closes: the unit contributes for forecast months 1..``sale_month`` and
    is removed from the following month onward (0-based index ``sale_month``).
    So ``sale_month=6`` means "sold 6 months out" - six months of contribution,
    then gone. In post-sale months, interest is reduced by
    ``proceeds * annual_rate / 12`` (debt paid down with the sale proceeds).

    The input ``forecast`` is **never mutated** - a deep copy is taken
    immediately and all writes go to that copy.

    Assumptions (documented):
    - Working-capital impact of the carve-out is held constant.
    - One-time proceeds are excluded from FCF (FCF is operating only).
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
        label = out.index[i]
        row = out.loc[label]

        gross_profit = row["gross_profit"] - carve_out.gross_profit
        opex = row["opex"] - carve_out.opex
        da = row["da"] - carve_out.da
        capex = row["capex"] - carve_out.capex
        ebitda = gross_profit - opex
        interest = row["interest"] - monthly_interest_saved
        pretax = ebitda - da - interest   # EBIT (= EBITDA - D&A) less interest
        tax = max(0.0, pretax) * tax_rate
        net_income = pretax - tax
        ocf = net_income + da + row["wc_cash_impact"]
        fcf = ocf - capex
        change_in_cash = fcf - row["principal"]

        updates = {
            "revenue": row["revenue"] - carve_out.revenue,
            "gross_profit": gross_profit, "opex": opex, "da": da, "ebitda": ebitda,
            "interest": interest, "pretax_income": pretax, "tax": tax,
            "net_income": net_income, "capex": capex, "operating_cash_flow": ocf,
            "free_cash_flow": fcf, "change_in_cash": change_in_cash,
        }
        for col in _CASH_COLUMNS:
            out.at[label, col] = float(updates[col])

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
