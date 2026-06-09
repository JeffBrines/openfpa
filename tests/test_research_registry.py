import pytest

from pyfpa.memory.experiments import ExperimentCheck
from pyfpa.research.epochs import ResearchEpoch, evaluate_challenger
from pyfpa.research.objective import MetricObjective, ResearchObjective
from pyfpa.research.registry import (
    ModelRegistry,
    ModelVersion,
    load_model_registry,
    promote_challenger,
    register_challenger,
    save_model_registry,
)


def _epoch(challenger_id="model-v2", *, eligible=True):
    objective = ResearchObjective(
        metrics=[MetricObjective(name="cash_error", weight=1.0)],
        hard_checks=["reconcile"],
        min_improvement=0.05,
    )
    evaluation = evaluate_challenger(
        objective,
        {"cash_error": 0.20},
        {"cash_error": 0.10 if eligible else 0.195},
        [ExperimentCheck(name="reconcile", result="pass")],
    )
    return ResearchEpoch(
        epoch_id="epoch-1",
        created="2026-06-09",
        status="proposed" if eligible else "discarded",
        hypothesis="Improve collections timing",
        champion_id="model-v1",
        challenger_id=challenger_id,
        evaluation=evaluation,
    )


def test_register_and_promote_challenger_with_human_approval(tmp_path):
    champion = ModelVersion(model_id="model-v1", created="2026-01-01", artifact="model.py")
    challenger = ModelVersion(
        model_id="model-v2",
        created="2026-06-09",
        artifact="models/generated/collections.py",
        source_epoch="epoch-1",
    )
    registry = register_challenger(ModelRegistry(champion=champion), challenger)
    promoted = promote_challenger(
        registry,
        challenger_id="model-v2",
        epoch=_epoch(),
        approved_by="CFO",
        approved_at="2026-06-09",
    )

    assert promoted.champion == challenger
    assert promoted.retired == [champion]
    assert promoted.promotions[0].approved_by == "CFO"
    path = tmp_path / "registry.yaml"
    save_model_registry(promoted, path)
    assert load_model_registry(path) == promoted


def test_promotion_rejects_missing_approval_or_ineligible_epoch():
    challenger = ModelVersion(
        model_id="model-v2",
        created="2026-06-09",
        artifact="candidate.py",
        source_epoch="epoch-1",
    )
    registry = register_challenger(ModelRegistry(), challenger)
    with pytest.raises(ValueError, match="approved_by"):
        promote_challenger(
            registry,
            challenger_id="model-v2",
            epoch=_epoch(),
            approved_by="",
            approved_at="2026-06-09",
        )
    with pytest.raises(ValueError, match="promotion-eligible"):
        promote_challenger(
            registry,
            challenger_id="model-v2",
            epoch=_epoch(eligible=False),
            approved_by="CFO",
            approved_at="2026-06-09",
        )


def test_duplicate_model_id_rejected():
    version = ModelVersion(model_id="model-v1", created="2026-01-01", artifact="model.py")
    with pytest.raises(ValueError, match="already registered"):
        register_challenger(ModelRegistry(champion=version), version)
