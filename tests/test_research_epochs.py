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


def test_clamp_prevents_near_zero_baseline_from_dominating():
    """A near-zero champion baseline should not swamp the weighted objective.

    Three metrics improve ~98 percent each; the fourth has a near-zero champion
    baseline that triggers a raw improvement far below -1. After clamping, the
    fourth contributes at most -1.0 to the weighted sum, so weighted_improvement
    is close to 0.75 * 0.98 - 0.25 * 1.0, not a large negative number.
    """
    objective = ResearchObjective(
        metrics=[
            MetricObjective(name="m1", weight=0.25, direction="lower"),
            MetricObjective(name="m2", weight=0.25, direction="lower"),
            MetricObjective(name="m3", weight=0.25, direction="lower"),
            MetricObjective(name="near_zero", weight=0.25, direction="lower"),
        ],
    )
    champion = {"m1": 0.10, "m2": 0.10, "m3": 0.10, "near_zero": 0.01}
    challenger = {"m1": 0.002, "m2": 0.002, "m3": 0.002, "near_zero": 0.20}
    result = evaluate_challenger(objective, champion, challenger, [])

    assert result.per_metric_improvement["near_zero"] == pytest.approx(-1.0)
    expected = 0.75 * 0.98 - 0.25 * 1.0
    assert result.weighted_improvement == pytest.approx(expected, abs=0.01)
    assert result.weighted_improvement > -5.0


def test_clamp_boundary_raw_below_minus_one_clamped_to_minus_one():
    """Raw improvement of -5 is clamped to -1.0."""
    objective = ResearchObjective(
        metrics=[MetricObjective(name="err", weight=1.0, direction="lower")]
    )
    champion = {"err": 0.01}
    challenger = {"err": 0.06}
    result = evaluate_challenger(objective, champion, challenger, [])

    raw = (0.01 - 0.06) / 0.01
    assert raw < -1.0
    assert result.per_metric_improvement["err"] == pytest.approx(-1.0)


def test_clamp_boundary_raw_above_plus_one_clamped_to_plus_one():
    """Raw improvement of +3 is clamped to +1.0."""
    objective = ResearchObjective(
        metrics=[MetricObjective(name="err", weight=1.0, direction="higher")]
    )
    champion = {"err": 0.01}
    challenger = {"err": 0.04}
    result = evaluate_challenger(objective, champion, challenger, [])

    raw = (0.04 - 0.01) / 0.01
    assert raw > 1.0
    assert result.per_metric_improvement["err"] == pytest.approx(1.0)


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
