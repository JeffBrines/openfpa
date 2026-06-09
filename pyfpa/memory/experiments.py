from __future__ import annotations

from pathlib import Path
from typing import Literal

import yaml
from pydantic import BaseModel, Field, model_validator


ExperimentStatus = Literal["draft", "proposed", "accepted", "rejected", "reverted"]
CheckResult = Literal["pass", "fail", "not_run"]
DecisionOutcome = Literal["accepted", "rejected", "reverted"]


class ExperimentCheck(BaseModel):
    name: str
    result: CheckResult
    details: str = ""


class ExperimentDecision(BaseModel):
    outcome: DecisionOutcome
    decided_by: str
    decided_at: str
    notes: str = ""


class Experiment(BaseModel):
    """Evidence and ratification record for one company-specific model change."""

    schema_version: int = 1
    slug: str = Field(pattern=r"^[a-z0-9][a-z0-9._-]*$")
    created: str
    status: ExperimentStatus = "draft"
    hypothesis: str
    cfo_question: str = ""
    rationale: str = ""
    evidence: list[str] = Field(default_factory=list)
    training_periods: list[str] = Field(default_factory=list)
    holdout_periods: list[str] = Field(default_factory=list)
    files_changed: list[str] = Field(default_factory=list)
    metrics_before: dict[str, float] = Field(default_factory=dict)
    metrics_after: dict[str, float] = Field(default_factory=dict)
    checks: list[ExperimentCheck] = Field(default_factory=list)
    decision: ExperimentDecision | None = None

    @model_validator(mode="after")
    def _validate_ratification(self) -> "Experiment":
        terminal = {"accepted", "rejected", "reverted"}
        if self.status in terminal:
            if self.decision is None:
                raise ValueError(f"{self.status} experiments require a decision")
            if self.decision.outcome != self.status:
                raise ValueError("experiment status must match decision outcome")
        elif self.decision is not None:
            raise ValueError("draft or proposed experiments cannot have a decision")

        if self.status == "accepted":
            if not self.evidence:
                raise ValueError("accepted experiments require evidence")
            if not self.files_changed:
                raise ValueError("accepted experiments require changed files")
            if not self.checks:
                raise ValueError("accepted experiments require checks")
            if any(check.result != "pass" for check in self.checks):
                raise ValueError("accepted experiments require all checks to pass")
        return self


def save_experiment(
    experiment: Experiment,
    directory: str | Path,
    *,
    overwrite: bool = False,
) -> Path:
    """Save an experiment as YAML; history is never overwritten implicitly."""
    directory = Path(directory)
    directory.mkdir(parents=True, exist_ok=True)
    path = directory / f"{experiment.slug}.experiment.yaml"
    if path.exists() and not overwrite:
        raise FileExistsError(f"experiment already exists: {path}")
    path.write_text(yaml.safe_dump(experiment.model_dump(), sort_keys=False))
    return path


def load_experiment(path: str | Path) -> Experiment:
    """Load and validate one experiment record."""
    path = Path(path)
    if not path.exists():
        raise FileNotFoundError(f"experiment not found: {path}")
    return Experiment.model_validate(yaml.safe_load(path.read_text()))


def load_experiments(directory: str | Path) -> list[Experiment]:
    """Load all experiment records in lexical order."""
    directory = Path(directory)
    if not directory.exists():
        return []
    return [
        load_experiment(path)
        for path in sorted(directory.glob("*.experiment.yaml"))
    ]
