from __future__ import annotations

from pathlib import Path

from pyfpa.memory.intake import Intake, save_intake


WORKSPACE_DIRS = (
    "sources",
    "mappings",
    "corrections",
    "forecasts",
    "experiments",
    "decisions",
    "models",
    "research",
)

_GENERATED_DIRS = (
    "connectors/generated",
    "models/generated",
    "skills/generated",
    "agents/generated",
)


def workspace_path(company_root: str | Path) -> Path:
    """Return the `.fpa` memory path for a company workspace."""
    return Path(company_root) / ".fpa"


def initialize_workspace(
    company_root: str | Path,
    *,
    business_name: str = "Company",
) -> Path:
    """Create a company `.fpa` workspace without overwriting existing memory."""
    workspace = workspace_path(company_root)
    workspace.mkdir(parents=True, exist_ok=True)
    for directory in WORKSPACE_DIRS:
        (workspace / directory).mkdir(exist_ok=True)
    for directory in _GENERATED_DIRS:
        (Path(company_root) / directory).mkdir(parents=True, exist_ok=True)

    source_registry = workspace / "sources" / "registry.yaml"
    if not source_registry.exists():
        from pyfpa.memory.lineage import SourceRegistry, save_source_registry

        save_source_registry(SourceRegistry(), source_registry)

    mapping_registry = workspace / "mappings" / "registry.yaml"
    if not mapping_registry.exists():
        from pyfpa.memory.lineage import MappingRegistry, save_mapping_registry

        save_mapping_registry(MappingRegistry(), mapping_registry)

    objective = workspace / "research" / "objective.yaml"
    if not objective.exists():
        from pyfpa.research.objective import (
            MetricObjective,
            ResearchObjective,
            save_research_objective,
        )

        save_research_objective(
            ResearchObjective(
                metrics=[
                    MetricObjective(name="ending_cash_error", weight=0.4),
                    MetricObjective(name="ebitda_error", weight=0.3),
                    MetricObjective(name="revenue_error", weight=0.2),
                    MetricObjective(name="gross_margin_error", weight=0.1),
                ],
                hard_checks=[
                    "source reconciliation",
                    "accounting invariants",
                    "holdout separation",
                ],
                min_improvement=0.02,
                complexity_penalty=0.01,
            ),
            objective,
        )

    registry = workspace / "models" / "registry.yaml"
    if not registry.exists():
        from pyfpa.research.registry import ModelRegistry, save_model_registry

        save_model_registry(ModelRegistry(), registry)

    entrypoints = workspace / "models" / "entrypoints.yaml"
    if not entrypoints.exists():
        from pyfpa.memory.entrypoints import (
            EntrypointRegistry,
            save_entrypoint_registry,
        )

        save_entrypoint_registry(EntrypointRegistry(), entrypoints)

    intake = workspace / "intake.md"
    if not intake.exists():
        save_intake(Intake(business_name=business_name), intake)

    profile = workspace / "business-profile.md"
    if not profile.exists():
        from pyfpa.memory.onboarding import render_business_profile

        profile.write_text(render_business_profile(Intake(business_name=business_name)))

    scorecard = workspace / "scorecard.md"
    if not scorecard.exists():
        scorecard.write_text("# Forecast Scorecard\n")

    learnings = workspace / "learnings.md"
    if not learnings.exists():
        learnings.write_text("# Learnings\n")

    memory = workspace / "MEMORY.md"
    if not memory.exists():
        memory.write_text(
            f"# {business_name} FP&A Memory\n\n"
            "- `intake.md`: onboarding facts, evidence, confidence, and open questions\n"
            "- `business-profile.md`: durable business context derived from intake\n"
            "- `sources/`: source inventory and data provenance\n"
            "- `mappings/`: account and operational-data mappings\n"
            "- `corrections/`: typed human corrections recorded by fpa-capture-correction, applied via pyfpa.apply_corrections\n"
            "- `forecasts/`: immutable forecast snapshots and their scores, written by pyfpa.backtest\n"
            "- `scorecard.md`: rendered forecast track record across all scored periods\n"
            "- `learnings.md`: accepted model changes with evidence and backtest delta\n"
            "- `experiments/`: model hypotheses, evidence, checks, and ratification decisions\n"
            "- `decisions/`: material CFO decisions and approvals\n"
            "- `models/`: champion/challenger history and generated entrypoints\n"
            "- `research/`: immutable autonomous research epochs\n"
            "- `../connectors/generated/`: fixture-tested company data access\n"
        )
    return workspace
