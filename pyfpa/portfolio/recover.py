from __future__ import annotations

from pathlib import Path

from pyfpa.backtest.snapshot import Snapshot, load_snapshot


def recover_actuals(snapshot: Snapshot) -> dict[str, float]:
    """Recover the realized actuals from a scored snapshot by inverting the stored
    per-line error: actual = predicted / (1 + error). Only scored lines are
    recoverable; an unscored snapshot yields {}."""
    if snapshot.score is None:
        return {}
    out: dict[str, float] = {}
    for line, error in snapshot.score.per_line.items():
        if line in snapshot.predicted:
            out[line] = snapshot.predicted[line] / (1.0 + error)
    return out


def best_snapshot(client_path: str | Path) -> Snapshot | None:
    """The lowest-fitness scored snapshot in <client>/.fpa/forecasts/ — the
    assumptions that worked best for that client. None if no scored snapshot."""
    forecasts = Path(client_path) / ".fpa" / "forecasts"
    if not forecasts.exists():
        return None
    scored = [
        snap for f in sorted(forecasts.glob("*.snapshot.yaml"))
        if (snap := load_snapshot(f)).score is not None
    ]
    return min(scored, key=lambda s: s.score.fitness) if scored else None
