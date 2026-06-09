from pyfpa.memory.workspace import initialize_workspace, workspace_path
from pyfpa.memory.entrypoints import load_entrypoint_registry
from pyfpa.memory.lineage import load_mapping_registry, load_source_registry
from pyfpa.memory.onboarding import PROFILE_HEADINGS, render_business_profile
from pyfpa.memory.intake import Intake
from pyfpa.research.objective import load_research_objective
from pyfpa.research.registry import load_model_registry


def test_initialize_workspace_creates_memory_contract(tmp_path):
    workspace = initialize_workspace(tmp_path, business_name="Acme")

    assert workspace == workspace_path(tmp_path)
    assert (workspace / "MEMORY.md").exists()
    assert (workspace / "intake.md").exists()
    assert (workspace / "business-profile.md").exists()
    assert (workspace / "scorecard.md").exists()
    assert (workspace / "learnings.md").exists()
    assert load_research_objective(workspace / "research" / "objective.yaml").min_improvement == 0.02
    assert load_model_registry(workspace / "models" / "registry.yaml").champion is None
    assert load_entrypoint_registry(
        workspace / "models" / "entrypoints.yaml"
    ).entrypoints == []
    assert load_source_registry(workspace / "sources" / "registry.yaml").sources == []
    assert load_mapping_registry(workspace / "mappings" / "registry.yaml").mappings == []
    for directory in (
        "sources", "mappings", "corrections", "forecasts", "experiments", "decisions",
        "models", "research",
    ):
        assert (workspace / directory).is_dir()
    for directory in (
        "connectors/generated",
        "models/generated",
        "skills/generated",
        "agents/generated",
    ):
        assert (tmp_path / directory).is_dir()


def test_initialize_workspace_does_not_overwrite_memory(tmp_path):
    workspace = initialize_workspace(tmp_path, business_name="Acme")
    memory = workspace / "MEMORY.md"
    intake = workspace / "intake.md"
    memory.write_text("# Custom Memory\n")
    intake.write_text("---\nbusiness_name: Custom\nfacts: []\n---\n")

    initialize_workspace(tmp_path, business_name="Other")

    assert memory.read_text() == "# Custom Memory\n"
    assert intake.read_text() == "---\nbusiness_name: Custom\nfacts: []\n---\n"


def _extract_h2_headings(text: str) -> list[str]:
    """Return all ## headings from a markdown document."""
    return [
        line[3:].strip()
        for line in text.splitlines()
        if line.startswith("## ")
    ]


def test_business_profile_headings_are_unified_across_init_and_onboarding(tmp_path):
    """initialize_workspace and render_business_profile must share a single
    source of truth for section headings so init-then-onboard produces no
    schema flip."""
    workspace = initialize_workspace(tmp_path, business_name="Acme")
    stub_headings = _extract_h2_headings(
        (workspace / "business-profile.md").read_text()
    )

    rendered = render_business_profile(Intake(business_name="Acme"))
    rendered_headings = _extract_h2_headings(rendered)

    assert stub_headings == rendered_headings, (
        "initialize_workspace stub headings differ from render_business_profile headings; "
        "both must come from PROFILE_HEADINGS"
    )
    assert len(stub_headings) == len(PROFILE_HEADINGS)


def test_memory_index_describes_complete_vault(tmp_path):
    """MEMORY.md must reference every documented vault artifact."""
    workspace = initialize_workspace(tmp_path, business_name="Acme")
    content = (workspace / "MEMORY.md").read_text()

    required_artifacts = [
        "intake.md",
        "business-profile.md",
        "sources/",
        "mappings/",
        "corrections/",
        "forecasts/",
        "scorecard.md",
        "learnings.md",
        "experiments/",
        "decisions/",
        "models/",
        "research/",
    ]
    for artifact in required_artifacts:
        assert artifact in content, f"MEMORY.md missing entry for: {artifact}"
