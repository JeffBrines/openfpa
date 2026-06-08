from __future__ import annotations

from collections.abc import Callable, Mapping, Sequence

from pyfpa.config.schemas import EntityConfig
from pyfpa.models.cashflow import cashflow_from_config
from pyfpa.backtest.score import (
    DEFAULT_SCORE_LINES, ScoreResult, aggregate_periods, extract_lines, score_forecast,
)

BuildCfgFn = Callable[[dict[str, Mapping[str, float]]], EntityConfig]


def holdout_backtest(
    actuals_by_period: Mapping[str, Mapping[str, float]],
    build_cfg_fn: BuildCfgFn,
    *,
    holdout: int,
    score_lines: Sequence[str] = DEFAULT_SCORE_LINES,
    weights: Mapping[str, float] | None = None,
) -> ScoreResult:
    """Fit on all but the last `holdout` periods, predict the holdout, and score
    predicted vs the held-out actuals. The business-specific `build_cfg_fn`
    (fit actuals -> a config that forecasts the holdout window) is supplied by the
    caller; this harness only owns the split and the scoring. Nothing is scored on
    data it was fit on."""
    periods = list(actuals_by_period)
    if len(periods) <= holdout:
        raise ValueError(f"need more than {holdout} periods, got {len(periods)}")
    fit_periods = periods[:-holdout]
    holdout_periods = periods[-holdout:]

    fit_actuals = {p: dict(actuals_by_period[p]) for p in fit_periods}
    cfg = build_cfg_fn(fit_actuals)
    predicted = extract_lines(cashflow_from_config(cfg), score_lines)
    actual = aggregate_periods([dict(actuals_by_period[p]) for p in holdout_periods], score_lines)
    return score_forecast(predicted, actual, weights=weights)
