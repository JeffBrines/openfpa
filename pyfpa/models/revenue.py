from __future__ import annotations

import pandas as pd

from pyfpa.config.schemas import EntityConfig
from pyfpa.models.periods import month_index


def revenue_from_config(cfg: EntityConfig) -> pd.DataFrame:
    """Monthly revenue per channel + total. Seasonality is by calendar month;
    growth compounds per forecast year (every 12 months from start)."""
    idx = month_index(cfg.start_month, cfg.horizon_months)
    data: dict[str, list[float]] = {}
    for ch in cfg.channels:
        total_w = sum(ch.seasonality)
        norm = [w / total_w for w in ch.seasonality]
        series = []
        for i, period in enumerate(idx):
            year_offset = i // 12
            month_pos = period.month - 1
            growth = (1.0 + ch.growth_rate) ** year_offset
            series.append(ch.annual_revenue * norm[month_pos] * growth)
        data[ch.name] = series
    df = pd.DataFrame(data, index=idx)
    return df.assign(total=df.sum(axis=1))
