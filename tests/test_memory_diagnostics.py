from __future__ import annotations

import subprocess
import sys
from pathlib import Path

from pyfpa.memory.diagnostics import validate_workspace, WorkspaceReport


def _init_workspace(root: Path) -> None:
    """Minimal workspace scaffold for diagnostic tests."""
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
