from pyfpa.memory.workspace import initialize_workspace, workspace_path
from pyfpa.memory.entrypoints import load_entrypoint_registry
from pyfpa.memory.lineage import load_mapping_registry, load_source_registry
from pyfpa.research.objective import load_research_objective
from pyfpa.research.registry import load_model_registry


def test_initialize_workspace_creates_memory_contract(tmp_path):
    workspace = initialize_workspace(tmp_path, business_name="Acme")

    assert workspace == workspace_path(tmp_path)
    assert (workspace / "MEMORY.md").exists()
    assert (workspace / "intake.md").exists()
    assert (workspace / "business-profile.md").exists()
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
