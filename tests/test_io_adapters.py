import pytest
from pyfpa.io import adapters


@pytest.mark.parametrize("fetch", [
    adapters.from_netsuite,
    adapters.from_quickbooks,
    adapters.from_shopify,
])
def test_adapter_returns_nonempty_normalized_mapping(fetch):
    result = fetch()
    assert isinstance(result, dict)
    assert len(result) > 0
    assert all(isinstance(k, str) for k in result)
    assert all(isinstance(v, float) for v in result.values())


def test_netsuite_fixture_values():
    result = adapters.from_netsuite()
    assert result["Cost of Goods Sold"] == -2_900_000.0


def test_adapter_accepts_custom_fixture(tmp_path):
    custom = tmp_path / "custom.csv"
    custom.write_text("Account,Amount\nFoo,123\n")
    assert adapters.from_quickbooks(fixture=custom) == {"Foo": 123.0}
