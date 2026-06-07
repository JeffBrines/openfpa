from __future__ import annotations

import pandas as pd


def runway_summary(forecast_df: pd.DataFrame) -> dict:
    """Summarize a 13-week forecast: cash trough and first negative week.

    Returns {"min_cash": float, "min_week": int, "first_negative_week": int | None}.
    """
    ending = forecast_df["ending_cash"]
    negative_weeks = ending.index[ending < 0]
    first_negative = None if negative_weeks.empty else int(negative_weeks[0])
    return {
        "min_cash": float(ending.min()),
        "min_week": int(ending.idxmin()),
        "first_negative_week": first_negative,
    }
