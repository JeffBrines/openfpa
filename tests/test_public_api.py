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
        "Segment", "segment_pnl", "roll_up_segments", "segments_to_channels",
        "Carveout", "divest", "net_debt_to_ebitda", "reconcile",
        "ScoreResult", "score_forecast", "Snapshot", "snapshot_forecast",
        "save_snapshot", "load_snapshot", "holdout_backtest",
        "magnitude_cap", "persistent_miss", "render_scorecard",
        "Override", "Correction", "load_corrections", "save_correction", "apply_corrections",
        "apply_override", "Experiment", "ExperimentCheck", "ExperimentDecision",
        "load_experiment", "load_experiments", "save_experiment",
        "initialize_workspace", "workspace_path",
        "Intake", "IntakeFact", "IntakeQuestion", "intake_ready", "load_intake",
        "next_intake_questions", "record_intake_fact", "save_intake",
        "ArchitectureProposal", "render_architecture_proposal", "render_business_profile",
        "write_onboarding_outputs",
        "MemoryEntry", "MemoryHit", "MemoryIndex", "build_context_pack",
        "build_memory_index", "load_memory_index", "save_memory_index", "search_memory",
        "CompanyEntrypoint", "EntrypointKind", "EntrypointRegistry",
        "load_entrypoint_registry", "register_entrypoint", "save_entrypoint_registry",
        "MappingRegistry", "MappingRule", "MappingStatus", "SourceKind",
        "SourceRecord", "SourceRegistry", "load_mapping_registry",
        "load_source_registry", "profile_table", "reconcile_account_table",
        "register_mapping", "register_source", "save_mapping_registry",
        "save_source_registry",
        "ConnectorAuth", "ConnectorManifest", "connector_bundle_path",
        "connector_generated_root", "load_connector_manifest",
        "load_connector_manifests", "save_connector_manifest",
        "scaffold_connector_bundle", "validate_connector_bundle",
        "EpochEvaluation", "MetricObjective", "ModelRegistry", "ModelVersion",
        "PromotionRecord", "ResearchEpoch", "ResearchObjective", "evaluate_challenger",
        "load_epoch", "load_epochs", "load_model_registry", "promote_challenger",
        "register_challenger", "save_epoch", "save_model_registry",
        "load_research_objective", "save_research_objective",
        "Portfolio", "load_portfolio", "mine_priors", "find_recurring_skills",
        "validate_prior", "promote_prior", "promote_skill", "seed_from_library",
    }, "pyfpa.__all__ must exactly match expected public API"


def test_top_level_smoke():
    from pathlib import Path
    repo_root = Path(__file__).resolve().parents[1]
    cfg = pyfpa.load_config(repo_root / "examples/ridgeline/config.yaml")
    df = pyfpa.cashflow_from_config(cfg)
    assert len(df) == 12
