from __future__ import annotations

import csv
from collections import Counter
from pathlib import Path
from typing import Literal

import pandas as pd
import yaml
from pydantic import BaseModel, Field, field_validator, model_validator

from pyfpa.io.pl_csv import _parse_amount


SourceKind = Literal[
    "local_file",
    "shared_folder",
    "accounting_system",
    "operating_system",
    "api",
    "public_filing",
    "manual",
]
MappingStatus = Literal["mapped", "ignored"]


class SourceRecord(BaseModel):
    source_id: str = Field(pattern=r"^[a-z][a-z0-9-]*$")
    kind: SourceKind
    location: str
    entity: str
    currency: str = Field(min_length=3, max_length=3)
    periods: list[str] = Field(default_factory=list)
    extraction_method: str
    refreshed_at: str = ""
    notes: str = ""

    @field_validator("location", "entity", "extraction_method")
    @classmethod
    def validate_required_text(cls, value: str) -> str:
        value = value.strip()
        if not value:
            raise ValueError("value must not be empty")
        return value

    @field_validator("currency")
    @classmethod
    def normalize_currency(cls, value: str) -> str:
        return value.upper()

    @field_validator("periods")
    @classmethod
    def normalize_periods(cls, value: list[str]) -> list[str]:
        periods = [item.strip() for item in value]
        if any(not item for item in periods):
            raise ValueError("periods must not contain empty values")
        return list(dict.fromkeys(periods))


class SourceRegistry(BaseModel):
    schema_version: int = 1
    sources: list[SourceRecord] = Field(default_factory=list)

    @model_validator(mode="after")
    def validate_unique_source_ids(self):
        source_ids = [source.source_id for source in self.sources]
        duplicates = sorted(
            source_id
            for source_id, count in Counter(source_ids).items()
            if count > 1
        )
        if duplicates:
            raise ValueError(f"duplicate source IDs: {duplicates}")
        return self


class MappingRule(BaseModel):
    source_id: str = Field(pattern=r"^[a-z][a-z0-9-]*$")
    source_value: str
    target: str
    status: MappingStatus = "mapped"
    rationale: str = ""

    @field_validator("source_value", "target", "rationale")
    @classmethod
    def normalize_text(cls, value: str) -> str:
        return value.strip()

    @model_validator(mode="after")
    def validate_rule(self):
        if not self.source_value:
            raise ValueError("source_value must not be empty")
        if self.status == "mapped" and not self.target:
            raise ValueError("mapped rules require a target")
        if self.status == "ignored" and not self.rationale:
            raise ValueError("ignored rules require a rationale")
        return self


class MappingRegistry(BaseModel):
    schema_version: int = 1
    mappings: list[MappingRule] = Field(default_factory=list)

    @model_validator(mode="after")
    def validate_unique_mapping_keys(self):
        keys = [
            (mapping.source_id, mapping.source_value)
            for mapping in self.mappings
        ]
        duplicates = sorted(
            f"{source_id}:{source_value}"
            for (source_id, source_value), count in Counter(keys).items()
            if count > 1
        )
        if duplicates:
            raise ValueError(f"duplicate mapping keys: {duplicates}")
        return self


def load_source_registry(path: str | Path) -> SourceRegistry:
    path = Path(path)
    if not path.exists():
        return SourceRegistry()
    return SourceRegistry.model_validate(yaml.safe_load(path.read_text()) or {})


def save_source_registry(registry: SourceRegistry, path: str | Path) -> None:
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(yaml.safe_dump(registry.model_dump(), sort_keys=False))


def register_source(
    registry: SourceRegistry,
    source: SourceRecord,
    *,
    overwrite: bool = False,
) -> SourceRegistry:
    existing = next(
        (item for item in registry.sources if item.source_id == source.source_id),
        None,
    )
    if existing is not None and not overwrite:
        raise ValueError(f"source already registered: {source.source_id}")
    retained = [item for item in registry.sources if item.source_id != source.source_id]
    return registry.model_copy(update={
        "sources": sorted([*retained, source], key=lambda item: item.source_id)
    })


def load_mapping_registry(path: str | Path) -> MappingRegistry:
    path = Path(path)
    if not path.exists():
        return MappingRegistry()
    return MappingRegistry.model_validate(yaml.safe_load(path.read_text()) or {})


def save_mapping_registry(registry: MappingRegistry, path: str | Path) -> None:
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(yaml.safe_dump(registry.model_dump(), sort_keys=False))


def register_mapping(
    registry: MappingRegistry,
    mapping: MappingRule,
    *,
    overwrite: bool = False,
) -> MappingRegistry:
    existing = next(
        (
            item for item in registry.mappings
            if item.source_id == mapping.source_id
            and item.source_value == mapping.source_value
        ),
        None,
    )
    if existing is not None and not overwrite:
        raise ValueError(
            f"mapping already registered: {mapping.source_id}:{mapping.source_value}"
        )
    retained = [
        item for item in registry.mappings
        if not (
            item.source_id == mapping.source_id
            and item.source_value == mapping.source_value
        )
    ]
    return registry.model_copy(update={
        "mappings": sorted(
            [*retained, mapping],
            key=lambda item: (item.source_id, item.source_value),
        )
    })


def profile_table(path: str | Path) -> dict:
    path = Path(path)
    if not path.exists():
        raise FileNotFoundError(f"source file not found: {path}")
    suffix = path.suffix.casefold()
    if suffix == ".csv":
        frame = pd.read_csv(path)
    elif suffix == ".tsv":
        frame = pd.read_csv(path, sep="\t")
    elif suffix in {".xls", ".xlsm", ".xlsx"}:
        frame = pd.read_excel(path)
    else:
        raise ValueError("source-profile supports CSV, TSV, XLS, XLSM, and XLSX")
    return {
        "path": str(path),
        "rows": int(len(frame)),
        "columns": [str(column) for column in frame.columns],
        "empty_by_column": {
            str(column): int(frame[column].isna().sum())
            for column in frame.columns
        },
        "duplicate_rows": int(frame.duplicated().sum()),
    }


def reconcile_account_table(
    path: str | Path,
    *,
    source_id: str,
    mappings: MappingRegistry,
    account_column: str,
    amount_column: str,
    expected: dict[str, float] | None = None,
    tolerance: float = 0.01,
) -> dict:
    path = Path(path)
    if path.suffix.casefold() != ".csv":
        raise ValueError("reconcile-source currently supports CSV files")
    rows: list[tuple[str, float]] = []
    with path.open(newline="") as handle:
        reader = csv.DictReader(handle)
        fields = reader.fieldnames or []
        if account_column not in fields or amount_column not in fields:
            raise ValueError(
                f"expected columns {account_column!r} and {amount_column!r}, got {fields}"
            )
        for row in reader:
            account = (row.get(account_column) or "").strip()
            if not account:
                continue
            rows.append((account, _parse_amount(row.get(amount_column))))

    accounts = [account for account, _ in rows]
    duplicates = sorted(
        account for account, count in Counter(accounts).items() if count > 1
    )
    rules = {
        item.source_value: item
        for item in mappings.mappings
        if item.source_id == source_id
    }
    unmapped = sorted({
        account for account in accounts if account not in rules
    })
    ignored = sorted({
        account for account in accounts
        if account in rules and rules[account].status == "ignored"
    })
    mapped_totals: dict[str, float] = {}
    for account, amount in rows:
        rule = rules.get(account)
        if rule is None or rule.status == "ignored":
            continue
        mapped_totals[rule.target] = mapped_totals.get(rule.target, 0.0) + amount

    variances: dict[str, dict[str, float | bool]] = {}
    expected = expected or {}
    for target in sorted(set(mapped_totals) | set(expected)):
        mapped = float(mapped_totals.get(target, 0.0))
        expected_value = float(expected.get(target, 0.0))
        variance = mapped - expected_value
        variance_pct = variance / expected_value if expected_value else 0.0
        within = mapped == expected_value if expected_value == 0 else abs(variance_pct) <= tolerance
        variances[target] = {
            "mapped": mapped,
            "expected": expected_value,
            "variance": variance,
            "variance_pct": variance_pct,
            "within_tolerance": within,
        }

    expected_passed = all(
        item["within_tolerance"] for item in variances.values()
    ) if expected else True
    passed = not duplicates and not unmapped and expected_passed
    return {
        "source_id": source_id,
        "path": str(path),
        "row_count": len(rows),
        "source_total": sum(amount for _, amount in rows),
        "mapped_total": sum(mapped_totals.values()),
        "mapped_totals": mapped_totals,
        "duplicates": duplicates,
        "unmapped": unmapped,
        "ignored": ignored,
        "expected_provided": bool(expected),
        "variances": variances,
        "passed": passed,
    }
