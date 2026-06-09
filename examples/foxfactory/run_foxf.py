"""Fox Factory worked example — full pipeline.

Phase A reproduces audited FY2024/FY2025 operating mechanics from actual drivers.
Phase B replays two FY2025 champion/challenger holdout epochs.
Phase C forecasts FY2026-FY2027 at the segment level, anchored to Q1 FY2026.
Phase D models a Marucci-divestiture FCF/leverage sensitivity.

Run:  python3 examples/foxfactory/run_foxf.py
Outputs land in examples/foxfactory/output/.
"""
from __future__ import annotations

import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO_ROOT = HERE.parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

import pandas as pd

import foxf_model as fm
from pyfpa.analysis.reconcile import reconcile
from pyfpa.analysis.segments import segment_pnl
from pyfpa.memory.entrypoints import (
    CompanyEntrypoint,
    load_entrypoint_registry,
    register_entrypoint,
    save_entrypoint_registry,
)
from pyfpa.memory.intake import (
    load_intake,
    record_intake_fact,
    save_intake,
)
from pyfpa.memory.lineage import (
    MappingRegistry,
    MappingRule,
    SourceRecord,
    SourceRegistry,
    save_mapping_registry,
    save_source_registry,
)
from pyfpa.memory.workspace import initialize_workspace
from pyfpa.research import (
    ModelRegistry, ModelVersion, register_challenger, save_epoch,
    save_model_registry, save_research_objective,
)

OUT = HERE / "output"

DEMO_INTAKE_FACTS = {
    "business_model": (
        "Fox designs and manufactures premium ride-dynamics products and "
        "sports equipment for OEM, aftermarket, and specialty-sports customers."
    ),
    "revenue_model": (
        "Revenue is primarily product sales reported across PVG, AAG, and SSG; "
        "detailed customer billing terms are not publicly disclosed."
    ),
    "customer_channels": "Model PVG, AAG, and SSG as distinct operating segments.",
    "collections": (
        "FY2025 year-end receivables imply about 47 days sales outstanding; "
        "customer-level collection timing is not public."
    ),
    "supplier_payments": (
        "FY2025 payables imply about 50 days payable outstanding, with a material "
        "inventory purchasing cycle."
    ),
    "seasonality": (
        "Demand is cyclical and exposed to powersports and bicycle channel "
        "inventory cycles; the public demo has limited intra-year history."
    ),
    "entities": (
        "The demo models the consolidated USD public company on its 52/53-week "
        "fiscal calendar."
    ),
    "financing": (
        "Fox uses a term loan and revolver and ended FY2025 with about $524M of "
        "total debt."
    ),
    "data_sources": (
        "Committed CSV files derived from source-traced SEC 10-K and 10-Q filings."
    ),
    "planning_cadence": (
        "The public evidence supports quarterly reporting and annual forecasting; "
        "Fox's internal planning cadence is not public."
    ),
    "cfo_priorities": (
        "Restore segment margins, deleverage after the Marucci acquisition, and "
        "evaluate portfolio allocation."
    ),
}

DEMO_ARCHITECTURE_DECISION = """# Initial Model Architecture

**Status:** Approved for the public Fox Factory worked example.

## Objective

Demonstrate a source-traced public-company workflow with separate accounting
reproduction, historical holdout research, forward forecasting, and capital
allocation sensitivity.

## Data Access

- Committed CSV extracts sourced from SEC 10-K and 10-Q filings.
- `pull_edgar.py` refreshes the public source data.
- `data/SOURCES.md` preserves the filing trail.

## Model Components

- Consolidated finance kernel for revenue, COGS, working capital, debt, and cash.
- Generated PVG, AAG, and SSG segment rollup.
- FY2025 champion and challenger holdout evaluation.
- FY2026-FY2027 forward forecast.
- Marucci divestiture sensitivity.

## Validation

- Source and segment rollups.
- Actual-driver accounting reproduction.
- Held-out FY2025 forecast metrics.
- Working-capital continuity across forecast years.
- Full regression suite in CI.
"""

DEMO_SOURCES = (
    (
        "foxf-income-statement",
        "data/income_statement.csv",
        ["FY2023", "FY2024", "FY2025", "Q1_FY2026"],
        "income_statement",
    ),
    (
        "foxf-balance-sheet",
        "data/balance_sheet.csv",
        ["FY2022", "FY2023", "FY2024", "FY2025"],
        "balance_sheet",
    ),
    (
        "foxf-cash-flow",
        "data/cash_flow.csv",
        ["FY2023", "FY2024", "FY2025"],
        "cash_flow",
    ),
    (
        "foxf-segments",
        "data/segments.csv",
        ["FY2023", "FY2024", "FY2025"],
        "segments",
    ),
    (
        "foxf-quarterly",
        "data/quarterly.csv",
        ["Q1_FY2025", "Q1_FY2026"],
        "quarterly",
    ),
)


def _m(v: float) -> str:
    """Format a dollar figure in millions."""
    return f"-${abs(v) / 1e6:,.1f}M" if v < 0 else f"${v / 1e6:,.1f}M"


def _lev(x: float) -> str:
    """Leverage; a negative net-debt position reads as 'net cash', not '-2.1x'."""
    return "net cash" if x < 0 else f"{x:.2f}x"


# --------------------------------------------------------------------------- #
# Phase A — actual-driver reproduction
# --------------------------------------------------------------------------- #
def phase_a() -> str:
    lines = [
        "# Phase A — Actual-driver accounting reproduction",
        "",
        "The pyfpa engine is driven with Fox Factory's **actual** reported drivers",
        "(segment net sales, blended COGS%, working-capital days, D&A, capex) and",
        "its output is compared to the reported figures. This proves the accounting",
        "mechanics reproduce known outcomes; it is **not** an independent forecast",
        "validation because the target-year drivers are inputs. Tolerance: 1%.",
        "",
    ]
    for fy, prior in [("FY2024", "FY2023"), ("FY2025", "FY2024")]:
        model = fm.phase_a_model(fy, prior)
        actual = fm.phase_a_actual(fy, prior)
        rec = reconcile(model, actual, tolerance=0.01)
        lines += [f"## {fy}", "", "| Line | Model | Reported | Variance | Tie |",
                  "|---|--:|--:|--:|:--:|"]
        for name, r in rec.iterrows():
            tie = "yes" if r["within_tolerance"] else "no"
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
        "- This phase therefore validates the **operating arithmetic and the",
        "  working-capital cash mechanic**, while Phase B below provides the",
        "  independent historical holdout.",
        "",
    ]
    return "\n".join(lines)


# --------------------------------------------------------------------------- #
# Phase B — historical holdout research
# --------------------------------------------------------------------------- #
def phase_b() -> str:
    epochs = fm.historical_research_epochs()
    lines = [
        "# Phase B — FY2025 historical holdout research",
        "",
        "The research loop fits only on FY2023-FY2024 and holds FY2025 out.",
        "The champion is a flat FY2024 run rate. Each challenger is scored on",
        "revenue, gross profit, Adjusted EBITDA, and working-capital balances,",
        "with accounting checks required and a complexity penalty applied.",
        "",
        "| Epoch | Hypothesis | Status | Objective gain |",
        "|---|---|---:|--:|",
    ]
    for epoch in epochs:
        lines.append(
            f"| {epoch.epoch_id} | {epoch.hypothesis} | {epoch.status} | "
            f"{epoch.evaluation.objective_gain * 100:+.1f}% |"
        )
    broad, refined = epochs
    lines += [
        "",
        "## What the loop learned",
        "",
        f"- **Epoch 1 was discarded.** It improved revenue and gross profit but",
        f"  over-recovered segment margins, worsening Adjusted EBITDA error from",
        f"  {broad.evaluation.champion_metrics['adjusted_ebitda_error'] * 100:.1f}%",
        f"  to {broad.evaluation.challenger_metrics['adjusted_ebitda_error'] * 100:.1f}%.",
        "- **Epoch 2 separated sales recovery from margin recovery.** Revenue moves",
        "  halfway toward FY2023, but margins recover only 5%. That challenger",
        f"  improves the weighted holdout objective by",
        f"  {refined.evaluation.objective_gain * 100:.1f}% and passes every hard check.",
        "- The challenger remains **proposed**, not promoted. A human would decide",
        "  whether its recovery logic should become the champion.",
        "",
        "## Champion vs strongest challenger",
        "",
        "| Metric | Flat FY2024 champion | Recovery challenger |",
        "|---|--:|--:|",
    ]
    labels = {
        "revenue_error": "Revenue error",
        "gross_profit_error": "Gross profit error",
        "adjusted_ebitda_error": "Adjusted EBITDA error",
        "working_capital_balance_error": "Working-capital balance error",
    }
    for metric, label in labels.items():
        lines.append(
            f"| {label} | "
            f"{refined.evaluation.champion_metrics[metric] * 100:.1f}% | "
            f"{refined.evaluation.challenger_metrics[metric] * 100:.1f}% |"
        )
    lines += [
        "",
        "> This is a deliberately small annual holdout with three historical years.",
        "> It demonstrates the research discipline, not production-grade statistical certainty.",
        "",
    ]
    return "\n".join(lines)


def holdout_workbook_rows() -> pd.DataFrame:
    """Flatten historical research epochs for an auditable workbook tab."""
    rows = []
    for epoch in fm.historical_research_epochs():
        for metric, champion_value in epoch.evaluation.champion_metrics.items():
            challenger_value = epoch.evaluation.challenger_metrics[metric]
            rows.append({
                "epoch": epoch.epoch_id,
                "status": epoch.status,
                "hypothesis": epoch.hypothesis,
                "metric": metric,
                "champion_error": champion_value,
                "challenger_error": challenger_value,
                "error_improvement": champion_value - challenger_value,
                "objective_gain": epoch.evaluation.objective_gain,
                "promotion_eligible": epoch.evaluation.promotion_eligible,
            })
    return pd.DataFrame(rows)


def initialize_demo_workspace() -> Path:
    workspace = initialize_workspace(
        HERE,
        business_name="Fox Factory Holding Corp.",
    )
    intake_path = workspace / "intake.md"
    intake = load_intake(intake_path)
    existing = {fact.key for fact in intake.facts}
    for key, answer in DEMO_INTAKE_FACTS.items():
        if key in existing:
            continue
        intake = record_intake_fact(
            intake,
            key=key,
            answer=answer,
            source_type="local_file",
            sources=["data/SOURCES.md", ".fpa/business-profile.md"],
            confidence=0.85,
        )
    save_intake(intake, intake_path)
    decision_path = workspace / "decisions" / "initial-model-architecture.md"
    if not decision_path.exists():
        decision_path.write_text(DEMO_ARCHITECTURE_DECISION)
    register_demo_lineage(workspace)
    return workspace


def register_demo_lineage(workspace: Path) -> None:
    sources = []
    mappings = []
    for source_id, location, periods, namespace in DEMO_SOURCES:
        sources.append(SourceRecord(
            source_id=source_id,
            kind="public_filing",
            location=location,
            entity="Fox Factory Holding Corp.",
            currency="USD",
            periods=periods,
            extraction_method=(
                "pull_edgar.py extracts source-traced SEC filing values into "
                "a committed CSV"
            ),
            notes="Filing URLs, accessions, and table provenance are in data/SOURCES.md.",
        ))
        frame = pd.read_csv(HERE / location)
        if source_id == "foxf-segments":
            source_values = (
                frame["segment"].astype(str) + "." + frame["metric"].astype(str)
            )
        else:
            source_values = frame["line"].astype(str)
        mappings.extend(
            MappingRule(
                source_id=source_id,
                source_value=source_value,
                target=f"{namespace}.{source_value}",
                rationale="Normalized field used by the Fox worked example.",
            )
            for source_value in source_values
        )
    save_source_registry(
        SourceRegistry(sources=sources),
        workspace / "sources" / "registry.yaml",
    )
    save_mapping_registry(
        MappingRegistry(mappings=mappings),
        workspace / "mappings" / "registry.yaml",
    )


# --------------------------------------------------------------------------- #
# Phase C — forward forecast
# --------------------------------------------------------------------------- #
def _annual(forecast: pd.DataFrame, year: int) -> pd.Series:
    return forecast[forecast.index.year == year].sum()


def phase_c(forecast: pd.DataFrame, segs: dict) -> str:
    q1_prev, q1_curr = fm.q1_values()
    q1 = fm.q1_yoy()
    lines = [
        "# Phase C — FY2026-FY2027 segment-level forecast",
        "",
        "Base = FY2025 actuals. FY2026 net-sales growth is anchored to the reported",
        f"Q1 FY2026 print ({_m(q1_curr)} vs Q1 FY2025 {_m(q1_prev)} = **{q1 * 100:+.1f}% YoY**;",
        "the modeled segment blend below is +3.6%). Adjusted-EBITDA margins step modestly",
        "off FY2025.",
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
# Phase D — Marucci sensitivity
# --------------------------------------------------------------------------- #
def phase_d(forecast: pd.DataFrame) -> tuple[str, pd.DataFrame, pd.DataFrame]:
    bs = fm.balance_sheet()
    debt = float(bs.loc["long_term_debt_total", "FY2025"])
    grid = fm.divestiture_grid(forecast, debt_balance=debt)
    proceeds_grid = fm.proceeds_sensitivity(forecast, debt_balance=debt, sale_month=12)
    lines = [
        "# Phase D — Marucci divestiture sensitivity",
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
        lines.append(f"| {name} | {_m(r['two_yr_fcf'])} | {_lev(r['net_debt_to_ebitda'])} |")
    lines += [
        "",
        "Selling Marucci *lowers* 2-year FCF (you give up its cash generation) but also",
        "*lowers leverage* (proceeds retire debt). The later the sale, the more Marucci",
        "FCF is retained first.",
        "",
        "### Proceeds sensitivity (sale held at 12 months)",
        "",
        "Price is an input (default $300M) or an EV/EBITDA exit multiple on estimated",
        f"Marucci EBITDA (~{_m(fm.marucci_ebitda())}). More proceeds retire more debt.",
        "",
        "| Sale price | Proceeds | 2-yr Free Cash Flow | Net debt / EBITDA |",
        "|---|--:|--:|--:|",
    ]
    for name, r in proceeds_grid.iterrows():
        lines.append(
            f"| {name} | {_m(r['proceeds'])} | {_m(r['two_yr_fcf'])} | "
            f"{_lev(r['net_debt_to_ebitda'])} |"
        )
    lines += [
        "",
        "Whether the deleveraging is worth the lost FCF — and at what price — is the",
        "capital-allocation question this sensitivity frames.",
        "",
    ]
    return "\n".join(lines), grid, proceeds_grid


# --------------------------------------------------------------------------- #
def main() -> None:
    OUT.mkdir(exist_ok=True)
    workspace = initialize_demo_workspace()
    forecast, segs = fm.build_forecast()

    (OUT / "reconciliation.md").write_text(phase_a())
    (OUT / "historical-holdout.md").write_text(phase_b())
    (OUT / "forecast-briefing.md").write_text(phase_c(forecast, segs))
    divest_md, grid, proceeds_grid = phase_d(forecast)
    (OUT / "divestiture.md").write_text(divest_md)

    research_dir = workspace / "research"
    models_dir = workspace / "models"
    save_research_objective(fm.HOLDOUT_OBJECTIVE, research_dir / "objective.yaml")
    epochs = fm.historical_research_epochs()
    for epoch in epochs:
        save_epoch(epoch, research_dir, overwrite=True)
    registry = ModelRegistry(champion=ModelVersion(
        model_id="foxf-flat-fy2024-run-rate",
        created="2026-06-09",
        artifact="foxf_model.py",
        description="Flat FY2024 operating run rate used as the FY2025 holdout champion.",
    ))
    strongest = epochs[-1]
    if strongest.evaluation.promotion_eligible:
        registry = register_challenger(registry, ModelVersion(
            model_id=strongest.challenger_id,
            created=strongest.created,
            artifact="foxf_model.py::historical_candidate",
            source_epoch=strongest.epoch_id,
            description="Revenue recovery with slower margin recovery.",
        ))
    save_model_registry(registry, models_dir / "registry.yaml")
    entrypoint_path = models_dir / "entrypoints.yaml"
    entrypoints = register_entrypoint(
        load_entrypoint_registry(entrypoint_path),
        CompanyEntrypoint(
            name="foxf-pipeline",
            kind="forecast",
            description=(
                "Run Fox actual-driver reproduction, historical holdout, "
                "forward forecast, and Marucci sensitivity."
            ),
            command=["python3", "run_foxf.py"],
            inputs=[
                "data/income_statement.csv",
                "data/balance_sheet.csv",
                "data/cash_flow.csv",
                "data/segments.csv",
                "data/quarterly.csv",
            ],
            outputs=[
                "output/reconciliation.md",
                "output/historical-holdout.md",
                "output/forecast-briefing.md",
                "output/divestiture.md",
                "output/foxf-forecast.xlsx",
            ],
        ),
        overwrite=True,
    )
    save_entrypoint_registry(entrypoints, entrypoint_path)

    with pd.ExcelWriter(OUT / "foxf-forecast.xlsx") as xl:
        holdout_workbook_rows().to_excel(
            xl, sheet_name="Historical holdout", index=False
        )
        forecast.to_excel(xl, sheet_name="Forecast (monthly)")
        for fy in ("FY2026", "FY2027"):
            segment_pnl(segs[fy]).to_excel(xl, sheet_name=f"Segments {fy}")
        grid.to_excel(xl, sheet_name="Divestiture (timing)")
        proceeds_grid.to_excel(xl, sheet_name="Divestiture (price)")

    print("Wrote output/reconciliation.md, historical-holdout.md, forecast-briefing.md,")
    print("divestiture.md, foxf-forecast.xlsx, and .fpa research/model memory")
    print("\nPhase B historical holdout: see output/historical-holdout.md")
    print("Phase D divestiture grid:")
    print(grid.to_string())


if __name__ == "__main__":
    main()
