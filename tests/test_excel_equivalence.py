import pytest

pytest.importorskip("formulas")

from pyfpa.config.loader import load_config
from pyfpa.config.schemas import EntityConfig
from pyfpa.excel.model_workbook import model_to_excel
from pyfpa.excel.verify import verify_workbook
from pyfpa.models.cashflow import cashflow_from_config


def test_ridgeline_workbook_reproduces_engine(tmp_path):
    cfg = load_config("examples/ridgeline/config.yaml")
    path = tmp_path / "ridgeline.xlsx"
    model_to_excel(cfg, path)
    report = verify_workbook(path, cashflow_from_config(cfg))
    assert report.passed, report.failures[:10]
    assert report.lines_checked >= 10


def test_edge_config_nol_debt_seasonality_reproduces_engine(tmp_path):
    cfg = EntityConfig.model_validate({
        "name": "Edge", "start_month": "2026-04", "horizon_months": 24, "tax_rate": 0.25,
        "channels": [
            {"name": "A", "annual_revenue": 2_400_000.0, "growth_rate": 0.12,
             "seasonality": [1, 1, 2, 3, 2, 1, 1, 1, 2, 3, 4, 3], "cogs_pct": 0.55},
            {"name": "B", "annual_revenue": 900_000.0, "growth_rate": -0.05,
             "seasonality": [2, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 2], "cogs_pct": 0.35},
        ],
        "opex": [
            {"name": "fixed_g_a", "kind": "fixed", "monthly_amount": 80_000.0},
            {"name": "var_mktg", "kind": "variable", "pct_of_revenue": 0.07},
        ],
        "debt": [
            {"name": "term", "kind": "term_loan", "opening_balance": 240_000.0,
             "annual_rate": 0.09, "monthly_principal": 25_000.0},
            {"name": "loc", "kind": "loc", "opening_balance": 150_000.0, "annual_rate": 0.11},
        ],
        "working_capital": {"dso_days": 38.0, "dpo_days": 42.0, "dio_days": 75.0},
        "opening_balances": {"cash": 25_000.0, "ar": 180_000.0, "ap": 110_000.0,
                              "inventory": 260_000.0, "nol": 500_000.0},
        "da_monthly": 6_000.0, "capex_monthly": 9_000.0,
    })
    path = tmp_path / "edge.xlsx"
    model_to_excel(cfg, path)
    report = verify_workbook(path, cashflow_from_config(cfg))
    assert report.passed, report.failures[:10]
