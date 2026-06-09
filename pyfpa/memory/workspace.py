from __future__ import annotations

from pathlib import Path

from pyfpa.memory.intake import Intake, save_intake


_WORKSPACE_DIRS = (
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
    for directory in _WORKSPACE_DIRS:
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
        profile.write_text(
            f"# {business_name} Business Profile\n\n"
            "## Business Model\n\n"
            "## Revenue Drivers\n\n"
            "## Cost Structure\n\n"
            "## Working Capital\n\n"
            "## Financing\n\n"
            "## Seasonality And Risks\n"
        )

    memory = workspace / "MEMORY.md"
    if not memory.exists():
        memory.write_text(
            f"# {business_name} FP&A Memory\n\n"
            "- [[intake]]: onboarding facts, evidence, confidence, and open questions\n"
            "- [[business-profile]]: durable business context\n"
            "- `sources/`: source inventory and provenance\n"
            "- `mappings/`: account and operational-data mappings\n"
            "- `corrections/`: human-authored corrections\n"
            "- `forecasts/`: immutable forecast snapshots and scores\n"
            "- `experiments/`: model hypotheses, evidence, and outcomes\n"
            "- `decisions/`: material CFO decisions and approvals\n"
            "- `models/`: champion/challenger history and generated entrypoints\n"
            "- `research/`: immutable autonomous research epochs\n"
            "- `../connectors/generated/`: fixture-tested company data access\n"
        )
    return workspace
