from __future__ import annotations

import pandas as pd
from pydantic import BaseModel, Field

from pyfpa.config.schemas import Channel

_COLUMNS = ["revenue", "cogs", "gross_profit", "gross_margin", "opex", "segment_income"]


class Segment(BaseModel):
    name: str
    annual_revenue: float = Field(ge=0)
    growth_rate: float = 0.0          # annual YoY, compounded per forecast year
    cogs_pct: float = Field(ge=0, le=1)
    opex: float = 0.0                 # annual segment-level operating expense


def segment_pnl(segments: list[Segment]) -> pd.DataFrame:
    """Per-segment P&L down to segment income. Index is segment name."""
    if not segments:
        return pd.DataFrame(columns=_COLUMNS)
    rows = []
    for s in segments:
        revenue = s.annual_revenue
        cogs = revenue * s.cogs_pct
        gross_profit = revenue - cogs
        rows.append({
            "name": s.name,
            "revenue": revenue,
            "cogs": cogs,
            "gross_profit": gross_profit,
            "gross_margin": (gross_profit / revenue) if revenue else 0.0,
            "opex": s.opex,
            "segment_income": gross_profit - s.opex,
        })
    return pd.DataFrame(rows).set_index("name")[_COLUMNS]


def roll_up_segments(segments: list[Segment]) -> pd.Series:
    """Consolidate segment P&Ls into a single total row (Series)."""
    df = segment_pnl(segments)
    if df.empty:
        return pd.Series({c: 0.0 for c in _COLUMNS})
    # gross_margin is excluded from the sum and recomputed from totals — averaging
    # per-segment margins would be wrong (it ignores each segment's revenue weight).
    total = df[["revenue", "cogs", "gross_profit", "opex", "segment_income"]].sum()
    total["gross_margin"] = (total["gross_profit"] / total["revenue"]) if total["revenue"] else 0.0
    return total[_COLUMNS]


def segments_to_channels(segments: list[Segment]) -> list[Channel]:
    """Map segments to engine revenue Channels (flat seasonality) for the
    consolidated cash forecast. Segment-level opex is applied separately at the
    entity level, so it is intentionally not carried here."""
    return [
        Channel(
            name=s.name,
            annual_revenue=s.annual_revenue,
            growth_rate=s.growth_rate,
            seasonality=[1.0] * 12,
            cogs_pct=s.cogs_pct,
        )
        for s in segments
    ]
