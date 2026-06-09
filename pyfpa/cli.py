from __future__ import annotations

import argparse
import json
import os
import re
import sys
from collections.abc import Callable, Sequence
from pathlib import Path
from typing import Any

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
from pyfpa.memory.workspace import initialize_workspace, workspace_path
from pyfpa.research.objective import load_research_objective
from pyfpa.research.registry import load_model_registry


SCHEMA_VERSION = 1
EXIT_OK = 0
EXIT_FAILED = 1
EXIT_USAGE = 2

_IGNORED_DIRECTORIES = {
    ".fpa",
    ".git",
    ".hg",
    ".mypy_cache",
    ".pytest_cache",
    ".ruff_cache",
    ".tox",
    ".venv",
    "__pycache__",
    "build",
    "dist",
    "node_modules",
    "venv",
}
_DATA_EXTENSIONS = {
    ".csv",
    ".json",
    ".parquet",
    ".pdf",
    ".tsv",
    ".xls",
    ".xlsm",
    ".xlsx",
    ".xml",
    ".yaml",
    ".yml",
}
_CONTEXT_EXTENSIONS = {".md", ".txt"}
_CLASSIFIERS = (
    ("profit_and_loss", ("pnl", "p l", "profit loss", "income statement")),
    ("balance_sheet", ("balance sheet", "balance_sheet", "trial balance", "trial_balance")),
    ("ar_aging", ("ar aging", "ar_aging", "accounts receivable", "receivable aging")),
    ("ap_aging", ("ap aging", "ap_aging", "accounts payable", "payable aging")),
    ("inventory", ("inventory", "stock on hand", "stock_on_hand", "sku", "item detail")),
    ("cash_and_bank", ("cash", "bank", "treasury")),
    ("payroll_and_headcount", ("payroll", "headcount", "wages", "compensation")),
    ("sales_and_revenue", ("sales", "revenue", "bookings", "orders", "crm")),
    ("budget_and_forecast", ("budget", "forecast", "plan", "scenario")),
    ("operations", ("operations", "operational", "production", "utilization", "fleet")),
)
_CONTEXT_SIGNALS = (
    "business",
    "board",
    "covenant",
    "finance",
    "model",
    "planning",
    "pricing",
    "strategy",
)
_REQUIRED_WORKSPACE_DIRS = (
    "sources",
    "mappings",
    "corrections",
    "forecasts",
    "experiments",
    "decisions",
    "models",
    "research",
)


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


def _normalized_name(path: Path) -> str:
    return re.sub(r"[^a-z0-9]+", " ", path.stem.casefold()).strip()


def _classify_file(path: Path) -> tuple[str, list[str]]:
    name = _normalized_name(path)
    for category, signals in _CLASSIFIERS:
        matched = [signal for signal in signals if signal.replace("_", " ") in name]
        if matched:
            return category, matched
    return "unclassified", []


def _is_candidate_file(path: Path) -> bool:
    suffix = path.suffix.casefold()
    if suffix in _DATA_EXTENSIONS:
        return True
    if suffix not in _CONTEXT_EXTENSIONS:
        return False
    name = _normalized_name(path)
    return any(signal in name for signal in _CONTEXT_SIGNALS)


def _inventory_files(root: Path, *, max_files: int) -> tuple[list[dict[str, Any]], bool]:
    files: list[dict[str, Any]] = []
    for current, directories, filenames in os.walk(root):
        directories[:] = sorted(
            directory
            for directory in directories
            if directory not in _IGNORED_DIRECTORIES and not directory.startswith(".")
        )
        for filename in sorted(filenames):
            if filename.startswith("."):
                continue
            path = Path(current) / filename
            if not _is_candidate_file(path):
                continue
            category, signals = _classify_file(path)
            files.append(
                {
                    "path": path.relative_to(root).as_posix(),
                    "extension": path.suffix.casefold(),
                    "bytes": path.stat().st_size,
                    "category": category,
                    "signals": signals,
                }
            )
            if len(files) > max_files:
                return files[:max_files], True
    return files, False


def _workspace_counts(workspace: Path) -> dict[str, int]:
    return {
        directory: sum(1 for path in (workspace / directory).glob("*") if path.is_file())
        for directory in _REQUIRED_WORKSPACE_DIRS
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
            "next_command": f"openfpa inspect-data {json.dumps(str(root))}",
        },
    )


def command_inspect_data(args: argparse.Namespace) -> int:
    root = _root(args.path)
    if not root.is_dir():
        return _failure("inspect-data", root, "path_not_found", "inspection path is not a directory")
    files, truncated = _inventory_files(root, max_files=args.max_files)
    category_counts: dict[str, int] = {}
    for item in files:
        category = item["category"]
        category_counts[category] = category_counts.get(category, 0) + 1
    priority_categories = {
        "profit_and_loss",
        "balance_sheet",
        "ar_aging",
        "ap_aging",
        "inventory",
    }
    found_categories = set(category_counts)
    return _success(
        "inspect-data",
        root,
        {
            "files": files,
            "file_count": len(files),
            "category_counts": category_counts,
            "missing_priority_categories": sorted(priority_categories - found_categories),
            "truncated": truncated,
            "max_files": args.max_files,
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
                "next_command": f"openfpa init {json.dumps(str(root))}",
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
                f"openfpa connector-validate {json.dumps(str(root))} "
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


def _check(
    checks: list[dict[str, str]],
    *,
    name: str,
    result: str,
    details: str,
) -> None:
    checks.append({"name": name, "result": result, "details": details})


def command_doctor(args: argparse.Namespace) -> int:
    root = _root(args.path)
    workspace = workspace_path(root)
    checks: list[dict[str, str]] = []
    if not workspace.is_dir():
        _check(
            checks,
            name="workspace",
            result="error",
            details=f"missing workspace: {workspace}",
        )
    else:
        _check(checks, name="workspace", result="pass", details=str(workspace))
        for directory in _REQUIRED_WORKSPACE_DIRS:
            path = workspace / directory
            _check(
                checks,
                name=f"directory:{directory}",
                result="pass" if path.is_dir() else "error",
                details=str(path),
            )
        try:
            intake = load_intake(workspace / "intake.md")
            _check(
                checks,
                name="intake",
                result="pass",
                details=(
                    f"{len(intake.facts)} facts; "
                    f"ready={str(intake_ready(intake)).lower()}"
                ),
            )
        except Exception as exc:
            _check(checks, name="intake", result="error", details=str(exc))
        try:
            objective = load_research_objective(workspace / "research" / "objective.yaml")
            _check(
                checks,
                name="research_objective",
                result="pass",
                details=f"{len(objective.metrics)} metrics; {len(objective.hard_checks)} hard checks",
            )
        except Exception as exc:
            _check(checks, name="research_objective", result="error", details=str(exc))
        try:
            registry = load_model_registry(workspace / "models" / "registry.yaml")
            _check(
                checks,
                name="model_registry",
                result="pass",
                details=(
                    f"champion={registry.champion.model_id if registry.champion else 'none'}; "
                    f"challengers={len(registry.challengers)}"
                ),
            )
        except Exception as exc:
            _check(checks, name="model_registry", result="error", details=str(exc))
        try:
            entrypoint_path = workspace / "models" / "entrypoints.yaml"
            if not entrypoint_path.exists():
                raise FileNotFoundError(f"entrypoint registry not found: {entrypoint_path}")
            entrypoints = load_entrypoint_registry(entrypoint_path)
            _check(
                checks,
                name="entrypoint_registry",
                result="pass",
                details=f"{len(entrypoints.entrypoints)} registered entrypoints",
            )
        except Exception as exc:
            _check(checks, name="entrypoint_registry", result="error", details=str(exc))
        try:
            source_path = workspace / "sources" / "registry.yaml"
            if not source_path.exists():
                raise FileNotFoundError(f"source registry not found: {source_path}")
            sources = load_source_registry(source_path)
            _check(
                checks,
                name="source_registry",
                result="pass",
                details=f"{len(sources.sources)} registered sources",
            )
        except Exception as exc:
            _check(checks, name="source_registry", result="error", details=str(exc))
        try:
            mapping_path = workspace / "mappings" / "registry.yaml"
            if not mapping_path.exists():
                raise FileNotFoundError(f"mapping registry not found: {mapping_path}")
            mappings = load_mapping_registry(mapping_path)
            _check(
                checks,
                name="mapping_registry",
                result="pass",
                details=f"{len(mappings.mappings)} registered mappings",
            )
        except Exception as exc:
            _check(checks, name="mapping_registry", result="error", details=str(exc))
        try:
            connectors = load_connector_manifests(root)
            _check(
                checks,
                name="generated_connector_contracts",
                result="pass",
                details=f"{len(connectors)} generated connector manifests",
            )
        except Exception as exc:
            _check(
                checks,
                name="generated_connector_contracts",
                result="error",
                details=str(exc),
            )

    errors = [check for check in checks if check["result"] == "error"]
    warnings = [check for check in checks if check["result"] == "warning"]
    payload = {
        "healthy": not errors,
        "checks": checks,
        "error_count": len(errors),
        "warning_count": len(warnings),
    }
    if errors:
        return _failure(
            "doctor",
            root,
            "diagnostic_failure",
            f"{len(errors)} diagnostic check(s) failed",
            data=payload,
        )
    return _success("doctor", root, payload)


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
