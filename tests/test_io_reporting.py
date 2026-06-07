import pyfpa
import pandas as pd
from pyfpa.io.reporting import to_briefing_md, forecast_to_excel

REPO_ROOT = __import__("pathlib").Path(__file__).resolve().parents[1]


def _monthly():
    return pyfpa.cashflow_from_config(
        pyfpa.load_config(REPO_ROOT / "examples/ridgeline/config.yaml")
    )


def test_briefing_has_title_headline_and_table():
    md = to_briefing_md(_monthly(), title="Ridgeline Briefing")
    assert md.startswith("# Ridgeline Briefing")
    assert "## Headline" in md
    assert "**Revenue:**" in md
    assert "**Ending cash:**" in md
    assert "## Monthly" in md
    # 12 month rows in the table (one pipe-row per month)
    assert md.count("| 2026-") == 12


def test_briefing_includes_runway_when_provided():
    runway = {"min_cash": -85000.0, "min_week": 6, "first_negative_week": 3}
    md = to_briefing_md(_monthly(), runway=runway)
    assert "## 13-Week Cash Runway" in md
    assert "week 6" in md
    assert "week 3" in md
    # negative money renders as -$85,000, not $-85,000
    assert "-$85,000" in md
    assert "$-85,000" not in md


def test_briefing_omits_runway_when_absent():
    md = to_briefing_md(_monthly())
    assert "13-Week Cash Runway" not in md


def test_forecast_to_excel_roundtrip(tmp_path):
    df = _monthly()
    out = tmp_path / "forecast.xlsx"
    forecast_to_excel(df, out)
    assert out.exists()
    back = pd.read_excel(out, sheet_name="Forecast", index_col=0)
    assert len(back) == len(df)
    assert "ending_cash" in back.columns


def test_briefing_missing_columns_raises():
    import pytest
    bad = pd.DataFrame({"revenue": [1.0]})  # missing ebitda/net_income/ending_cash
    with pytest.raises(ValueError):
        to_briefing_md(bad)
