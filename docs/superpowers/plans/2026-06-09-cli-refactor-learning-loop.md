# CLI Refactor + Learning-Loop Wiring Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Split `pyfpa/cli.py` (1,221 lines) into focused modules under 800 lines and wire the existing learning-loop library (corrections, snapshots/scorecard, experiments, context-pack, onboarding) into new CLI subcommands.

**Architecture:** Extract data-classification logic to `pyfpa/memory/inspection.py` and doctor validation logic to `pyfpa/memory/diagnostics.py`; each exposes a pure library function that the CLI handler calls as a thin wrapper. Add six new subcommands in `pyfpa/cli.py` (and split into `pyfpa/cli_commands/` only if still over 800 lines after extraction). Fix the `init` next_command hint to always use `python3 -m pyfpa.cli` form. Update README and AGENTS.md command lists.

**Tech Stack:** Python 3.11+, pydantic v2, pytest, pyyaml, existing `pyfpa` library functions.

---

## File Map

| File | Action | Responsibility |
|---|---|---|
| `pyfpa/memory/inspection.py` | Create | Pure `inspect_data_files()` function; data-classification constants |
| `pyfpa/memory/diagnostics.py` | Create | Pure `validate_workspace()` returning `WorkspaceReport` pydantic model |
| `pyfpa/memory/workspace.py` | Modify | Export `WORKSPACE_DIRS` (rename from `_WORKSPACE_DIRS`) |
| `pyfpa/cli.py` | Modify | Thin wrappers only; add 6 new subcommands; fix `next_command` hints; delete `_REQUIRED_WORKSPACE_DIRS` |
| `pyfpa/cli_commands/` | Create if needed | Handler split if cli.py still over 800 lines after extraction |
| `tests/test_memory_inspection.py` | Create | Unit tests for `inspect_data_files` |
| `tests/test_memory_diagnostics.py` | Create | Unit tests for `validate_workspace` |
| `tests/test_cli.py` | Modify | Add tests for 6 new subcommands |
| `README.md` | Modify | Add new commands to CLI section; source-checkout note |
| `AGENTS.md` | Modify | Add new commands to the operating contract list |

---

## Task 1: Expose `WORKSPACE_DIRS` from `workspace.py`

**Files:**
- Modify: `pyfpa/memory/workspace.py`

- [ ] **Step 1: Read the current workspace.py**

Read `/Volumes/Crucial/openfpa/pyfpa/memory/workspace.py`. The constant `_WORKSPACE_DIRS` is private (underscore prefix). We need it public so `diagnostics.py` and `cli.py` can both import it without duplicating the list.

- [ ] **Step 2: Rename the constant**

In `pyfpa/memory/workspace.py`, change `_WORKSPACE_DIRS` to `WORKSPACE_DIRS` at the definition site (line 8) and at every use inside the file (line 40: `for directory in _WORKSPACE_DIRS:`).

```python
# Before (line 8)
_WORKSPACE_DIRS = (

# After (line 8)
WORKSPACE_DIRS = (
```

And on line 40:
```python
# Before
    for directory in _WORKSPACE_DIRS:
# After
    for directory in WORKSPACE_DIRS:
```

- [ ] **Step 3: Run existing workspace tests**

```bash
cd /Volumes/Crucial/openfpa && python3 -m pytest tests/test_memory_workspace.py -v
```

Expected: all pass (the rename is internal, nothing imports `_WORKSPACE_DIRS` from outside yet).

- [ ] **Step 4: Verify cli.py uses its own copy, not workspace**

Grep confirms `_REQUIRED_WORKSPACE_DIRS` is defined in cli.py and not imported:
```bash
grep -n "_REQUIRED_WORKSPACE_DIRS\|WORKSPACE_DIRS" /Volumes/Crucial/openfpa/pyfpa/cli.py
```

Expected output: lines 104-113 define `_REQUIRED_WORKSPACE_DIRS` locally.

- [ ] **Step 5: Commit**

```bash
cd /Volumes/Crucial/openfpa
git add pyfpa/memory/workspace.py
git commit -m "refactor: export WORKSPACE_DIRS from workspace.py"
```

---

## Task 2: Create `pyfpa/memory/inspection.py`

**Files:**
- Create: `pyfpa/memory/inspection.py`
- Create: `tests/test_memory_inspection.py`

This moves the data-classification engine out of `cli.py` into a pure library function. The CLI handler becomes a thin wrapper.

- [ ] **Step 1: Write the failing test**

Create `tests/test_memory_inspection.py`:

```python
from __future__ import annotations

import pytest
from pathlib import Path

from pyfpa.memory.inspection import inspect_data_files, InspectionResult


def test_classifies_financial_files_by_name(tmp_path):
    (tmp_path / "Income Statement FY2025.xlsx").write_bytes(b"xlsx")
    (tmp_path / "AR Aging.csv").write_text("customer,balance\n")
    (tmp_path / "Inventory Detail.tsv").write_text("sku\tunits\n")
    (tmp_path / "notes.md").write_text("not a financial artifact")

    result = inspect_data_files(tmp_path)

    assert isinstance(result, InspectionResult)
    assert result.file_count == 3
    assert result.category_counts["ar_aging"] == 1
    assert result.category_counts["inventory"] == 1
    assert result.category_counts["profit_and_loss"] == 1
    assert "balance_sheet" in result.missing_priority_categories


def test_skips_hidden_directories(tmp_path):
    hidden = tmp_path / ".private"
    hidden.mkdir()
    (hidden / "Balance Sheet.xlsx").write_bytes(b"xlsx")

    result = inspect_data_files(tmp_path)

    assert result.file_count == 0


def test_truncation_flag_when_max_files_exceeded(tmp_path):
    for i in range(5):
        (tmp_path / f"file{i}.csv").write_text("Account,Amount\n")

    result = inspect_data_files(tmp_path, max_files=3)

    assert result.truncated is True
    assert len(result.files) == 3


def test_context_md_included_only_when_signal_present(tmp_path):
    (tmp_path / "business-model.md").write_text("# Business Model\n")
    (tmp_path / "random-notes.md").write_text("# Random notes\n")

    result = inspect_data_files(tmp_path)

    paths = [f["path"] for f in result.files]
    assert "business-model.md" in paths
    assert "random-notes.md" not in paths
```

- [ ] **Step 2: Run test to confirm it fails**

```bash
cd /Volumes/Crucial/openfpa && python3 -m pytest tests/test_memory_inspection.py -v
```

Expected: `ModuleNotFoundError: No module named 'pyfpa.memory.inspection'`

- [ ] **Step 3: Create `pyfpa/memory/inspection.py`**

```python
from __future__ import annotations

import os
import re
from pathlib import Path
from typing import Any

from pydantic import BaseModel

from pyfpa.memory.workspace import WORKSPACE_DIRS  # noqa: F401 (re-exported)


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
_PRIORITY_CATEGORIES = frozenset({
    "profit_and_loss",
    "balance_sheet",
    "ar_aging",
    "ap_aging",
    "inventory",
})


class InspectionResult(BaseModel):
    files: list[dict[str, Any]]
    file_count: int
    category_counts: dict[str, int]
    missing_priority_categories: list[str]
    truncated: bool
    max_files: int


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


def inspect_data_files(root: Path, *, max_files: int = 500) -> InspectionResult:
    """Walk `root`, classify likely financial and operating data files, and
    return a typed result. Pure: no writes, no side effects."""
    files: list[dict[str, Any]] = []
    truncated = False
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
                files = files[:max_files]
                truncated = True
                break
        if truncated:
            break
    category_counts: dict[str, int] = {}
    for item in files:
        cat = item["category"]
        category_counts[cat] = category_counts.get(cat, 0) + 1
    found = set(category_counts)
    return InspectionResult(
        files=files,
        file_count=len(files),
        category_counts=category_counts,
        missing_priority_categories=sorted(_PRIORITY_CATEGORIES - found),
        truncated=truncated,
        max_files=max_files,
    )
```

- [ ] **Step 4: Run test to confirm pass**

```bash
cd /Volumes/Crucial/openfpa && python3 -m pytest tests/test_memory_inspection.py -v
```

Expected: all 4 tests PASS.

- [ ] **Step 5: Commit**

```bash
cd /Volumes/Crucial/openfpa
git add pyfpa/memory/inspection.py tests/test_memory_inspection.py
git commit -m "feat: extract inspect_data_files() into pyfpa.memory.inspection"
```

---

## Task 3: Create `pyfpa/memory/diagnostics.py`

**Files:**
- Create: `pyfpa/memory/diagnostics.py`
- Create: `tests/test_memory_diagnostics.py`

Moves the `command_doctor` validation walk into a pure library function. The CLI `command_doctor` becomes a thin wrapper that renders the `WorkspaceReport`.

- [ ] **Step 1: Write the failing tests**

Create `tests/test_memory_diagnostics.py`:

```python
from __future__ import annotations

import pytest
from pathlib import Path

from pyfpa.memory.diagnostics import validate_workspace, WorkspaceReport


def _init_workspace(root: Path) -> None:
    """Minimal workspace scaffold for diagnostic tests."""
    import subprocess, sys
    result = subprocess.run(
        [sys.executable, "-m", "pyfpa.cli", "init", str(root)],
        capture_output=True, text=True, check=False,
    )
    assert result.returncode == 0, result.stderr


def test_validate_workspace_healthy(tmp_path):
    _init_workspace(tmp_path)
    report = validate_workspace(tmp_path)

    assert isinstance(report, WorkspaceReport)
    assert report.healthy is True
    assert report.error_count == 0
    assert any(c["name"] == "workspace" and c["result"] == "pass" for c in report.checks)


def test_validate_workspace_missing_workspace(tmp_path):
    report = validate_workspace(tmp_path)

    assert report.healthy is False
    assert report.error_count >= 1
    assert any(c["name"] == "workspace" and c["result"] == "error" for c in report.checks)


def test_validate_workspace_corrupt_registry(tmp_path):
    _init_workspace(tmp_path)
    (tmp_path / ".fpa" / "models" / "registry.yaml").write_text("not: [valid")

    report = validate_workspace(tmp_path)

    assert report.healthy is False
    assert any(
        c["name"] == "model_registry" and c["result"] == "error"
        for c in report.checks
    )


def test_validate_workspace_reports_corrections_and_snapshots(tmp_path):
    _init_workspace(tmp_path)
    corrections_dir = tmp_path / ".fpa" / "corrections"
    corrections_dir.mkdir(exist_ok=True)
    # Write a valid correction
    (corrections_dir / "test-corr.md").write_text(
        "---\ntype: parametric\ntarget: working_capital.dio_days\n"
        "status: open\ndate: '2026-01-01'\n---\nTest correction.\n"
    )

    report = validate_workspace(tmp_path)

    assert report.healthy is True
    correction_check = next(
        (c for c in report.checks if c["name"] == "corrections"), None
    )
    assert correction_check is not None
    assert correction_check["result"] == "pass"
    assert "1" in correction_check["details"]


def test_validate_workspace_reports_snapshots(tmp_path):
    _init_workspace(tmp_path)

    report = validate_workspace(tmp_path)

    snapshot_check = next(
        (c for c in report.checks if c["name"] == "snapshots"), None
    )
    assert snapshot_check is not None
    assert "0" in snapshot_check["details"]
```

- [ ] **Step 2: Run test to confirm failure**

```bash
cd /Volumes/Crucial/openfpa && python3 -m pytest tests/test_memory_diagnostics.py -v
```

Expected: `ModuleNotFoundError: No module named 'pyfpa.memory.diagnostics'`

- [ ] **Step 3: Create `pyfpa/memory/diagnostics.py`**

```python
from __future__ import annotations

from pathlib import Path

from pydantic import BaseModel

from pyfpa.memory.workspace import WORKSPACE_DIRS, workspace_path


class WorkspaceReport(BaseModel):
    healthy: bool
    checks: list[dict[str, str]]
    error_count: int
    warning_count: int


def _check(
    checks: list[dict[str, str]],
    *,
    name: str,
    result: str,
    details: str,
) -> None:
    checks.append({"name": name, "result": result, "details": details})


def validate_workspace(root: Path) -> WorkspaceReport:
    """Run all workspace contract checks and return a typed report.
    Pure: reads files, does not write anything."""
    workspace = workspace_path(root)
    checks: list[dict[str, str]] = []

    if not workspace.is_dir():
        _check(
            checks,
            name="workspace",
            result="error",
            details=f"missing workspace: {workspace}",
        )
        errors = [c for c in checks if c["result"] == "error"]
        warnings = [c for c in checks if c["result"] == "warning"]
        return WorkspaceReport(
            healthy=not errors,
            checks=checks,
            error_count=len(errors),
            warning_count=len(warnings),
        )

    _check(checks, name="workspace", result="pass", details=str(workspace))

    for directory in WORKSPACE_DIRS:
        path = workspace / directory
        _check(
            checks,
            name=f"directory:{directory}",
            result="pass" if path.is_dir() else "error",
            details=str(path),
        )

    try:
        from pyfpa.memory.intake import intake_ready, load_intake

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
        from pyfpa.research.objective import load_research_objective

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
        from pyfpa.research.registry import load_model_registry

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
        from pyfpa.memory.entrypoints import load_entrypoint_registry

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
        from pyfpa.memory.lineage import load_source_registry

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
        from pyfpa.memory.lineage import load_mapping_registry

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
        from pyfpa.memory.connectors import load_connector_manifests

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

    try:
        from pyfpa.memory.corrections import load_corrections

        corrections = load_corrections(workspace / "corrections")
        _check(
            checks,
            name="corrections",
            result="pass",
            details=f"{len(corrections)} corrections",
        )
    except Exception as exc:
        _check(checks, name="corrections", result="error", details=str(exc))

    try:
        from pyfpa.backtest.snapshot import load_snapshot

        forecasts_dir = workspace / "forecasts"
        snapshot_count = 0
        parse_errors: list[str] = []
        if forecasts_dir.is_dir():
            for snap_path in sorted(forecasts_dir.glob("*.yaml")):
                try:
                    load_snapshot(snap_path)
                    snapshot_count += 1
                except Exception as exc:
                    parse_errors.append(f"{snap_path.name}: {exc}")
        if parse_errors:
            _check(
                checks,
                name="snapshots",
                result="error",
                details=f"{snapshot_count} ok; errors: {'; '.join(parse_errors)}",
            )
        else:
            _check(
                checks,
                name="snapshots",
                result="pass",
                details=f"{snapshot_count} snapshots",
            )
    except Exception as exc:
        _check(checks, name="snapshots", result="error", details=str(exc))

    errors = [c for c in checks if c["result"] == "error"]
    warnings = [c for c in checks if c["result"] == "warning"]
    return WorkspaceReport(
        healthy=not errors,
        checks=checks,
        error_count=len(errors),
        warning_count=len(warnings),
    )
```

- [ ] **Step 4: Run tests to confirm pass**

```bash
cd /Volumes/Crucial/openfpa && python3 -m pytest tests/test_memory_diagnostics.py -v
```

Expected: all 5 tests PASS.

- [ ] **Step 5: Commit**

```bash
cd /Volumes/Crucial/openfpa
git add pyfpa/memory/diagnostics.py tests/test_memory_diagnostics.py
git commit -m "feat: extract validate_workspace() into pyfpa.memory.diagnostics"
```

---

## Task 4: Slim `pyfpa/cli.py` (wire inspection, diagnostics, dedupe dir list)

**Files:**
- Modify: `pyfpa/cli.py`

Replace the inline classification engine and doctor walk with thin wrappers over the new library functions. Delete `_REQUIRED_WORKSPACE_DIRS` and the redundant constants from cli.py. Fix the `init` `next_command` hint.

- [ ] **Step 1: Edit `pyfpa/cli.py` imports**

At the top of `pyfpa/cli.py`, add:

```python
from pyfpa.memory.inspection import InspectionResult, inspect_data_files
from pyfpa.memory.diagnostics import WorkspaceReport, validate_workspace
from pyfpa.memory.workspace import WORKSPACE_DIRS
```

Remove from the existing body: `_IGNORED_DIRECTORIES`, `_DATA_EXTENSIONS`, `_CONTEXT_EXTENSIONS`, `_CLASSIFIERS`, `_CONTEXT_SIGNALS`, `_REQUIRED_WORKSPACE_DIRS`, `_normalized_name`, `_classify_file`, `_is_candidate_file`, `_inventory_files`, and the `_check` helper.

- [ ] **Step 2: Replace `command_inspect_data`**

```python
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
```

- [ ] **Step 3: Replace `_workspace_counts` to use imported `WORKSPACE_DIRS`**

```python
def _workspace_counts(workspace: Path) -> dict[str, int]:
    return {
        directory: sum(1 for path in (workspace / directory).glob("*") if path.is_file())
        for directory in WORKSPACE_DIRS
        if (workspace / directory).is_dir()
    }
```

- [ ] **Step 4: Replace `command_doctor`**

```python
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
```

Remove the old `_check` helper function from cli.py (it now lives in diagnostics.py).

- [ ] **Step 5: Fix `command_init` next_command hint**

Change:
```python
"next_command": f"openfpa inspect-data {json.dumps(str(root))}",
```
To:
```python
"next_command": f"python3 -m pyfpa.cli inspect-data {json.dumps(str(root))}",
```

Similarly fix the `command_status` hint when uninitialized:
```python
"next_command": f"python3 -m pyfpa.cli init {json.dumps(str(root))}",
```

And fix `command_connector_scaffold` next_command:
```python
"next_command": (
    f"python3 -m pyfpa.cli connector-validate {json.dumps(str(root))} "
    f"--name {manifest.name}"
),
```

- [ ] **Step 6: Run full test suite**

```bash
cd /Volumes/Crucial/openfpa && python3 -m pytest tests/ -q --tb=short
```

Expected: all 235 tests PASS (the existing CLI tests use `python3 -m pyfpa.cli` and exercise `next_command` values indirectly).

- [ ] **Step 7: Check line count**

```bash
wc -l /Volumes/Crucial/openfpa/pyfpa/cli.py
```

Expected: under 900 (likely 780-850 after extraction; target is under 800 before adding new commands).

- [ ] **Step 8: Commit**

```bash
cd /Volumes/Crucial/openfpa
git add pyfpa/cli.py
git commit -m "refactor: slim cli.py via inspection/diagnostics extraction, fix next_command hints"
```

---

## Task 5: Wire `correction-record` and `correction-list`

**Files:**
- Modify: `pyfpa/cli.py`
- Modify: `tests/test_cli.py`

- [ ] **Step 1: Write the failing tests**

Add to `tests/test_cli.py`:

```python
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
```

- [ ] **Step 2: Run tests to confirm failure**

```bash
cd /Volumes/Crucial/openfpa && python3 -m pytest tests/test_cli.py::test_correction_record_and_list tests/test_cli.py::test_correction_record_with_override -v
```

Expected: FAIL with `unrecognized arguments: correction-record`.

- [ ] **Step 3: Add handlers and parser entries in `pyfpa/cli.py`**

Add imports at top:
```python
from pyfpa.memory.corrections import Correction, Override, load_corrections, save_correction
```

Add handler functions:
```python
def command_correction_record(args: argparse.Namespace) -> int:
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
```

Add parser entries in `build_parser()` before the `return parser` line:
```python
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
```

- [ ] **Step 4: Run new tests**

```bash
cd /Volumes/Crucial/openfpa && python3 -m pytest tests/test_cli.py::test_correction_record_and_list tests/test_cli.py::test_correction_record_with_override -v
```

Expected: PASS.

- [ ] **Step 5: Run full suite**

```bash
cd /Volumes/Crucial/openfpa && python3 -m pytest tests/ -q --tb=short
```

Expected: all pass.

- [ ] **Step 6: Commit**

```bash
cd /Volumes/Crucial/openfpa
git add pyfpa/cli.py tests/test_cli.py
git commit -m "feat: add correction-record and correction-list CLI subcommands"
```

---

## Task 6: Wire `scorecard-render`

**Files:**
- Modify: `pyfpa/cli.py`
- Modify: `tests/test_cli.py`

- [ ] **Step 1: Write the failing test**

Add to `tests/test_cli.py`:

```python
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
```

- [ ] **Step 2: Run tests to confirm failure**

```bash
cd /Volumes/Crucial/openfpa && python3 -m pytest tests/test_cli.py::test_scorecard_render_empty_workspace tests/test_cli.py::test_scorecard_render_writes_table_for_scored_snapshots -v
```

Expected: FAIL.

- [ ] **Step 3: Add handler and parser in `pyfpa/cli.py`**

Add imports:
```python
from pyfpa.backtest.learn import render_scorecard
from pyfpa.backtest.snapshot import load_snapshot
```

Add handler:
```python
def command_scorecard_render(args: argparse.Namespace) -> int:
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
```

Add parser entry in `build_parser()`:
```python
    scorecard_parser = subparsers.add_parser(
        "scorecard-render",
        help="Load all snapshots, render the scorecard, write .fpa/scorecard.md",
    )
    scorecard_parser.add_argument("path", nargs="?", default=".")
    scorecard_parser.set_defaults(handler=command_scorecard_render)
```

- [ ] **Step 4: Run new tests**

```bash
cd /Volumes/Crucial/openfpa && python3 -m pytest tests/test_cli.py::test_scorecard_render_empty_workspace tests/test_cli.py::test_scorecard_render_writes_table_for_scored_snapshots -v
```

Expected: PASS.

- [ ] **Step 5: Commit**

```bash
cd /Volumes/Crucial/openfpa
git add pyfpa/cli.py tests/test_cli.py
git commit -m "feat: add scorecard-render CLI subcommand"
```

---

## Task 7: Wire `experiment-list`

**Files:**
- Modify: `pyfpa/cli.py`
- Modify: `tests/test_cli.py`

- [ ] **Step 1: Write the failing test**

Add to `tests/test_cli.py`:

```python
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
```

- [ ] **Step 2: Run tests to confirm failure**

```bash
cd /Volumes/Crucial/openfpa && python3 -m pytest tests/test_cli.py::test_experiment_list_empty tests/test_cli.py::test_experiment_list_with_experiments -v
```

Expected: FAIL.

- [ ] **Step 3: Add handler and parser in `pyfpa/cli.py`**

Add import:
```python
from pyfpa.memory.experiments import load_experiments
```

Add handler:
```python
def command_experiment_list(args: argparse.Namespace) -> int:
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
```

Add parser entry in `build_parser()`:
```python
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
```

- [ ] **Step 4: Run new tests**

```bash
cd /Volumes/Crucial/openfpa && python3 -m pytest tests/test_cli.py::test_experiment_list_empty tests/test_cli.py::test_experiment_list_with_experiments -v
```

Expected: PASS.

- [ ] **Step 5: Commit**

```bash
cd /Volumes/Crucial/openfpa
git add pyfpa/cli.py tests/test_cli.py
git commit -m "feat: add experiment-list CLI subcommand"
```

---

## Task 8: Wire `context-pack`

**Files:**
- Modify: `pyfpa/cli.py`
- Modify: `tests/test_cli.py`

Note: `build_context_pack(index, task, ...)` takes a pre-built `MemoryIndex`. The CLI handler builds the index inline from the workspace (no persistent index file required).

- [ ] **Step 1: Write the failing test**

Add to `tests/test_cli.py`:

```python
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
```

- [ ] **Step 2: Run tests to confirm failure**

```bash
cd /Volumes/Crucial/openfpa && python3 -m pytest tests/test_cli.py::test_context_pack_returns_markdown tests/test_cli.py::test_context_pack_respects_limit -v
```

Expected: FAIL.

- [ ] **Step 3: Add handler and parser in `pyfpa/cli.py`**

Add imports:
```python
from pyfpa.memory.retrieval import build_context_pack, build_memory_index, search_memory
```

Add handler:
```python
def command_context_pack(args: argparse.Namespace) -> int:
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
```

Add parser entry in `build_parser()`:
```python
    context_pack_parser = subparsers.add_parser(
        "context-pack",
        help="Build a bounded task-relevant memory pack from .fpa/ for an agent",
    )
    context_pack_parser.add_argument("path", nargs="?", default=".")
    context_pack_parser.add_argument("--task", required=True)
    context_pack_parser.add_argument("--category", action="append", default=[])
    context_pack_parser.add_argument("--limit", type=int, default=8)
    context_pack_parser.set_defaults(handler=command_context_pack)
```

Also add `--limit` validation in `main()`:

After the existing `if getattr(args, "limit", 1) < 1:` check, the context-pack `--limit` shares the same attribute name, so the existing validation covers it.

- [ ] **Step 4: Run new tests**

```bash
cd /Volumes/Crucial/openfpa && python3 -m pytest tests/test_cli.py::test_context_pack_returns_markdown tests/test_cli.py::test_context_pack_respects_limit -v
```

Expected: PASS.

- [ ] **Step 5: Commit**

```bash
cd /Volumes/Crucial/openfpa
git add pyfpa/cli.py tests/test_cli.py
git commit -m "feat: add context-pack CLI subcommand"
```

---

## Task 9: Wire `onboarding-render`

**Files:**
- Modify: `pyfpa/cli.py`
- Modify: `tests/test_cli.py`

`write_onboarding_outputs(intake, workspace, proposal)` requires an `ArchitectureProposal`. The CLI must accept the proposal fields as flags so it is scriptable by an agent. The proposal summary is required; lists (connectors, components, skills, risks, checks) default to empty.

- [ ] **Step 1: Write the failing test**

Add to `tests/test_cli.py`:

```python
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
    assert run_cli("init", str(tmp_path), "--business-name", "Acme").returncode == 0
    # Record enough intake facts to make intake ready
    from pyfpa.memory.intake import Intake, next_intake_questions, record_intake_fact
    from pyfpa.memory.workspace import workspace_path
    import subprocess, sys, json
    # Use CLI to record facts until ready
    workspace = workspace_path(tmp_path)
    intake_path = workspace / "intake.md"
    from pyfpa.memory.intake import load_intake, save_intake
    intake = load_intake(intake_path)
    from pyfpa.memory.intake import next_intake_questions
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
```

- [ ] **Step 2: Run tests to confirm failure**

```bash
cd /Volumes/Crucial/openfpa && python3 -m pytest tests/test_cli.py::test_onboarding_render_requires_ready_intake tests/test_cli.py::test_onboarding_render_writes_profile_and_proposal -v
```

Expected: FAIL.

- [ ] **Step 3: Add handler and parser in `pyfpa/cli.py`**

Add imports:
```python
from pyfpa.memory.onboarding import ArchitectureProposal, write_onboarding_outputs
from pyfpa.memory.intake import load_intake
```

Add handler:
```python
def command_onboarding_render(args: argparse.Namespace) -> int:
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
```

Add parser entry in `build_parser()`:
```python
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
```

- [ ] **Step 4: Run new tests**

```bash
cd /Volumes/Crucial/openfpa && python3 -m pytest tests/test_cli.py::test_onboarding_render_requires_ready_intake tests/test_cli.py::test_onboarding_render_writes_profile_and_proposal -v
```

Expected: PASS.

- [ ] **Step 5: Commit**

```bash
cd /Volumes/Crucial/openfpa
git add pyfpa/cli.py tests/test_cli.py
git commit -m "feat: add onboarding-render CLI subcommand"
```

---

## Task 10: Check line count; split into `cli_commands/` if over 800 lines

**Files:**
- Conditionally create: `pyfpa/cli_commands/__init__.py`, `pyfpa/cli_commands/learning.py`, `pyfpa/cli_commands/lineage.py`
- Conditionally modify: `pyfpa/cli.py`

- [ ] **Step 1: Check line count**

```bash
wc -l /Volumes/Crucial/openfpa/pyfpa/cli.py
```

- [ ] **Step 2: If under 800, skip to Task 11**

If the line count is under 800, no split is needed. Move to Task 11.

- [ ] **Step 3: If over 800, create `pyfpa/cli_commands/` split**

The split strategy: move the 6 new learning-loop handlers plus the correction/experiment handlers to `pyfpa/cli_commands/learning.py`, and the source/mapping/reconcile/connector handlers to `pyfpa/cli_commands/lineage.py`. Keep `build_parser()`, `main()`, `_success`, `_failure`, `_root`, `JsonArgumentParser`, and the `command_init` / `command_inspect_data` / `command_status` / `command_doctor` in `cli.py`.

Create `pyfpa/cli_commands/__init__.py` (empty):
```python
```

Create `pyfpa/cli_commands/learning.py`:
```python
from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

# Import shared helpers from cli to avoid re-defining
from pyfpa.cli import _failure, _root, _success, workspace_path, EXIT_OK, EXIT_FAILED
from pyfpa.memory.corrections import Correction, Override, load_corrections, save_correction
from pyfpa.memory.experiments import load_experiments
from pyfpa.backtest.learn import render_scorecard
from pyfpa.backtest.snapshot import load_snapshot
from pyfpa.memory.retrieval import build_context_pack, build_memory_index, search_memory
from pyfpa.memory.onboarding import ArchitectureProposal, write_onboarding_outputs
from pyfpa.memory.intake import load_intake


def command_correction_record(args: argparse.Namespace) -> int:
    # ... (same body as above)


def command_correction_list(args: argparse.Namespace) -> int:
    # ... (same body as above)


def command_scorecard_render(args: argparse.Namespace) -> int:
    # ... (same body as above)


def command_experiment_list(args: argparse.Namespace) -> int:
    # ... (same body as above)


def command_context_pack(args: argparse.Namespace) -> int:
    # ... (same body as above)


def command_onboarding_render(args: argparse.Namespace) -> int:
    # ... (same body as above)
```

**NOTE:** Only implement this step if `wc -l pyfpa/cli.py` reports over 800 after Task 9. If so, move the 6 handler bodies to `cli_commands/learning.py` and import them back in `cli.py`:
```python
from pyfpa.cli_commands.learning import (
    command_correction_record,
    command_correction_list,
    command_scorecard_render,
    command_experiment_list,
    command_context_pack,
    command_onboarding_render,
)
```

`python3 -m pyfpa.cli` continues to work because the entry point is `pyfpa/cli.py:main()`.

- [ ] **Step 4: Verify entry point still works**

```bash
cd /Volumes/Crucial/openfpa && python3 -m pyfpa.cli --help
```

Expected: help text listing all commands including the new ones.

- [ ] **Step 5: Run full suite**

```bash
cd /Volumes/Crucial/openfpa && python3 -m pytest tests/ -q --tb=short
```

Expected: all tests PASS.

- [ ] **Step 6: Confirm final line count**

```bash
wc -l /Volumes/Crucial/openfpa/pyfpa/cli.py
```

Expected: under 800.

- [ ] **Step 7: Commit (if split was done)**

```bash
cd /Volumes/Crucial/openfpa
git add pyfpa/cli_commands/ pyfpa/cli.py
git commit -m "refactor: split learning-loop handlers into cli_commands/learning.py"
```

---

## Task 11: Update README and AGENTS.md

**Files:**
- Modify: `README.md`
- Modify: `AGENTS.md`

- [ ] **Step 1: Add new commands to README CLI section**

In `README.md`, find the CLI command list block (around line 188-206). Add the 6 new commands:

```text
openfpa correction-record
openfpa correction-list
openfpa scorecard-render
openfpa experiment-list
openfpa context-pack
openfpa onboarding-render
```

Also add, immediately after the command list, the source-checkout note:

```text
In a source checkout without the `openfpa` console script installed, every
command also works as `python3 -m pyfpa.cli <command>`.
```

- [ ] **Step 2: Add new commands to AGENTS.md**

In `AGENTS.md`, in the "Company Onboarding" section under the CLI bullet list, add:

```
  - `openfpa correction-record <company-root> --slug <slug> --type <type> --target <target> --date <date>` after establishing a correction
  - `openfpa correction-list <company-root>` to review recorded corrections
  - `openfpa scorecard-render <company-root>` to rebuild scorecard.md from all snapshots
  - `openfpa experiment-list <company-root>` to review experiment records
  - `openfpa context-pack <company-root> --task "<task>"` to retrieve bounded memory for a task
  - `openfpa onboarding-render <company-root> --proposal-summary "<summary>"` when intake is ready
```

- [ ] **Step 3: Verify no em dashes introduced**

```bash
grep -rn -- "—" /Volumes/Crucial/openfpa/pyfpa/ /Volumes/Crucial/openfpa/tests/ /Volumes/Crucial/openfpa/README.md /Volumes/Crucial/openfpa/AGENTS.md
```

Expected: no output (no em dashes in modified files).

- [ ] **Step 4: Run full test suite one final time**

```bash
cd /Volumes/Crucial/openfpa && python3 -m pytest tests/ -q --tb=short
```

Expected: all tests PASS, count >= 235.

- [ ] **Step 5: Commit**

```bash
cd /Volumes/Crucial/openfpa
git add README.md AGENTS.md
git commit -m "docs: add learning-loop CLI commands to README and AGENTS.md"
```

---

## Self-Review

### Spec Coverage Check

| Spec requirement | Task covering it |
|---|---|
| Create `pyfpa/memory/inspection.py` with `inspect_data_files()` | Task 2 |
| Create `pyfpa/memory/diagnostics.py` with `validate_workspace()` returning pydantic model | Task 3 |
| Dedupe dir list: `WORKSPACE_DIRS` from workspace.py, delete `_REQUIRED_WORKSPACE_DIRS` from cli.py | Tasks 1, 4 |
| Unit tests for inspection and diagnostics | Tasks 2, 3 |
| `correction-record` subcommand | Task 5 |
| `correction-list` subcommand | Task 5 |
| `scorecard-render` subcommand | Task 6 |
| `experiment-list` subcommand | Task 7 |
| `context-pack` subcommand | Task 8 |
| `onboarding-render` subcommand | Task 9 |
| `doctor` extends to check corrections + snapshots | Task 3 (diagnostics.py includes these checks; `command_doctor` wraps it) |
| CLI tests matching existing pattern | Tasks 5-9 all use `run_cli` + `output_json` |
| `cli.py` under 800 lines | Task 10 |
| README source-checkout note | Task 11 |
| Fix `init` `next_command` hint to `python3 -m pyfpa.cli` form | Task 4 |
| AGENTS.md updated | Task 11 |
| Full suite green | Tasks 4, 10 |

### Placeholder Scan

No TBD, TODO, or "similar to" references. All code blocks are complete. The `cli_commands/learning.py` in Task 10 says "same body as above" -- that is intentional conditional logic (only implement if over 800 lines). The instruction is to copy the exact bodies defined in Tasks 5-9, which are fully spelled out.

### Type Consistency

- `InspectionResult` defined in Task 2, used in Task 4's `command_inspect_data` wrapper.
- `WorkspaceReport` defined in Task 3, used in Task 4's `command_doctor` wrapper.
- `WORKSPACE_DIRS` renamed in Task 1, imported in Tasks 3 and 4.
- `Correction`, `Override`, `save_correction`, `load_corrections` imported from `pyfpa.memory.corrections` -- matching the actual module API read during research.
- `load_experiments` imported from `pyfpa.memory.experiments` -- matches actual API.
- `render_scorecard(snapshots)` from `pyfpa.backtest.learn` -- matches actual signature.
- `load_snapshot(path)` from `pyfpa.backtest.snapshot` -- matches actual signature.
- `build_context_pack(index, task, *, categories, limit)` from `pyfpa.memory.retrieval` -- matches actual signature.
- `write_onboarding_outputs(intake, workspace, proposal)` from `pyfpa.memory.onboarding` -- matches actual signature.
- `ArchitectureProposal` from `pyfpa.memory.onboarding` -- matches actual class.
- `load_intake` from `pyfpa.memory.intake` -- already imported in cli.py for other commands.

All consistent.
