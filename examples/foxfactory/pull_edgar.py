"""Pull Fox Factory (FOXF, CIK 1424929) financials from SEC EDGAR.

Re-runnable and source-auditable: every figure is fetched from EDGAR's XBRL APIs
or the rendered 10-K financial-report files, and `data/SOURCES.md` records the
accession numbers and URLs. SEC requires a descriptive User-Agent with contact
info — see https://www.sec.gov/os/accessing-edgar-data.

Usage:  python3 examples/foxfactory/pull_edgar.py
"""
from __future__ import annotations

import json
import subprocess
from io import StringIO
from pathlib import Path

import pandas as pd

CIK = "0001424929"
UA = "openfpa-research jeff.brines@gmail.com"
DATA = Path(__file__).parent / "data"

# Fox's fiscal year ends on the Sunday closest to Dec 31 (52/53-week year).
FY_END = {2022: "2022-12-30", 2023: "2023-12-29", 2024: "2025-01-03", 2025: "2026-01-02"}
FYS = (2023, 2024, 2025)

# 10-K accessions used (for the audit trail in SOURCES.md).
TENK = {
    2023: "000142492924000006",  # FY2023 (period end 2023-12-29)
    2024: "000142492925000007",  # FY2024 (period end 2025-01-03)
    2025: "000142492926000012",  # FY2025 (period end 2026-01-02)
}
SEG_REPORT = "R106.htm"  # "Segment Information - Summary of Segment Information (Details)" in FY2025 10-K


def _curl(url: str) -> bytes:
    result = subprocess.run(
        ["curl", "-s", "-H", f"User-Agent: {UA}", url], capture_output=True
    )
    if result.returncode != 0:
        raise RuntimeError(f"curl failed for {url}: {result.stderr.decode()[:200]}")
    return result.stdout


def _concept(tag: str) -> list[dict] | None:
    try:
        doc = json.loads(
            _curl(f"https://data.sec.gov/api/xbrl/companyconcept/CIK{CIK}/us-gaap/{tag}.json")
        )
        return doc["units"]["USD"]
    except Exception:
        return None


def annual(tag: str, fy: int) -> float | None:
    """Full-year (10-K, ~365-day) value for a duration concept in fiscal year `fy`."""
    rows = _concept(tag)
    if not rows:
        return None
    value = None
    for r in rows:
        if r.get("form") == "10-K" and r.get("fy") == fy and r.get("start"):
            span = (pd.Timestamp(r["end"]) - pd.Timestamp(r["start"])).days
            if 350 <= span <= 380:
                value = float(r["val"])
    return value


def instant(tag: str, fy: int) -> float | None:
    """Balance-sheet (point-in-time) value at the fiscal year-end of `fy`."""
    rows = _concept(tag)
    if not rows:
        return None
    value = None
    for r in rows:
        if r.get("end") == FY_END[fy] and not r.get("start"):
            value = float(r["val"])
    return value


def latest_quarter(tag: str) -> tuple[str, str, float] | None:
    """Most recent ~quarterly (80-100 day) value for a duration concept."""
    rows = _concept(tag)
    if not rows:
        return None
    quarters = [
        r for r in rows
        if r.get("start") and 80 <= (pd.Timestamp(r["end"]) - pd.Timestamp(r["start"])).days <= 100
    ]
    if not quarters:
        return None
    r = sorted(quarters, key=lambda r: r["end"])[-1]
    return r["start"], r["end"], float(r["val"])


def _row(line: str, tag: str, kind: str, q1: float | None = None) -> dict:
    cells = {"line": line}
    for fy in FYS:
        cells[f"FY{fy}"] = annual(tag, fy) if kind == "annual" else instant(tag, fy)
    if q1 is not None:
        cells["Q1_FY2026"] = q1
    return cells


def pull_income_statement() -> pd.DataFrame:
    q1_rev = latest_quarter("RevenueFromContractWithCustomerExcludingAssessedTax")
    q1_gp = latest_quarter("GrossProfit")
    q1_ni = latest_quarter("NetIncomeLoss")
    rows = [
        _row("net_sales", "RevenueFromContractWithCustomerExcludingAssessedTax", "annual", q1_rev[2]),
        _row("cost_of_sales", "CostOfGoodsAndServicesSold", "annual", q1_rev[2] - q1_gp[2]),
        _row("gross_profit", "GrossProfit", "annual", q1_gp[2]),
        _row("general_and_admin", "GeneralAndAdministrativeExpense", "annual"),
        _row("research_and_development", "ResearchAndDevelopmentExpense", "annual"),
        _row("goodwill_impairment", "GoodwillImpairmentLoss", "annual", 0.0),
        _row("operating_income", "OperatingIncomeLoss", "annual"),
        _row("interest_expense", "InterestExpense", "annual"),
        _row("income_tax", "IncomeTaxExpenseBenefit", "annual"),
        _row("net_income", "NetIncomeLoss", "annual", q1_ni[2]),
    ]
    return pd.DataFrame(rows)


def pull_balance_sheet() -> pd.DataFrame:
    # FY2022 column included as the opening balance for FY2023 reconciliation.
    tags = [
        ("cash", "CashAndCashEquivalentsAtCarryingValue"),
        ("accounts_receivable", "AccountsReceivableNetCurrent"),
        ("inventory", "InventoryNet"),
        ("accounts_payable", "AccountsPayableCurrent"),
        ("long_term_debt_total", "LongTermDebt"),
        ("goodwill", "Goodwill"),
    ]
    rows = []
    for line, tag in tags:
        cells = {"line": line}
        for fy in (2022, 2023, 2024, 2025):
            cells[f"FY{fy}"] = instant(tag, fy)
        rows.append(cells)
    return pd.DataFrame(rows)


def pull_cash_flow() -> pd.DataFrame:
    rows = [
        _row("operating_cash_flow", "NetCashProvidedByUsedInOperatingActivities", "annual"),
        _row("capex", "PaymentsToAcquirePropertyPlantAndEquipment", "annual"),
        _row("depreciation_amortization", "DepreciationAndAmortization", "annual"),
    ]
    return pd.DataFrame(rows)


def pull_segments() -> pd.DataFrame:
    """Segment net sales + Adjusted EBITDA from the FY2025 10-K segment footnote.

    Fox reports segment Adjusted EBITDA (ASU 2023-07), not segment gross profit or
    operating income. The footnote table carries all three fiscal years.
    """
    url = f"https://www.sec.gov/Archives/edgar/data/1424929/{TENK[2025]}/{SEG_REPORT}"
    html = _curl(url).decode()
    table = pd.read_html(StringIO(html))[0]
    table.columns = ["label", "q4", "q1prev", "FY2025", "FY2024", "FY2023"]

    def money(v) -> float:
        return float(str(v).replace("$", "").replace(",", "").replace("(", "-").replace(")", "").strip())

    # Walk the long-form footnote: a segment header row (e.g. "PVG | Operating Segments")
    # is followed by its "Net sales" and "Adjusted EBITDA" rows.
    seg_map = {
        "PVG": "PVG",
        "Aftermarket Applications Group": "AAG",
        "SSG": "SSG",
    }
    rows: list[dict] = []
    current: str | None = None
    for _, r in table.iterrows():
        label = str(r["label"]).strip()
        for needle, code in seg_map.items():
            if label.startswith(needle) and "Operating Segments" in label:
                current = code
        if current and label == "Net sales":
            rows.append({"segment": current, "metric": "net_sales",
                         "FY2023": money(r["FY2023"]), "FY2024": money(r["FY2024"]),
                         "FY2025": money(r["FY2025"])})
        if current and label == "Adjusted EBITDA":
            rows.append({"segment": current, "metric": "adjusted_ebitda",
                         "FY2023": money(r["FY2023"]), "FY2024": money(r["FY2024"]),
                         "FY2025": money(r["FY2025"])})
            current = None  # reset after capturing both metrics for a segment
    return pd.DataFrame(rows)


def write_sources() -> None:
    lines = [
        "# Sources",
        "",
        "All figures pulled from SEC EDGAR for **Fox Factory Holding Corp. (CIK 1424929)**.",
        "Regenerate with `python3 examples/foxfactory/pull_edgar.py`.",
        "",
        "## Consolidated income statement, balance sheet, cash flow",
        "",
        "XBRL company-concept API, e.g.:",
        "`https://data.sec.gov/api/xbrl/companyconcept/CIK0001424929/us-gaap/<TAG>.json`",
        "",
        "Filed in these 10-Ks:",
        f"- FY2023 (period end 2023-12-29): accession {TENK[2023]}",
        f"- FY2024 (period end 2025-01-03): accession {TENK[2024]}",
        f"- FY2025 (period end 2026-01-02): accession {TENK[2025]}",
        "- Q1 FY2026 (period end 2026-04-03): latest 10-Q (most recent quarterly value per concept)",
        "",
        "## Segment net sales + Adjusted EBITDA",
        "",
        f"FY2025 10-K segment footnote: "
        f"https://www.sec.gov/Archives/edgar/data/1424929/{TENK[2025]}/{SEG_REPORT}",
        "(Fox reports segment **Adjusted EBITDA** under ASU 2023-07 — not segment gross",
        "profit or operating income. The table carries FY2023-FY2025.)",
        "",
        "## Marucci acquisition anchor (Phase C divestiture)",
        "",
        f"FY2023 10-K acquisitions footnote: "
        f"https://www.sec.gov/Archives/edgar/data/1424929/{TENK[2023]}/R97.htm",
        "- Acquired 2023-11-14; total consideration **$567,194K** (cash $567,092K).",
        "- Goodwill $244,790K; finite-lived intangibles $279,100K; inventory $44,972K.",
        "- Pro-forma (R98): combined FY2023 sales with full-year Marucci ~$1,632,076K.",
        "",
    ]
    (DATA / "SOURCES.md").write_text("\n".join(lines))


def main() -> None:
    DATA.mkdir(parents=True, exist_ok=True)
    pull_income_statement().to_csv(DATA / "income_statement.csv", index=False)
    pull_balance_sheet().to_csv(DATA / "balance_sheet.csv", index=False)
    pull_cash_flow().to_csv(DATA / "cash_flow.csv", index=False)
    pull_segments().to_csv(DATA / "segments.csv", index=False)
    write_sources()
    print("Wrote data/*.csv and data/SOURCES.md")


if __name__ == "__main__":
    main()
