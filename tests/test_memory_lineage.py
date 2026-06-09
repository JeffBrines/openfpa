import pytest

from pyfpa.memory.lineage import (
    MappingRegistry,
    MappingRule,
    SourceRecord,
    SourceRegistry,
    load_mapping_registry,
    load_source_registry,
    profile_table,
    reconcile_account_table,
    register_mapping,
    register_source,
    save_mapping_registry,
    save_source_registry,
)


def source() -> SourceRecord:
    return SourceRecord(
        source_id="gl-actuals",
        kind="local_file",
        location="data/gl.csv",
        entity="Acme",
        currency="usd",
        periods=["2026-01"],
        extraction_method="Manual export",
    )


def test_source_and_mapping_registries_round_trip(tmp_path):
    source_path = tmp_path / "sources.yaml"
    mapping_path = tmp_path / "mappings.yaml"
    sources = register_source(SourceRegistry(), source())
    mappings = register_mapping(
        MappingRegistry(),
        MappingRule(
            source_id="gl-actuals",
            source_value="Product Revenue",
            target="revenue",
        ),
    )

    save_source_registry(sources, source_path)
    save_mapping_registry(mappings, mapping_path)

    assert load_source_registry(source_path) == sources
    assert load_mapping_registry(mapping_path) == mappings
    assert sources.sources[0].currency == "USD"


def test_registry_updates_require_explicit_overwrite():
    sources = register_source(SourceRegistry(), source())
    mappings = register_mapping(
        MappingRegistry(),
        MappingRule(source_id="gl-actuals", source_value="Rent", target="opex.rent"),
    )

    with pytest.raises(ValueError, match="already registered"):
        register_source(sources, source())
    with pytest.raises(ValueError, match="already registered"):
        register_mapping(
            mappings,
            MappingRule(source_id="gl-actuals", source_value="Rent", target="opex.rent"),
        )


def test_registries_reject_duplicate_keys():
    with pytest.raises(ValueError, match="duplicate source IDs"):
        SourceRegistry(sources=[source(), source()])
    mapping = MappingRule(
        source_id="gl-actuals",
        source_value="Rent",
        target="opex.rent",
    )
    with pytest.raises(ValueError, match="duplicate mapping keys"):
        MappingRegistry(mappings=[mapping, mapping])


def test_ignored_mapping_requires_rationale():
    with pytest.raises(ValueError, match="ignored rules require a rationale"):
        MappingRule(
            source_id="gl-actuals",
            source_value="Subtotal",
            target="",
            status="ignored",
        )


def test_profile_table_reports_shape_and_duplicates(tmp_path):
    path = tmp_path / "actuals.csv"
    path.write_text("Account,Amount\nRevenue,10\nRevenue,10\nRent,\n")

    profile = profile_table(path)

    assert profile["rows"] == 3
    assert profile["columns"] == ["Account", "Amount"]
    assert profile["empty_by_column"]["Amount"] == 1
    assert profile["duplicate_rows"] == 1


def test_reconcile_account_table_reports_unmapped_duplicates_and_variance(tmp_path):
    path = tmp_path / "actuals.csv"
    path.write_text(
        "Account,Amount\n"
        "Product Revenue,100\n"
        "Product Revenue,50\n"
        "Rent,(20)\n"
        "Mystery,5\n"
    )
    mappings = MappingRegistry(mappings=[
        MappingRule(
            source_id="gl-actuals",
            source_value="Product Revenue",
            target="revenue",
        ),
        MappingRule(
            source_id="gl-actuals",
            source_value="Rent",
            target="opex",
        ),
    ])

    result = reconcile_account_table(
        path,
        source_id="gl-actuals",
        mappings=mappings,
        account_column="Account",
        amount_column="Amount",
        expected={"revenue": 140, "opex": -20},
    )

    assert result["passed"] is False
    assert result["duplicates"] == ["Product Revenue"]
    assert result["unmapped"] == ["Mystery"]
    assert result["mapped_totals"] == {"revenue": 150.0, "opex": -20.0}
    assert result["variances"]["revenue"]["within_tolerance"] is False


def test_ignored_mapping_does_not_count_as_unmapped(tmp_path):
    path = tmp_path / "actuals.csv"
    path.write_text("Account,Amount\nSubtotal,100\n")
    mappings = MappingRegistry(mappings=[
        MappingRule(
            source_id="gl-actuals",
            source_value="Subtotal",
            target="",
            status="ignored",
            rationale="Presentation subtotal",
        )
    ])

    result = reconcile_account_table(
        path,
        source_id="gl-actuals",
        mappings=mappings,
        account_column="Account",
        amount_column="Amount",
    )

    assert result["passed"] is True
    assert result["ignored"] == ["Subtotal"]
    assert result["unmapped"] == []
