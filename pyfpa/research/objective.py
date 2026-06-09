from __future__ import annotations

from pathlib import Path
from typing import Literal

import yaml
from pydantic import BaseModel, Field, model_validator


MetricDirection = Literal["lower", "higher"]


class MetricObjective(BaseModel):
    name: str
    weight: float = Field(gt=0)
    direction: MetricDirection = "lower"


class ResearchObjective(BaseModel):
    """Company-specific fitness function plus non-negotiable checks."""

    metrics: list[MetricObjective]
    hard_checks: list[str] = Field(default_factory=list)
    min_improvement: float = Field(default=0.0, ge=0)
    complexity_penalty: float = Field(default=0.0, ge=0)

    @model_validator(mode="after")
    def _unique_metrics(self) -> "ResearchObjective":
        names = [metric.name for metric in self.metrics]
        if len(names) != len(set(names)):
            raise ValueError("objective metric names must be unique")
        if len(self.hard_checks) != len(set(self.hard_checks)):
            raise ValueError("hard check names must be unique")
        return self


def save_research_objective(
    objective: ResearchObjective,
    path: str | Path,
) -> None:
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(yaml.safe_dump(objective.model_dump(), sort_keys=False))


def load_research_objective(path: str | Path) -> ResearchObjective:
    path = Path(path)
    if not path.exists():
        raise FileNotFoundError(f"research objective not found: {path}")
    return ResearchObjective.model_validate(yaml.safe_load(path.read_text()))
