"""Regression guard: the engine must keep reproducing Fox Factory's audited
actuals (Phase A) to the dollar. Shares the exact code path used by run_foxf.py.
"""
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
EXAMPLE = ROOT / "examples" / "foxfactory"
sys.path.insert(0, str(EXAMPLE))

pytestmark = pytest.mark.skipif(
    not (EXAMPLE / "data" / "income_statement.csv").exists(),
    reason="Fox Factory EDGAR data not pulled (run examples/foxfactory/pull_edgar.py)",
)


@pytest.mark.parametrize("fy,prior", [("FY2024", "FY2023"), ("FY2025", "FY2024")])
def test_phase_a_reconciles_to_the_dollar(fy, prior):
    import foxf_model as fm
    from pyfpa.analysis.reconcile import reconcile

    model = fm.phase_a_model(fy, prior)
    actual = fm.phase_a_actual(fy, prior)
    rec = reconcile(model, actual, tolerance=0.01)
    assert rec["within_tolerance"].all(), rec[["model", "actual", "variance_pct"]]
    # the operating economics and working-capital cash mechanic tie essentially exactly
    assert abs(rec.loc["adjusted_ebitda", "variance_pct"]) < 1e-9
    assert abs(rec.loc["operating_cash_flow_before_tax", "variance_pct"]) < 1e-6


def test_forecast_is_coherent():
    import foxf_model as fm

    forecast, segs = fm.build_forecast()
    assert len(forecast) == 24  # FY2026 + FY2027 monthly
    # forecast years are profitable (no impairment) and FCF-positive
    fy26 = forecast[forecast.index.year == 2026].sum()
    assert fy26["net_income"] > 0
    assert fy26["free_cash_flow"] > 0
    # segment net sales roll up to the consolidated forecast revenue
    from pyfpa.analysis.segments import roll_up_segments
    seg_sales = float(roll_up_segments(segs["FY2026"])["net_sales"])
    assert seg_sales == pytest.approx(float(fy26["revenue"]), rel=1e-9)
