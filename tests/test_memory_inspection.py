from __future__ import annotations

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
