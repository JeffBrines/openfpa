from pathlib import Path

from pyfpa.config.schemas import EntityConfig
from pyfpa.models.cashflow import cashflow_from_config
from pyfpa.backtest.snapshot import snapshot_forecast, save_snapshot
from pyfpa.backtest.score import score_forecast
from pyfpa.portfolio.manifest import Portfolio, ClientRef
from pyfpa.portfolio.mine import mine_priors, find_recurring_skills


def _base_cfg(dio):
    return EntityConfig.model_validate({
        "name": "c", "start_month": "2026-01", "horizon_months": 12, "tax_rate": 0.0,
        "channels": [{"name": "C", "annual_revenue": 1_200_000.0, "growth_rate": 0.0,
                      "seasonality": [1.0] * 12, "cogs_pct": 0.5}],
        "opex": [], "debt": [],
        "working_capital": {"dso_days": 30.0, "dpo_days": 30.0, "dio_days": dio},
        "opening_balances": {"cash": 0.0},
    })


def _make_client(tmp_path, name, dio, *, gen_skills=()):
    root = tmp_path / name
    cfg = _base_cfg(dio)
    fc = cashflow_from_config(cfg)
    snap = snapshot_forecast(cfg, fc, label="2026", created="2026-01-01")
    snap = snap.model_copy(update={"score": score_forecast(snap.predicted, snap.predicted)})
    (root / ".fpa" / "forecasts").mkdir(parents=True, exist_ok=True)
    save_snapshot(snap, root / ".fpa" / "forecasts" / "2026.snapshot.yaml")
    for s in gen_skills:
        d = root / "skills" / "generated" / s
        d.mkdir(parents=True, exist_ok=True)
        (d / "SKILL.md").write_text(f"---\nname: {s}\ndescription: x\n---\n")
    return ClientRef(path=str(root), type="d2c")


def _portfolio(clients):
    return Portfolio(library="lib", clients=clients)


def test_mine_priors_tight_cluster(tmp_path):
    clients = [_make_client(tmp_path, n, dio) for n, dio in [("a", 44.0), ("b", 45.0), ("c", 46.0)]]
    cands = mine_priors(_portfolio(clients), "d2c", min_support=3, dispersion_max=0.15)
    dio = [c for c in cands if c.driver == "working_capital.dio_days"]
    assert len(dio) == 1
    assert dio[0].value == 45.0
    assert len(dio[0].support) == 3


def test_mine_priors_scattered_yields_nothing(tmp_path):
    clients = [_make_client(tmp_path, n, dio) for n, dio in [("a", 20.0), ("b", 50.0), ("c", 95.0)]]
    cands = mine_priors(_portfolio(clients), "d2c", min_support=3, dispersion_max=0.15)
    assert [c for c in cands if c.driver == "working_capital.dio_days"] == []


def test_mine_priors_below_min_support(tmp_path):
    clients = [_make_client(tmp_path, n, 45.0) for n in ("a", "b")]
    assert mine_priors(_portfolio(clients), "d2c", min_support=3) == []


def test_mine_priors_unanimous_value_is_strongest_cluster(tmp_path):
    # all three clients run da_monthly=0 — a perfectly tight (unanimous) cluster
    # should still become a prior, not be dropped by a divide-by-zero mean.
    clients = [_make_client(tmp_path, n, 45.0) for n in ("a", "b", "c")]
    cands = mine_priors(_portfolio(clients), "d2c", min_support=3)
    da = [c for c in cands if c.driver == "da_monthly"]
    assert len(da) == 1
    assert da[0].value == 0.0
    assert da[0].dispersion == 0.0


def test_find_recurring_skills(tmp_path):
    clients = [_make_client(tmp_path, n, 45.0, gen_skills=["arr-waterfall"]) for n in ("a", "b", "c")]
    clients.append(_make_client(tmp_path, "d", 45.0, gen_skills=["one-off"]))
    skills = find_recurring_skills(_portfolio(clients), "d2c", min_support=3)
    names = [s.name for s in skills]
    assert "arr-waterfall" in names
    assert "one-off" not in names
