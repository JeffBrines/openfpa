from __future__ import annotations

from collections.abc import Sequence

from pyfpa.backtest.snapshot import Snapshot


def magnitude_cap(old: float, new: float, *, cap: float = 0.25) -> float:
    """Clamp `new` to within ±`cap` (relative) of `old`, preventing overcorrection.
    A zero base has no defined relative bound, so `new` passes through."""
    if old == 0:
        return new
    lo, hi = sorted((old * (1 - cap), old * (1 + cap)))
    return max(lo, min(new, hi))


def persistent_miss(errors: Sequence[float], *, k: int = 2, threshold: float = 0.0) -> bool:
    """True when the last `k` per-line errors are all the same sign and all exceed
    `threshold` in magnitude - a repeated, directional miss, not noise."""
    if len(errors) < k:
        return False
    last = errors[-k:]
    return (all(e > threshold for e in last)) or (all(e < -threshold for e in last))


def render_scorecard(snapshots: Sequence[Snapshot]) -> str:
    """Render scored snapshots as a markdown track record (chronological)."""
    lines = [
        "# Forecast Scorecard",
        "",
        "| Period | Fitness (lower=better) | Per-line error |",
        "|---|--:|---|",
    ]
    for s in snapshots:
        if s.score is None:
            continue
        errs = ", ".join(f"{k} {v * 100:+.1f}%" for k, v in s.score.per_line.items())
        lines.append(f"| {s.label} | {s.score.fitness:.4f} | {errs} |")
    return "\n".join(lines) + "\n"
