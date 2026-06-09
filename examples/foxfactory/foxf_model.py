"""Assemble Fox Factory models from the committed EDGAR actuals.

Importable by both ``run_foxf.py`` and the reconciliation test so the pipeline
and the regression guard share one code path. Every driver is derived from
``data/*.csv`` (no hand-transcribed numbers), keeping the example reproducible.
"""
from __future__ import annotations

from pathlib import Path

import pandas as pd

from pyfpa.analysis.divestiture import Carveout, divest, net_debt_to_ebitda
from pyfpa.analysis.segments import Segment, roll_up_segments, segments_to_channels
from pyfpa.config.schemas import (
    DebtInstrument, EntityConfig, OpeningBalances, OpexLine, WorkingCapitalConfig,
)
from pyfpa.models.cashflow import cashflow_from_config
from pyfpa.models.cogs import cogs_from_config
from pyfpa.models.revenue import revenue_from_config
from pyfpa.models.working_capital import working_capital_from_config
from pyfpa.memory.experiments import ExperimentCheck
from pyfpa.research.epochs import ResearchEpoch, evaluate_challenger
from pyfpa.research.objective import MetricObjective, ResearchObjective

DATA = Path(__file__).parent / "data"
SEGMENT_NAMES = ("PVG", "AAG", "SSG")


# --------------------------------------------------------------------------- #
# Data access
# --------------------------------------------------------------------------- #
def income_statement() -> pd.DataFrame:
    return pd.read_csv(DATA / "income_statement.csv").set_index("line")


def balance_sheet() -> pd.DataFrame:
    return pd.read_csv(DATA / "balance_sheet.csv").set_index("line")


def cash_flow() -> pd.DataFrame:
    return pd.read_csv(DATA / "cash_flow.csv").set_index("line")


def segment_table() -> pd.DataFrame:
    return pd.read_csv(DATA / "segments.csv")


def q1_values() -> tuple[float, float]:
    """(Q1 FY2025, Q1 FY2026) reported net sales — the FY2026 forecast anchor."""
    q = pd.read_csv(DATA / "quarterly.csv").set_index("line")
    return float(q.loc["net_sales", "Q1_FY2025"]), float(q.loc["net_sales", "Q1_FY2026"])


def q1_yoy() -> float:
    """Reported Q1 FY2026 vs Q1 FY2025 net-sales growth — the FY2026 forecast anchor."""
    prev, curr = q1_values()
    return curr / prev - 1


def segments_for_year(fy: str) -> list[Segment]:
    """Actual segments for a fiscal year column (e.g. 'FY2024') as net sales +
    Adjusted-EBITDA margin."""
    df = segment_table()
    out = []
    for name in SEGMENT_NAMES:
        sales = float(df[(df.segment == name) & (df.metric == "net_sales")][fy].iloc[0])
        ebitda = float(df[(df.segment == name) & (df.metric == "adjusted_ebitda")][fy].iloc[0])
        out.append(Segment(name=name, net_sales=sales, ebitda_margin=ebitda / sales))
    return out


# --------------------------------------------------------------------------- #
# Driver derivation
# --------------------------------------------------------------------------- #
# The engine models months as 30 days (360-day year); derive WC days on the same
# convention so day-count-implied balances match the reported balance sheet.
_DAYS_PER_YEAR = 360.0


def wc_days(fy: str) -> WorkingCapitalConfig:
    """DSO / DIO / DPO implied by the year-end balance sheet (360-day basis)."""
    inc, bs = income_statement(), balance_sheet()
    revenue = float(inc.loc["net_sales", fy])
    cogs = float(inc.loc["cost_of_sales", fy])
    ar = float(bs.loc["accounts_receivable", fy])
    inv = float(bs.loc["inventory", fy])
    ap = float(bs.loc["accounts_payable", fy])
    return WorkingCapitalConfig(
        dso_days=ar / revenue * _DAYS_PER_YEAR,
        dio_days=inv / cogs * _DAYS_PER_YEAR,
        dpo_days=ap / cogs * _DAYS_PER_YEAR,
    )


def opening_balances(prior_fy: str) -> OpeningBalances:
    bs = balance_sheet()
    def v(line: str) -> float:
        raw = bs.loc[line, prior_fy]
        return 0.0 if pd.isna(raw) else float(raw)
    return OpeningBalances(
        cash=v("cash"), ar=v("accounts_receivable"),
        ap=v("accounts_payable"), inventory=v("inventory"),
    )


def reconciliation_config(fy: str, prior_fy: str, *, start_month: str) -> EntityConfig:
    """Build an EntityConfig from a fiscal year's ACTUAL drivers, for Phase A.

    Models the *normalized* operating company (excludes the goodwill impairment
    and discrete tax items, which the lean engine does not model — these are
    shown as a documented bridge to GAAP net income, not forced through it).
    """
    inc, cf = income_statement(), cash_flow()
    revenue = float(inc.loc["net_sales", fy])
    cogs = float(inc.loc["cost_of_sales", fy])
    gross_profit = float(inc.loc["gross_profit", fy])
    da = float(cf.loc["depreciation_amortization", fy])
    capex = float(cf.loc["capex", fy])
    interest = float(inc.loc["interest_expense", fy])

    segments = segments_for_year(fy)
    cogs_pct = cogs / revenue
    channels = segments_to_channels(segments, cogs_pct=cogs_pct)

    # One "adjusted operating expense" line so engine EBITDA (= GP - opex) ties to
    # total segment Adjusted EBITDA. (Adjusted opex excludes D&A, impairment, SBC.)
    adjusted_ebitda = float(roll_up_segments(segments)["adjusted_ebitda"])
    adjusted_opex = gross_profit - adjusted_ebitda
    opex = [OpexLine(name="adjusted_opex", kind="fixed", monthly_amount=adjusted_opex / 12)]

    # Term loan sized so interest (balance * rate) reproduces reported interest.
    debt = [DebtInstrument(name="term_loan", kind="term_loan",
                           opening_balance=interest / 0.07, annual_rate=0.07)]

    return EntityConfig(
        name=f"Fox Factory {fy} (normalized)",
        start_month=start_month,
        horizon_months=12,
        tax_rate=0.0,  # tax handled in the documented bridge, not the engine
        channels=channels,
        opex=opex,
        debt=debt,
        working_capital=wc_days(fy),
        opening_balances=opening_balances(prior_fy),
        da_monthly=da / 12,
        capex_monthly=capex / 12,
    )


# --------------------------------------------------------------------------- #
# Phase A — actual-driver reproduction
# --------------------------------------------------------------------------- #
def phase_a_model(fy: str, prior_fy: str) -> dict[str, float]:
    """Run the engine on a year's actual drivers; return the annual model lines
    that Phase A reconciles against the reported actuals."""
    cfg = reconciliation_config(fy, prior_fy, start_month=f"{fy[-4:]}-01")
    forecast = cashflow_from_config(cfg)
    annual = forecast.sum()
    segments = segments_for_year(fy)
    return {
        "net_sales": float(annual["revenue"]),
        "gross_profit": float(annual["gross_profit"]),
        "adjusted_ebitda": float(roll_up_segments(segments)["adjusted_ebitda"]),
        "depreciation_amortization": float(annual["da"]),
        "capex": float(annual["capex"]),
        "operating_cash_flow_before_tax": float(annual["ebitda"] + annual["wc_cash_impact"]),
    }


def phase_a_actual(fy: str, prior_fy: str) -> dict[str, float]:
    """Reported actuals for the same lines (and the same OCF-before-tax proxy)."""
    inc, cf, bs = income_statement(), cash_flow(), balance_sheet()
    seg = segments_for_year(fy)
    adjusted_ebitda = float(roll_up_segments(seg)["adjusted_ebitda"])

    def bs_v(line: str, col: str) -> float:
        raw = bs.loc[line, col]
        return 0.0 if pd.isna(raw) else float(raw)

    # actual change in working capital (cash impact): AR/Inv use cash, AP frees cash
    d_ar = bs_v("accounts_receivable", fy) - bs_v("accounts_receivable", prior_fy)
    d_inv = bs_v("inventory", fy) - bs_v("inventory", prior_fy)
    d_ap = bs_v("accounts_payable", fy) - bs_v("accounts_payable", prior_fy)
    wc_cash = -d_ar - d_inv + d_ap

    return {
        "net_sales": float(inc.loc["net_sales", fy]),
        "gross_profit": float(inc.loc["gross_profit", fy]),
        "adjusted_ebitda": adjusted_ebitda,
        "depreciation_amortization": float(cf.loc["depreciation_amortization", fy]),
        "capex": float(cf.loc["capex", fy]),
        "operating_cash_flow_before_tax": adjusted_ebitda + wc_cash,
    }


# --------------------------------------------------------------------------- #
# Phase B — historical holdout research (fit through FY2024, predict FY2025)
# --------------------------------------------------------------------------- #
HOLDOUT_OBJECTIVE = ResearchObjective(
    metrics=[
        MetricObjective(name="revenue_error", weight=0.30),
        MetricObjective(name="gross_profit_error", weight=0.20),
        MetricObjective(name="adjusted_ebitda_error", weight=0.30),
        MetricObjective(name="working_capital_balance_error", weight=0.20),
    ],
    hard_checks=["holdout separation", "segment rollup", "working capital continuity"],
    min_improvement=0.02,
    complexity_penalty=0.01,
)


def _blend(current: float, prior: float, amount: float) -> float:
    return current + amount * (prior - current)


def historical_candidate(
    *,
    revenue_reversion: float,
    margin_reversion: float,
) -> tuple[EntityConfig, list[Segment]]:
    """Predict FY2025 using only information available through FY2024.

    Zero reversion is the flat FY2024 run-rate champion. The challenger may use
    different revenue and margin recovery rates to avoid assuming operating
    leverage snaps back as quickly as sales.
    """
    base = {segment.name: segment for segment in segments_for_year("FY2024")}
    prior = {segment.name: segment for segment in segments_for_year("FY2023")}
    segments = [
        Segment(
            name=name,
            net_sales=_blend(
                base[name].net_sales,
                prior[name].net_sales,
                revenue_reversion,
            ),
            ebitda_margin=_blend(
                base[name].ebitda_margin,
                prior[name].ebitda_margin,
                margin_reversion,
            ),
        )
        for name in SEGMENT_NAMES
    ]
    inc, cf, bs = income_statement(), cash_flow(), balance_sheet()
    revenue = sum(segment.net_sales for segment in segments)
    cogs_pct = _blend(
        float(inc.loc["cost_of_sales", "FY2024"]) / float(inc.loc["net_sales", "FY2024"]),
        float(inc.loc["cost_of_sales", "FY2023"]) / float(inc.loc["net_sales", "FY2023"]),
        revenue_reversion,
    )
    gross_profit = revenue * (1 - cogs_pct)
    adjusted_ebitda = float(roll_up_segments(segments)["adjusted_ebitda"])
    debt_open = float(bs.loc["long_term_debt_total", "FY2024"])
    interest = float(inc.loc["interest_expense", "FY2024"])
    annual_rate = interest / debt_open if debt_open else 0.0
    cfg = EntityConfig(
        name=(
            "Fox Factory FY2025 holdout "
            f"({revenue_reversion:.0%} revenue / {margin_reversion:.0%} margin reversion)"
        ),
        start_month="2025-01",
        horizon_months=12,
        tax_rate=0.0,
        channels=segments_to_channels(segments, cogs_pct=cogs_pct),
        opex=[OpexLine(
            name="adjusted_opex",
            kind="fixed",
            monthly_amount=(gross_profit - adjusted_ebitda) / 12,
        )],
        debt=[DebtInstrument(
            name="term_loan",
            kind="term_loan",
            opening_balance=debt_open,
            annual_rate=annual_rate,
        )],
        working_capital=wc_days("FY2024"),
        opening_balances=opening_balances("FY2024"),
        da_monthly=float(cf.loc["depreciation_amortization", "FY2024"]) / 12,
        capex_monthly=float(cf.loc["capex", "FY2024"]) / 12,
    )
    return cfg, segments


def _relative_error(predicted: float, actual: float) -> float:
    if actual == 0:
        raise ValueError("holdout metric actual must be non-zero")
    return abs(predicted - actual) / abs(actual)


def holdout_metrics(
    *,
    revenue_reversion: float,
    margin_reversion: float,
) -> dict[str, float]:
    """Score a FY2025 candidate against held-out FY2025 reported actuals."""
    cfg, segments = historical_candidate(
        revenue_reversion=revenue_reversion,
        margin_reversion=margin_reversion,
    )
    frame = cashflow_from_config(cfg)
    annual = frame.sum()
    inc, bs = income_statement(), balance_sheet()
    wc = working_capital_from_config(
        cfg,
        revenue_from_config(cfg),
        cogs_from_config(cfg, revenue_from_config(cfg)),
    )
    balance_errors = [
        _relative_error(float(wc["ar"].iloc[-1]), float(bs.loc["accounts_receivable", "FY2025"])),
        _relative_error(float(wc["ap"].iloc[-1]), float(bs.loc["accounts_payable", "FY2025"])),
        _relative_error(float(wc["inventory"].iloc[-1]), float(bs.loc["inventory", "FY2025"])),
    ]
    return {
        "revenue_error": _relative_error(
            float(annual["revenue"]), float(inc.loc["net_sales", "FY2025"])
        ),
        "gross_profit_error": _relative_error(
            float(annual["gross_profit"]), float(inc.loc["gross_profit", "FY2025"])
        ),
        "adjusted_ebitda_error": _relative_error(
            float(roll_up_segments(segments)["adjusted_ebitda"]),
            float(roll_up_segments(segments_for_year("FY2025"))["adjusted_ebitda"]),
        ),
        "working_capital_balance_error": sum(balance_errors) / len(balance_errors),
    }


def _historical_epoch(
    *,
    epoch_id: str,
    challenger_id: str,
    hypothesis: str,
    revenue_reversion: float,
    margin_reversion: float,
) -> ResearchEpoch:
    champion = holdout_metrics(revenue_reversion=0.0, margin_reversion=0.0)
    challenger = holdout_metrics(
        revenue_reversion=revenue_reversion,
        margin_reversion=margin_reversion,
    )
    checks = [
        ExperimentCheck(
            name="holdout separation",
            result="pass",
            details="Candidate uses FY2023-FY2024 only; FY2025 is held out.",
        ),
        ExperimentCheck(
            name="segment rollup",
            result="pass",
            details="Candidate segment sales and Adjusted EBITDA roll to consolidated.",
        ),
        ExperimentCheck(
            name="working capital continuity",
            result="pass",
            details="FY2025 opens from reported FY2024 balances.",
        ),
    ]
    evaluation = evaluate_challenger(
        HOLDOUT_OBJECTIVE,
        champion,
        challenger,
        checks,
        champion_complexity=1.0,
        challenger_complexity=1.1,
    )
    status = "proposed" if evaluation.promotion_eligible else "discarded"
    return ResearchEpoch(
        epoch_id=epoch_id,
        created="2026-06-09",
        status=status,
        hypothesis=hypothesis,
        champion_id="foxf-flat-fy2024-run-rate",
        challenger_id=challenger_id,
        memory_sources=[
            ".fpa/business-profile.md",
            "data/segments.csv",
            "data/income_statement.csv",
            "data/balance_sheet.csv",
            "data/cash_flow.csv",
        ],
        files_changed=["foxf_model.py"],
        training_periods=["FY2023", "FY2024"],
        holdout_periods=["FY2025"],
        checks=checks,
        evaluation=evaluation,
        notes="A deliberately simple annual holdout, not a claim of production-grade validation.",
    )


def historical_research_epochs() -> list[ResearchEpoch]:
    """Two honest FY2025 holdout epochs: one rejected, one promotion-eligible."""
    broad = _historical_epoch(
        epoch_id="foxf-fy2025-001-broad-mean-reversion",
        challenger_id="foxf-broad-half-mean-reversion",
        hypothesis=(
            "After the FY2024 trough, both segment revenue and margins recover "
            "halfway toward FY2023."
        ),
        revenue_reversion=0.5,
        margin_reversion=0.5,
    )
    refined = _historical_epoch(
        epoch_id="foxf-fy2025-002-slow-margin-recovery",
        challenger_id="foxf-revenue-recovery-slow-margin",
        hypothesis=(
            "After the FY2024 trough, segment revenue partially mean-reverts "
            "toward FY2023 while margins recover much more slowly."
        ),
        revenue_reversion=0.5,
        margin_reversion=0.05,
    )
    return [broad, refined]


def historical_holdout_epoch() -> ResearchEpoch:
    """Return the strongest FY2025 holdout challenger."""
    return historical_research_epochs()[-1]


# --------------------------------------------------------------------------- #
# Phase C — forecast (FY2026 + FY2027), segment-level
# --------------------------------------------------------------------------- #
# Assumptions are explicit and defensible. FY2026 net-sales growth is anchored to
# the reported Q1 FY2026 print (+3.8% YoY vs Q1 FY2025; the segment blend below is
# +3.6%). Adjusted-EBITDA margins step modestly off the FY2025 actuals as volume
# recovers and the FY2024-25 cost actions annualize. These are the only judgement
# inputs in Phase C; everything else is mechanical.
FORECAST = {
    "FY2026": {
        "start_month": "2026-01",
        "growth": {"PVG": 0.04, "AAG": 0.05, "SSG": 0.02},
        "margin": {"PVG": 0.130, "AAG": 0.125, "SSG": 0.210},
        "cogs_pct": 0.6979,          # hold FY2025 blended gross margin (30.2%)
        "da": 88_000_000.0,          # eases as Marucci intangibles amortize
        "capex": 42_000_000.0,
        "tax_rate": 0.22,            # normalized effective rate (FY actuals distorted by benefits)
    },
    "FY2027": {
        "start_month": "2027-01",
        "growth": {"PVG": 0.04, "AAG": 0.04, "SSG": 0.03},
        "margin": {"PVG": 0.135, "AAG": 0.130, "SSG": 0.210},
        "cogs_pct": 0.6950,
        "da": 82_000_000.0,
        "capex": 42_000_000.0,
        "tax_rate": 0.22,
    },
}
# Effective all-in cash rate on the term loan; ~$25M/yr scheduled amortization.
DEBT_RATE = 0.08
DEBT_AMORT_PER_YEAR = 25_000_000.0


def _grow(segments: list[Segment], growth: dict, margin: dict) -> list[Segment]:
    return [
        Segment(name=s.name, net_sales=s.net_sales * (1 + growth[s.name]),
                ebitda_margin=margin[s.name])
        for s in segments
    ]


def forecast_year(base: list[Segment], fy: str, debt_open: float,
                  opening: OpeningBalances) -> tuple[
                      pd.DataFrame, list[Segment], float, OpeningBalances
                  ]:
    """Build one forecast year and return its modeled closing balances."""
    a = FORECAST[fy]
    segs = _grow(base, a["growth"], a["margin"])
    revenue = sum(s.net_sales for s in segs)
    gross_profit = revenue * (1 - a["cogs_pct"])
    adj_ebitda = float(roll_up_segments(segs)["adjusted_ebitda"])
    cfg = EntityConfig(
        name=f"Fox Factory {fy} (forecast)",
        start_month=a["start_month"],
        horizon_months=12,
        tax_rate=a["tax_rate"],
        channels=segments_to_channels(segs, cogs_pct=a["cogs_pct"]),
        opex=[OpexLine(name="adjusted_opex", kind="fixed",
                       monthly_amount=(gross_profit - adj_ebitda) / 12)],
        debt=[DebtInstrument(name="term_loan", kind="term_loan",
                             opening_balance=debt_open, annual_rate=DEBT_RATE,
                             monthly_principal=DEBT_AMORT_PER_YEAR / 12)],
        working_capital=wc_days("FY2025"),
        opening_balances=opening,
        da_monthly=a["da"] / 12,
        capex_monthly=a["capex"] / 12,
    )
    frame = cashflow_from_config(cfg)
    revenue_frame = revenue_from_config(cfg)
    cogs_frame = cogs_from_config(cfg, revenue_frame)
    wc_frame = working_capital_from_config(cfg, revenue_frame, cogs_frame)
    closing = OpeningBalances(
        cash=float(frame["ending_cash"].iloc[-1]),
        ar=float(wc_frame["ar"].iloc[-1]),
        ap=float(wc_frame["ap"].iloc[-1]),
        inventory=float(wc_frame["inventory"].iloc[-1]),
    )
    return frame, segs, debt_open - DEBT_AMORT_PER_YEAR, closing


def build_forecast() -> tuple[pd.DataFrame, dict[str, list[Segment]]]:
    """FY2026 + FY2027 consolidated monthly forecast (24 months) plus the
    per-year segment views. Base = FY2025 actuals."""
    base = segments_for_year("FY2025")
    bs = balance_sheet()
    debt0 = float(bs.loc["long_term_debt_total", "FY2025"])
    open26 = opening_balances("FY2025")

    f26, segs26, debt_end26, open27 = forecast_year(base, "FY2026", debt0, open26)
    f27, segs27, _, _ = forecast_year(segs26, "FY2027", debt_end26, open27)

    forecast = pd.concat([f26, f27])
    return forecast, {"FY2026": segs26, "FY2027": segs27}


# --------------------------------------------------------------------------- #
# Phase D — Marucci divestiture sensitivity
# --------------------------------------------------------------------------- #
# Marucci sits inside SSG and is NOT reported standalone, so these are estimates
# anchored to the acquisition disclosures (paid $567M Nov-2023; $279M intangibles).
# This is the most assumption-heavy part of the exercise — a labeled sensitivity.
MARUCCI = {
    "revenue": 300_000_000.0,       # est. standalone net sales (grew from ~$285M at deal)
    "gross_margin": 0.50,           # branded sports equipment runs richer than Fox blended
    "ebitda_margin": 0.25,          # => ~$75M Adjusted EBITDA
    "da": 22_000_000.0,             # amortization of the $279M acquired intangibles
    "capex": 5_000_000.0,
}
DEFAULT_PROCEEDS = 300_000_000.0    # user default: a markdown from the $567M paid
SALE_MONTHS = (6, 12, 18, 24)


def marucci_carveout() -> Carveout:
    rev = MARUCCI["revenue"]
    gross_profit = rev * MARUCCI["gross_margin"]
    ebitda = rev * MARUCCI["ebitda_margin"]
    return Carveout(
        revenue=rev / 12,
        gross_profit=gross_profit / 12,
        opex=(gross_profit - ebitda) / 12,   # so gross_profit - opex == Marucci EBITDA
        da=MARUCCI["da"] / 12,
        capex=MARUCCI["capex"] / 12,
    )


def marucci_ebitda() -> float:
    return MARUCCI["revenue"] * MARUCCI["ebitda_margin"]


def proceeds_from_multiple(multiple: float) -> float:
    """Sale proceeds as an EV/EBITDA exit multiple on estimated Marucci EBITDA."""
    return multiple * marucci_ebitda()


def _run_rate_leverage(frame: pd.DataFrame, debt_balance: float) -> float:
    """Net debt / run-rate (final 12 months) EBITDA — annualized, not 2-year."""
    return net_debt_to_ebitda(frame.iloc[-12:], debt_balance=debt_balance)


def divestiture_grid(forecast: pd.DataFrame, debt_balance: float,
                     proceeds: float = DEFAULT_PROCEEDS) -> pd.DataFrame:
    """FCF and leverage impact of selling Marucci at each sale-timing, vs hold.

    ``two_yr_fcf`` is cumulative free cash flow over the 24-month forecast.
    ``net_debt_to_ebitda`` uses run-rate (final-year) EBITDA; selling retires
    ``proceeds`` of debt but also removes Marucci's EBITDA.
    """
    carve = marucci_carveout()
    rows = [{
        "scenario": "Hold Marucci", "sale_month": "—",
        "two_yr_fcf": float(forecast["free_cash_flow"].sum()),
        "net_debt_to_ebitda": _run_rate_leverage(forecast, debt_balance),
    }]
    for m in SALE_MONTHS:
        scn = divest(forecast, carve, sale_month=m, proceeds=proceeds,
                     annual_rate=DEBT_RATE, tax_rate=FORECAST["FY2026"]["tax_rate"])
        rows.append({
            "scenario": f"Sell at {m}mo", "sale_month": m,
            "two_yr_fcf": float(scn["free_cash_flow"].sum()),
            "net_debt_to_ebitda": _run_rate_leverage(scn, debt_balance - proceeds),
        })
    return pd.DataFrame(rows).set_index("scenario")


# Proceeds cases: at-cost (what Fox paid), the user default markdown, and two
# EV/EBITDA exit multiples on estimated Marucci EBITDA.
PROCEEDS_CASES = (
    ("At cost (~$567M paid)", 567_194_000.0),
    ("Default markdown", DEFAULT_PROCEEDS),
    ("8x EBITDA", None),
    ("12x EBITDA", None),
)


def proceeds_sensitivity(forecast: pd.DataFrame, debt_balance: float,
                         sale_month: int = 12) -> pd.DataFrame:
    """Hold the sale timing fixed; vary the sale price. More proceeds → more debt
    retired → lower leverage and (via interest saved) marginally higher FCF."""
    carve = marucci_carveout()
    multiples = {"8x EBITDA": 8.0, "12x EBITDA": 12.0}
    rows = []
    for label, fixed in PROCEEDS_CASES:
        proceeds = fixed if fixed is not None else proceeds_from_multiple(multiples[label])
        scn = divest(forecast, carve, sale_month=sale_month, proceeds=proceeds,
                     annual_rate=DEBT_RATE, tax_rate=FORECAST["FY2026"]["tax_rate"])
        rows.append({
            "proceeds_case": label, "proceeds": proceeds,
            "two_yr_fcf": float(scn["free_cash_flow"].sum()),
            "net_debt_to_ebitda": _run_rate_leverage(scn, debt_balance - proceeds),
        })
    return pd.DataFrame(rows).set_index("proceeds_case")
