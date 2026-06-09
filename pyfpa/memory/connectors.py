from __future__ import annotations

from math import isfinite
from pathlib import Path, PurePosixPath
import re
import shutil
import subprocess
import tempfile
from typing import Literal

import yaml
from pydantic import BaseModel, Field, field_validator, model_validator

from pyfpa.memory.lineage import MappingRegistry, reconcile_account_table


ConnectorAuth = Literal["none", "host_environment", "mcp"]
_CONNECTOR_NAME = re.compile(r"^[a-z][a-z0-9-]*$")


def _relative_path(value: str) -> str:
    value = value.strip()
    path = PurePosixPath(value)
    if not value or path.is_absolute() or ".." in path.parts:
        raise ValueError("path must be a non-empty relative path without '..'")
    return path.as_posix()


def _connector_name(value: str) -> str:
    if not _CONNECTOR_NAME.fullmatch(value):
        raise ValueError("connector name must use lowercase letters, numbers, and hyphens")
    return value


class ConnectorManifest(BaseModel):
    schema_version: int = 1
    name: str = Field(pattern=r"^[a-z][a-z0-9-]*$")
    source_id: str = Field(pattern=r"^[a-z][a-z0-9-]*$")
    description: str
    auth_method: ConnectorAuth
    source_account_column: str
    source_amount_column: str
    fixture_path: str
    fixture_command: list[str] = Field(min_length=1)
    expected_totals: dict[str, float] = Field(min_length=1)
    live_ready: bool = False
    live_command: list[str] = Field(default_factory=list)

    @field_validator(
        "description",
        "source_account_column",
        "source_amount_column",
    )
    @classmethod
    def validate_required_text(cls, value: str) -> str:
        value = value.strip()
        if not value:
            raise ValueError("value must not be empty")
        return value

    @field_validator("fixture_path")
    @classmethod
    def validate_fixture_path(cls, value: str) -> str:
        return _relative_path(value)

    @field_validator("fixture_command", "live_command")
    @classmethod
    def validate_commands(cls, value: list[str]) -> list[str]:
        command = [item.strip() for item in value]
        if any(not item for item in command):
            raise ValueError("command arguments must not be empty")
        return command

    @field_validator("expected_totals")
    @classmethod
    def validate_expected_totals(cls, value: dict[str, float]) -> dict[str, float]:
        if any(not key.strip() for key in value):
            raise ValueError("expected total names must not be empty")
        if any(not isfinite(amount) for amount in value.values()):
            raise ValueError("expected totals must be finite")
        return value

    @model_validator(mode="after")
    def validate_command_contract(self):
        if self.source_account_column == self.source_amount_column:
            raise ValueError("source account and amount columns must differ")
        fixture_tokens = set(self.fixture_command)
        if "{fixture}" not in fixture_tokens or "{output}" not in fixture_tokens:
            raise ValueError(
                "fixture_command must contain {fixture} and {output} arguments"
            )
        if "--live" in fixture_tokens:
            raise ValueError("fixture_command must not enable live mode")
        if self.live_ready and not self.live_command:
            raise ValueError("live_ready connectors require a live_command")
        return self


def connector_generated_root(company_root: str | Path) -> Path:
    return Path(company_root) / "connectors" / "generated"


def connector_bundle_path(company_root: str | Path, name: str) -> Path:
    return connector_generated_root(company_root) / _connector_name(name)


def load_connector_manifest(path: str | Path) -> ConnectorManifest:
    path = Path(path)
    if path.is_dir():
        path = path / "connector.yaml"
    if not path.exists():
        raise FileNotFoundError(f"connector manifest not found: {path}")
    return ConnectorManifest.model_validate(yaml.safe_load(path.read_text()) or {})


def save_connector_manifest(
    manifest: ConnectorManifest,
    path: str | Path,
) -> None:
    path = Path(path)
    if path.suffix != ".yaml":
        path = path / "connector.yaml"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(yaml.safe_dump(manifest.model_dump(), sort_keys=False))


def load_connector_manifests(company_root: str | Path) -> list[ConnectorManifest]:
    root = connector_generated_root(company_root)
    if not root.exists():
        return []
    manifests = []
    for bundle in sorted(
        path for path in root.iterdir()
        if path.is_dir() and not path.name.startswith(".")
    ):
        manifest = load_connector_manifest(bundle)
        if manifest.name != bundle.name:
            raise ValueError(
                f"connector directory {bundle.name!r} contains manifest for "
                f"{manifest.name!r}"
            )
        manifests.append(manifest)
    return manifests


def _connector_module(
    *,
    account_column: str,
    amount_column: str,
) -> str:
    return f'''from __future__ import annotations

import csv
from pathlib import Path


SOURCE_ACCOUNT_COLUMN = {account_column!r}
SOURCE_AMOUNT_COLUMN = {amount_column!r}


def _parse_amount(raw: str | None) -> float:
    value = (raw or "").strip().replace("$", "").replace(",", "")
    if value in ("", "-"):
        return 0.0
    negative = value.startswith("(") and value.endswith(")")
    if negative:
        value = value[1:-1]
    amount = float(value)
    return -amount if negative else amount


def normalize_fixture(path: str | Path) -> dict[str, float]:
    path = Path(path)
    result: dict[str, float] = {{}}
    with path.open(newline="") as handle:
        reader = csv.DictReader(handle)
        fields = reader.fieldnames or []
        required = {{SOURCE_ACCOUNT_COLUMN, SOURCE_AMOUNT_COLUMN}}
        if not required.issubset(fields):
            raise ValueError(
                f"expected columns {{sorted(required)}}, got {{fields}}"
            )
        for row in reader:
            account = (row.get(SOURCE_ACCOUNT_COLUMN) or "").strip()
            if not account:
                continue
            if account in result:
                raise ValueError(f"duplicate account: {{account}}")
            result[account] = _parse_amount(row.get(SOURCE_AMOUNT_COLUMN))
    return result


def extract_live() -> dict[str, float]:
    raise NotImplementedError(
        "Implement host-authenticated live extraction before setting live_ready"
    )


def write_normalized(values: dict[str, float], path: str | Path) -> None:
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="") as handle:
        writer = csv.writer(handle)
        writer.writerow(["Account", "Amount"])
        writer.writerows(sorted(values.items()))
'''


def _runner_module() -> str:
    return '''from __future__ import annotations

import argparse

from connector import extract_live, normalize_fixture, write_normalized


def main() -> None:
    parser = argparse.ArgumentParser()
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--fixture")
    mode.add_argument("--live", action="store_true")
    parser.add_argument("--output", required=True)
    args = parser.parse_args()

    values = extract_live() if args.live else normalize_fixture(args.fixture)
    write_normalized(values, args.output)


if __name__ == "__main__":
    main()
'''


def _readme(manifest: ConnectorManifest) -> str:
    return f"""# {manifest.name}

{manifest.description}

## Contract

- Source ID: `{manifest.source_id}`
- Authentication: `{manifest.auth_method}`
- Fixture: `{manifest.fixture_path}`
- Fixture output: canonical `Account,Amount` CSV
- Duplicate accounts: fail
- Unmapped accounts: fail
- Golden mapped totals: stored in `connector.yaml`

## Validate

```bash
openfpa connector-validate . --name {manifest.name}
```

Fixture validation never accesses a live system. Implement `extract_live()` in
`connector.py`, add a fixture-backed test for the source response shape, and set
`live_ready: true` only after the live command is safe and documented.

Never commit credentials or an unredacted production export.
"""


def scaffold_connector_bundle(
    company_root: str | Path,
    *,
    name: str,
    source_id: str,
    description: str,
    auth_method: ConnectorAuth,
    fixture: str | Path,
    account_column: str,
    amount_column: str,
    mappings: MappingRegistry,
    overwrite: bool = False,
) -> tuple[ConnectorManifest, dict]:
    company_root = Path(company_root)
    fixture = Path(fixture)
    if not fixture.exists():
        raise FileNotFoundError(f"connector fixture not found: {fixture}")
    if fixture.suffix.casefold() != ".csv":
        raise ValueError("connector scaffold currently requires a CSV fixture")

    reconciliation = reconcile_account_table(
        fixture,
        source_id=source_id,
        mappings=mappings,
        account_column=account_column,
        amount_column=amount_column,
    )
    if not reconciliation["passed"]:
        raise ValueError(
            "fixture must have no duplicate or unmapped accounts before scaffolding"
        )
    if not reconciliation["mapped_totals"]:
        raise ValueError("fixture must produce at least one mapped total")

    manifest = ConnectorManifest(
        name=name,
        source_id=source_id,
        description=description,
        auth_method=auth_method,
        source_account_column=account_column,
        source_amount_column=amount_column,
        fixture_path="fixtures/source.csv",
        fixture_command=[
            "python3",
            "run.py",
            "--fixture",
            "{fixture}",
            "--output",
            "{output}",
        ],
        expected_totals=reconciliation["mapped_totals"],
    )
    bundle = connector_bundle_path(company_root, name)
    if bundle.exists():
        if not overwrite:
            raise FileExistsError(f"connector bundle already exists: {bundle}")
        shutil.rmtree(bundle)

    (bundle / "fixtures").mkdir(parents=True)
    shutil.copyfile(fixture, bundle / manifest.fixture_path)
    save_connector_manifest(manifest, bundle)
    (bundle / "connector.py").write_text(
        _connector_module(
            account_column=account_column,
            amount_column=amount_column,
        )
    )
    (bundle / "run.py").write_text(_runner_module())
    (bundle / "README.md").write_text(_readme(manifest))
    return manifest, reconciliation


def validate_connector_bundle(
    company_root: str | Path,
    *,
    name: str,
    mappings: MappingRegistry,
    timeout: float = 30.0,
) -> dict:
    company_root = Path(company_root)
    bundle = connector_bundle_path(company_root, name)
    manifest = load_connector_manifest(bundle)
    if manifest.name != name:
        raise ValueError(
            f"connector directory {name!r} contains manifest for {manifest.name!r}"
        )
    fixture = (bundle / manifest.fixture_path).resolve()
    if not fixture.is_relative_to(bundle.resolve()):
        raise ValueError("fixture path escapes connector bundle")
    if not fixture.exists():
        raise FileNotFoundError(f"connector fixture not found: {fixture}")

    with tempfile.TemporaryDirectory() as temp_dir:
        output = Path(temp_dir) / "normalized.csv"
        command = [
            str(fixture) if item == "{fixture}"
            else str(output) if item == "{output}"
            else item
            for item in manifest.fixture_command
        ]
        completed = subprocess.run(
            command,
            cwd=bundle,
            text=True,
            capture_output=True,
            check=False,
            timeout=timeout,
        )
        if completed.returncode != 0:
            raise RuntimeError(
                f"fixture command failed with exit code {completed.returncode}: "
                f"{completed.stderr.strip()}"
            )
        if not output.exists():
            raise RuntimeError("fixture command did not create normalized output")
        reconciliation = reconcile_account_table(
            output,
            source_id=manifest.source_id,
            mappings=mappings,
            account_column="Account",
            amount_column="Amount",
            expected=manifest.expected_totals,
            tolerance=0.0,
        )
    return {
        "manifest": manifest.model_dump(),
        "command": command,
        "returncode": completed.returncode,
        "reconciliation": reconciliation,
        "passed": reconciliation["passed"],
    }
