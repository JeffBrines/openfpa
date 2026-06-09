from __future__ import annotations

import os
import re
from pathlib import Path
from typing import Any

from pydantic import BaseModel


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
