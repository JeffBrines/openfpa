"""Assemble Fox Factory models from the committed EDGAR actuals.

Importable by both ``run_foxf.py`` and the reconciliation test so the pipeline
and the regression guard share one code path. Every driver is derived from
``data/*.csv`` (no hand-transcribed numbers), keeping the example reproducible.
"""
from __future__ import annotations

from pathlib import Path

import pandas as pd

from pyfpa.analysis.segments import Segment, roll_up_segments, segments_to_channels
from pyfpa.config.schemas import (
    Channel, DebtInstrument, EntityConfig, OpeningBalances, OpexLine, WorkingCapitalConfig,
)
from pyfpa.models.cashflow import cashflow_from_config

DATA = Path(__file__).parent / "data"
SEGMENT_NAMES = ("PVG", "AAG", "SSG")


# --------------------------------------------------------------------------- #
# Data access
# --------------------------------------------------------------------------- #
def _table(name: str) -> pd.DataFrame:
    return pd.read_csv(DATA / name).set_index(pd.read_csv(DATA / name).columns[0])


def income_statement() -> pd.DataFrame:
    return pd.read_csv(DATA / "income_statement.csv").set_index("line")


def balance_sheet() -> pd.DataFrame:
    return pd.read_csv(DATA / "balance_sheet.csv").set_index("line")


def cash_flow() -> pd.DataFrame:
    return pd.read_csv(DATA / "cash_flow.csv").set_index("line")


def segment_table() -> pd.DataFrame:
    return pd.read_csv(DATA / "segments.csv")


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
# Phase A — reconciliation
# --------------------------------------------------------------------------- #
def phase_a_model(fy: str, prior_fy: str) -> dict[str, float]:
    """Run the engine on a year's actual drivers; return the annual model lines
    that Phase A reconciles against the reported actuals."""
    cfg = reconciliation_config(fy, prior_fy, start_month="2024-01")
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
