from __future__ import annotations

from collections.abc import Mapping, Sequence

import pandas as pd

DEFAULT_SCORE_LINES = ["ending_cash", "ebitda", "revenue", "gross_margin"]
DEFAULT_WEIGHTS = {"ending_cash": 0.4, "ebitda": 0.3, "revenue": 0.2, "gross_margin": 0.1}


def extract_lines(forecast_df: pd.DataFrame, score_lines: Sequence[str]) -> dict[str, float]:
    """Reduce a monthly forecast to a {line: value} dict for scoring.

    `ending_cash` is a stock (take the last month); `gross_margin` is a ratio
    (Σ gross_profit / Σ revenue); every other line is a flow (sum)."""
    revenue = float(forecast_df["revenue"].sum())
    out: dict[str, float] = {}
    for line in score_lines:
        if line == "ending_cash":
            out[line] = float(forecast_df["ending_cash"].iloc[-1])
        elif line == "gross_margin":
            gp = float(forecast_df["gross_profit"].sum())
            out[line] = (gp / revenue) if revenue else 0.0
        else:
            out[line] = float(forecast_df[line].sum())
    return out


def aggregate_periods(
    period_dicts: Sequence[Mapping[str, float]], score_lines: Sequence[str]
) -> dict[str, float]:
    """Aggregate a chronological list of per-period actual dicts the same way
    `extract_lines` aggregates a forecast (flow=sum, stock=last, ratio=ΣGP/Σrev)."""
    revenue = sum(float(d.get("revenue", 0.0)) for d in period_dicts)
    out: dict[str, float] = {}
    for line in score_lines:
        if line == "ending_cash":
            out[line] = float(period_dicts[-1].get("ending_cash", 0.0))
        elif line == "gross_margin":
            gp = sum(float(d.get("gross_profit", 0.0)) for d in period_dicts)
            out[line] = (gp / revenue) if revenue else 0.0
        else:
            out[line] = sum(float(d.get(line, 0.0)) for d in period_dicts)
    return out
