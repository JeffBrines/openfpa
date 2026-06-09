from __future__ import annotations

import argparse
import json
import sys
from collections.abc import Callable, Sequence
from pathlib import Path
from typing import Any

from pyfpa.memory.diagnostics import WorkspaceReport, validate_workspace
from pyfpa.memory.entrypoints import (
    CompanyEntrypoint,
    load_entrypoint_registry,
    register_entrypoint,
    save_entrypoint_registry,
)
from pyfpa.memory.connectors import (
    connector_bundle_path,
    load_connector_manifests,
    scaffold_connector_bundle,
    validate_connector_bundle,
)
from pyfpa.memory.inspection import InspectionResult, inspect_data_files
from pyfpa.memory.intake import (
    intake_ready,
    load_intake,
    next_intake_questions,
    record_intake_fact,
    save_intake,
)
from pyfpa.memory.lineage import (
    MappingRule,
    SourceRecord,
    load_mapping_registry,
    load_source_registry,
    profile_table,
    reconcile_account_table,
    register_mapping,
    register_source,
    save_mapping_registry,
    save_source_registry,
)
from pyfpa.memory.workspace import WORKSPACE_DIRS, initialize_workspace, workspace_path
from pyfpa.research.objective import load_research_objective
from pyfpa.research.registry import load_model_registry


SCHEMA_VERSION = 1
EXIT_OK = 0
EXIT_FAILED = 1
EXIT_USAGE = 2


class JsonArgumentParser(argparse.ArgumentParser):
    def error(self, message: str) -> None:
        _write_json(
            {
                "schema_version": SCHEMA_VERSION,
                "command": "usage",
                "ok": False,
                "error": {"type": "usage_error", "message": message},
            },
            stream=sys.stderr,
        )
        raise SystemExit(EXIT_USAGE)


def _write_json(payload: dict[str, Any], *, stream: Any = sys.stdout) -> None:
    stream.write(json.dumps(payload, indent=2, sort_keys=True) + "\n")


def _success(command: str, root: Path, data: dict[str, Any]) -> int:
    _write_json(
        {
            "schema_version": SCHEMA_VERSION,
            "command": command,
            "ok": True,
            "root": str(root),
            "data": data,
        }
    )
    return EXIT_OK


def _failure(
    command: str,
    root: Path,
    error_type: str,
    message: str,
    *,
    data: dict[str, Any] | None = None,
) -> int:
    payload: dict[str, Any] = {
        "schema_version": SCHEMA_VERSION,
        "command": command,
        "ok": False,
        "root": str(root),
        "error": {"type": error_type, "message": message},
    }
    if data is not None:
        payload["data"] = data
    _write_json(payload)
    return EXIT_FAILED


def _root(path: str) -> Path:
    return Path(path).expanduser().resolve()


def _workspace_counts(workspace: Path) -> dict[str, int]:
    return {
        directory: sum(1 for path in (workspace / directory).glob("*") if path.is_file())
        for directory in WORKSPACE_DIRS
        if (workspace / directory).is_dir()
    }


def command_init(args: argparse.Namespace) -> int:
    root = _root(args.path)
    root.mkdir(parents=True, exist_ok=True)
    existed = workspace_path(root).exists()
    business_name = args.business_name or root.name or "Company"
    workspace = initialize_workspace(root, business_name=business_name)
    return _success(
        "init",
        root,
        {
            "workspace": str(workspace),
            "created": not existed,
            "business_name": load_intake(workspace / "intake.md").business_name,
            "next_command": f"python3 -m pyfpa.cli inspect-data {json.dumps(str(root))}",
        },
    )


def command_inspect_data(args: argparse.Namespace) -> int:
    root = _root(args.path)
    if not root.is_dir():
        return _failure("inspect-data", root, "path_not_found", "inspection path is not a directory")
    result = inspect_data_files(root, max_files=args.max_files)
    return _success(
        "inspect-data",
        root,
        {
            "files": result.files,
            "file_count": result.file_count,
            "category_counts": result.category_counts,
            "missing_priority_categories": result.missing_priority_categories,
            "truncated": result.truncated,
            "max_files": result.max_files,
            "writes_performed": False,
        },
    )


def command_status(args: argparse.Namespace) -> int:
    root = _root(args.path)
    workspace = workspace_path(root)
    if not workspace.is_dir():
        return _success(
            "status",
            root,
            {
                "initialized": False,
                "workspace": str(workspace),
                "next_command": f"python3 -m pyfpa.cli init {json.dumps(str(root))}",
            },
        )
    try:
        intake = load_intake(workspace / "intake.md")
        registry = load_model_registry(workspace / "models" / "registry.yaml")
        entrypoints = load_entrypoint_registry(
            workspace / "models" / "entrypoints.yaml"
        )
        sources = load_source_registry(workspace / "sources" / "registry.yaml")
        mappings = load_mapping_registry(workspace / "mappings" / "registry.yaml")
        connectors = load_connector_manifests(root)
    except Exception as exc:
        return _failure("status", root, "invalid_workspace", str(exc))
    facts_by_status: dict[str, int] = {}
    for fact in intake.facts:
        facts_by_status[fact.status] = facts_by_status.get(fact.status, 0) + 1
    questions = next_intake_questions(intake)
    return _success(
        "status",
        root,
        {
            "initialized": True,
            "workspace": str(workspace),
            "business_name": intake.business_name,
            "intake_ready": intake_ready(intake),
            "fact_count": len(intake.facts),
            "facts_by_status": facts_by_status,
            "next_question_count": len(questions),
            "next_question_topic": questions[0].topic if questions else None,
            "business_profile_exists": (workspace / "business-profile.md").exists(),
            "architecture_proposal_exists": (
                workspace / "decisions" / "initial-model-architecture.md"
            ).exists(),
            "champion": registry.champion.model_id if registry.champion else None,
            "challenger_count": len(registry.challengers),
            "promotion_count": len(registry.promotions),
            "entrypoint_count": len(entrypoints.entrypoints),
            "entrypoints": [item.name for item in entrypoints.entrypoints],
            "source_count": len(sources.sources),
            "mapping_count": len(mappings.mappings),
            "connector_count": len(connectors),
            "connectors": [item.name for item in connectors],
            "artifact_counts": _workspace_counts(workspace),
        },
    )


def command_intake_next(args: argparse.Namespace) -> int:
    root = _root(args.path)
    intake_path = workspace_path(root) / "intake.md"
    if not intake_path.exists():
        return _failure(
            "intake-next",
            root,
            "workspace_not_initialized",
            "initialize the company workspace before requesting intake questions",
        )
    try:
        intake = load_intake(intake_path)
        questions = next_intake_questions(intake, limit=args.limit)
    except Exception as exc:
        return _failure("intake-next", root, "invalid_intake", str(exc))
    return _success(
        "intake-next",
        root,
        {
            "business_name": intake.business_name,
            "intake_ready": intake_ready(intake),
            "questions": [question.model_dump() for question in questions],
            "question_count": len(questions),
            "writes_performed": False,
        },
    )


def command_intake_record(args: argparse.Namespace) -> int:
    root = _root(args.path)
    intake_path = workspace_path(root) / "intake.md"
    if not intake_path.exists():
        return _failure(
            "intake-record",
            root,
            "workspace_not_initialized",
            "initialize the company workspace before recording intake facts",
        )
    try:
        intake = load_intake(intake_path)
        intake = record_intake_fact(
            intake,
            key=args.key,
            answer=args.answer,
            source_type=args.source_type,
            sources=args.source,
            confidence=args.confidence,
            topic=args.topic,
            question=args.question,
        )
        save_intake(intake, intake_path)
        fact = next(item for item in intake.facts if item.key == args.key)
        questions = next_intake_questions(intake)
    except Exception as exc:
        return _failure("intake-record", root, "invalid_intake_fact", str(exc))
    return _success(
        "intake-record",
        root,
        {
            "fact": fact.model_dump(),
            "intake_ready": intake_ready(intake),
            "next_question_count": len(questions),
            "next_question_topic": questions[0].topic if questions else None,
            "intake_path": str(intake_path),
        },
    )


def _entrypoint_registry_path(root: Path) -> Path:
    return workspace_path(root) / "models" / "entrypoints.yaml"


def _command_from_json(value: str) -> list[str]:
    command = json.loads(value)
    if (
        not isinstance(command, list)
        or not command
        or any(not isinstance(item, str) for item in command)
    ):
        raise ValueError("--command-json must be a non-empty JSON array of strings")
    return command


def command_entrypoint_register(args: argparse.Namespace) -> int:
    root = _root(args.path)
    registry_path = _entrypoint_registry_path(root)
    if not workspace_path(root).is_dir():
        return _failure(
            "entrypoint-register",
            root,
            "workspace_not_initialized",
            "initialize the company workspace before registering entrypoints",
        )
    try:
        entrypoint = CompanyEntrypoint(
            name=args.name,
            kind=args.kind,
            description=args.description,
            command=_command_from_json(args.command_json),
            working_directory=args.working_directory,
            inputs=args.input,
            outputs=args.output,
        )
        registry = register_entrypoint(
            load_entrypoint_registry(registry_path),
            entrypoint,
            overwrite=args.overwrite,
        )
        save_entrypoint_registry(registry, registry_path)
    except Exception as exc:
        return _failure(
            "entrypoint-register",
            root,
            "invalid_entrypoint",
            str(exc),
        )
    return _success(
        "entrypoint-register",
        root,
        {
            "entrypoint": entrypoint.model_dump(),
            "registry_path": str(registry_path),
            "entrypoint_count": len(registry.entrypoints),
        },
    )


def command_entrypoint_list(args: argparse.Namespace) -> int:
    root = _root(args.path)
    registry_path = _entrypoint_registry_path(root)
    if not workspace_path(root).is_dir():
        return _failure(
            "entrypoint-list",
            root,
            "workspace_not_initialized",
            "initialize the company workspace before listing entrypoints",
        )
    try:
        registry = load_entrypoint_registry(registry_path)
    except Exception as exc:
        return _failure("entrypoint-list", root, "invalid_entrypoint_registry", str(exc))
    entrypoints = [
        item for item in registry.entrypoints
        if args.kind is None or item.kind == args.kind
    ]
    return _success(
        "entrypoint-list",
        root,
        {
            "entrypoints": [item.model_dump() for item in entrypoints],
            "entrypoint_count": len(entrypoints),
            "registry_path": str(registry_path),
            "writes_performed": False,
        },
    )


def _source_registry_path(root: Path) -> Path:
    return workspace_path(root) / "sources" / "registry.yaml"


def _mapping_registry_path(root: Path) -> Path:
    return workspace_path(root) / "mappings" / "registry.yaml"


def command_source_register(args: argparse.Namespace) -> int:
    root = _root(args.path)
    registry_path = _source_registry_path(root)
    if not workspace_path(root).is_dir():
        return _failure(
            "source-register",
            root,
            "workspace_not_initialized",
            "initialize the company workspace before registering sources",
        )
    try:
        source = SourceRecord(
            source_id=args.source_id,
            kind=args.kind,
            location=args.location,
            entity=args.entity,
            currency=args.currency,
            periods=args.period,
            extraction_method=args.extraction_method,
            refreshed_at=args.refreshed_at,
            notes=args.notes,
        )
        registry = register_source(
            load_source_registry(registry_path),
            source,
            overwrite=args.overwrite,
        )
        save_source_registry(registry, registry_path)
    except Exception as exc:
        return _failure("source-register", root, "invalid_source", str(exc))
    return _success(
        "source-register",
        root,
        {
            "source": source.model_dump(),
            "registry_path": str(registry_path),
            "source_count": len(registry.sources),
        },
    )


def command_source_list(args: argparse.Namespace) -> int:
    root = _root(args.path)
    registry_path = _source_registry_path(root)
    if not workspace_path(root).is_dir():
        return _failure(
            "source-list",
            root,
            "workspace_not_initialized",
            "initialize the company workspace before listing sources",
        )
    try:
        registry = load_source_registry(registry_path)
    except Exception as exc:
        return _failure("source-list", root, "invalid_source_registry", str(exc))
    sources = [
        source for source in registry.sources
        if args.kind is None or source.kind == args.kind
    ]
    return _success(
        "source-list",
        root,
        {
            "sources": [source.model_dump() for source in sources],
            "source_count": len(sources),
            "registry_path": str(registry_path),
            "writes_performed": False,
        },
    )


def command_source_profile(args: argparse.Namespace) -> int:
    root = _root(args.path)
    file_path = Path(args.file).expanduser()
    if not file_path.is_absolute():
        file_path = root / file_path
    try:
        profile = profile_table(file_path.resolve())
    except Exception as exc:
        return _failure("source-profile", root, "profile_failed", str(exc))
    return _success(
        "source-profile",
        root,
        {**profile, "writes_performed": False},
    )


def command_mapping_register(args: argparse.Namespace) -> int:
    root = _root(args.path)
    registry_path = _mapping_registry_path(root)
    if not workspace_path(root).is_dir():
        return _failure(
            "mapping-register",
            root,
            "workspace_not_initialized",
            "initialize the company workspace before registering mappings",
        )
    try:
        sources = load_source_registry(_source_registry_path(root))
        if not any(source.source_id == args.source_id for source in sources.sources):
            raise ValueError(f"source is not registered: {args.source_id}")
        mapping = MappingRule(
            source_id=args.source_id,
            source_value=args.source_value,
            target=args.target,
            status=args.status,
            rationale=args.rationale,
        )
        registry = register_mapping(
            load_mapping_registry(registry_path),
            mapping,
            overwrite=args.overwrite,
        )
        save_mapping_registry(registry, registry_path)
    except Exception as exc:
        return _failure("mapping-register", root, "invalid_mapping", str(exc))
    return _success(
        "mapping-register",
        root,
        {
            "mapping": mapping.model_dump(),
            "registry_path": str(registry_path),
            "mapping_count": len(registry.mappings),
        },
    )


def command_mapping_list(args: argparse.Namespace) -> int:
    root = _root(args.path)
    registry_path = _mapping_registry_path(root)
    if not workspace_path(root).is_dir():
        return _failure(
            "mapping-list",
            root,
            "workspace_not_initialized",
            "initialize the company workspace before listing mappings",
        )
    try:
        registry = load_mapping_registry(registry_path)
    except Exception as exc:
        return _failure("mapping-list", root, "invalid_mapping_registry", str(exc))
    mappings = [
        mapping for mapping in registry.mappings
        if (args.source_id is None or mapping.source_id == args.source_id)
        and (args.status is None or mapping.status == args.status)
    ]
    return _success(
        "mapping-list",
        root,
        {
            "mappings": [mapping.model_dump() for mapping in mappings],
            "mapping_count": len(mappings),
            "registry_path": str(registry_path),
            "writes_performed": False,
        },
    )


def _expected_from_json(value: str | None) -> dict[str, float] | None:
    if value is None:
        return None
    expected = json.loads(value)
    if not isinstance(expected, dict) or any(
        not isinstance(key, str) or not isinstance(amount, (int, float))
        for key, amount in expected.items()
    ):
        raise ValueError("--expected-json must be a JSON object of numeric totals")
    return {key: float(amount) for key, amount in expected.items()}


def command_reconcile_source(args: argparse.Namespace) -> int:
    root = _root(args.path)
    if not workspace_path(root).is_dir():
        return _failure(
            "reconcile-source",
            root,
            "workspace_not_initialized",
            "initialize the company workspace before reconciling sources",
        )
    try:
        source_registry = load_source_registry(_source_registry_path(root))
        source = next(
            item for item in source_registry.sources
            if item.source_id == args.source_id
        )
        file_path = Path(args.file or source.location).expanduser()
        if not file_path.is_absolute():
            file_path = root / file_path
        result = reconcile_account_table(
            file_path.resolve(),
            source_id=args.source_id,
            mappings=load_mapping_registry(_mapping_registry_path(root)),
            account_column=args.account_column,
            amount_column=args.amount_column,
            expected=_expected_from_json(args.expected_json),
            tolerance=args.tolerance,
        )
        if args.allow_unmapped and not result["duplicates"]:
            expected_passed = all(
                item["within_tolerance"] for item in result["variances"].values()
            ) if result["expected_provided"] else True
            result["passed"] = expected_passed
    except StopIteration:
        return _failure(
            "reconcile-source",
            root,
            "source_not_found",
            f"source is not registered: {args.source_id}",
        )
    except Exception as exc:
        return _failure("reconcile-source", root, "reconciliation_failed", str(exc))
    if not result["passed"]:
        return _failure(
            "reconcile-source",
            root,
            "reconciliation_failed",
            "source contains duplicates, unmapped values, or out-of-tolerance totals",
            data=result,
        )
    return _success("reconcile-source", root, result)


def command_connector_scaffold(args: argparse.Namespace) -> int:
    root = _root(args.path)
    if not workspace_path(root).is_dir():
        return _failure(
            "connector-scaffold",
            root,
            "workspace_not_initialized",
            "initialize the company workspace before scaffolding connectors",
        )
    fixture = Path(args.fixture).expanduser()
    if not fixture.is_absolute():
        fixture = root / fixture
    try:
        sources = load_source_registry(_source_registry_path(root))
        if not any(source.source_id == args.source_id for source in sources.sources):
            raise ValueError(f"source is not registered: {args.source_id}")
        manifest, reconciliation = scaffold_connector_bundle(
            root,
            name=args.name,
            source_id=args.source_id,
            description=args.description,
            auth_method=args.auth_method,
            fixture=fixture.resolve(),
            account_column=args.account_column,
            amount_column=args.amount_column,
            mappings=load_mapping_registry(_mapping_registry_path(root)),
            overwrite=args.overwrite,
        )
    except Exception as exc:
        return _failure(
            "connector-scaffold",
            root,
            "connector_scaffold_failed",
            str(exc),
        )
    return _success(
        "connector-scaffold",
        root,
        {
            "manifest": manifest.model_dump(),
            "bundle_path": str(connector_bundle_path(root, manifest.name)),
            "fixture_reconciliation": reconciliation,
            "next_command": (
                f"python3 -m pyfpa.cli connector-validate {json.dumps(str(root))} "
                f"--name {manifest.name}"
            ),
        },
    )


def command_connector_list(args: argparse.Namespace) -> int:
    root = _root(args.path)
    if not workspace_path(root).is_dir():
        return _failure(
            "connector-list",
            root,
            "workspace_not_initialized",
            "initialize the company workspace before listing connectors",
        )
    try:
        manifests = [
            manifest
            for manifest in load_connector_manifests(root)
            if args.source_id is None or manifest.source_id == args.source_id
        ]
    except Exception as exc:
        return _failure(
            "connector-list",
            root,
            "invalid_connector_manifest",
            str(exc),
        )
    return _success(
        "connector-list",
        root,
        {
            "connectors": [manifest.model_dump() for manifest in manifests],
            "connector_count": len(manifests),
            "writes_performed": False,
        },
    )


def command_connector_validate(args: argparse.Namespace) -> int:
    root = _root(args.path)
    if not workspace_path(root).is_dir():
        return _failure(
            "connector-validate",
            root,
            "workspace_not_initialized",
            "initialize the company workspace before validating connectors",
        )
    try:
        result = validate_connector_bundle(
            root,
            name=args.name,
            mappings=load_mapping_registry(_mapping_registry_path(root)),
            timeout=args.timeout,
        )
    except Exception as exc:
        return _failure(
            "connector-validate",
            root,
            "connector_validation_failed",
            str(exc),
        )
    if not result["passed"]:
        return _failure(
            "connector-validate",
            root,
            "connector_validation_failed",
            "connector fixture output failed reconciliation",
            data=result,
        )
    return _success("connector-validate", root, result)


def command_doctor(args: argparse.Namespace) -> int:
    root = _root(args.path)
    report = validate_workspace(root)
    payload = {
        "healthy": report.healthy,
        "checks": report.checks,
        "error_count": report.error_count,
        "warning_count": report.warning_count,
    }
    if not report.healthy:
        return _failure(
            "doctor",
            root,
            "diagnostic_failure",
            f"{report.error_count} diagnostic check(s) failed",
            data=payload,
        )
    return _success("doctor", root, payload)


def command_correction_record(args: argparse.Namespace) -> int:
    from pyfpa.memory.corrections import Correction, Override, save_correction

    root = _root(args.path)
    workspace = workspace_path(root)
    if not workspace.is_dir():
        return _failure(
            "correction-record",
            root,
            "workspace_not_initialized",
            "initialize the company workspace before recording corrections",
        )
    try:
        override = None
        if args.override_path is not None:
            override = Override(path=args.override_path, value=args.override_value)
        correction = Correction(
            slug=args.slug,
            type=args.type,
            target=args.target,
            status=args.status,
            date=args.date,
            override=override,
            notes=args.notes or "",
        )
        save_correction(correction, workspace / "corrections")
    except Exception as exc:
        return _failure("correction-record", root, "invalid_correction", str(exc))
    return _success(
        "correction-record",
        root,
        {
            "slug": correction.slug,
            "type": correction.type,
            "target": correction.target,
            "status": correction.status,
            "date": correction.date,
            "override": correction.override.model_dump() if correction.override else None,
            "corrections_dir": str(workspace / "corrections"),
        },
    )


def command_correction_list(args: argparse.Namespace) -> int:
    from pyfpa.memory.corrections import load_corrections

    root = _root(args.path)
    workspace = workspace_path(root)
    if not workspace.is_dir():
        return _failure(
            "correction-list",
            root,
            "workspace_not_initialized",
            "initialize the company workspace before listing corrections",
        )
    try:
        corrections = load_corrections(workspace / "corrections")
    except Exception as exc:
        return _failure("correction-list", root, "invalid_correction", str(exc))
    filtered = [
        c for c in corrections
        if args.status is None or c.status == args.status
    ]
    return _success(
        "correction-list",
        root,
        {
            "corrections": [
                {"slug": c.slug, "type": c.type, "target": c.target, "status": c.status}
                for c in filtered
            ],
            "correction_count": len(filtered),
            "writes_performed": False,
        },
    )


def command_scorecard_render(args: argparse.Namespace) -> int:
    from pyfpa.backtest.learn import render_scorecard
    from pyfpa.backtest.snapshot import load_snapshot

    root = _root(args.path)
    workspace = workspace_path(root)
    if not workspace.is_dir():
        return _failure(
            "scorecard-render",
            root,
            "workspace_not_initialized",
            "initialize the company workspace before rendering scorecard",
        )
    forecasts_dir = workspace / "forecasts"
    snapshots = []
    parse_errors = []
    if forecasts_dir.is_dir():
        for snap_path in sorted(forecasts_dir.glob("*.yaml")):
            try:
                snapshots.append(load_snapshot(snap_path))
            except Exception as exc:
                parse_errors.append(f"{snap_path.name}: {exc}")
    if parse_errors:
        return _failure(
            "scorecard-render",
            root,
            "invalid_snapshot",
            "; ".join(parse_errors),
        )
    scored = [s for s in snapshots if s.score is not None]
    unscored = [s for s in snapshots if s.score is None]
    scorecard_path = workspace / "scorecard.md"
    try:
        scorecard_path.write_text(render_scorecard(snapshots))
    except Exception as exc:
        return _failure("scorecard-render", root, "render_failed", str(exc))
    return _success(
        "scorecard-render",
        root,
        {
            "scorecard_path": str(scorecard_path),
            "snapshot_count": len(snapshots),
            "scored_count": len(scored),
            "unscored_count": len(unscored),
        },
    )


def command_experiment_list(args: argparse.Namespace) -> int:
    from pyfpa.memory.experiments import load_experiments

    root = _root(args.path)
    workspace = workspace_path(root)
    if not workspace.is_dir():
        return _failure(
            "experiment-list",
            root,
            "workspace_not_initialized",
            "initialize the company workspace before listing experiments",
        )
    try:
        experiments = load_experiments(workspace / "experiments")
    except Exception as exc:
        return _failure("experiment-list", root, "invalid_experiment", str(exc))
    filtered = [
        e for e in experiments
        if args.status is None or e.status == args.status
    ]
    return _success(
        "experiment-list",
        root,
        {
            "experiments": [
                {
                    "slug": e.slug,
                    "status": e.status,
                    "hypothesis": e.hypothesis,
                    "snapshot": e.snapshot,
                    "created": e.created,
                }
                for e in filtered
            ],
            "experiment_count": len(filtered),
            "writes_performed": False,
        },
    )


def command_context_pack(args: argparse.Namespace) -> int:
    from pyfpa.memory.retrieval import build_context_pack, build_memory_index, search_memory

    root = _root(args.path)
    workspace = workspace_path(root)
    if not workspace.is_dir():
        return _failure(
            "context-pack",
            root,
            "workspace_not_initialized",
            "initialize the company workspace before building a context pack",
        )
    try:
        index = build_memory_index(workspace)
        pack = build_context_pack(
            index,
            args.task,
            categories=args.category or None,
            limit=args.limit,
        )
        hits = search_memory(index, args.task, categories=args.category or None, limit=args.limit)
    except Exception as exc:
        return _failure("context-pack", root, "context_pack_failed", str(exc))
    return _success(
        "context-pack",
        root,
        {
            "pack": pack,
            "hit_count": len(hits),
            "entry_count": len(index.entries),
            "writes_performed": False,
        },
    )


def command_onboarding_render(args: argparse.Namespace) -> int:
    from pyfpa.memory.onboarding import ArchitectureProposal, write_onboarding_outputs

    root = _root(args.path)
    workspace = workspace_path(root)
    if not workspace.is_dir():
        return _failure(
            "onboarding-render",
            root,
            "workspace_not_initialized",
            "initialize the company workspace before rendering onboarding outputs",
        )
    try:
        intake = load_intake(workspace / "intake.md")
        proposal = ArchitectureProposal(
            summary=args.proposal_summary,
            connectors=args.connector or [],
            model_components=args.model_component or [],
            generated_skills=args.generated_skill or [],
            risks=args.risk or [],
            validation_checks=args.validation_check or [],
        )
        profile_path, proposal_path = write_onboarding_outputs(intake, workspace, proposal)
    except Exception as exc:
        return _failure("onboarding-render", root, "onboarding_render_failed", str(exc))
    return _success(
        "onboarding-render",
        root,
        {
            "profile_path": str(profile_path),
            "proposal_path": str(proposal_path),
        },
    )


def build_parser() -> argparse.ArgumentParser:
    parser = JsonArgumentParser(
        prog="openfpa",
        description="Machine-oriented FP&A toolbelt for AI coding agents.",
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    init_parser = subparsers.add_parser("init", help="Initialize a company workspace")
    init_parser.add_argument("path", nargs="?", default=".")
    init_parser.add_argument("--business-name")
    init_parser.set_defaults(handler=command_init)

    inspect_parser = subparsers.add_parser(
        "inspect-data",
        help="Inventory likely financial and operating data files",
    )
    inspect_parser.add_argument("path", nargs="?", default=".")
    inspect_parser.add_argument("--max-files", type=int, default=500)
    inspect_parser.set_defaults(handler=command_inspect_data)

    status_parser = subparsers.add_parser("status", help="Report company workspace state")
    status_parser.add_argument("path", nargs="?", default=".")
    status_parser.set_defaults(handler=command_status)

    intake_parser = subparsers.add_parser(
        "intake-next",
        help="Return the next related unresolved intake questions",
    )
    intake_parser.add_argument("path", nargs="?", default=".")
    intake_parser.add_argument("--limit", type=int, default=3)
    intake_parser.set_defaults(handler=command_intake_next)

    record_parser = subparsers.add_parser(
        "intake-record",
        help="Record one sourced intake fact",
    )
    record_parser.add_argument("path", nargs="?", default=".")
    record_parser.add_argument("--key", required=True)
    record_parser.add_argument("--answer", required=True)
    record_parser.add_argument(
        "--source-type",
        required=True,
        choices=("user", "local_file", "external", "inference"),
    )
    record_parser.add_argument("--source", action="append", default=[])
    record_parser.add_argument("--confidence", type=float)
    record_parser.add_argument("--topic")
    record_parser.add_argument("--question")
    record_parser.set_defaults(handler=command_intake_record)

    register_parser = subparsers.add_parser(
        "entrypoint-register",
        help="Publish a generated company command for agent discovery",
    )
    register_parser.add_argument("path", nargs="?", default=".")
    register_parser.add_argument("--name", required=True)
    register_parser.add_argument(
        "--kind",
        required=True,
        choices=("forecast", "close", "cash", "research", "report", "connector", "custom"),
    )
    register_parser.add_argument("--description", required=True)
    register_parser.add_argument("--command-json", required=True)
    register_parser.add_argument("--working-directory", default=".")
    register_parser.add_argument("--input", action="append", default=[])
    register_parser.add_argument("--output", action="append", default=[])
    register_parser.add_argument("--overwrite", action="store_true")
    register_parser.set_defaults(handler=command_entrypoint_register)

    list_parser = subparsers.add_parser(
        "entrypoint-list",
        help="List generated company commands",
    )
    list_parser.add_argument("path", nargs="?", default=".")
    list_parser.add_argument(
        "--kind",
        choices=("forecast", "close", "cash", "research", "report", "connector", "custom"),
    )
    list_parser.set_defaults(handler=command_entrypoint_list)

    source_register_parser = subparsers.add_parser(
        "source-register",
        help="Register source provenance and coverage",
    )
    source_register_parser.add_argument("path", nargs="?", default=".")
    source_register_parser.add_argument("--source-id", required=True)
    source_register_parser.add_argument(
        "--kind",
        required=True,
        choices=(
            "local_file",
            "shared_folder",
            "accounting_system",
            "operating_system",
            "api",
            "public_filing",
            "manual",
        ),
    )
    source_register_parser.add_argument("--location", required=True)
    source_register_parser.add_argument("--entity", required=True)
    source_register_parser.add_argument("--currency", required=True)
    source_register_parser.add_argument("--period", action="append", default=[])
    source_register_parser.add_argument("--extraction-method", required=True)
    source_register_parser.add_argument("--refreshed-at", default="")
    source_register_parser.add_argument("--notes", default="")
    source_register_parser.add_argument("--overwrite", action="store_true")
    source_register_parser.set_defaults(handler=command_source_register)

    source_list_parser = subparsers.add_parser(
        "source-list",
        help="List registered company data sources",
    )
    source_list_parser.add_argument("path", nargs="?", default=".")
    source_list_parser.add_argument(
        "--kind",
        choices=(
            "local_file",
            "shared_folder",
            "accounting_system",
            "operating_system",
            "api",
            "public_filing",
            "manual",
        ),
    )
    source_list_parser.set_defaults(handler=command_source_list)

    profile_parser = subparsers.add_parser(
        "source-profile",
        help="Profile a CSV, TSV, or Excel source without writing",
    )
    profile_parser.add_argument("path", nargs="?", default=".")
    profile_parser.add_argument("--file", required=True)
    profile_parser.set_defaults(handler=command_source_profile)

    mapping_register_parser = subparsers.add_parser(
        "mapping-register",
        help="Register one exact source-to-model mapping",
    )
    mapping_register_parser.add_argument("path", nargs="?", default=".")
    mapping_register_parser.add_argument("--source-id", required=True)
    mapping_register_parser.add_argument("--source-value", required=True)
    mapping_register_parser.add_argument("--target", default="")
    mapping_register_parser.add_argument(
        "--status", choices=("mapped", "ignored"), default="mapped"
    )
    mapping_register_parser.add_argument("--rationale", default="")
    mapping_register_parser.add_argument("--overwrite", action="store_true")
    mapping_register_parser.set_defaults(handler=command_mapping_register)

    mapping_list_parser = subparsers.add_parser(
        "mapping-list",
        help="List exact source-to-model mappings",
    )
    mapping_list_parser.add_argument("path", nargs="?", default=".")
    mapping_list_parser.add_argument("--source-id")
    mapping_list_parser.add_argument("--status", choices=("mapped", "ignored"))
    mapping_list_parser.set_defaults(handler=command_mapping_list)

    reconcile_parser = subparsers.add_parser(
        "reconcile-source",
        help="Reconcile a registered CSV source through exact mappings",
    )
    reconcile_parser.add_argument("path", nargs="?", default=".")
    reconcile_parser.add_argument("--source-id", required=True)
    reconcile_parser.add_argument("--file")
    reconcile_parser.add_argument("--account-column", default="Account")
    reconcile_parser.add_argument("--amount-column", default="Amount")
    reconcile_parser.add_argument("--expected-json")
    reconcile_parser.add_argument("--tolerance", type=float, default=0.01)
    reconcile_parser.add_argument("--allow-unmapped", action="store_true")
    reconcile_parser.set_defaults(handler=command_reconcile_source)

    connector_scaffold_parser = subparsers.add_parser(
        "connector-scaffold",
        help="Generate a fixture-backed company connector bundle",
    )
    connector_scaffold_parser.add_argument("path", nargs="?", default=".")
    connector_scaffold_parser.add_argument("--name", required=True)
    connector_scaffold_parser.add_argument("--source-id", required=True)
    connector_scaffold_parser.add_argument("--description", required=True)
    connector_scaffold_parser.add_argument(
        "--auth-method",
        choices=("none", "host_environment", "mcp"),
        required=True,
    )
    connector_scaffold_parser.add_argument("--fixture", required=True)
    connector_scaffold_parser.add_argument("--account-column", default="Account")
    connector_scaffold_parser.add_argument("--amount-column", default="Amount")
    connector_scaffold_parser.add_argument("--overwrite", action="store_true")
    connector_scaffold_parser.set_defaults(handler=command_connector_scaffold)

    connector_list_parser = subparsers.add_parser(
        "connector-list",
        help="List generated company connector contracts",
    )
    connector_list_parser.add_argument("path", nargs="?", default=".")
    connector_list_parser.add_argument("--source-id")
    connector_list_parser.set_defaults(handler=command_connector_list)

    connector_validate_parser = subparsers.add_parser(
        "connector-validate",
        help="Execute fixture mode and reconcile normalized connector output",
    )
    connector_validate_parser.add_argument("path", nargs="?", default=".")
    connector_validate_parser.add_argument("--name", required=True)
    connector_validate_parser.add_argument("--timeout", type=float, default=30.0)
    connector_validate_parser.set_defaults(handler=command_connector_validate)

    doctor_parser = subparsers.add_parser("doctor", help="Validate workspace contracts")
    doctor_parser.add_argument("path", nargs="?", default=".")
    doctor_parser.set_defaults(handler=command_doctor)

    correction_record_parser = subparsers.add_parser(
        "correction-record",
        help="Record one typed human correction into .fpa/corrections/",
    )
    correction_record_parser.add_argument("path", nargs="?", default=".")
    correction_record_parser.add_argument("--slug", required=True)
    correction_record_parser.add_argument(
        "--type", required=True, choices=("parametric", "structural", "context")
    )
    correction_record_parser.add_argument("--target", required=True)
    correction_record_parser.add_argument(
        "--status", choices=("open", "applied", "superseded"), default="open"
    )
    correction_record_parser.add_argument("--date", required=True)
    correction_record_parser.add_argument("--notes", default="")
    correction_record_parser.add_argument("--override-path")
    correction_record_parser.add_argument("--override-value", type=float)
    correction_record_parser.set_defaults(handler=command_correction_record)

    correction_list_parser = subparsers.add_parser(
        "correction-list",
        help="List recorded corrections",
    )
    correction_list_parser.add_argument("path", nargs="?", default=".")
    correction_list_parser.add_argument(
        "--status", choices=("open", "applied", "superseded")
    )
    correction_list_parser.set_defaults(handler=command_correction_list)

    scorecard_parser = subparsers.add_parser(
        "scorecard-render",
        help="Load all snapshots, render the scorecard, write .fpa/scorecard.md",
    )
    scorecard_parser.add_argument("path", nargs="?", default=".")
    scorecard_parser.set_defaults(handler=command_scorecard_render)

    experiment_list_parser = subparsers.add_parser(
        "experiment-list",
        help="List experiment records from .fpa/experiments/",
    )
    experiment_list_parser.add_argument("path", nargs="?", default=".")
    experiment_list_parser.add_argument(
        "--status",
        choices=("draft", "proposed", "accepted", "rejected", "reverted"),
    )
    experiment_list_parser.set_defaults(handler=command_experiment_list)

    context_pack_parser = subparsers.add_parser(
        "context-pack",
        help="Build a bounded task-relevant memory pack from .fpa/ for an agent",
    )
    context_pack_parser.add_argument("path", nargs="?", default=".")
    context_pack_parser.add_argument("--task", required=True)
    context_pack_parser.add_argument("--category", action="append", default=[])
    context_pack_parser.add_argument("--limit", type=int, default=8)
    context_pack_parser.set_defaults(handler=command_context_pack)

    onboarding_render_parser = subparsers.add_parser(
        "onboarding-render",
        help="Write business-profile.md and initial-model-architecture.md from intake",
    )
    onboarding_render_parser.add_argument("path", nargs="?", default=".")
    onboarding_render_parser.add_argument("--proposal-summary", required=True)
    onboarding_render_parser.add_argument("--connector", action="append", default=[])
    onboarding_render_parser.add_argument("--model-component", action="append", default=[])
    onboarding_render_parser.add_argument("--generated-skill", action="append", default=[])
    onboarding_render_parser.add_argument("--risk", action="append", default=[])
    onboarding_render_parser.add_argument("--validation-check", action="append", default=[])
    onboarding_render_parser.set_defaults(handler=command_onboarding_render)

    return parser


def main(argv: Sequence[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    if getattr(args, "max_files", 1) < 1:
        parser.error("--max-files must be at least 1")
    if getattr(args, "limit", 1) < 1:
        parser.error("--limit must be at least 1")
    if getattr(args, "tolerance", 0.0) < 0:
        parser.error("--tolerance must be non-negative")
    if getattr(args, "timeout", 1.0) <= 0:
        parser.error("--timeout must be greater than zero")
    handler: Callable[[argparse.Namespace], int] = args.handler
    try:
        return handler(args)
    except Exception as exc:
        root = _root(getattr(args, "path", "."))
        return _failure(args.command, root, "unexpected_error", str(exc))


if __name__ == "__main__":
    raise SystemExit(main())
