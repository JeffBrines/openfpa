from __future__ import annotations

import copy
import statistics

from pydantic import BaseModel

from pyfpa.config.schemas import EntityConfig
from pyfpa.models.cashflow import cashflow_from_config
from pyfpa.backtest.score import DEFAULT_SCORE_LINES, extract_lines, score_forecast
from pyfpa.memory.paths import apply_override
from pyfpa.portfolio.manifest import ClientRef
from pyfpa.portfolio.mine import client_driver_value
from pyfpa.portfolio.recover import best_snapshot, recover_actuals


class ValidationResult(BaseModel):
    mean_delta: float
    n_folds: int
    validated: bool


def validate_prior(driver: str, type_clients: list[ClientRef], *, tolerance: float = 0.0) -> ValidationResult:
    """Leave-one-out cross-client check. For each usable client, derive `driver`'s
    value as the median across the OTHER clients, apply it to the held-out client's
    best-snapshot config, re-forecast, and score against that client's recovered
    actuals. A prior is `validated` if the mean fitness delta (new - original) is
    <= tolerance with >= 2 folds — a peer-derived value does not degrade held-out fit."""
    usable = []
    for c in type_clients:
        snap = best_snapshot(c.path)
        value = client_driver_value(c, driver)
        if snap is not None and snap.score is not None and value is not None:
            usable.append((value, snap))
    n = len(usable)
    if n < 2:
        return ValidationResult(mean_delta=0.0, n_folds=n, validated=False)

    deltas = []
    for i, (_, snap) in enumerate(usable):
        peer_values = [usable[j][0] for j in range(n) if j != i]
        prior_value = statistics.median(peer_values)
        data = copy.deepcopy(snap.assumptions)
        apply_override(data, driver, prior_value)
        forecast = cashflow_from_config(EntityConfig.model_validate(data))
        predicted = extract_lines(forecast, DEFAULT_SCORE_LINES)
        new_fitness = score_forecast(predicted, recover_actuals(snap)).fitness
        deltas.append(new_fitness - snap.score.fitness)

    mean_delta = statistics.fmean(deltas)
    return ValidationResult(mean_delta=mean_delta, n_folds=n, validated=mean_delta <= tolerance)
