import pytest
from pydantic import ValidationError

from pyfpa.memory.experiments import (
    Experiment,
    ExperimentCheck,
    ExperimentDecision,
    load_experiment,
    load_experiments,
    save_experiment,
)


def _accepted_experiment() -> Experiment:
    return Experiment(
        slug="2026-06-09-collections-lag",
        created="2026-06-09",
        status="accepted",
        hypothesis="Wholesale collections arrive one month later than the base model.",
        cfo_question="Why does cash keep landing below forecast?",
        evidence=["AR aging export", ".fpa/corrections/collections.md"],
        training_periods=["2025-01..2025-09"],
        holdout_periods=["2025-10..2025-12"],
        files_changed=["models/generated/collections.py"],
        metrics_before={"ending_cash_wape": 0.18},
        metrics_after={"ending_cash_wape": 0.07},
        checks=[
            ExperimentCheck(name="cash reconciliation", result="pass"),
            ExperimentCheck(name="holdout improvement", result="pass"),
        ],
        decision=ExperimentDecision(
            outcome="accepted",
            decided_by="CFO",
            decided_at="2026-06-09",
            notes="Matches the collections process.",
        ),
    )


def test_experiment_round_trip(tmp_path):
    experiment = _accepted_experiment()
    path = save_experiment(experiment, tmp_path)

    assert load_experiment(path) == experiment
    assert load_experiments(tmp_path) == [experiment]


def test_experiment_history_does_not_overwrite_implicitly(tmp_path):
    experiment = _accepted_experiment()
    save_experiment(experiment, tmp_path)

    with pytest.raises(FileExistsError):
        save_experiment(experiment, tmp_path)

    save_experiment(experiment, tmp_path, overwrite=True)


def test_accepted_experiment_requires_ratification_and_passing_checks():
    data = _accepted_experiment().model_dump()
    data["decision"] = None
    with pytest.raises(ValidationError, match="require a decision"):
        Experiment.model_validate(data)

    data = _accepted_experiment().model_dump()
    data["checks"][0]["result"] = "fail"
    with pytest.raises(ValidationError, match="all checks to pass"):
        Experiment.model_validate(data)


def test_proposed_experiment_cannot_claim_a_decision():
    data = _accepted_experiment().model_dump()
    data["status"] = "proposed"
    with pytest.raises(ValidationError, match="cannot have a decision"):
        Experiment.model_validate(data)


def test_experiment_snapshot_field_round_trips(tmp_path):
    """snapshot field is preserved on save/load and defaults to None."""
    base = _accepted_experiment()

    # defaults to None when absent
    assert base.snapshot is None

    # explicit snapshot label round-trips
    with_snapshot = base.model_copy(
        update={"snapshot": "forecasts/2025-12.snapshot.yaml"}
    )
    path = save_experiment(with_snapshot, tmp_path)
    loaded = load_experiment(path)
    assert loaded.snapshot == "forecasts/2025-12.snapshot.yaml"


def test_experiment_without_snapshot_round_trips(tmp_path):
    """Experiments without a snapshot still save and load correctly."""
    experiment = _accepted_experiment()
    path = save_experiment(experiment, tmp_path)
    loaded = load_experiment(path)
    assert loaded.snapshot is None
    assert loaded == experiment
