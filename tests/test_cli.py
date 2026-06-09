import json
import subprocess
import sys
import tomllib
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def run_cli(*args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, "-m", "pyfpa.cli", *args],
        cwd=ROOT,
        text=True,
        capture_output=True,
        check=False,
    )


def output_json(result: subprocess.CompletedProcess[str]) -> dict:
    assert result.stdout, result.stderr
    return json.loads(result.stdout)


def test_project_registers_openfpa_console_script():
    project = tomllib.loads((ROOT / "pyproject.toml").read_text())

    assert project["project"]["scripts"]["openfpa"] == "pyfpa.cli:main"


def test_init_is_idempotent_and_returns_machine_readable_state(tmp_path):
    company = tmp_path / "acme"

    first = run_cli("init", str(company), "--business-name", "Acme")
    second = run_cli("init", str(company), "--business-name", "Other")

    assert first.returncode == 0
    assert second.returncode == 0
    first_payload = output_json(first)
    second_payload = output_json(second)
    assert first_payload["command"] == "init"
    assert first_payload["data"]["created"] is True
    assert first_payload["data"]["business_name"] == "Acme"
    assert second_payload["data"]["created"] is False
    assert second_payload["data"]["business_name"] == "Acme"
    assert (company / ".fpa" / "intake.md").exists()


def test_inspect_data_classifies_likely_financial_files_without_writing(tmp_path):
    (tmp_path / "Income Statement FY2025.xlsx").write_bytes(b"xlsx")
    (tmp_path / "AR Aging.csv").write_text("customer,balance\n")
    (tmp_path / "Inventory Detail.tsv").write_text("sku\tunits\n")
    (tmp_path / "notes.md").write_text("not a financial artifact")
    hidden = tmp_path / ".private"
    hidden.mkdir()
    (hidden / "Balance Sheet.xlsx").write_bytes(b"xlsx")

    result = run_cli("inspect-data", str(tmp_path))

    assert result.returncode == 0
    payload = output_json(result)
    assert payload["data"]["writes_performed"] is False
    assert payload["data"]["category_counts"] == {
        "ar_aging": 1,
        "inventory": 1,
        "profit_and_loss": 1,
    }
    assert payload["data"]["missing_priority_categories"] == [
        "ap_aging",
        "balance_sheet",
    ]
    assert not (tmp_path / ".fpa").exists()


def test_status_and_intake_next_expose_state_for_the_agent(tmp_path):
    uninitialized = run_cli("status", str(tmp_path))
    assert output_json(uninitialized)["data"]["initialized"] is False

    assert run_cli("init", str(tmp_path), "--business-name", "Acme").returncode == 0
    status = run_cli("status", str(tmp_path))
    questions = run_cli("intake-next", str(tmp_path), "--limit", "2")

    assert status.returncode == 0
    status_payload = output_json(status)["data"]
    assert status_payload["initialized"] is True
    assert status_payload["intake_ready"] is False
    assert status_payload["champion"] is None
    assert status_payload["entrypoint_count"] == 0
    assert status_payload["source_count"] == 0
    assert status_payload["mapping_count"] == 0
    assert status_payload["connector_count"] == 0

    assert questions.returncode == 0
    question_payload = output_json(questions)["data"]
    assert question_payload["question_count"] == 2
    assert {item["topic"] for item in question_payload["questions"]} == {"business"}
    assert question_payload["writes_performed"] is False


def test_intake_record_persists_provenance_and_advances_questions(tmp_path):
    assert run_cli("init", str(tmp_path), "--business-name", "Acme").returncode == 0

    result = run_cli(
        "intake-record",
        str(tmp_path),
        "--key",
        "business_model",
        "--answer",
        "Commercial coffee roasting",
        "--source-type",
        "local_file",
        "--source",
        "company-data/overview.md",
        "--confidence",
        "0.9",
    )

    assert result.returncode == 0
    payload = output_json(result)["data"]
    assert payload["fact"]["status"] == "inferred"
    assert payload["fact"]["sources"] == ["company-data/overview.md"]
    questions = output_json(run_cli("intake-next", str(tmp_path)))["data"]["questions"]
    assert all(question["key"] != "business_model" for question in questions)


def test_entrypoint_register_list_and_overwrite(tmp_path):
    assert run_cli("init", str(tmp_path)).returncode == 0
    args = (
        "entrypoint-register",
        str(tmp_path),
        "--name",
        "forecast",
        "--kind",
        "forecast",
        "--description",
        "Run the generated monthly forecast.",
        "--command-json",
        '["python3", "models/generated/forecast.py"]',
        "--input",
        "data/actuals.csv",
        "--output",
        "output/forecast.xlsx",
    )

    registered = run_cli(*args)
    duplicate = run_cli(*args)
    overwritten = run_cli(*args, "--overwrite")
    listed = run_cli("entrypoint-list", str(tmp_path), "--kind", "forecast")

    assert registered.returncode == 0
    assert duplicate.returncode == 1
    assert output_json(duplicate)["error"]["type"] == "invalid_entrypoint"
    assert overwritten.returncode == 0
    assert listed.returncode == 0
    entrypoints = output_json(listed)["data"]["entrypoints"]
    assert entrypoints == [{
        "command": ["python3", "models/generated/forecast.py"],
        "description": "Run the generated monthly forecast.",
        "inputs": ["data/actuals.csv"],
        "kind": "forecast",
        "name": "forecast",
        "outputs": ["output/forecast.xlsx"],
        "working_directory": ".",
    }]


def test_entrypoint_register_rejects_unsafe_paths(tmp_path):
    assert run_cli("init", str(tmp_path)).returncode == 0

    result = run_cli(
        "entrypoint-register",
        str(tmp_path),
        "--name",
        "forecast",
        "--kind",
        "forecast",
        "--description",
        "Run forecast.",
        "--command-json",
        '["python3", "forecast.py"]',
        "--output",
        "../outside.xlsx",
    )

    assert result.returncode == 1
    assert output_json(result)["error"]["type"] == "invalid_entrypoint"


def test_source_mapping_profile_and_reconciliation_commands(tmp_path):
    assert run_cli("init", str(tmp_path)).returncode == 0
    data = tmp_path / "data"
    data.mkdir()
    (data / "actuals.csv").write_text(
        "Account,Amount\nProduct Revenue,100\nRent,(20)\n"
    )

    source_result = run_cli(
        "source-register",
        str(tmp_path),
        "--source-id",
        "gl-actuals",
        "--kind",
        "local_file",
        "--location",
        "data/actuals.csv",
        "--entity",
        "Acme",
        "--currency",
        "USD",
        "--period",
        "2026-01",
        "--extraction-method",
        "Manual export",
    )
    assert source_result.returncode == 0

    for source_value, target in (
        ("Product Revenue", "revenue"),
        ("Rent", "opex"),
    ):
        result = run_cli(
            "mapping-register",
            str(tmp_path),
            "--source-id",
            "gl-actuals",
            "--source-value",
            source_value,
            "--target",
            target,
        )
        assert result.returncode == 0

    profile = run_cli(
        "source-profile",
        str(tmp_path),
        "--file",
        "data/actuals.csv",
    )
    reconciled = run_cli(
        "reconcile-source",
        str(tmp_path),
        "--source-id",
        "gl-actuals",
        "--expected-json",
        '{"revenue": 100, "opex": -20}',
    )

    assert profile.returncode == 0
    assert output_json(profile)["data"]["rows"] == 2
    assert reconciled.returncode == 0
    assert output_json(reconciled)["data"]["mapped_total"] == 80.0
    assert output_json(run_cli("source-list", str(tmp_path)))["data"]["source_count"] == 1
    assert output_json(run_cli("mapping-list", str(tmp_path)))["data"]["mapping_count"] == 2


def test_reconcile_source_fails_for_unmapped_accounts(tmp_path):
    assert run_cli("init", str(tmp_path)).returncode == 0
    (tmp_path / "actuals.csv").write_text("Account,Amount\nMystery,10\n")
    assert run_cli(
        "source-register",
        str(tmp_path),
        "--source-id",
        "gl-actuals",
        "--kind",
        "local_file",
        "--location",
        "actuals.csv",
        "--entity",
        "Acme",
        "--currency",
        "USD",
        "--extraction-method",
        "Manual export",
    ).returncode == 0

    result = run_cli("reconcile-source", str(tmp_path), "--source-id", "gl-actuals")

    assert result.returncode == 1
    payload = output_json(result)
    assert payload["data"]["unmapped"] == ["Mystery"]
    assert payload["error"]["type"] == "reconciliation_failed"


def test_reconcile_source_requires_initialized_workspace(tmp_path):
    result = run_cli(
        "reconcile-source",
        str(tmp_path),
        "--source-id",
        "gl-actuals",
    )

    assert result.returncode == 1
    assert output_json(result)["error"]["type"] == "workspace_not_initialized"


def test_connector_scaffold_list_and_validate(tmp_path):
    assert run_cli("init", str(tmp_path)).returncode == 0
    fixture = tmp_path / "redacted.csv"
    fixture.write_text("Account,Amount\nProduct Revenue,100\nRent,(20)\n")
    assert run_cli(
        "source-register",
        str(tmp_path),
        "--source-id",
        "gl-actuals",
        "--kind",
        "accounting_system",
        "--location",
        "quickbooks",
        "--entity",
        "Acme",
        "--currency",
        "USD",
        "--period",
        "2026-05",
        "--extraction-method",
        "QuickBooks P&L report",
    ).returncode == 0
    for source_value, target in (
        ("Product Revenue", "revenue.product"),
        ("Rent", "opex.rent"),
    ):
        assert run_cli(
            "mapping-register",
            str(tmp_path),
            "--source-id",
            "gl-actuals",
            "--source-value",
            source_value,
            "--target",
            target,
        ).returncode == 0

    scaffolded = run_cli(
        "connector-scaffold",
        str(tmp_path),
        "--name",
        "quickbooks-pl",
        "--source-id",
        "gl-actuals",
        "--description",
        "Pull and normalize the monthly P&L.",
        "--auth-method",
        "host_environment",
        "--fixture",
        "redacted.csv",
    )
    listed = run_cli("connector-list", str(tmp_path))
    validated = run_cli(
        "connector-validate",
        str(tmp_path),
        "--name",
        "quickbooks-pl",
    )

    assert scaffolded.returncode == 0, scaffolded.stdout
    assert listed.returncode == 0
    assert validated.returncode == 0, validated.stdout
    assert output_json(listed)["data"]["connector_count"] == 1
    assert output_json(validated)["data"]["reconciliation"]["passed"] is True
    status = output_json(run_cli("status", str(tmp_path)))["data"]
    assert status["connector_count"] == 1
    assert status["connectors"] == ["quickbooks-pl"]


def test_connector_scaffold_rejects_unmapped_fixture(tmp_path):
    assert run_cli("init", str(tmp_path)).returncode == 0
    (tmp_path / "redacted.csv").write_text("Account,Amount\nMystery,10\n")
    assert run_cli(
        "source-register",
        str(tmp_path),
        "--source-id",
        "gl-actuals",
        "--kind",
        "accounting_system",
        "--location",
        "quickbooks",
        "--entity",
        "Acme",
        "--currency",
        "USD",
        "--extraction-method",
        "QuickBooks P&L report",
    ).returncode == 0

    result = run_cli(
        "connector-scaffold",
        str(tmp_path),
        "--name",
        "quickbooks-pl",
        "--source-id",
        "gl-actuals",
        "--description",
        "Pull and normalize the monthly P&L.",
        "--auth-method",
        "host_environment",
        "--fixture",
        "redacted.csv",
    )

    assert result.returncode == 1
    assert output_json(result)["error"]["type"] == "connector_scaffold_failed"
    assert not (tmp_path / "connectors" / "generated" / "quickbooks-pl").exists()


def test_doctor_returns_nonzero_json_when_workspace_contract_is_broken(tmp_path):
    healthy = run_cli("init", str(tmp_path))
    assert healthy.returncode == 0
    assert run_cli("doctor", str(tmp_path)).returncode == 0

    (tmp_path / ".fpa" / "models" / "registry.yaml").write_text("not: [valid")
    broken = run_cli("doctor", str(tmp_path))

    assert broken.returncode == 1
    payload = output_json(broken)
    assert payload["ok"] is False
    assert payload["error"]["type"] == "diagnostic_failure"
    assert payload["data"]["healthy"] is False
    assert any(
        check["name"] == "model_registry" and check["result"] == "error"
        for check in payload["data"]["checks"]
    )


def test_doctor_requires_entrypoint_registry(tmp_path):
    assert run_cli("init", str(tmp_path)).returncode == 0
    (tmp_path / ".fpa" / "models" / "entrypoints.yaml").unlink()

    result = run_cli("doctor", str(tmp_path))

    assert result.returncode == 1
    payload = output_json(result)
    assert any(
        check["name"] == "entrypoint_registry" and check["result"] == "error"
        for check in payload["data"]["checks"]
    )


def test_doctor_requires_lineage_registries(tmp_path):
    assert run_cli("init", str(tmp_path)).returncode == 0
    (tmp_path / ".fpa" / "sources" / "registry.yaml").unlink()
    (tmp_path / ".fpa" / "mappings" / "registry.yaml").unlink()

    result = run_cli("doctor", str(tmp_path))

    assert result.returncode == 1
    payload = output_json(result)
    failed = {
        check["name"] for check in payload["data"]["checks"]
        if check["result"] == "error"
    }
    assert {"source_registry", "mapping_registry"} <= failed


def test_doctor_rejects_invalid_generated_connector_manifest(tmp_path):
    assert run_cli("init", str(tmp_path)).returncode == 0
    bundle = tmp_path / "connectors" / "generated" / "broken"
    bundle.mkdir(parents=True)
    (bundle / "connector.yaml").write_text("not: [valid")

    result = run_cli("doctor", str(tmp_path))

    assert result.returncode == 1
    payload = output_json(result)
    assert any(
        check["name"] == "generated_connector_contracts"
        and check["result"] == "error"
        for check in payload["data"]["checks"]
    )


def test_usage_errors_are_json_on_stderr(tmp_path):
    result = run_cli("inspect-data", str(tmp_path), "--max-files", "0")

    assert result.returncode == 2
    assert result.stdout == ""
    payload = json.loads(result.stderr)
    assert payload["ok"] is False
    assert payload["error"]["type"] == "usage_error"


def test_correction_record_and_list(tmp_path):
    assert run_cli("init", str(tmp_path)).returncode == 0

    result = run_cli(
        "correction-record",
        str(tmp_path),
        "--slug", "2026-06-09-dio-lag",
        "--type", "parametric",
        "--target", "working_capital.dio_days",
        "--status", "open",
        "--date", "2026-06-09",
        "--notes", "DIO is 45 days not 30.",
    )

    assert result.returncode == 0, result.stdout
    payload = output_json(result)["data"]
    assert payload["slug"] == "2026-06-09-dio-lag"
    assert payload["type"] == "parametric"
    assert (tmp_path / ".fpa" / "corrections" / "2026-06-09-dio-lag.md").exists()

    listed = run_cli("correction-list", str(tmp_path))

    assert listed.returncode == 0
    ldata = output_json(listed)["data"]
    assert ldata["correction_count"] == 1
    assert ldata["corrections"][0]["slug"] == "2026-06-09-dio-lag"
    assert ldata["corrections"][0]["status"] == "open"


def test_correction_record_with_override(tmp_path):
    assert run_cli("init", str(tmp_path)).returncode == 0

    result = run_cli(
        "correction-record",
        str(tmp_path),
        "--slug", "2026-06-09-dio-override",
        "--type", "parametric",
        "--target", "working_capital.dio_days",
        "--status", "applied",
        "--date", "2026-06-09",
        "--override-path", "working_capital.dio_days",
        "--override-value", "45.0",
    )

    assert result.returncode == 0
    payload = output_json(result)["data"]
    assert payload["override"] == {"path": "working_capital.dio_days", "value": 45.0}


def test_scorecard_render_empty_workspace(tmp_path):
    assert run_cli("init", str(tmp_path)).returncode == 0

    result = run_cli("scorecard-render", str(tmp_path))

    assert result.returncode == 0, result.stdout
    payload = output_json(result)["data"]
    assert payload["scored_count"] == 0
    assert payload["unscored_count"] == 0
    assert (tmp_path / ".fpa" / "scorecard.md").exists()


def test_scorecard_render_writes_table_for_scored_snapshots(tmp_path):
    import yaml
    assert run_cli("init", str(tmp_path)).returncode == 0
    forecasts = tmp_path / ".fpa" / "forecasts"
    forecasts.mkdir(exist_ok=True)
    snap = {
        "label": "2026-01",
        "created": "2026-02-01",
        "assumptions": {},
        "predicted": {},
        "score": {
            "fitness": 0.05,
            "per_line": {"revenue": 0.02},
            "weights": {},
        },
    }
    (forecasts / "2026-01.snapshot.yaml").write_text(yaml.safe_dump(snap))

    result = run_cli("scorecard-render", str(tmp_path))

    assert result.returncode == 0
    payload = output_json(result)["data"]
    assert payload["scored_count"] == 1
    scorecard_text = (tmp_path / ".fpa" / "scorecard.md").read_text()
    assert "2026-01" in scorecard_text


def test_experiment_list_empty(tmp_path):
    assert run_cli("init", str(tmp_path)).returncode == 0

    result = run_cli("experiment-list", str(tmp_path))

    assert result.returncode == 0, result.stdout
    payload = output_json(result)["data"]
    assert payload["experiment_count"] == 0
    assert payload["experiments"] == []


def test_experiment_list_with_experiments(tmp_path):
    import yaml
    assert run_cli("init", str(tmp_path)).returncode == 0
    experiments_dir = tmp_path / ".fpa" / "experiments"
    experiments_dir.mkdir(exist_ok=True)
    exp = {
        "schema_version": 1,
        "slug": "2026-06-09-dio-lag",
        "created": "2026-06-09",
        "status": "draft",
        "hypothesis": "DIO is 45 days.",
        "snapshot": None,
        "cfo_question": "",
        "rationale": "",
        "evidence": [],
        "training_periods": [],
        "holdout_periods": [],
        "files_changed": [],
        "metrics_before": {},
        "metrics_after": {},
        "checks": [],
        "decision": None,
    }
    (experiments_dir / "2026-06-09-dio-lag.experiment.yaml").write_text(yaml.safe_dump(exp))

    result = run_cli("experiment-list", str(tmp_path))

    assert result.returncode == 0
    payload = output_json(result)["data"]
    assert payload["experiment_count"] == 1
    first = payload["experiments"][0]
    assert first["slug"] == "2026-06-09-dio-lag"
    assert first["status"] == "draft"
    assert first["snapshot"] is None


def test_context_pack_returns_markdown(tmp_path):
    assert run_cli("init", str(tmp_path), "--business-name", "Acme").returncode == 0

    result = run_cli(
        "context-pack",
        str(tmp_path),
        "--task", "review cash forecast assumptions",
    )

    assert result.returncode == 0, result.stdout
    payload = output_json(result)["data"]
    assert "# Task Memory Pack" in payload["pack"]
    assert payload["hit_count"] >= 0


def test_context_pack_respects_limit(tmp_path):
    assert run_cli("init", str(tmp_path), "--business-name", "Acme").returncode == 0

    result = run_cli(
        "context-pack",
        str(tmp_path),
        "--task", "forecast revenue",
        "--limit", "2",
    )

    assert result.returncode == 0
    payload = output_json(result)["data"]
    assert payload["hit_count"] <= 2


def test_onboarding_render_requires_ready_intake(tmp_path):
    assert run_cli("init", str(tmp_path), "--business-name", "Acme").returncode == 0

    result = run_cli(
        "onboarding-render",
        str(tmp_path),
        "--proposal-summary", "Build a driver-based forecast.",
    )

    assert result.returncode == 1
    payload = output_json(result)
    assert payload["error"]["type"] == "onboarding_render_failed"


def test_onboarding_render_writes_profile_and_proposal(tmp_path):
    from pyfpa.memory.intake import (
        load_intake,
        next_intake_questions,
        record_intake_fact,
        save_intake,
    )
    from pyfpa.memory.workspace import workspace_path

    assert run_cli("init", str(tmp_path), "--business-name", "Acme").returncode == 0
    workspace = workspace_path(tmp_path)
    intake_path = workspace / "intake.md"
    intake = load_intake(intake_path)
    while questions := next_intake_questions(intake):
        for q in questions:
            intake = record_intake_fact(
                intake, key=q.key, answer=f"Known {q.key}",
                source_type="user", sources=["CFO interview"],
            )
    save_intake(intake, intake_path)

    result = run_cli(
        "onboarding-render",
        str(tmp_path),
        "--proposal-summary", "Build a driver-based forecast.",
        "--connector", "QuickBooks P&L",
        "--model-component", "Channel revenue model",
    )

    assert result.returncode == 0, result.stdout
    payload = output_json(result)["data"]
    assert payload["profile_path"].endswith("business-profile.md")
    assert payload["proposal_path"].endswith("initial-model-architecture.md")
    assert (tmp_path / ".fpa" / "business-profile.md").exists()
    assert (tmp_path / ".fpa" / "decisions" / "initial-model-architecture.md").exists()
