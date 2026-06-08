# Self-Improving Backtest Loop — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build the per-client self-improvement loop — snapshot forecasts, score them against the user's actuals (weighted MAPE), and surface ratified improvements — as a lean tested `pyfpa.backtest` package plus an `fpa-backtest-learn` skill.

**Architecture:** Hybrid. `pyfpa/backtest/` owns the objective, deterministic mechanics (extract scored lines from a forecast, score vs actuals via the existing `reconcile`, run a holdout backtest on history, and the mechanizable guardrail helpers). The `fpa-backtest-learn` skill owns judgment (attribution, proposals, ratification) and the `.fpa/` memory workflow. All new code is pure, immutable, typed, unit-tested.

**Tech Stack:** Python 3.11+, pydantic v2, pandas, PyYAML (existing deps).

**Spec:** `docs/superpowers/specs/2026-06-08-backtest-learning-loop-design.md`

---

## File Structure

| Path | Responsibility |
| --- | --- |
| `pyfpa/backtest/__init__.py` (create) | Re-export the package's public names. |
| `pyfpa/backtest/score.py` (create) | `DEFAULT_WEIGHTS`, `DEFAULT_SCORE_LINES`, `extract_lines`, `aggregate_periods`, `ScoreResult`, `score_forecast`. |
| `pyfpa/backtest/snapshot.py` (create) | `Snapshot`, `snapshot_forecast`, `save_snapshot`, `load_snapshot`. |
| `pyfpa/backtest/holdout.py` (create) | `holdout_backtest`. |
| `pyfpa/backtest/learn.py` (create) | `magnitude_cap`, `persistent_miss`, `render_scorecard`. |
| `pyfpa/__init__.py` (modify) | Export the public backtest symbols. |
| `skills/fpa-backtest-learn/SKILL.md` (create) | The judgment + `.fpa/` workflow skill. |
| `skills/fpa-monthly-close/SKILL.md` (modify) | Add a "Next" pointer to `fpa-backtest-learn`. |
| `.claude-plugin/plugin.json` (modify) | Register the new skill. |
| `tests/test_backtest_score.py` (create) | Unit tests for scoring + extraction. |
| `tests/test_backtest_snapshot.py` (create) | Unit tests for snapshot round-trip. |
| `tests/test_backtest_holdout.py` (create) | Unit tests for the holdout harness (incl. discrimination). |
| `tests/test_backtest_learn.py` (create) | Unit tests for the guardrail helpers + scorecard render. |
| `tests/test_public_api.py` (modify) | Keep the `__all__` contract test in sync. |

Conventions (from `~/.claude/rules`): immutability (return new objects), small focused files, clear names, pydantic v2, comprehensive correctness. Tests live FLAT in `tests/` (e.g. `tests/test_cogs.py`). Use `python3 -m pytest`.

---

## Group 1 — Scoring core (`pyfpa/backtest/score.py`)

### Task 1: `extract_lines` + `aggregate_periods`

These turn a forecast DataFrame (and a list of per-period actual dicts) into the scored-line dict, handling that `ending_cash` is a stock (take the last), `gross_margin` is a ratio (gross_profit / revenue), and the rest are flows (sum).

**Files:**
- Create: `pyfpa/backtest/__init__.py` (empty for now), `pyfpa/backtest/score.py`
- Test: `tests/test_backtest_score.py`

- [ ] **Step 1: Write the failing test**

```python
# tests/test_backtest_score.py
import pandas as pd
import pytest
from pyfpa.backtest.score import extract_lines, aggregate_periods, DEFAULT_SCORE_LINES


def _forecast():
    idx = pd.period_range("2026-01", periods=3, freq="M")
    return pd.DataFrame({
        "revenue": [100.0, 100.0, 100.0],
        "gross_profit": [40.0, 40.0, 40.0],
        "ebitda": [30.0, 30.0, 30.0],
        "ending_cash": [50.0, 70.0, 90.0],
    }, index=idx)


def test_extract_lines_flow_stock_ratio():
    out = extract_lines(_forecast(), DEFAULT_SCORE_LINES)
    assert out["revenue"] == 300.0           # flow: sum
    assert out["ebitda"] == 90.0             # flow: sum
    assert out["ending_cash"] == 90.0        # stock: last
    assert out["gross_margin"] == pytest.approx(120.0 / 300.0)  # ratio: ΣGP/Σrev


def test_aggregate_periods_matches_extract():
    periods = [
        {"revenue": 100.0, "gross_profit": 40.0, "ebitda": 30.0, "ending_cash": 50.0},
        {"revenue": 100.0, "gross_profit": 40.0, "ebitda": 30.0, "ending_cash": 70.0},
        {"revenue": 100.0, "gross_profit": 40.0, "ebitda": 30.0, "ending_cash": 90.0},
    ]
    out = aggregate_periods(periods, DEFAULT_SCORE_LINES)
    assert out["revenue"] == 300.0
    assert out["ending_cash"] == 90.0        # last period's stock
    assert out["gross_margin"] == pytest.approx(0.4)
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python3 -m pytest tests/test_backtest_score.py -v`
Expected: FAIL (`ModuleNotFoundError: pyfpa.backtest`).

- [ ] **Step 3: Implement**

Create empty `pyfpa/backtest/__init__.py`. Then `pyfpa/backtest/score.py`:

```python
from __future__ import annotations

from collections.abc import Mapping, Sequence

import pandas as pd

DEFAULT_SCORE_LINES = ["ending_cash", "ebitda", "revenue", "gross_margin"]
DEFAULT_WEIGHTS = {"ending_cash": 0.4, "ebitda": 0.3, "revenue": 0.2, "gross_margin": 0.1}


def extract_lines(forecast_df: pd.DataFrame, score_lines: Sequence[str]) -> dict[str, float]:
    """Reduce a monthly forecast to a {line: value} dict for scoring.

    `ending_cash` is a stock (take the last month); `gross_margin` is a ratio
    (Σ gross_profit / Σ revenue); every other line is a flow (sum)."""
    revenue = float(forecast_df["revenue"].sum())
    out: dict[str, float] = {}
    for line in score_lines:
        if line == "ending_cash":
            out[line] = float(forecast_df["ending_cash"].iloc[-1])
        elif line == "gross_margin":
            gp = float(forecast_df["gross_profit"].sum())
            out[line] = (gp / revenue) if revenue else 0.0
        else:
            out[line] = float(forecast_df[line].sum())
    return out


def aggregate_periods(
    period_dicts: Sequence[Mapping[str, float]], score_lines: Sequence[str]
) -> dict[str, float]:
    """Aggregate a chronological list of per-period actual dicts the same way
    `extract_lines` aggregates a forecast (flow=sum, stock=last, ratio=ΣGP/Σrev)."""
    revenue = sum(float(d.get("revenue", 0.0)) for d in period_dicts)
    out: dict[str, float] = {}
    for line in score_lines:
        if line == "ending_cash":
            out[line] = float(period_dicts[-1].get("ending_cash", 0.0))
        elif line == "gross_margin":
            gp = sum(float(d.get("gross_profit", 0.0)) for d in period_dicts)
            out[line] = (gp / revenue) if revenue else 0.0
        else:
            out[line] = sum(float(d.get(line, 0.0)) for d in period_dicts)
    return out
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `python3 -m pytest tests/test_backtest_score.py -v`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add pyfpa/backtest/__init__.py pyfpa/backtest/score.py tests/test_backtest_score.py
git commit -m "feat: backtest line extraction (flow/stock/ratio aggregation)"
```

### Task 2: `ScoreResult` + `score_forecast`

**Files:**
- Modify: `pyfpa/backtest/score.py`
- Test: `tests/test_backtest_score.py`

- [ ] **Step 1: Write the failing test**

```python
# append to tests/test_backtest_score.py
from pyfpa.backtest.score import ScoreResult, score_forecast, DEFAULT_WEIGHTS


def test_score_forecast_weighted_mape():
    predicted = {"ending_cash": 110.0, "ebitda": 90.0, "revenue": 300.0, "gross_margin": 0.40}
    actual = {"ending_cash": 100.0, "ebitda": 100.0, "revenue": 300.0, "gross_margin": 0.40}
    res = score_forecast(predicted, actual)
    # per-line signed error = predicted/actual - 1
    assert res.per_line["ending_cash"] == pytest.approx(0.10)
    assert res.per_line["ebitda"] == pytest.approx(-0.10)
    assert res.per_line["revenue"] == pytest.approx(0.0)
    # weighted MAPE with DEFAULT_WEIGHTS (0.4,0.3,0.2,0.1): 0.4*0.1 + 0.3*0.1 = 0.07
    assert res.fitness == pytest.approx(0.07)


def test_score_forecast_skips_absent_and_zero_actual_lines():
    # 'revenue' missing from predicted, 'ebitda' has zero actual -> both skipped;
    # only ending_cash scored -> weights renormalize to 1.0 on it.
    res = score_forecast(
        {"ending_cash": 90.0, "ebitda": 30.0},
        {"ending_cash": 100.0, "ebitda": 0.0},
    )
    assert set(res.per_line) == {"ending_cash"}
    assert res.fitness == pytest.approx(0.10)  # 1.0 * |0.9-1|
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python3 -m pytest tests/test_backtest_score.py::test_score_forecast_weighted_mape -v`
Expected: FAIL (`ImportError`).

- [ ] **Step 3: Implement**

Append to `pyfpa/backtest/score.py` (add `from pydantic import BaseModel` and `from pyfpa.analysis.reconcile import reconcile` at the top):

```python
class ScoreResult(BaseModel):
    fitness: float                       # weighted MAPE across scored lines; lower is better
    per_line: dict[str, float]           # signed error %, predicted/actual - 1
    weights: dict[str, float]            # the (renormalized) weights actually used


def score_forecast(
    predicted: Mapping[str, float],
    actual: Mapping[str, float],
    *,
    weights: Mapping[str, float] | None = None,
) -> ScoreResult:
    """Weighted MAPE of predicted vs actual over the scored lines present in both
    (and with non-zero actual). Per-line error reuses `reconcile`'s variance_pct.
    Weights are renormalized over the lines actually scored."""
    weights = dict(weights or DEFAULT_WEIGHTS)
    lines = [l for l in weights if l in predicted and l in actual and actual[l] != 0]
    if not lines:
        return ScoreResult(fitness=0.0, per_line={}, weights={})
    rec = reconcile({l: predicted[l] for l in lines}, {l: actual[l] for l in lines})
    per_line = {l: float(rec.loc[l, "variance_pct"]) for l in lines}
    total_w = sum(weights[l] for l in lines)
    used = {l: weights[l] / total_w for l in lines}
    fitness = sum(used[l] * abs(per_line[l]) for l in lines)
    return ScoreResult(fitness=fitness, per_line=per_line, weights=used)
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `python3 -m pytest tests/test_backtest_score.py -v`
Expected: PASS (all four).

- [ ] **Step 5: Commit**

```bash
git add pyfpa/backtest/score.py tests/test_backtest_score.py
git commit -m "feat: weighted-MAPE forecast scoring on top of reconcile"
```

---

## Group 2 — Snapshot persistence (`pyfpa/backtest/snapshot.py`)

### Task 3: `Snapshot` + `snapshot_forecast` + YAML round-trip

**Files:**
- Create: `pyfpa/backtest/snapshot.py`
- Test: `tests/test_backtest_snapshot.py`

- [ ] **Step 1: Write the failing test**

```python
# tests/test_backtest_snapshot.py
import pandas as pd
import pytest
from pyfpa.config.schemas import EntityConfig
from pyfpa.models.cashflow import cashflow_from_config
from pyfpa.backtest.snapshot import Snapshot, snapshot_forecast, save_snapshot, load_snapshot
from pyfpa.backtest.score import score_forecast


def _cfg():
    return EntityConfig.model_validate({
        "name": "T", "start_month": "2026-01", "horizon_months": 12, "tax_rate": 0.0,
        "channels": [{"name": "C", "annual_revenue": 1_200_000.0, "growth_rate": 0.0,
                      "seasonality": [1.0] * 12, "cogs_pct": 0.5}],
        "opex": [], "debt": [],
        "working_capital": {"dso_days": 0, "dpo_days": 0, "dio_days": 0},
        "opening_balances": {"cash": 0.0},
    })


def test_snapshot_forecast_captures_assumptions_and_predictions():
    cfg = _cfg()
    snap = snapshot_forecast(cfg, cashflow_from_config(cfg),
                             label="2026", created="2026-02-01")
    assert snap.label == "2026"
    assert snap.assumptions["channels"][0]["annual_revenue"] == 1_200_000.0
    assert snap.predicted["revenue"] == pytest.approx(1_200_000.0)
    assert snap.score is None


def test_snapshot_round_trip(tmp_path):
    cfg = _cfg()
    snap = snapshot_forecast(cfg, cashflow_from_config(cfg),
                             label="2026", created="2026-02-01")
    snap = snap.model_copy(update={"score": score_forecast(snap.predicted, snap.predicted)})
    p = tmp_path / "2026.snapshot.yaml"
    save_snapshot(snap, p)
    back = load_snapshot(p)
    assert back.label == "2026"
    assert back.predicted == snap.predicted
    assert back.score.fitness == pytest.approx(0.0)
    assert back.assumptions == snap.assumptions
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python3 -m pytest tests/test_backtest_snapshot.py -v`
Expected: FAIL (`ModuleNotFoundError`).

- [ ] **Step 3: Implement**

```python
# pyfpa/backtest/snapshot.py
from __future__ import annotations

from collections.abc import Sequence
from pathlib import Path

import pandas as pd
import yaml
from pydantic import BaseModel

from pyfpa.config.schemas import EntityConfig
from pyfpa.backtest.score import DEFAULT_SCORE_LINES, ScoreResult, extract_lines


class Snapshot(BaseModel):
    """The full record of one forecast: the assumptions it used, the lines it
    predicted, and (once the period closes) the realized score."""
    label: str
    created: str                 # caller-supplied date string; never generated here
    assumptions: dict            # serialized EntityConfig
    predicted: dict[str, float]
    score: ScoreResult | None = None


def snapshot_forecast(
    cfg: EntityConfig,
    forecast_df: pd.DataFrame,
    *,
    label: str,
    created: str,
    score_lines: Sequence[str] = DEFAULT_SCORE_LINES,
) -> Snapshot:
    return Snapshot(
        label=label,
        created=created,
        assumptions=cfg.model_dump(),
        predicted=extract_lines(forecast_df, score_lines),
    )


def save_snapshot(snapshot: Snapshot, path: str | Path) -> None:
    Path(path).write_text(yaml.safe_dump(snapshot.model_dump(), sort_keys=False))


def load_snapshot(path: str | Path) -> Snapshot:
    p = Path(path)
    if not p.exists():
        raise FileNotFoundError(f"snapshot not found: {p}")
    return Snapshot.model_validate(yaml.safe_load(p.read_text()))
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `python3 -m pytest tests/test_backtest_snapshot.py -v`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add pyfpa/backtest/snapshot.py tests/test_backtest_snapshot.py
git commit -m "feat: forecast snapshots with YAML round-trip"
```

---

## Group 3 — Holdout backtest (`pyfpa/backtest/holdout.py`)

### Task 4: `holdout_backtest`

**Files:**
- Create: `pyfpa/backtest/holdout.py`
- Test: `tests/test_backtest_holdout.py`

The harness splits ordered periods into fit (all but the last `holdout`) and holdout (the last `holdout`); calls the caller's `build_cfg_fn(fit_actuals)` to get a config that forecasts the holdout window; runs the engine; and scores predicted vs the aggregated holdout actuals.

- [ ] **Step 1: Write the failing test**

```python
# tests/test_backtest_holdout.py
import pytest
from pyfpa.config.schemas import EntityConfig
from pyfpa.backtest.holdout import holdout_backtest


def _actuals():
    # 6 months, revenue flat at 100/mo, gross_profit 40, ebitda 30, cash +20/mo
    out = {}
    cash = 0.0
    for i in range(6):
        cash += 20.0
        out[f"2026-{i+1:02d}"] = {"revenue": 100.0, "gross_profit": 40.0,
                                  "ebitda": 30.0, "ending_cash": cash}
    return out


def _build_cfg(growth):
    # build_cfg_fn factory: forecasts a 3-month holdout at the given monthly run-rate.
    def _fn(fit_actuals):
        n = len(fit_actuals)
        last_rev = list(fit_actuals.values())[-1]["revenue"]
        annual = last_rev * 12 * (1 + growth)
        return EntityConfig.model_validate({
            "name": "h", "start_month": f"2026-{n+1:02d}", "horizon_months": 3,
            "tax_rate": 0.0,
            "channels": [{"name": "C", "annual_revenue": annual, "growth_rate": 0.0,
                          "seasonality": [1.0] * 12, "cogs_pct": 0.6}],
            "opex": [], "debt": [],
            "working_capital": {"dso_days": 0, "dpo_days": 0, "dio_days": 0},
            "opening_balances": {"cash": 80.0},   # fit-window ending cash (4 * 20)
        })
    return _fn


def test_holdout_backtest_scores_holdout():
    res = holdout_backtest(_actuals(), _build_cfg(0.0), holdout=3,
                           score_lines=["revenue", "ebitda"])
    assert "revenue" in res.per_line
    assert res.fitness >= 0.0


def test_holdout_discriminates_better_assumption():
    # the flat (0% growth) model matches the flat actuals better than a +50% one
    good = holdout_backtest(_actuals(), _build_cfg(0.0), holdout=3, score_lines=["revenue"])
    bad = holdout_backtest(_actuals(), _build_cfg(0.5), holdout=3, score_lines=["revenue"])
    assert good.fitness < bad.fitness


def test_holdout_rejects_too_few_periods():
    with pytest.raises(ValueError):
        holdout_backtest({"2026-01": {"revenue": 1.0}}, _build_cfg(0.0), holdout=3,
                         score_lines=["revenue"])
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python3 -m pytest tests/test_backtest_holdout.py -v`
Expected: FAIL (`ModuleNotFoundError`).

- [ ] **Step 3: Implement**

```python
# pyfpa/backtest/holdout.py
from __future__ import annotations

from collections.abc import Callable, Mapping, Sequence

from pyfpa.config.schemas import EntityConfig
from pyfpa.models.cashflow import cashflow_from_config
from pyfpa.backtest.score import (
    DEFAULT_SCORE_LINES, ScoreResult, aggregate_periods, extract_lines, score_forecast,
)

BuildCfgFn = Callable[[dict[str, Mapping[str, float]]], EntityConfig]


def holdout_backtest(
    actuals_by_period: Mapping[str, Mapping[str, float]],
    build_cfg_fn: BuildCfgFn,
    *,
    holdout: int,
    score_lines: Sequence[str] = DEFAULT_SCORE_LINES,
    weights: Mapping[str, float] | None = None,
) -> ScoreResult:
    """Fit on all but the last `holdout` periods, predict the holdout, and score
    predicted vs the held-out actuals. The business-specific `build_cfg_fn`
    (fit actuals -> a config that forecasts the holdout window) is supplied by the
    caller; this harness only owns the split and the scoring. Nothing is scored on
    data it was fit on."""
    periods = list(actuals_by_period)
    if len(periods) <= holdout:
        raise ValueError(f"need more than {holdout} periods, got {len(periods)}")
    fit_periods = periods[:-holdout]
    holdout_periods = periods[-holdout:]

    fit_actuals = {p: dict(actuals_by_period[p]) for p in fit_periods}
    cfg = build_cfg_fn(fit_actuals)
    predicted = extract_lines(cashflow_from_config(cfg), score_lines)
    actual = aggregate_periods([dict(actuals_by_period[p]) for p in holdout_periods], score_lines)
    return score_forecast(predicted, actual, weights=weights)
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `python3 -m pytest tests/test_backtest_holdout.py -v`
Expected: PASS (all three — note the discrimination test is the core proof the metric works).

- [ ] **Step 5: Commit**

```bash
git add pyfpa/backtest/holdout.py tests/test_backtest_holdout.py
git commit -m "feat: holdout backtest harness (train/holdout split + score)"
```

---

## Group 4 — Guardrail + render helpers (`pyfpa/backtest/learn.py`)

### Task 5: `magnitude_cap`, `persistent_miss`, `render_scorecard`

**Files:**
- Create: `pyfpa/backtest/learn.py`
- Test: `tests/test_backtest_learn.py`

- [ ] **Step 1: Write the failing test**

```python
# tests/test_backtest_learn.py
import pytest
from pyfpa.backtest.learn import magnitude_cap, persistent_miss, render_scorecard
from pyfpa.backtest.snapshot import Snapshot
from pyfpa.backtest.score import ScoreResult


def test_magnitude_cap_clamps_relative():
    assert magnitude_cap(100.0, 200.0, cap=0.25) == pytest.approx(125.0)   # up-clamp
    assert magnitude_cap(100.0, 10.0, cap=0.25) == pytest.approx(75.0)     # down-clamp
    assert magnitude_cap(100.0, 110.0, cap=0.25) == pytest.approx(110.0)   # within cap
    assert magnitude_cap(0.0, 5.0, cap=0.25) == 5.0                        # zero base: pass


def test_persistent_miss_requires_k_same_signed():
    assert persistent_miss([0.1, 0.2], k=2) is True          # two positive
    assert persistent_miss([-0.1, -0.2], k=2) is True        # two negative
    assert persistent_miss([0.1, -0.2], k=2) is False        # sign flip
    assert persistent_miss([0.2], k=2) is False              # too short
    assert persistent_miss([0.001, 0.001], k=2, threshold=0.01) is False  # under threshold


def test_render_scorecard_table():
    snaps = [
        Snapshot(label="2026-01", created="2026-02-01", assumptions={}, predicted={},
                 score=ScoreResult(fitness=0.05, per_line={"revenue": 0.02}, weights={})),
        Snapshot(label="2026-02", created="2026-03-01", assumptions={}, predicted={},
                 score=ScoreResult(fitness=0.03, per_line={"revenue": -0.01}, weights={})),
    ]
    md = render_scorecard(snaps)
    assert "| 2026-01 |" in md
    assert "| 2026-02 |" in md
    assert "fitness" in md.lower()
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python3 -m pytest tests/test_backtest_learn.py -v`
Expected: FAIL (`ModuleNotFoundError`).

- [ ] **Step 3: Implement**

```python
# pyfpa/backtest/learn.py
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
    `threshold` in magnitude — a repeated, directional miss, not noise."""
    if len(errors) < k:
        return False
    last = errors[-k:]
    return (all(e > threshold for e in last)) or (all(e < -threshold for e in last))


def render_scorecard(snapshots: Sequence[Snapshot]) -> str:
    """Render scored snapshots as a markdown track record (chronological)."""
    lines = ["# Forecast Scorecard", "", "| Period | Fitness (lower=better) | Per-line error |",
             "|---|--:|---|"]
    for s in snapshots:
        if s.score is None:
            continue
        errs = ", ".join(f"{k} {v * 100:+.1f}%" for k, v in s.score.per_line.items())
        lines.append(f"| {s.label} | {s.score.fitness:.4f} | {errs} |")
    return "\n".join(lines) + "\n"
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `python3 -m pytest tests/test_backtest_learn.py -v`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add pyfpa/backtest/learn.py tests/test_backtest_learn.py
git commit -m "feat: guardrail helpers (magnitude cap, persistence) + scorecard render"
```

---

## Group 5 — Package wiring

### Task 6: Re-export + public API

**Files:**
- Modify: `pyfpa/backtest/__init__.py`, `pyfpa/__init__.py`, `tests/test_public_api.py`

- [ ] **Step 1: Fill `pyfpa/backtest/__init__.py`**

```python
from pyfpa.backtest.score import (
    DEFAULT_SCORE_LINES, DEFAULT_WEIGHTS, ScoreResult,
    aggregate_periods, extract_lines, score_forecast,
)
from pyfpa.backtest.snapshot import Snapshot, snapshot_forecast, save_snapshot, load_snapshot
from pyfpa.backtest.holdout import holdout_backtest
from pyfpa.backtest.learn import magnitude_cap, persistent_miss, render_scorecard

__all__ = [
    "DEFAULT_SCORE_LINES", "DEFAULT_WEIGHTS", "ScoreResult", "aggregate_periods",
    "extract_lines", "score_forecast", "Snapshot", "snapshot_forecast",
    "save_snapshot", "load_snapshot", "holdout_backtest", "magnitude_cap",
    "persistent_miss", "render_scorecard",
]
```

- [ ] **Step 2: Export from `pyfpa/__init__.py`** — after the existing analysis imports add:

```python
from pyfpa.backtest import (
    ScoreResult, score_forecast, Snapshot, snapshot_forecast,
    save_snapshot, load_snapshot, holdout_backtest,
    magnitude_cap, persistent_miss, render_scorecard,
)
```

And extend `pyfpa/__init__.py`'s `__all__` with those same names:

```python
    "ScoreResult", "score_forecast", "Snapshot", "snapshot_forecast",
    "save_snapshot", "load_snapshot", "holdout_backtest",
    "magnitude_cap", "persistent_miss", "render_scorecard",
```

- [ ] **Step 3: Sync the public-API contract test** — `tests/test_public_api.py` asserts `set(pyfpa.__all__)` equals an expected set. Add the same ten names above to that expected set. (Read the test first; match its exact assertion form.)

- [ ] **Step 4: Verify + full suite**

Run: `python3 -c "import pyfpa; print(pyfpa.score_forecast, pyfpa.holdout_backtest, pyfpa.Snapshot)"`
Expected: prints the three symbols.
Run: `python3 -m pytest -q`
Expected: all pass.

- [ ] **Step 5: Commit**

```bash
git add pyfpa/backtest/__init__.py pyfpa/__init__.py tests/test_public_api.py
git commit -m "feat: export pyfpa.backtest public API"
```

---

## Group 6 — The skill

### Task 7: `fpa-backtest-learn` skill + registration

**Files:**
- Create: `skills/fpa-backtest-learn/SKILL.md`
- Modify: `skills/fpa-monthly-close/SKILL.md` (add a Next pointer), `.claude-plugin/plugin.json`

- [ ] **Step 1: Write `skills/fpa-backtest-learn/SKILL.md`** with this content:

```markdown
---
name: fpa-backtest-learn
description: Use when you want the model to learn from how its past forecasts actually turned out — scoring forecasts against the company's real actuals, backtesting assumptions on history, and proposing ratified improvements. Runs at/after monthly close.
---

# Backtest & Learn (Operate)

## Overview

The model should get measurably better at this business over time. This skill
scores past forecasts against the company's actuals, surfaces what keeps missing,
and proposes improvements a human ratifies. The objective metric is reconciliation
error against the user's own books (`pyfpa.score_forecast`) — the FP&A analog of a
validation loss.

**Core principle:** self-improving, but never self-ratifying. The loop proposes;
a human accepts. Everything it learns lives as plain files in `.fpa/` the user owns.

## Memory (`.fpa/`)

- `forecasts/<period>.snapshot.yaml` — each forecast's assumptions + predictions, and (after close) its score.
- `scorecard.md` — the running track record (rendered, never hand-edited).
- `learnings.md` — every accepted change: what, the evidence, the backtest delta, the date.

## Workflow

1. **Snapshot every forecast.** When you produce a forecast, persist it:
   `snapshot_forecast(cfg, forecast_df, label=<period>, created=<today>)` →
   `save_snapshot(..., ".fpa/forecasts/<period>.snapshot.yaml")`.
2. **Score at close.** When a period closes (actuals via **fpa-configure-actuals**),
   load that period's snapshot, `score_forecast(snap.predicted, actuals)`, write the
   score back into the snapshot, and re-render `scorecard.md` with `render_scorecard`.
3. **Attribute** each material per-line miss to a driver (volume / price / cost ratio
   / working-capital timing). **Run the fpa-cfo-judgment one-time-item screen first** —
   never blame the model for a one-off.
4. **Propose**, tagged by type:
   - **Parametric** (an assumption change): re-score it with `holdout_backtest` on the
     company's history. Surface it **only if it lowers holdout fitness** (not in-sample),
     ranked by the delta. Clamp the proposed move with `magnitude_cap` (±25%/cycle).
   - **Structural** (a methodology/skill change, e.g. a revenue-recognition lag): surface
     **only** when `persistent_miss` is true for the line (same-signed across K≥2 closes)
     and it survived the one-time screen. Hand it to **fpa-learn-business** to generate the
     skill *on approval* — propose, don't auto-write.
5. **Ratify + log.** Present proposals; the human accepts/rejects. On accept, update the
   config and append to `learnings.md` (what, evidence, holdout delta, date). Reversible.

## Bootstrap (day one)

If the company already has ~12+ months of actuals, you don't have to wait: run
`holdout_backtest` immediately (fit on the earlier months, hold out the recent ones)
to report current accuracy and the first round of parametric proposals.

## Guardrails (always)

- Never score on data the model was fit on (`holdout_backtest` enforces this).
- No proposal off a single period — require a persistent, same-signed miss.
- A parametric change must improve **holdout** fitness, not in-sample fit.
- Cap how far any assumption moves per cycle (`magnitude_cap`).
- Human ratifies everything; every change is logged and reversible.

## Next

Scored + learned → **fpa-board-briefing** (report the forecast and how it's tracking).
```

- [ ] **Step 2: Add a Next pointer in `skills/fpa-monthly-close/SKILL.md`** — its `## Next` section currently points to fpa-cash-runway and fpa-board-briefing. Append: ` and **fpa-backtest-learn** (score this close against the prior forecast and learn from the miss).`

- [ ] **Step 3: Register the skill in `.claude-plugin/plugin.json`** — read the file, find the array/list of skills, and add `fpa-backtest-learn` in the same shape as the existing entries (match their exact format — name/path keys).

- [ ] **Step 4: Verify the plugin manifest is valid JSON**

Run: `python3 -c "import json; json.load(open('.claude-plugin/plugin.json')); print('ok')"`
Expected: `ok`.

- [ ] **Step 5: Commit**

```bash
git add skills/fpa-backtest-learn/ skills/fpa-monthly-close/SKILL.md .claude-plugin/plugin.json
git commit -m "feat: fpa-backtest-learn skill — score, backtest, propose, ratify"
```

---

## Group 7 — Scenario test + docs

### Task 8: Structural-miss scenario test

**Files:**
- Create: `tests/test_backtest_scenario.py`

Proves the loop's structural trigger: a business whose cash conversion lags (predicted ending cash persistently overstates actual) produces a persistent, same-signed miss that `persistent_miss` flags.

- [ ] **Step 1: Write the test**

```python
# tests/test_backtest_scenario.py
from pyfpa.backtest.score import score_forecast
from pyfpa.backtest.learn import persistent_miss


def test_persistent_cash_overstatement_is_flagged():
    # Across three closes the model predicts ending cash above actual every time
    # (a real collections lag the model doesn't capture) -> structural trigger.
    closes = [
        ({"ending_cash": 100.0}, {"ending_cash": 90.0}),
        ({"ending_cash": 120.0}, {"ending_cash": 108.0}),
        ({"ending_cash": 140.0}, {"ending_cash": 126.0}),
    ]
    cash_errors = [score_forecast(p, a).per_line["ending_cash"] for p, a in closes]
    assert all(e > 0 for e in cash_errors)            # always overstated
    assert persistent_miss(cash_errors, k=3, threshold=0.05) is True
```

- [ ] **Step 2: Run test to verify it passes**

Run: `python3 -m pytest tests/test_backtest_scenario.py -v`
Expected: PASS (this exercises already-built functions, so it passes immediately — it's a behavior lock, not new code).

- [ ] **Step 3: Run the full suite**

Run: `python3 -m pytest -q`
Expected: all pass.

- [ ] **Step 4: Commit**

```bash
git add tests/test_backtest_scenario.py
git commit -m "test: structural-miss scenario (persistent cash overstatement flagged)"
```

### Task 9: README skillset + roadmap mention

**Files:**
- Modify: `README.md`

- [ ] **Step 1: Add the skill to the skillset list** — in the "The skillset is the point" numbered list, the **Operate** item names `fpa-monthly-close`, `fpa-cash-runway`, `fpa-board-briefing`. Add `fpa-backtest-learn` to that Operate item with a short gloss: "scores past forecasts against your actuals and proposes ratified improvements — the self-improving loop."

- [ ] **Step 2: Add a roadmap row** — in the "Project status & roadmap" table add: `| Self-improving backtest loop (\`pyfpa.backtest\` + \`fpa-backtest-learn\`) | ✅ Built |`.

- [ ] **Step 3: Commit**

```bash
git add README.md
git commit -m "docs: surface the self-improving backtest loop in the README"
```

### Task 10: Final verification + PR

- [ ] **Step 1: Full suite**

Run: `python3 -m pytest -q`
Expected: all green.

- [ ] **Step 2: Open the PR** (stacked on `feat/foxfactory-example`, which carries `reconcile`)

```bash
git push -u origin feat/backtest-learning-loop
gh pr create --base main --title "feat: self-improving backtest loop (pyfpa.backtest + fpa-backtest-learn)" \
  --body "Per-client self-improvement loop: snapshot forecasts, score them against the user's actuals (weighted MAPE on cash/EBITDA/revenue/margin via reconcile), holdout-backtest on history, and propose ratified parametric + structural improvements. Memory is transparent files in .fpa/. Lean tested pyfpa.backtest package + fpa-backtest-learn skill. Spec: docs/superpowers/specs/2026-06-08-backtest-learning-loop-design.md. Depends on reconcile from #1."
```

Expected: PR opened. Jeff reviews/merges.

---

## Self-Review notes

- **Spec coverage:** memory layout → Tasks 3,5,7. `score.py` (extract/score) → Tasks 1,2. `snapshot.py` → Task 3. `holdout.py` → Task 4. `learn.py` (cap/persistence/render) → Task 5. Skill responsibilities (snapshot/score/attribute/propose/ratify) → Task 7. Guardrails → Tasks 4 (holdout separation), 5 (cap, persistence), 7 (one-time screen, improve-out-of-sample, human ratify). Fitness metric → Task 2. Bootstrap holdout → Tasks 4, 7. Success criteria 1–7 → covered. Testing list → Tasks 1,2,3,4,5,8.
- **Signature consistency:** `extract_lines`, `aggregate_periods`, `ScoreResult(fitness, per_line, weights)`, `score_forecast(predicted, actual, *, weights)`, `Snapshot(label, created, assumptions, predicted, score)`, `snapshot_forecast(cfg, forecast_df, *, label, created, score_lines)`, `holdout_backtest(actuals_by_period, build_cfg_fn, *, holdout, score_lines, weights)`, `magnitude_cap(old, new, *, cap)`, `persistent_miss(errors, *, k, threshold)`, `render_scorecard(snapshots)` — used identically everywhere.
- **No autonomous apply / no cross-client library / no new ingestion** — honored (scope boundaries).
