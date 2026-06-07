from __future__ import annotations

import pandas as pd


def month_index(start_month: str, horizon_months: int) -> pd.PeriodIndex:
    """Monthly PeriodIndex of length `horizon_months` starting at `start_month` (YYYY-MM)."""
    start = pd.Period(start_month, freq="M")
    return pd.period_range(start=start, periods=horizon_months, freq="M")
