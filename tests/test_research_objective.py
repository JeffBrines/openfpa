import pytest
from pydantic import ValidationError

from pyfpa.research.objective import (
    MetricObjective,
    ResearchObjective,
    load_research_objective,
    save_research_objective,
)


def test_objective_rejects_duplicate_metrics():
    with pytest.raises(ValidationError, match="must be unique"):
        ResearchObjective(metrics=[
            MetricObjective(name="cash_error", weight=1.0),
            MetricObjective(name="cash_error", weight=2.0),
        ])


def test_objective_round_trip(tmp_path):
    objective = ResearchObjective(
        metrics=[MetricObjective(name="cash_error", weight=1.0)],
        hard_checks=["reconcile"],
    )
    path = tmp_path / "objective.yaml"

    save_research_objective(objective, path)

    assert load_research_objective(path) == objective


def test_objective_rejects_duplicate_hard_checks():
    with pytest.raises(ValidationError, match="hard check names must be unique"):
        ResearchObjective(
            metrics=[MetricObjective(name="cash_error", weight=1.0)],
            hard_checks=["reconcile", "reconcile"],
        )
