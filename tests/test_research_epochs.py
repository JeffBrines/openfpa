import pytest
from pydantic import ValidationError

from pyfpa.memory.experiments import ExperimentCheck
from pyfpa.research.epochs import (
    ResearchEpoch,
    evaluate_challenger,
    load_epoch,
    load_epochs,
    save_epoch,
)
from pyfpa.research.objective import MetricObjective, ResearchObjective


def _objective():
    return ResearchObjective(
        metrics=[
            MetricObjective(name="cash_error", weight=0.7, direction="lower"),
            MetricObjective(name="bias_control", weight=0.3, direction="higher"),
        ],
        hard_checks=["cash reconciliation", "holdout"],
        min_improvement=0.05,
        complexity_penalty=0.01,
    )


def _checks(result="pass"):
    return [
        ExperimentCheck(name="cash reconciliation", result=result),
        ExperimentCheck(name="holdout", result="pass"),
    ]


def test_evaluate_challenger_combines_metrics_checks_and_complexity():
    result = evaluate_challenger(
        _objective(),
        {"cash_error": 0.20, "bias_control": 0.80},
        {"cash_error": 0.10, "bias_control": 0.88},
        _checks(),
        champion_complexity=5,
        challenger_complexity=7,
    )

    assert result.per_metric_improvement["cash_error"] == pytest.approx(0.5)
    assert result.per_metric_improvement["bias_control"] == pytest.approx(0.1)
    assert result.complexity_cost == pytest.approx(0.02)
    assert result.objective_gain == pytest.approx(0.36)
    assert result.promotion_eligible is True


def test_failed_hard_check_blocks_promotion():
    result = evaluate_challenger(
        _objective(),
        {"cash_error": 0.20, "bias_control": 0.80},
        {"cash_error": 0.05, "bias_control": 0.90},
        _checks(result="fail"),
    )

    assert result.objective_gain > 0
    assert result.hard_checks_passed is False
    assert result.promotion_eligible is False


def test_zero_baseline_metric_has_bounded_improvement():
    objective = ResearchObjective(
        metrics=[MetricObjective(name="violations", weight=1.0, direction="lower")]
    )
    result = evaluate_challenger(
        objective,
        {"violations": 0.0},
        {"violations": 1.0},
        [],
    )

    assert result.per_metric_improvement["violations"] == -1.0


def test_evaluation_requires_all_metrics_and_checks():
    with pytest.raises(ValueError, match="missing objective metrics"):
        evaluate_challenger(
            _objective(),
            {"cash_error": 0.2},
            {"cash_error": 0.1},
            _checks(),
        )
    with pytest.raises(ValueError, match="missing hard checks"):
        evaluate_challenger(
            _objective(),
            {"cash_error": 0.2, "bias_control": 0.8},
            {"cash_error": 0.1, "bias_control": 0.9},
            [],
        )


def test_epoch_round_trip_and_promotion_gate(tmp_path):
    evaluation = evaluate_challenger(
        _objective(),
        {"cash_error": 0.20, "bias_control": 0.80},
        {"cash_error": 0.10, "bias_control": 0.88},
        _checks(),
    )
    epoch = ResearchEpoch(
        epoch_id="2026-06-09-001",
        created="2026-06-09",
        status="proposed",
        hypothesis="Add a collections lag.",
        champion_id="model-v1",
        challenger_id="model-v2",
        checks=_checks(),
        evaluation=evaluation,
    )

    path = save_epoch(epoch, tmp_path)

    assert load_epoch(path) == epoch
    assert load_epochs(tmp_path) == [epoch]
    with pytest.raises(FileExistsError):
        save_epoch(epoch, tmp_path)
    save_epoch(epoch, tmp_path, overwrite=True)


def test_ineligible_epoch_cannot_be_proposed():
    evaluation = evaluate_challenger(
        _objective(),
        {"cash_error": 0.20, "bias_control": 0.80},
        {"cash_error": 0.19, "bias_control": 0.80},
        _checks(),
    )
    with pytest.raises(ValidationError, match="promotion-eligible"):
        ResearchEpoch(
            epoch_id="weak",
            created="2026-06-09",
            status="proposed",
            hypothesis="Weak candidate",
            champion_id="model-v1",
            challenger_id="model-v2",
            evaluation=evaluation,
        )
