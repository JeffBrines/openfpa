import pytest
from pyfpa.memory.paths import _set_by_path


def test_set_nested_scalar():
    data = {"working_capital": {"dio_days": 30.0}}
    _set_by_path(data, "working_capital.dio_days", 45.0)
    assert data["working_capital"]["dio_days"] == 45.0


def test_set_list_index():
    data = {"channels": [{"seasonality": [1.0] * 12}]}
    _set_by_path(data, "channels[0].seasonality[11]", 2.0)
    assert data["channels"][0]["seasonality"][11] == 2.0


def test_set_star_applies_to_all_list_items():
    data = {"channels": [{"cogs_pct": 0.5}, {"cogs_pct": 0.4}]}
    _set_by_path(data, "channels[*].cogs_pct", 0.6)
    assert [c["cogs_pct"] for c in data["channels"]] == [0.6, 0.6]


def test_bad_path_raises_valueerror():
    with pytest.raises(ValueError):
        _set_by_path({"a": {}}, "a.missing.deep", 1.0)
    with pytest.raises(ValueError):
        _set_by_path({"a": 1}, "a[", 1.0)  # malformed segment
