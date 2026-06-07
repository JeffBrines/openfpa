from pathlib import Path
import yaml

from pyfpa.cash13.schemas import Cash13Config
from pyfpa.cash13.forecast import cash13_forecast
from pyfpa.cash13.runway import runway_summary

REPO_ROOT = Path(__file__).resolve().parents[1]


def _load_ridgeline_cash13() -> Cash13Config:
    with (REPO_ROOT / "examples/ridgeline/cash13.yaml").open() as f:
        return Cash13Config.model_validate(yaml.safe_load(f))


def test_ridgeline_cash13_runs_and_dips():
    cfg = _load_ridgeline_cash13()
    df = cash13_forecast(cfg)
    assert len(df) == 13
    summary = runway_summary(df)
    # The inventory build should pull the trough below the opening balance.
    assert summary["min_cash"] < cfg.opening_cash
    # Sanity: ending cash is the running sum of net cash plus opening.
    assert round(df["ending_cash"].iloc[-1], 2) == round(
        cfg.opening_cash + df["net_cash"].sum(), 2
    )


import pyfpa  # noqa: E402


def test_cash13_public_exports():
    for name in ["Cash13Config", "WeeklyFlow", "expand_flow",
                 "cash13_forecast", "runway_summary"]:
        assert hasattr(pyfpa, name), f"missing public export: {name}"
    assert {"Cash13Config", "WeeklyFlow", "expand_flow",
            "cash13_forecast", "runway_summary"}.issubset(set(pyfpa.__all__))
