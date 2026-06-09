from __future__ import annotations

import argparse
import json
from pathlib import Path

from pyfpa.cli_helpers import _failure, _root, _success
from pyfpa.memory.connectors import (
    connector_bundle_path,
    load_connector_manifests,
    scaffold_connector_bundle,
    validate_connector_bundle,
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
from pyfpa.memory.workspace import workspace_path


def _source_registry_path(root: Path) -> Path:
    return workspace_path(root) / "sources" / "registry.yaml"


def _mapping_registry_path(root: Path) -> Path:
    return workspace_path(root) / "mappings" / "registry.yaml"


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
