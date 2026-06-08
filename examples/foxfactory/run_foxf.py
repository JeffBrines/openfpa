"""Fox Factory worked example — full pipeline.

Phase A reconciles the pyfpa engine against audited FY2024/FY2025 actuals.
Phase B forecasts FY2026-FY2027 at the segment level, anchored to Q1 FY2026.
Phase C models a Marucci-divestiture FCF/leverage sensitivity.

Run:  python3 examples/foxfactory/run_foxf.py
Outputs land in examples/foxfactory/output/.
"""
from __future__ import annotations

from pathlib import Path

import pandas as pd

import foxf_model as fm
from pyfpa.analysis.reconcile import reconcile
from pyfpa.analysis.segments import segment_pnl

OUT = Path(__file__).parent / "output"


def _m(v: float) -> str:
    """Format a dollar figure in millions."""
    return f"-${abs(v) / 1e6:,.1f}M" if v < 0 else f"${v / 1e6:,.1f}M"


# --------------------------------------------------------------------------- #
# Phase A
# --------------------------------------------------------------------------- #
def phase_a() -> str:
    lines = [
        "# Phase A — Engine reconciliation vs audited actuals",
        "",
        "The pyfpa engine is driven with Fox Factory's **actual** reported drivers",
        "(segment net sales, blended COGS%, working-capital days, D&A, capex) and",
        "its output is compared to the reported figures. Tolerance: 1%.",
        "",
    ]
    for fy, prior in [("FY2024", "FY2023"), ("FY2025", "FY2024")]:
        model = fm.phase_a_model(fy, prior)
        actual = fm.phase_a_actual(fy, prior)
        rec = reconcile(model, actual, tolerance=0.01)
        lines += [f"## {fy}", "", "| Line | Model | Reported | Variance | Tie |",
                  "|---|--:|--:|--:|:--:|"]
        for name, r in rec.iterrows():
            tie = "✅" if r["within_tolerance"] else "⚠️"
            lines.append(
                f"| {name} | {_m(r['model'])} | {_m(r['actual'])} | "
                f"{r['variance_pct'] * 100:+.2f}% | {tie} |"
            )
        lines.append("")
    lines += [
        "## What the engine does not model (documented bridge)",
        "",
        "- **FY2025 goodwill impairment of $557.3M** (non-cash) — drove GAAP operating",
        "  income to -$522.9M and a -$544.6M net loss even as revenue recovered. The",
        "  lean engine models the operating business; the impairment is a discrete",
        "  non-cash item shown here, not forced through the engine.",
        "- **Discrete tax items** — Fox booked tax *benefits* in FY2024/FY2025; the",
        "  engine's tax model only taxes positive income, so net income is bridged",
        "  separately, not reconciled here.",
        "- Reconciliation therefore ties the **operating economics and the",
        "  working-capital cash mechanic** exactly, and lists the below-the-line items",
        "  explicitly — which is how a CFO would expect a lean model to behave.",
        "",
    ]
    return "\n".join(lines)


# --------------------------------------------------------------------------- #
# Phase B
# --------------------------------------------------------------------------- #
def _annual(forecast: pd.DataFrame, year: int) -> pd.Series:
    return forecast[forecast.index.year == year].sum()


def phase_b(forecast: pd.DataFrame, segs: dict) -> str:
    lines = [
        "# Phase B — FY2026-FY2027 segment-level forecast",
        "",
        "Base = FY2025 actuals. FY2026 net-sales growth is anchored to the reported",
        "Q1 FY2026 print (+3.8% YoY). Adjusted-EBITDA margins step modestly off FY2025.",
        "",
        "## Consolidated",
        "",
        "| Metric | FY2026 | FY2027 |",
        "|---|--:|--:|",
    ]
    a26, a27 = _annual(forecast, 2026), _annual(forecast, 2027)
    rows = [
        ("Net sales", "revenue"), ("Gross profit", "gross_profit"),
        ("Adjusted EBITDA", "ebitda"), ("Net income", "net_income"),
        ("Operating cash flow", "operating_cash_flow"), ("Free cash flow", "free_cash_flow"),
    ]
    for label, col in rows:
        lines.append(f"| {label} | {_m(a26[col])} | {_m(a27[col])} |")
    lines += ["", "## Segment net sales & Adjusted EBITDA", ""]
    for fy in ("FY2026", "FY2027"):
        pnl = segment_pnl(segs[fy])
        lines += [f"### {fy}", "", "| Segment | Net sales | Adj EBITDA | Margin |",
                  "|---|--:|--:|--:|"]
        for name, r in pnl.iterrows():
            lines.append(
                f"| {name} | {_m(r['net_sales'])} | {_m(r['adjusted_ebitda'])} | "
                f"{r['ebitda_margin'] * 100:.1f}% |"
            )
        lines.append("")
    return "\n".join(lines)


# --------------------------------------------------------------------------- #
# Phase C
# --------------------------------------------------------------------------- #
def phase_c(forecast: pd.DataFrame) -> tuple[str, pd.DataFrame]:
    bs = fm.balance_sheet()
    debt = float(bs.loc["long_term_debt_total", "FY2025"])
    grid = fm.divestiture_grid(forecast, debt_balance=debt)
    lines = [
        "# Phase C — Marucci divestiture sensitivity",
        "",
        f"**Most assumption-heavy part of the exercise — a labeled sensitivity.**",
        "Marucci sits inside SSG and is not reported standalone. Estimates are anchored",
        "to the acquisition disclosures: Fox paid **$567.2M** (Nov 2023), incl. $279M of",
        f"intangibles. Assumed standalone: ~{_m(fm.MARUCCI['revenue'])} net sales, "
        f"~{fm.MARUCCI['ebitda_margin'] * 100:.0f}% EBITDA margin "
        f"(~{_m(fm.MARUCCI['revenue'] * fm.MARUCCI['ebitda_margin'])} EBITDA).",
        "",
        f"Sale proceeds default to **{_m(fm.DEFAULT_PROCEEDS)}** (a markdown from the",
        "$567M paid — sports-equipment multiples compressed since 2023). Proceeds pay",
        f"down the term loan at {fm.DEBT_RATE * 100:.0f}%, cutting interest. One-time",
        "proceeds are excluded from FCF; they reduce net debt for the leverage line.",
        "",
        "| Scenario | 2-yr Free Cash Flow | Net debt / EBITDA |",
        "|---|--:|--:|",
    ]
    for name, r in grid.iterrows():
        lines.append(f"| {name} | {_m(r['two_yr_fcf'])} | {r['net_debt_to_ebitda']:.2f}x |")
    lines += [
        "",
        "Selling Marucci *lowers* 2-year FCF (you give up its cash generation) but also",
        "*lowers leverage* (proceeds retire debt). The later the sale, the more Marucci",
        "FCF is retained first. Whether the deleveraging is worth the lost FCF is the",
        "capital-allocation question this sensitivity frames.",
        "",
    ]
    return "\n".join(lines), grid


# --------------------------------------------------------------------------- #
def main() -> None:
    OUT.mkdir(exist_ok=True)
    forecast, segs = fm.build_forecast()

    (OUT / "reconciliation.md").write_text(phase_a())
    (OUT / "forecast-briefing.md").write_text(phase_b(forecast, segs))
    divest_md, grid = phase_c(forecast)
    (OUT / "divestiture.md").write_text(divest_md)

    with pd.ExcelWriter(OUT / "foxf-forecast.xlsx") as xl:
        forecast.to_excel(xl, sheet_name="Forecast (monthly)")
        for fy in ("FY2026", "FY2027"):
            segment_pnl(segs[fy]).to_excel(xl, sheet_name=f"Segments {fy}")
        grid.to_excel(xl, sheet_name="Divestiture")

    print("Wrote output/reconciliation.md, forecast-briefing.md, divestiture.md, foxf-forecast.xlsx")
    print("\nPhase A reconciliation: see output/reconciliation.md")
    print("Phase C divestiture grid:")
    print(grid.to_string())


if __name__ == "__main__":
    main()
