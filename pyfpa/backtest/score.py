from __future__ import annotations

from collections.abc import Mapping, Sequence

import pandas as pd
from pydantic import BaseModel

from pyfpa.analysis.reconcile import reconcile

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
    if not period_dicts:
        return {line: 0.0 for line in score_lines}
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


class ScoreResult(BaseModel):
    fitness: float                       # weighted MAPE across scored lines; lower is better
    per_line: dict[str, float]           # signed error %, predicted/actual - 1
    weights: dict[str, float]            # the (renormalized) weights actually used


def score_forecast(
    predicted: Mapping[str, float],
    actual: Mapping[str, float],
    *,
    weights: Mapping[str, float] | None = None,
) -> ScoreResult:
    """Weighted MAPE of predicted vs actual over the scored lines present in both
    (and with non-zero actual). Per-line error reuses `reconcile`'s variance_pct.
    Weights are renormalized over the lines actually scored."""
    weights = dict(weights or DEFAULT_WEIGHTS)
    lines = [line for line in weights if line in predicted and line in actual and actual[line] != 0]
    if not lines:
        raise ValueError("no scorable lines: provide matching, non-zero actuals")
    rec = reconcile({line: predicted[line] for line in lines},
                    {line: actual[line] for line in lines})
    per_line = {line: float(rec.loc[line, "variance_pct"]) for line in lines}
    total_w = sum(weights[line] for line in lines)
    if total_w <= 0:
        raise ValueError("scoring weights must sum to a positive value")
    used = {line: weights[line] / total_w for line in lines}
    fitness = sum(used[line] * abs(per_line[line]) for line in lines)
    return ScoreResult(fitness=fitness, per_line=per_line, weights=used)
