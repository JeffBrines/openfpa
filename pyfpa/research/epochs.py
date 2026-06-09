from __future__ import annotations

from pathlib import Path
from typing import Literal

import yaml
from pydantic import BaseModel, Field, model_validator

from pyfpa.memory.experiments import ExperimentCheck
from pyfpa.research.objective import ResearchObjective


EpochStatus = Literal["generated", "evaluated", "discarded", "proposed", "promoted"]

#: Per-metric improvement is clamped to this magnitude before weighting.
#: Percent-of-champion improvement saturates at +/-100 percent, so no single
#: near-zero-baseline metric can dominate the weighted objective.
#: With min_improvement >= 0 and this clamp, the objective is bounded in
#: [-1 - complexity_penalty, 1].
IMPROVEMENT_CLAMP = 1.0


class EpochEvaluation(BaseModel):
    champion_metrics: dict[str, float]
    challenger_metrics: dict[str, float]
    per_metric_improvement: dict[str, float]
    weighted_improvement: float
    complexity_cost: float
    objective_gain: float
    hard_checks_passed: bool
    promotion_eligible: bool


class ResearchEpoch(BaseModel):
    schema_version: int = 1
    epoch_id: str = Field(pattern=r"^[a-z0-9][a-z0-9._-]*$")
    created: str
    status: EpochStatus = "generated"
    hypothesis: str
    champion_id: str
    challenger_id: str
    memory_sources: list[str] = Field(default_factory=list)
    files_changed: list[str] = Field(default_factory=list)
    training_periods: list[str] = Field(default_factory=list)
    holdout_periods: list[str] = Field(default_factory=list)
    checks: list[ExperimentCheck] = Field(default_factory=list)
    evaluation: EpochEvaluation | None = None
    notes: str = ""

    @model_validator(mode="after")
    def _evaluation_matches_status(self) -> "ResearchEpoch":
        if self.status != "generated" and self.evaluation is None:
            raise ValueError(f"{self.status} epochs require an evaluation")
        if self.status in {"proposed", "promoted"} and not self.evaluation.promotion_eligible:
            raise ValueError("only promotion-eligible epochs may be proposed or promoted")
        return self


def evaluate_challenger(
    objective: ResearchObjective,
    champion_metrics: dict[str, float],
    challenger_metrics: dict[str, float],
    checks: list[ExperimentCheck],
    *,
    champion_complexity: float = 0.0,
    challenger_complexity: float = 0.0,
) -> EpochEvaluation:
    """Compare a challenger to the champion under a company-specific objective."""
    missing = [
        metric.name
        for metric in objective.metrics
        if metric.name not in champion_metrics or metric.name not in challenger_metrics
    ]
    if missing:
        raise ValueError(f"missing objective metrics: {missing}")
    check_results = {check.name: check.result for check in checks}
    missing_checks = [name for name in objective.hard_checks if name not in check_results]
    if missing_checks:
        raise ValueError(f"missing hard checks: {missing_checks}")

    total_weight = sum(metric.weight for metric in objective.metrics)
    improvements: dict[str, float] = {}
    weighted = 0.0
    for metric in objective.metrics:
        champion = champion_metrics[metric.name]
        challenger = challenger_metrics[metric.name]
        if champion == 0:
            if challenger == 0:
                improvement = 0.0
            elif metric.direction == "lower":
                improvement = -1.0
            else:
                improvement = 1.0
        else:
            denominator = abs(champion)
            if metric.direction == "lower":
                improvement = (champion - challenger) / denominator
            else:
                improvement = (challenger - champion) / denominator
        improvement = max(-IMPROVEMENT_CLAMP, min(IMPROVEMENT_CLAMP, improvement))
        improvements[metric.name] = improvement
        weighted += (metric.weight / total_weight) * improvement

    complexity_cost = objective.complexity_penalty * max(
        0.0, challenger_complexity - champion_complexity
    )
    objective_gain = weighted - complexity_cost
    hard_checks_passed = all(
        check_results[name] == "pass" for name in objective.hard_checks
    )
    return EpochEvaluation(
        champion_metrics=champion_metrics,
        challenger_metrics=challenger_metrics,
        per_metric_improvement=improvements,
        weighted_improvement=weighted,
        complexity_cost=complexity_cost,
        objective_gain=objective_gain,
        hard_checks_passed=hard_checks_passed,
        promotion_eligible=hard_checks_passed and objective_gain >= objective.min_improvement,
    )


def save_epoch(
    epoch: ResearchEpoch,
    directory: str | Path,
    *,
    overwrite: bool = False,
) -> Path:
    directory = Path(directory)
    directory.mkdir(parents=True, exist_ok=True)
    path = directory / f"{epoch.epoch_id}.epoch.yaml"
    if path.exists() and not overwrite:
        raise FileExistsError(f"research epoch already exists: {path}")
    path.write_text(yaml.safe_dump(epoch.model_dump(), sort_keys=False))
    return path


def load_epoch(path: str | Path) -> ResearchEpoch:
    path = Path(path)
    if not path.exists():
        raise FileNotFoundError(f"research epoch not found: {path}")
    return ResearchEpoch.model_validate(yaml.safe_load(path.read_text()))


def load_epochs(directory: str | Path) -> list[ResearchEpoch]:
    directory = Path(directory)
    if not directory.exists():
        return []
    return [load_epoch(path) for path in sorted(directory.glob("*.epoch.yaml"))]
