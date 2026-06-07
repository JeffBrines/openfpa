import pyfpa


def test_public_api_exports():
    for name in [
        "EntityConfig", "Channel", "OpexLine", "DebtInstrument",
        "WorkingCapitalConfig", "OpeningBalances", "load_config",
        "revenue_from_config", "cogs_from_config", "opex_from_config",
        "working_capital_from_config", "debt_from_config", "cashflow_from_config",
    ]:
        assert hasattr(pyfpa, name), f"missing public export: {name}"


def test_all_matches_public_api():
    assert set(pyfpa.__all__) == {
        "EntityConfig", "Channel", "OpexLine", "DebtInstrument",
        "WorkingCapitalConfig", "OpeningBalances", "load_config",
        "revenue_from_config", "cogs_from_config", "opex_from_config",
        "working_capital_from_config", "debt_from_config", "cashflow_from_config",
        "Cash13Config", "WeeklyFlow", "expand_flow", "cash13_forecast", "runway_summary",
        "load_cash13_config", "read_pl_csv", "to_briefing_md", "forecast_to_excel",
        "Sku", "sku_profitability", "pareto_breakpoint", "load_skus",
    }, "pyfpa.__all__ must exactly match expected public API"


def test_top_level_smoke():
    from pathlib import Path
    repo_root = Path(__file__).resolve().parents[1]
    cfg = pyfpa.load_config(repo_root / "examples/ridgeline/config.yaml")
    df = pyfpa.cashflow_from_config(cfg)
    assert len(df) == 12
