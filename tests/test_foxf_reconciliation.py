"""Regression guards for the Fox Factory real-company example.

Phase A reproduces known actual-driver mechanics; Phase B is the independent
FY2025 holdout; Phases C/D cover the forward forecast and sensitivity.
"""
import subprocess
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
def test_phase_a_reproduces_actual_driver_mechanics(fy, prior):
    import foxf_model as fm
    from pyfpa.analysis.reconcile import reconcile

    model = fm.phase_a_model(fy, prior)
    actual = fm.phase_a_actual(fy, prior)
    rec = reconcile(model, actual, tolerance=0.01)
    assert rec["within_tolerance"].all(), rec[["model", "actual", "variance_pct"]]
    # These target-year drivers are inputs, so this validates arithmetic, not forecasting.
    assert abs(rec.loc["adjusted_ebitda", "variance_pct"]) < 1e-9
    assert abs(rec.loc["operating_cash_flow_before_tax", "variance_pct"]) < 1e-6


def test_historical_holdout_proposes_refined_challenger_and_broad_is_weaker():
    """Verify research loop outcomes after the improvement-clamp fix.

    Before clamping, broad recovery (epoch 001) was discarded because a near-zero
    adjusted_ebitda_error baseline produced an improvement of -18.85, swamping the
    weighted average. After clamping to [-1, +1], that metric contributes -1.0 and
    broad squeaks over min_improvement. Refined (epoch 002) is still far stronger.
    """
    import foxf_model as fm

    broad, refined = fm.historical_research_epochs()
    assert broad.evaluation.promotion_eligible is True
    assert broad.evaluation.per_metric_improvement["adjusted_ebitda_error"] == pytest.approx(
        -1.0
    )
    assert broad.evaluation.objective_gain > 0
    assert broad.evaluation.objective_gain < 0.20
    assert refined.status == "proposed"
    assert refined.evaluation.promotion_eligible is True
    assert refined.evaluation.objective_gain > 0.50
    for metric, champion in refined.evaluation.champion_metrics.items():
        assert refined.evaluation.challenger_metrics[metric] < champion


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


def test_forecast_year_boundary_uses_modeled_closing_working_capital():
    import foxf_model as fm

    forecast, _ = fm.build_forecast()
    wc = fm.wc_days("FY2025")
    dec = forecast.loc["2026-12"]
    jan = forecast.loc["2027-01"]
    dec_ar = dec["revenue"] * wc.dso_days / 30
    dec_ap = dec["cogs"] * wc.dpo_days / 30
    dec_inventory = dec["cogs"] * wc.dio_days / 30
    jan_ar = jan["revenue"] * wc.dso_days / 30
    jan_ap = jan["cogs"] * wc.dpo_days / 30
    jan_inventory = jan["cogs"] * wc.dio_days / 30
    expected = -(jan_ar - dec_ar) + (jan_ap - dec_ap) - (jan_inventory - dec_inventory)

    assert jan["wc_cash_impact"] == pytest.approx(expected)


def test_foxf_pipeline_is_registered_for_agent_discovery():
    from pyfpa.memory.entrypoints import load_entrypoint_registry

    registry = load_entrypoint_registry(EXAMPLE / ".fpa" / "models" / "entrypoints.yaml")
    entrypoint = next(item for item in registry.entrypoints if item.name == "foxf-pipeline")

    assert entrypoint.kind == "forecast"
    assert entrypoint.command == ["python3", "run_foxf.py"]
    assert "output/foxf-forecast.xlsx" in entrypoint.outputs
    assert (EXAMPLE / ".fpa" / "decisions" / "initial-model-architecture.md").exists()


def test_foxf_sources_and_mappings_are_registered():
    from pyfpa.memory.lineage import (
        load_mapping_registry,
        load_source_registry,
    )

    sources = load_source_registry(EXAMPLE / ".fpa" / "sources" / "registry.yaml")
    mappings = load_mapping_registry(EXAMPLE / ".fpa" / "mappings" / "registry.yaml")

    assert {source.source_id for source in sources.sources} == {
        "foxf-balance-sheet",
        "foxf-cash-flow",
        "foxf-income-statement",
        "foxf-quarterly",
        "foxf-segments",
    }
    assert all(source.kind == "public_filing" for source in sources.sources)
    assert all(source.currency == "USD" for source in sources.sources)
    assert any(
        mapping.source_id == "foxf-income-statement"
        and mapping.source_value == "net_sales"
        and mapping.target == "income_statement.net_sales"
        for mapping in mappings.mappings
    )
    assert any(
        mapping.source_id == "foxf-segments"
        and mapping.source_value == "PVG.net_sales"
        and mapping.target == "segments.PVG.net_sales"
        for mapping in mappings.mappings
    )


def test_foxf_income_statement_mapping_covers_every_source_row():
    result = subprocess.run(
        [
            sys.executable,
            "-m",
            "pyfpa.cli",
            "reconcile-source",
            str(EXAMPLE),
            "--source-id",
            "foxf-income-statement",
            "--account-column",
            "line",
            "--amount-column",
            "FY2025",
        ],
        cwd=ROOT,
        text=True,
        capture_output=True,
        check=False,
    )

    assert result.returncode == 0, result.stdout


def test_foxf_workspace_passes_agent_toolbelt_diagnostics():
    result = subprocess.run(
        [sys.executable, "-m", "pyfpa.cli", "doctor", str(EXAMPLE)],
        cwd=ROOT,
        text=True,
        capture_output=True,
        check=False,
    )

    assert result.returncode == 0, result.stdout
