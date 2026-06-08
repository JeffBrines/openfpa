import pytest
from pyfpa.analysis.reconcile import reconcile


def test_reconcile_flags_within_tolerance():
    model = {"revenue": 1000.0, "net_income": 100.0}
    actual = {"revenue": 1005.0, "net_income": 130.0}
    df = reconcile(model, actual, tolerance=0.01)
    rev = df.loc["revenue"]
    assert rev["variance"] == pytest.approx(-5.0)
    assert rev["variance_pct"] == pytest.approx(-5.0 / 1005.0)
    assert bool(rev["within_tolerance"]) is True
    ni = df.loc["net_income"]
    assert bool(ni["within_tolerance"]) is False


def test_reconcile_zero_actual():
    df = reconcile({"x": 0.0}, {"x": 0.0}, tolerance=0.01)
    assert bool(df.loc["x"]["within_tolerance"]) is True


def test_reconcile_missing_model_line_defaults_zero():
    # a line present in actual but absent from model is treated as model=0.0
    df = reconcile({}, {"revenue": 100.0}, tolerance=0.01)
    rev = df.loc["revenue"]
    assert rev["model"] == 0.0
    assert rev["variance"] == pytest.approx(-100.0)
    assert bool(rev["within_tolerance"]) is False
