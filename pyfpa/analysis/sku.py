from __future__ import annotations

import pandas as pd
from pydantic import BaseModel, Field

_COLUMNS = [
    "units", "revenue", "cogs", "gross_profit", "gross_margin",
    "revenue_share", "cumulative_revenue_pct",
]


class Sku(BaseModel):
    name: str
    units: float = Field(ge=0)       # annual units
    price: float = Field(ge=0)       # per-unit selling price
    unit_cost: float = Field(ge=0)   # per-unit COGS


def sku_profitability(skus: list[Sku]) -> pd.DataFrame:
    """Per-SKU economics sorted by gross profit (desc), with revenue share and
    cumulative revenue % (Pareto). Index is the SKU name."""
    if not skus:
        return pd.DataFrame(columns=_COLUMNS)

    rows = []
    for s in skus:
        revenue = s.units * s.price
        cogs = s.units * s.unit_cost
        gross_profit = revenue - cogs
        rows.append({
            "sku": s.name,
            "units": s.units,
            "revenue": revenue,
            "cogs": cogs,
            "gross_profit": gross_profit,
            "gross_margin": (gross_profit / revenue) if revenue else 0.0,
        })

    df = pd.DataFrame(rows).set_index("sku")
    df = df.sort_values("gross_profit", ascending=False)
    total_revenue = df["revenue"].sum()
    share = df["revenue"] / total_revenue if total_revenue else df["revenue"] * 0.0
    return df.assign(
        revenue_share=share,
        cumulative_revenue_pct=share.cumsum(),
    )


def pareto_breakpoint(profitability_df: pd.DataFrame, threshold: float = 0.8) -> int:
    """Number of SKUs whose cumulative revenue first reaches `threshold` (the 80/20 count)."""
    cumulative = profitability_df["cumulative_revenue_pct"]
    for position, value in enumerate(cumulative, start=1):
        if value >= threshold:
            return position
    return len(profitability_df)
