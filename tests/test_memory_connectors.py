from pathlib import Path

import pytest

from pyfpa.memory.connectors import (
    ConnectorManifest,
    connector_bundle_path,
    load_connector_manifest,
    load_connector_manifests,
    scaffold_connector_bundle,
    validate_connector_bundle,
)
from pyfpa.memory.lineage import MappingRegistry, MappingRule


def mappings() -> MappingRegistry:
    return MappingRegistry(mappings=[
        MappingRule(
            source_id="gl-actuals",
            source_value="Product Revenue",
            target="revenue.product",
        ),
        MappingRule(
            source_id="gl-actuals",
            source_value="Rent",
            target="opex.rent",
        ),
    ])


def fixture(path: Path) -> Path:
    path.write_text("Account,Amount\nProduct Revenue,100\nRent,(20)\n")
    return path


def test_connector_manifest_rejects_unsafe_fixture_paths():
    with pytest.raises(ValueError, match="relative path"):
        ConnectorManifest(
            name="quickbooks-pl",
            source_id="gl-actuals",
            description="Pull the monthly P&L.",
            auth_method="host_environment",
            source_account_column="Account",
            source_amount_column="Amount",
            fixture_path="../production.csv",
            fixture_command=[
                "python3",
                "run.py",
                "--fixture",
                "{fixture}",
                "--output",
                "{output}",
            ],
            expected_totals={"revenue.product": 100.0},
        )


def test_connector_bundle_path_rejects_unsafe_name(tmp_path):
    with pytest.raises(ValueError, match="connector name"):
        connector_bundle_path(tmp_path, "../../outside")


def test_connector_manifest_requires_live_command_when_marked_ready():
    with pytest.raises(ValueError, match="live_command"):
        ConnectorManifest(
            name="quickbooks-pl",
            source_id="gl-actuals",
            description="Pull the monthly P&L.",
            auth_method="host_environment",
            source_account_column="Account",
            source_amount_column="Amount",
            fixture_path="fixtures/source.csv",
            fixture_command=[
                "python3",
                "run.py",
                "--fixture",
                "{fixture}",
                "--output",
                "{output}",
            ],
            expected_totals={"revenue.product": 100.0},
            live_ready=True,
        )


def test_connector_listing_rejects_bundle_without_manifest(tmp_path):
    (tmp_path / "connectors" / "generated" / "broken").mkdir(parents=True)

    with pytest.raises(FileNotFoundError, match="manifest not found"):
        load_connector_manifests(tmp_path)


def test_scaffold_and_validate_connector_bundle(tmp_path):
    source_fixture = fixture(tmp_path / "redacted.csv")

    manifest, reconciliation = scaffold_connector_bundle(
        tmp_path,
        name="quickbooks-pl",
        source_id="gl-actuals",
        description="Pull and normalize the monthly P&L.",
        auth_method="host_environment",
        fixture=source_fixture,
        account_column="Account",
        amount_column="Amount",
        mappings=mappings(),
    )

    bundle = tmp_path / "connectors" / "generated" / "quickbooks-pl"
    assert manifest.expected_totals == {
        "revenue.product": 100.0,
        "opex.rent": -20.0,
    }
    assert reconciliation["passed"] is True
    assert (bundle / "connector.yaml").exists()
    assert (bundle / "connector.py").exists()
    assert (bundle / "run.py").exists()
    assert (bundle / "fixtures" / "source.csv").read_text() == source_fixture.read_text()
    assert load_connector_manifest(bundle) == manifest
    assert load_connector_manifests(tmp_path) == [manifest]

    result = validate_connector_bundle(
        tmp_path,
        name="quickbooks-pl",
        mappings=mappings(),
    )

    assert result["passed"] is True
    assert result["reconciliation"]["unmapped"] == []
    assert result["reconciliation"]["mapped_totals"] == manifest.expected_totals


def test_scaffold_requires_explicit_overwrite(tmp_path):
    source_fixture = fixture(tmp_path / "redacted.csv")
    kwargs = {
        "name": "quickbooks-pl",
        "source_id": "gl-actuals",
        "description": "Pull and normalize the monthly P&L.",
        "auth_method": "host_environment",
        "fixture": source_fixture,
        "account_column": "Account",
        "amount_column": "Amount",
        "mappings": mappings(),
    }
    scaffold_connector_bundle(tmp_path, **kwargs)

    with pytest.raises(FileExistsError, match="already exists"):
        scaffold_connector_bundle(tmp_path, **kwargs)

    manifest, _ = scaffold_connector_bundle(tmp_path, overwrite=True, **kwargs)
    assert manifest.name == "quickbooks-pl"


def test_scaffold_rejects_unmapped_fixture(tmp_path):
    source_fixture = tmp_path / "redacted.csv"
    source_fixture.write_text("Account,Amount\nMystery,10\n")

    with pytest.raises(ValueError, match="duplicate or unmapped"):
        scaffold_connector_bundle(
            tmp_path,
            name="quickbooks-pl",
            source_id="gl-actuals",
            description="Pull and normalize the monthly P&L.",
            auth_method="host_environment",
            fixture=source_fixture,
            account_column="Account",
            amount_column="Amount",
            mappings=mappings(),
        )

    assert not (
        tmp_path / "connectors" / "generated" / "quickbooks-pl"
    ).exists()


def test_validation_detects_golden_total_regression(tmp_path):
    source_fixture = fixture(tmp_path / "redacted.csv")
    scaffold_connector_bundle(
        tmp_path,
        name="quickbooks-pl",
        source_id="gl-actuals",
        description="Pull and normalize the monthly P&L.",
        auth_method="host_environment",
        fixture=source_fixture,
        account_column="Account",
        amount_column="Amount",
        mappings=mappings(),
    )
    connector_file = (
        tmp_path
        / "connectors"
        / "generated"
        / "quickbooks-pl"
        / "fixtures"
        / "source.csv"
    )
    connector_file.write_text("Account,Amount\nProduct Revenue,90\nRent,(20)\n")

    result = validate_connector_bundle(
        tmp_path,
        name="quickbooks-pl",
        mappings=mappings(),
    )

    assert result["passed"] is False
    assert (
        result["reconciliation"]["variances"]["revenue.product"][
            "within_tolerance"
        ]
        is False
    )
