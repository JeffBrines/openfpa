from pyfpa.config.schemas import EntityConfig
from pyfpa.models.cashflow import cashflow_from_config
from pyfpa.backtest.snapshot import snapshot_forecast, save_snapshot
from pyfpa.backtest.score import score_forecast
from pyfpa.portfolio.manifest import ClientRef
from pyfpa.portfolio.validate import validate_prior


def _base_cfg(dio):
    return EntityConfig.model_validate({
        "name": "c", "start_month": "2026-01", "horizon_months": 12, "tax_rate": 0.0,
        "channels": [{"name": "C", "annual_revenue": 1_200_000.0, "growth_rate": 0.0,
                      "seasonality": [1.0] * 12, "cogs_pct": 0.5}],
        "opex": [], "debt": [],
        "working_capital": {"dso_days": 30.0, "dpo_days": 30.0, "dio_days": dio},
        "opening_balances": {"cash": 0.0},
    })


def _make_client(tmp_path, name, dio):
    root = tmp_path / name
    cfg = _base_cfg(dio)
    snap = snapshot_forecast(cfg, cashflow_from_config(cfg), label="2026", created="2026-01-01")
    snap = snap.model_copy(update={"score": score_forecast(snap.predicted, snap.predicted)})
    (root / ".fpa" / "forecasts").mkdir(parents=True, exist_ok=True)
    save_snapshot(snap, root / ".fpa" / "forecasts" / "2026.snapshot.yaml")
    return ClientRef(path=str(root), type="d2c")


def test_validate_tight_cluster_is_validated(tmp_path):
    clients = [_make_client(tmp_path, n, dio) for n, dio in [("a", 44.0), ("b", 45.0), ("c", 46.0)]]
    res = validate_prior("working_capital.dio_days", clients, tolerance=0.01)
    assert res.n_folds == 3
    assert res.mean_delta <= 0.01
    assert res.validated is True


def test_validate_scattered_not_validated(tmp_path):
    clients = [_make_client(tmp_path, n, dio) for n, dio in [("a", 10.0), ("b", 60.0), ("c", 120.0)]]
    res = validate_prior("working_capital.dio_days", clients, tolerance=0.0)
    assert res.validated is False


def test_validate_too_few_clients(tmp_path):
    clients = [_make_client(tmp_path, "a", 45.0)]
    res = validate_prior("working_capital.dio_days", clients)
    assert res.n_folds == 1
    assert res.validated is False
