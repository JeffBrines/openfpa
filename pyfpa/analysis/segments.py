from __future__ import annotations

import pandas as pd
from pydantic import BaseModel, Field

from pyfpa.config.schemas import Channel

_COLUMNS = ["net_sales", "adjusted_ebitda", "ebitda_margin"]


class Segment(BaseModel):
    """A reportable business segment.

    Public companies that follow ASU 2023-07 disclose segment **net sales** and
    segment **Adjusted EBITDA** — not segment gross profit or operating income
    (segment COGS is generally not broken out). This model mirrors that: each
    segment carries its net sales and an Adjusted-EBITDA margin.
    """
    name: str
    net_sales: float = Field(ge=0)
    growth_rate: float = 0.0          # annual YoY, compounded per forecast year
    ebitda_margin: float              # adjusted EBITDA / net sales


def segment_pnl(segments: list[Segment]) -> pd.DataFrame:
    """Per-segment net sales + Adjusted EBITDA. Index is segment name."""
    if not segments:
        return pd.DataFrame(columns=_COLUMNS)
    rows = []
    for s in segments:
        adjusted_ebitda = s.net_sales * s.ebitda_margin
        rows.append({
            "name": s.name,
            "net_sales": s.net_sales,
            "adjusted_ebitda": adjusted_ebitda,
            "ebitda_margin": s.ebitda_margin,
        })
    return pd.DataFrame(rows).set_index("name")[_COLUMNS]


def roll_up_segments(segments: list[Segment]) -> pd.Series:
    """Consolidate segments into total net sales + total Adjusted EBITDA.

    ``ebitda_margin`` is recomputed from the totals (revenue-weighted), never
    averaged across segments.
    """
    df = segment_pnl(segments)
    if df.empty:
        return pd.Series({c: 0.0 for c in _COLUMNS})
    total = df[["net_sales", "adjusted_ebitda"]].sum()
    total["ebitda_margin"] = (
        total["adjusted_ebitda"] / total["net_sales"] if total["net_sales"] else 0.0
    )
    return total[_COLUMNS]


def segments_to_channels(segments: list[Segment], *, cogs_pct: float) -> list[Channel]:
    """Map segments to engine revenue Channels for the consolidated forecast.

    Each segment becomes a revenue channel carrying its own net sales and growth
    rate, so the consolidated total reflects the segment mix. Segment-level COGS
    is not disclosed, so the **consolidated blended** ``cogs_pct`` is applied to
    every segment — by construction the channels sum back to consolidated COGS.
    Segment Adjusted-EBITDA margins live on the segment view, not here.
    """
    return [
        Channel(
            name=s.name,
            annual_revenue=s.net_sales,
            growth_rate=s.growth_rate,
            seasonality=[1.0] * 12,
            cogs_pct=cogs_pct,
        )
        for s in segments
    ]
