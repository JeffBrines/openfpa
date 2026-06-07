"""Run the full pyfpa pipeline on the synthetic Ridgeline Chair Co. demo.

Usage:
    python examples/ridgeline/run_demo.py
Writes a markdown CFO briefing and an Excel forecast into docs/demo/.
"""
from __future__ import annotations

from pathlib import Path

import pyfpa
from pyfpa.io.loaders import load_cash13_config
from pyfpa.io.reporting import forecast_to_excel, to_briefing_md

_HERE = Path(__file__).resolve().parent
_REPO_ROOT = _HERE.parents[1]
_TITLE = "Ridgeline Chair Co."


def run_demo(output_dir: str | Path) -> dict:
    """Build the monthly + 13-week forecasts, render the briefing, and write
    briefing.md + forecast.xlsx into output_dir. Returns key figures."""
    out = Path(output_dir)
    out.mkdir(parents=True, exist_ok=True)

    monthly = pyfpa.cashflow_from_config(
        pyfpa.load_config(_HERE / "config.yaml")
    )
    cash13 = pyfpa.cash13_forecast(load_cash13_config(_HERE / "cash13.yaml"))
    runway = pyfpa.runway_summary(cash13)

    briefing = to_briefing_md(monthly, title=_TITLE, runway=runway)
    (out / "briefing.md").write_text(briefing)
    forecast_to_excel(monthly, out / "forecast.xlsx")

    return {
        "revenue_total": round(monthly["revenue"].sum()),
        "ebitda_total": round(monthly["ebitda"].sum()),
        "net_income_total": round(monthly["net_income"].sum()),
        "ending_cash_dec": round(monthly["ending_cash"].iloc[-1]),
        "runway_min_cash": round(runway["min_cash"]),
        "runway_min_week": runway["min_week"],
        "runway_first_negative_week": runway["first_negative_week"],
    }


if __name__ == "__main__":
    figures = run_demo(_REPO_ROOT / "docs/demo")
    print(f"Wrote briefing.md + forecast.xlsx to docs/demo/")
    for key, value in figures.items():
        print(f"  {key}: {value}")
