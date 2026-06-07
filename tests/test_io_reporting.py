import pyfpa
from pyfpa.io.reporting import to_briefing_md

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


def test_briefing_omits_runway_when_absent():
    md = to_briefing_md(_monthly())
    assert "13-Week Cash Runway" not in md
