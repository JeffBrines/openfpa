# Portfolio Learning (Loop B) — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Cross-client learning for a fractional CFO's own (local) book — mine patterns that generalize across same-type clients, validate them with leave-one-out cross-client backtesting, and promote ratified priors/skills into a local library that seeds new clients.

**Architecture:** A tested `pyfpa.portfolio` package owns the mechanics (manifest, snapshot mining, leave-one-out validation reusing Loop A's scorer, the local library). An `fpa-portfolio-learn` skill owns judgment (present candidates, operator ratifies); `fpa-learn-business` seeds new clients from the library. All local, no network; pure, immutable, typed, unit-tested.

**Tech Stack:** Python 3.11+, pydantic v2, PyYAML, stdlib `statistics`/`copy` (existing deps).

**Spec:** `docs/superpowers/specs/2026-06-08-portfolio-learning-design.md`

---

## File Structure

| Path | Responsibility |
| --- | --- |
| `pyfpa/memory/paths.py` (modify) | Add public `apply_override` (wraps `_set_by_path`). |
| `pyfpa/memory/__init__.py`, `pyfpa/__init__.py` (modify) | Export `apply_override`. |
| `pyfpa/portfolio/__init__.py` (create) | Re-export the package's public names. |
| `pyfpa/portfolio/manifest.py` (create) | `ClientRef`, `Portfolio`, `load_portfolio`, `clients_of_type`. |
| `pyfpa/portfolio/recover.py` (create) | `recover_actuals`, `best_snapshot`. |
| `pyfpa/portfolio/mine.py` (create) | `MINEABLE_DRIVERS`, `PriorCandidate`, `mine_priors`, `SkillCandidate`, `find_recurring_skills`. |
| `pyfpa/portfolio/validate.py` (create) | `ValidationResult`, `validate_prior` (leave-one-out). |
| `pyfpa/portfolio/library.py` (create) | `load_library`, `promote_prior`, `promote_skill`, `seed_from_library`. |
| `pyfpa/__init__.py` (modify) | Export the portfolio public symbols. |
| `skills/fpa-portfolio-learn/SKILL.md` (create) | The judgment + workflow skill. |
| `skills/fpa-learn-business/SKILL.md` (modify) | Seed new clients from the library. |
| `README.md` (modify) | The "how it compounds" pass + skillset/roadmap rows. |
| `tests/test_memory_paths.py` (modify) | Test the new `apply_override`. |
| `tests/test_portfolio_manifest.py`, `test_portfolio_recover.py`, `test_portfolio_mine.py`, `test_portfolio_validate.py`, `test_portfolio_library.py` (create) | Unit tests. |
| `tests/test_public_api.py` (modify) | Keep the `__all__` contract test in sync. |

Conventions: immutability, small focused files, clear names, pydantic v2. Tests FLAT in `tests/`. Use `python3 -m pytest`. **All file paths the engine touches are caller-supplied; no network anywhere.**

---

## Group 1 — Public `apply_override` (memory touch-up)

### Task 1: promote `_set_by_path` to public `apply_override`

**Files:**
- Modify: `pyfpa/memory/paths.py`, `pyfpa/memory/__init__.py`, `pyfpa/__init__.py`, `tests/test_memory_paths.py`, `tests/test_public_api.py`

- [ ] **Step 1: Add the failing test** (append to `tests/test_memory_paths.py`):

```python
from pyfpa.memory.paths import apply_override


def test_apply_override_is_public_set_by_path():
    data = {"working_capital": {"dio_days": 30.0}}
    apply_override(data, "working_capital.dio_days", 45.0)
    assert data["working_capital"]["dio_days"] == 45.0
```

- [ ] **Step 2: Run, confirm fail**

Run: `python3 -m pytest tests/test_memory_paths.py::test_apply_override_is_public_set_by_path -v`
Expected: FAIL (`ImportError`).

- [ ] **Step 3: Implement** — append to `pyfpa/memory/paths.py`:

```python
def apply_override(data: dict, path: str, value: float) -> None:
    """Set ``value`` at dotted ``path`` (supports ``name``, ``name[n]``, ``name[*]``)
    in ``data``, in place. Public wrapper over the internal path setter."""
    _set_by_path(data, path, value)
```

In `pyfpa/memory/__init__.py`, add `apply_override` to the import from `pyfpa.memory.paths` (add a line `from pyfpa.memory.paths import apply_override`) and to `__all__`.
In `pyfpa/__init__.py`, add `apply_override` to the `from pyfpa.memory import (...)` block and to `__all__`.
In `tests/test_public_api.py`, add `"apply_override"` to the expected `__all__` set (keep exact-set-equality).

- [ ] **Step 4: Run tests**

Run: `python3 -m pytest -q`
Expected: all pass (incl. test_public_api).

- [ ] **Step 5: Commit**

```bash
git add pyfpa/memory/ pyfpa/__init__.py tests/test_memory_paths.py tests/test_public_api.py
git commit -m "feat: public apply_override in pyfpa.memory"
```

---

## Group 2 — Portfolio manifest (`pyfpa/portfolio/manifest.py`)

### Task 2: `ClientRef` + `Portfolio` + `load_portfolio` + `clients_of_type`

**Files:**
- Create: `pyfpa/portfolio/__init__.py` (empty for now), `pyfpa/portfolio/manifest.py`
- Test: `tests/test_portfolio_manifest.py`

- [ ] **Step 1: Failing test**

```python
# tests/test_portfolio_manifest.py
from pyfpa.portfolio.manifest import ClientRef, Portfolio, load_portfolio, clients_of_type


def test_load_portfolio_and_filter(tmp_path):
    (tmp_path / "p.yaml").write_text(
        "library: ~/.fpa/library\n"
        "clients:\n"
        "  - { path: ~/clients/acme, type: d2c-inventory }\n"
        "  - { path: ~/clients/haul, type: trucking }\n"
        "  - { path: ~/clients/peak, type: d2c-inventory }\n"
    )
    pf = load_portfolio(tmp_path / "p.yaml")
    assert pf.library == "~/.fpa/library"
    assert len(pf.clients) == 3
    d2c = clients_of_type(pf, "d2c-inventory")
    assert [c.path for c in d2c] == ["~/clients/acme", "~/clients/peak"]
    assert all(isinstance(c, ClientRef) for c in d2c)
```

- [ ] **Step 2: Run, confirm fail** (`ModuleNotFoundError`).

- [ ] **Step 3: Implement** — empty `pyfpa/portfolio/__init__.py`, then `pyfpa/portfolio/manifest.py`:

```python
from __future__ import annotations

from pathlib import Path

import yaml
from pydantic import BaseModel


class ClientRef(BaseModel):
    path: str          # client workspace root (contains .fpa/ and skills/)
    type: str          # business-type tag (the clustering key)


class Portfolio(BaseModel):
    library: str
    clients: list[ClientRef]


def load_portfolio(path: str | Path) -> Portfolio:
    p = Path(path)
    if not p.exists():
        raise FileNotFoundError(f"portfolio manifest not found: {p}")
    return Portfolio.model_validate(yaml.safe_load(p.read_text()))


def clients_of_type(portfolio: Portfolio, business_type: str) -> list[ClientRef]:
    return [c for c in portfolio.clients if c.type == business_type]
```

- [ ] **Step 4: Run** `python3 -m pytest tests/test_portfolio_manifest.py -v` → PASS.

- [ ] **Step 5: Commit**

```bash
git add pyfpa/portfolio/__init__.py pyfpa/portfolio/manifest.py tests/test_portfolio_manifest.py
git commit -m "feat: portfolio manifest (ClientRef, Portfolio, load, clients_of_type)"
```

---

## Group 3 — Recover actuals + best snapshot (`pyfpa/portfolio/recover.py`)

### Task 3: `recover_actuals` + `best_snapshot`

**Files:**
- Create: `pyfpa/portfolio/recover.py`
- Test: `tests/test_portfolio_recover.py`

- [ ] **Step 1: Failing test**

```python
# tests/test_portfolio_recover.py
import pytest
from pyfpa.backtest.snapshot import Snapshot, save_snapshot
from pyfpa.backtest.score import ScoreResult
from pyfpa.portfolio.recover import recover_actuals, best_snapshot


def _snap(label, fitness, predicted, per_line):
    return Snapshot(label=label, created="2026-01-01", assumptions={}, predicted=predicted,
                    score=ScoreResult(fitness=fitness, per_line=per_line, weights={}))


def test_recover_actuals_inverts_error():
    # per_line error = predicted/actual - 1  =>  actual = predicted / (1 + error)
    snap = _snap("p", 0.1, {"revenue": 110.0, "ebitda": 90.0}, {"revenue": 0.10, "ebitda": -0.10})
    act = recover_actuals(snap)
    assert act["revenue"] == pytest.approx(100.0)
    assert act["ebitda"] == pytest.approx(100.0)


def test_recover_actuals_no_score_is_empty():
    snap = Snapshot(label="p", created="2026-01-01", assumptions={}, predicted={"revenue": 1.0})
    assert recover_actuals(snap) == {}


def test_best_snapshot_picks_lowest_fitness(tmp_path):
    forecasts = tmp_path / ".fpa" / "forecasts"
    save_snapshot(_snap("2026-01", 0.20, {"revenue": 1.0}, {"revenue": 0.0}), forecasts / "a.snapshot.yaml")
    save_snapshot(_snap("2026-02", 0.05, {"revenue": 1.0}, {"revenue": 0.0}), forecasts / "b.snapshot.yaml")
    best = best_snapshot(tmp_path)
    assert best.label == "2026-02"


def test_best_snapshot_none_when_unscored_or_missing(tmp_path):
    assert best_snapshot(tmp_path / "nope") is None
    forecasts = tmp_path / ".fpa" / "forecasts"
    unscored = Snapshot(label="p", created="2026-01-01", assumptions={}, predicted={"revenue": 1.0})
    save_snapshot(unscored, forecasts / "u.snapshot.yaml")
    assert best_snapshot(tmp_path) is None
```

Note: `save_snapshot` takes a file path; it does not create parent dirs. Create them in the test if needed — `save_snapshot` writes to the given path, so ensure `forecasts` exists first (add `forecasts.mkdir(parents=True, exist_ok=True)` before the saves in each test that uses it).

- [ ] **Step 2: Run, confirm fail** (`ModuleNotFoundError`).

- [ ] **Step 3: Implement** `pyfpa/portfolio/recover.py`:

```python
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
```

- [ ] **Step 4: Run** `python3 -m pytest tests/test_portfolio_recover.py -v` → PASS. Then full suite.

- [ ] **Step 5: Commit**

```bash
git add pyfpa/portfolio/recover.py tests/test_portfolio_recover.py
git commit -m "feat: recover_actuals (invert stored score) + best_snapshot"
```

---

## Group 4 — Mining (`pyfpa/portfolio/mine.py`)

### Task 4: `mine_priors` + `find_recurring_skills`

**Files:**
- Create: `pyfpa/portfolio/mine.py`
- Test: `tests/test_portfolio_mine.py`

- [ ] **Step 1: Failing test**

```python
# tests/test_portfolio_mine.py
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
    assert dio[0].value == 45.0                 # median
    assert len(dio[0].support) == 3


def test_mine_priors_scattered_yields_nothing(tmp_path):
    clients = [_make_client(tmp_path, n, dio) for n, dio in [("a", 20.0), ("b", 50.0), ("c", 95.0)]]
    cands = mine_priors(_portfolio(clients), "d2c", min_support=3, dispersion_max=0.15)
    assert [c for c in cands if c.driver == "working_capital.dio_days"] == []


def test_mine_priors_below_min_support(tmp_path):
    clients = [_make_client(tmp_path, n, 45.0) for n in ("a", "b")]
    assert mine_priors(_portfolio(clients), "d2c", min_support=3) == []


def test_find_recurring_skills(tmp_path):
    clients = [_make_client(tmp_path, n, 45.0, gen_skills=["arr-waterfall"]) for n in ("a", "b", "c")]
    clients.append(_make_client(tmp_path, "d", 45.0, gen_skills=["one-off"]))
    skills = find_recurring_skills(_portfolio(clients), "d2c", min_support=3)
    names = [s.name for s in skills]
    assert "arr-waterfall" in names
    assert "one-off" not in names
```

- [ ] **Step 2: Run, confirm fail** (`ModuleNotFoundError`).

- [ ] **Step 3: Implement** `pyfpa/portfolio/mine.py`:

```python
from __future__ import annotations

import statistics
from pathlib import Path

from pydantic import BaseModel

from pyfpa.memory.corrections import load_corrections
from pyfpa.portfolio.manifest import ClientRef, Portfolio, clients_of_type
from pyfpa.portfolio.recover import best_snapshot

MINEABLE_DRIVERS = [
    "working_capital.dso_days", "working_capital.dio_days", "working_capital.dpo_days",
    "tax_rate", "da_monthly", "capex_monthly",
]


class PriorCandidate(BaseModel):
    business_type: str
    driver: str
    value: float
    support: list[str]
    dispersion: float


class SkillCandidate(BaseModel):
    business_type: str
    name: str
    support: list[str]
    source: str


def _get_by_path(data: dict, path: str) -> float | None:
    node = data
    for segment in path.split("."):
        if not isinstance(node, dict) or segment not in node:
            return None
        node = node[segment]
    return float(node) if isinstance(node, (int, float)) else None


def client_driver_value(client: ClientRef, driver: str) -> float | None:
    """The best-snapshot value for `driver`, overridden by an applied parametric
    correction on that exact path if one exists."""
    snap = best_snapshot(client.path)
    if snap is None:
        return None
    for c in load_corrections(Path(client.path) / ".fpa" / "corrections"):
        if c.status == "applied" and c.type == "parametric" and c.override and c.override.path == driver:
            return c.override.value
    return _get_by_path(snap.assumptions, driver)


def mine_priors(portfolio: Portfolio, business_type: str, *,
                min_support: int = 3, dispersion_max: float = 0.15) -> list[PriorCandidate]:
    """Drivers that cluster tightly (CoV <= dispersion_max) across >= min_support
    same-type clients become prior candidates at the median."""
    clients = clients_of_type(portfolio, business_type)
    out: list[PriorCandidate] = []
    for driver in MINEABLE_DRIVERS:
        present = [(c, v) for c in clients if (v := client_driver_value(c, driver)) is not None]
        if len(present) < min_support:
            continue
        values = [v for _, v in present]
        mean = statistics.fmean(values)
        cov = (statistics.pstdev(values) / abs(mean)) if mean else float("inf")
        if cov <= dispersion_max:
            out.append(PriorCandidate(
                business_type=business_type, driver=driver,
                value=statistics.median(values), support=[c.path for c, _ in present],
                dispersion=cov,
            ))
    return out


def find_recurring_skills(portfolio: Portfolio, business_type: str, *,
                          min_support: int = 3) -> list[SkillCandidate]:
    """Generated-skill directory names that recur across >= min_support same-type
    clients. (Structural corrections are an additional human signal the operator
    weighs in the skill, not a mechanical trigger here.)"""
    clients = clients_of_type(portfolio, business_type)
    by_name: dict[str, list[tuple[str, str]]] = {}
    for c in clients:
        generated = Path(c.path) / "skills" / "generated"
        if not generated.exists():
            continue
        for d in sorted(generated.iterdir()):
            if (d / "SKILL.md").exists():
                by_name.setdefault(d.name, []).append((c.path, str(d)))
    out: list[SkillCandidate] = []
    for name, refs in by_name.items():
        if len(refs) >= min_support:
            out.append(SkillCandidate(
                business_type=business_type, name=name,
                support=[p for p, _ in refs], source=refs[0][1],
            ))
    return out
```

- [ ] **Step 4: Run** `python3 -m pytest tests/test_portfolio_mine.py -v` → PASS (all four). Then full suite.

- [ ] **Step 5: Commit**

```bash
git add pyfpa/portfolio/mine.py tests/test_portfolio_mine.py
git commit -m "feat: mine_priors (clustering) + find_recurring_skills"
```

---

## Group 5 — Leave-one-out validation (`pyfpa/portfolio/validate.py`)

### Task 5: `validate_prior`

**Files:**
- Create: `pyfpa/portfolio/validate.py`
- Test: `tests/test_portfolio_validate.py`

- [ ] **Step 1: Failing test** (reuses the `_make_client` helper pattern from Task 4 — copy it into this file):

```python
# tests/test_portfolio_validate.py
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
    # all three clients share dio ≈ 45 → a peer-derived value ≈ each client's own → mean_delta ≈ 0
    clients = [_make_client(tmp_path, n, dio) for n, dio in [("a", 44.0), ("b", 45.0), ("c", 46.0)]]
    res = validate_prior("working_capital.dio_days", clients, tolerance=0.01)
    assert res.n_folds == 3
    assert res.mean_delta <= 0.01
    assert res.validated is True


def test_validate_scattered_not_validated(tmp_path):
    # wildly different dio → forcing a peer-median onto each degrades fit → positive mean_delta
    clients = [_make_client(tmp_path, n, dio) for n, dio in [("a", 10.0), ("b", 60.0), ("c", 120.0)]]
    res = validate_prior("working_capital.dio_days", clients, tolerance=0.0)
    assert res.validated is False


def test_validate_too_few_clients(tmp_path):
    clients = [_make_client(tmp_path, "a", 45.0)]
    res = validate_prior("working_capital.dio_days", clients)
    assert res.n_folds == 1
    assert res.validated is False
```

- [ ] **Step 2: Run, confirm fail** (`ModuleNotFoundError`).

- [ ] **Step 3: Implement** `pyfpa/portfolio/validate.py`:

```python
from __future__ import annotations

import copy
import statistics

from pydantic import BaseModel

from pyfpa.config.schemas import EntityConfig
from pyfpa.models.cashflow import cashflow_from_config
from pyfpa.backtest.score import DEFAULT_SCORE_LINES, extract_lines, score_forecast
from pyfpa.memory.paths import apply_override
from pyfpa.portfolio.manifest import ClientRef
from pyfpa.portfolio.mine import client_driver_value
from pyfpa.portfolio.recover import best_snapshot, recover_actuals


class ValidationResult(BaseModel):
    mean_delta: float
    n_folds: int
    validated: bool


def validate_prior(driver: str, type_clients: list[ClientRef], *, tolerance: float = 0.0) -> ValidationResult:
    """Leave-one-out cross-client check. For each usable client, derive `driver`'s
    value as the median across the OTHER clients, apply it to the held-out client's
    best-snapshot config, re-forecast, and score against that client's recovered
    actuals. A prior is `validated` if the mean fitness delta (new - original) is
    <= tolerance with >= 2 folds — a peer-derived value does not degrade held-out fit."""
    usable = []
    for c in type_clients:
        snap = best_snapshot(c.path)
        value = client_driver_value(c, driver)
        if snap is not None and snap.score is not None and value is not None:
            usable.append((value, snap))
    n = len(usable)
    if n < 2:
        return ValidationResult(mean_delta=0.0, n_folds=n, validated=False)

    deltas = []
    for i, (_, snap) in enumerate(usable):
        peer_values = [usable[j][0] for j in range(n) if j != i]
        prior_value = statistics.median(peer_values)
        data = copy.deepcopy(snap.assumptions)
        apply_override(data, driver, prior_value)
        forecast = cashflow_from_config(EntityConfig.model_validate(data))
        predicted = extract_lines(forecast, DEFAULT_SCORE_LINES)
        new_fitness = score_forecast(predicted, recover_actuals(snap)).fitness
        deltas.append(new_fitness - snap.score.fitness)

    mean_delta = statistics.fmean(deltas)
    return ValidationResult(mean_delta=mean_delta, n_folds=n, validated=mean_delta <= tolerance)
```

- [ ] **Step 4: Run** `python3 -m pytest tests/test_portfolio_validate.py -v` → PASS. The tight-cluster test proves the metric stays ≈0 for a robust prior; the scattered test proves it rejects a non-generalizing one. Then full suite.

- [ ] **Step 5: Commit**

```bash
git add pyfpa/portfolio/validate.py tests/test_portfolio_validate.py
git commit -m "feat: validate_prior — leave-one-out cross-client validation"
```

---

## Group 6 — Local library (`pyfpa/portfolio/library.py`)

### Task 6: `load_library` + `promote_prior` + `promote_skill` + `seed_from_library`

**Files:**
- Create: `pyfpa/portfolio/library.py`
- Test: `tests/test_portfolio_library.py`

- [ ] **Step 1: Failing test**

```python
# tests/test_portfolio_library.py
from pyfpa.config.schemas import EntityConfig
from pyfpa.portfolio.mine import PriorCandidate, SkillCandidate
from pyfpa.portfolio.validate import ValidationResult
from pyfpa.portfolio.library import (
    load_library, promote_prior, promote_skill, seed_from_library,
)


def _cfg(dio=30.0):
    return EntityConfig.model_validate({
        "name": "c", "start_month": "2026-01", "horizon_months": 12, "tax_rate": 0.0,
        "channels": [{"name": "C", "annual_revenue": 1_000_000.0, "growth_rate": 0.0,
                      "seasonality": [1.0] * 12, "cogs_pct": 0.5}],
        "opex": [], "debt": [],
        "working_capital": {"dso_days": 30.0, "dpo_days": 30.0, "dio_days": dio},
        "opening_balances": {"cash": 0.0},
    })


def test_promote_prior_and_seed(tmp_path):
    lib = tmp_path / "library"
    cand = PriorCandidate(business_type="d2c", driver="working_capital.dio_days",
                          value=45.0, support=["a", "b", "c"], dispersion=0.02)
    promote_prior(lib, cand, ValidationResult(mean_delta=-0.01, n_folds=3, validated=True))
    # the log records it
    assert "working_capital.dio_days" in (lib / "library-log.md").read_text()
    # a new client's config gets the prior as its starting value
    seeded = seed_from_library(lib, "d2c", _cfg(dio=30.0))
    assert seeded.working_capital.dio_days == 45.0
    assert _cfg(dio=30.0).working_capital.dio_days == 30.0     # base unmutated


def test_seed_unknown_type_is_noop(tmp_path):
    lib = tmp_path / "library"
    out = seed_from_library(lib, "saas", _cfg(dio=30.0))
    assert out.working_capital.dio_days == 30.0


def test_load_library_round_trip(tmp_path):
    lib = tmp_path / "library"
    cand = PriorCandidate(business_type="d2c", driver="tax_rate", value=0.25,
                          support=["a", "b", "c"], dispersion=0.01)
    promote_prior(lib, cand, ValidationResult(mean_delta=0.0, n_folds=3, validated=True))
    loaded = load_library(lib)
    assert any(p["driver"] == "tax_rate" and p["value"] == 0.25 for p in loaded["priors"]["d2c"])


def test_promote_skill_copies_and_logs(tmp_path):
    src = tmp_path / "src" / "arr-waterfall"
    src.mkdir(parents=True)
    (src / "SKILL.md").write_text("---\nname: arr-waterfall\ndescription: x\n---\n")
    lib = tmp_path / "library"
    promote_skill(lib, SkillCandidate(business_type="saas", name="arr-waterfall",
                                      support=["a", "b", "c"], source=str(src)))
    assert (lib / "skills" / "arr-waterfall" / "SKILL.md").exists()
    assert "arr-waterfall" in (lib / "library-log.md").read_text()
```

- [ ] **Step 2: Run, confirm fail** (`ModuleNotFoundError`).

- [ ] **Step 3: Implement** `pyfpa/portfolio/library.py`:

```python
from __future__ import annotations

import shutil
from pathlib import Path

import yaml

from pyfpa.config.schemas import EntityConfig
from pyfpa.memory.paths import apply_override
from pyfpa.portfolio.mine import PriorCandidate, SkillCandidate
from pyfpa.portfolio.validate import ValidationResult


def _log(library: Path, line: str) -> None:
    library.mkdir(parents=True, exist_ok=True)
    log = library / "library-log.md"
    header = "" if log.exists() else "# Library Log\n\n"
    with log.open("a") as f:
        f.write(header + line + "\n")


def load_library(library: str | Path) -> dict:
    """Read the library: {'priors': {type: [prior dicts]}, 'skills': [names]}."""
    library = Path(library)
    priors: dict[str, list[dict]] = {}
    priors_dir = library / "priors"
    if priors_dir.exists():
        for f in sorted(priors_dir.glob("*.yaml")):
            doc = yaml.safe_load(f.read_text()) or {}
            priors[doc.get("type", f.stem)] = doc.get("priors", [])
    skills = sorted(p.name for p in (library / "skills").glob("*")) if (library / "skills").exists() else []
    return {"priors": priors, "skills": skills}


def promote_prior(library: str | Path, candidate: PriorCandidate, validation: ValidationResult) -> None:
    """Append a ratified prior to priors/<type>.yaml and log it."""
    library = Path(library)
    priors_dir = library / "priors"
    priors_dir.mkdir(parents=True, exist_ok=True)
    path = priors_dir / f"{candidate.business_type}.yaml"
    doc = yaml.safe_load(path.read_text()) if path.exists() else None
    doc = doc or {"type": candidate.business_type, "priors": []}
    doc["priors"].append({
        "driver": candidate.driver, "value": candidate.value, "support": candidate.support,
        "cross_client_holdout_delta": validation.mean_delta, "n_folds": validation.n_folds,
    })
    path.write_text(yaml.safe_dump(doc, sort_keys=False))
    _log(library, f"- prior `{candidate.driver}` = {candidate.value} for {candidate.business_type} "
                  f"(support {len(candidate.support)}, Δ {validation.mean_delta:+.4f})")


def promote_skill(library: str | Path, candidate: SkillCandidate) -> None:
    """Copy a recurring generated skill into the library and log it."""
    library = Path(library)
    dest = library / "skills" / candidate.name
    dest.mkdir(parents=True, exist_ok=True)
    shutil.copytree(candidate.source, dest, dirs_exist_ok=True)
    _log(library, f"- skill `{candidate.name}` for {candidate.business_type} "
                  f"(support {len(candidate.support)})")


def seed_from_library(library: str | Path, business_type: str, cfg: EntityConfig) -> EntityConfig:
    """Apply the library's promoted priors for `business_type` to a starting config.
    Returns a NEW config (input unmutated). Priors are seeds; the per-client loop refines."""
    data = cfg.model_dump()
    for prior in load_library(library)["priors"].get(business_type, []):
        apply_override(data, prior["driver"], prior["value"])
    return EntityConfig.model_validate(data)
```

- [ ] **Step 4: Run** `python3 -m pytest tests/test_portfolio_library.py -v` → PASS. Then full suite.

- [ ] **Step 5: Commit**

```bash
git add pyfpa/portfolio/library.py tests/test_portfolio_library.py
git commit -m "feat: local library — promote priors/skills, seed new clients"
```

---

## Group 7 — Package wiring

### Task 7: Re-export + public API

**Files:**
- Modify: `pyfpa/portfolio/__init__.py`, `pyfpa/__init__.py`, `tests/test_public_api.py`

- [ ] **Step 1: Fill `pyfpa/portfolio/__init__.py`**

```python
from pyfpa.portfolio.manifest import ClientRef, Portfolio, load_portfolio, clients_of_type
from pyfpa.portfolio.recover import recover_actuals, best_snapshot
from pyfpa.portfolio.mine import (
    MINEABLE_DRIVERS, PriorCandidate, SkillCandidate, mine_priors, find_recurring_skills,
)
from pyfpa.portfolio.validate import ValidationResult, validate_prior
from pyfpa.portfolio.library import (
    load_library, promote_prior, promote_skill, seed_from_library,
)

__all__ = [
    "ClientRef", "Portfolio", "load_portfolio", "clients_of_type",
    "recover_actuals", "best_snapshot", "MINEABLE_DRIVERS", "PriorCandidate",
    "SkillCandidate", "mine_priors", "find_recurring_skills", "ValidationResult",
    "validate_prior", "load_library", "promote_prior", "promote_skill", "seed_from_library",
]
```

- [ ] **Step 2: Export the headline names from `pyfpa/__init__.py`** — after the `from pyfpa.memory import (...)` block add:

```python
from pyfpa.portfolio import (
    Portfolio, load_portfolio, mine_priors, find_recurring_skills,
    validate_prior, promote_prior, promote_skill, seed_from_library,
)
```

And extend `pyfpa/__init__.py`'s `__all__` with those eight names.

- [ ] **Step 3: Sync `tests/test_public_api.py`** — add the same eight names to the exact-set assertion. Read it first; keep exact-set-equality.

- [ ] **Step 4: Verify + full suite**

Run: `python3 -c "import pyfpa; print(pyfpa.mine_priors, pyfpa.validate_prior, pyfpa.seed_from_library)"`
Expected: prints the three.
Run: `python3 -m pytest -q`
Expected: all pass.

- [ ] **Step 5: Commit**

```bash
git add pyfpa/portfolio/__init__.py pyfpa/__init__.py tests/test_public_api.py
git commit -m "feat: export pyfpa.portfolio public API"
```

---

## Group 8 — Skill + integration

### Task 8: `fpa-portfolio-learn` skill + `fpa-learn-business` seeding

**Files:**
- Create: `skills/fpa-portfolio-learn/SKILL.md`
- Modify: `skills/fpa-learn-business/SKILL.md`

- [ ] **Step 1: Write `skills/fpa-portfolio-learn/SKILL.md`**:

```markdown
---
name: fpa-portfolio-learn
description: Use when you run FP&A for several clients and want your practice to compound — mines patterns that generalize across your same-type clients, validates them by leave-one-out cross-client backtesting, and promotes ratified priors and skills into a local library that seeds every new client. All local; nothing leaves your machine.
---

# Portfolio Learn (Loop B)

## Overview

Loop A makes the model better at one client. This makes your *practice* compound:
client #10 starts smarter than client #1 because your library carries what generalized
across #1–9. Everything is local — your own book, on your own machine.

**Core principle:** self-improving, never self-ratifying — propose, you accept. The
objective metric is cross-client: does a pattern learned on some clients fail to
degrade the *others*' backtest?

## Setup

A portfolio manifest `~/.fpa/portfolio.yaml` lists your clients + a business-type tag:
\```yaml
library: ~/.fpa/library
clients:
  - { path: ~/clients/acme,  type: d2c-inventory }
  - { path: ~/clients/peak,  type: d2c-inventory }
  - { path: ~/clients/haul,  type: trucking }
\```

## Workflow

1. **Load** the manifest (`pyfpa.load_portfolio`).
2. For each business-type with ≥ 3 clients:
   - **Priors:** `pyfpa.mine_priors(portfolio, type)` → drivers that cluster tightly.
     Validate each with `pyfpa.validate_prior(driver, clients_of_type)` (leave-one-out).
     Surface validated ones first (mean cross-client delta), then unvalidated/judgment.
   - **Skills:** `pyfpa.find_recurring_skills(portfolio, type)` for recurring generated
     skills. Also weigh recurring **structural corrections** across clients (read each
     `.fpa/corrections/` for `type: structural`) — a human-authored pattern that repeats
     is strong signal.
3. **Present** candidates ranked by evidence (support count + cross-client delta).
4. **Ratify.** On your acceptance, `pyfpa.promote_prior` / `pyfpa.promote_skill` writes the
   `~/.fpa/library/` and `library-log.md`. Reversible.

## Guardrails

- Local-only; nothing phones home.
- ≥ 3 clients to propose; tight-cluster only; a prior must not degrade held-out clients.
- You ratify everything; priors are *seeds*, not mandates — each client's Loop A refines.

## The payoff

New clients inherit the library: **fpa-learn-business** seeds their starting model from
your promoted priors (`pyfpa.seed_from_library`) and offers the promoted skills.

## Next

Promoted → next new client onboarded via **fpa-learn-business** starts smarter.
```

(Note: in the file, the triple-backtick yaml block above should use normal triple backticks — the `\``` escaping here is only for this plan document.)

- [ ] **Step 2: Wire seeding into `skills/fpa-learn-business/SKILL.md`** — in its workflow (when scaffolding a new client's model), add a step:
  "**Seed from your library.** If a portfolio library exists, start the model from what generalized across your same-type clients: `cfg = pyfpa.seed_from_library(library_path, business_type, cfg)` (priors are seeds — this client's loop refines them). Offer any promoted skills for the type."
  Place it consistent with the file's numbered-workflow style (read the file first).

- [ ] **Step 3: Verify frontmatter**

Run: `python3 -c "import pathlib,yaml; [yaml.safe_load(p.read_text().split('---')[1]) for p in pathlib.Path('skills').glob('*/SKILL.md')]; print('ok')"`
Expected: `ok`.

- [ ] **Step 4: Commit**

```bash
git add skills/fpa-portfolio-learn/ skills/fpa-learn-business/SKILL.md
git commit -m "feat: fpa-portfolio-learn skill + library seeding in learn-business"
```

---

## Group 9 — README pass + final

### Task 9: README "how it compounds" pass

**Files:**
- Modify: `README.md`

- [ ] **Step 1: Add `fpa-portfolio-learn` to the skillset list** — in the "The skillset is the point" numbered list **Operate** item, add `fpa-portfolio-learn` with a gloss: "and **`fpa-portfolio-learn`** — distills what generalizes across your whole book into a reusable library that seeds new clients (cross-client learning)."

- [ ] **Step 2: Add a roadmap row** — after the corrections row:
  `| Cross-client portfolio learning (\`pyfpa.portfolio\` + \`fpa-portfolio-learn\`) | ✅ Built |`

- [ ] **Step 3: Add a short "How it compounds" subsection** right after the "Why not just point Claude at your books?" section. Use this content:

```markdown
## How it compounds

openfpa isn't static — it gets better the more you use it, on two loops, both with your data staying in your repo:

- **Per client (Loop A).** Every close, it scores its last forecast against your actuals and proposes ratified tweaks. The model gets better at *this* business. Human corrections feed the same memory — the highest-signal fixes, captured durably.
- **Across your book (Loop B).** For a fractional CFO with many clients, it distills what *generalizes* — validated by leave-one-out cross-client backtesting — into a local library that seeds every new client. Client #10 starts smarter than client #1.

It's [Karpathy's AutoResearch](https://github.com/karpathy/autoresearch) idea applied to FP&A: an objective fitness metric (reconciliation error on your books) drives measurable self-improvement — at the client level *and* the portfolio level.
```

- [ ] **Step 4: Commit**

```bash
git add README.md
git commit -m "docs: 'how it compounds' — the two-loop self-improvement story"
```

### Task 10: Final verification + PR

- [ ] **Step 1: Full suite**

Run: `python3 -m pytest -q`
Expected: all green.

- [ ] **Step 2: Open the PR** (stacked on `feat/memory-corrections`)

```bash
git push -u origin feat/portfolio-learning
gh pr create --base feat/memory-corrections --head feat/portfolio-learning \
  --title "feat: cross-client portfolio learning (pyfpa.portfolio + fpa-portfolio-learn)" \
  --body "Loop B: a fractional CFO's practice compounds. Mines drivers that cluster across same-type clients (from Loop A snapshots + applied corrections), validates each with leave-one-out cross-client backtesting (reuses score_forecast — a prior must not degrade held-out clients), and promotes ratified priors/skills into a local ~/.fpa/library/ that seeds new clients via fpa-learn-business. All local, operator-ratified. Lean tested pyfpa.portfolio + fpa-portfolio-learn skill + the 'how it compounds' README. Spec: docs/superpowers/specs/2026-06-08-portfolio-learning-design.md. Stacked on the memory layer."
```

Expected: PR opened. Jeff reviews/merges.

---

## Self-Review notes

- **Spec coverage:** apply_override touch-up → Task 1. manifest → Task 2. recover_actuals/best_snapshot → Task 3. mine_priors/find_recurring_skills (+ MINEABLE_DRIVERS, dispersion gate, min_support) → Task 4. validate_prior leave-one-out → Task 5. library (load/promote_prior/promote_skill/seed_from_library) → Task 6. wiring → Task 7. fpa-portfolio-learn skill + learn-business seeding → Task 8. README "how it compounds" → Task 9. Guardrails (local-only, min_support, dispersion, held-out validation, ratify, seeds-not-mandates) → Tasks 4,5,6,8. Privacy (no network) → all tasks operate on caller paths.
- **Signature consistency:** `ClientRef(path,type)`, `Portfolio(library,clients)`, `clients_of_type`, `recover_actuals(snapshot)`, `best_snapshot(client_path)`, `client_driver_value(client,driver)`, `mine_priors(portfolio,type,*,min_support,dispersion_max)`, `PriorCandidate(business_type,driver,value,support,dispersion)`, `SkillCandidate(business_type,name,support,source)`, `find_recurring_skills(portfolio,type,*,min_support)`, `ValidationResult(mean_delta,n_folds,validated)`, `validate_prior(driver,type_clients,*,tolerance)`, `load_library`, `promote_prior(library,candidate,validation)`, `promote_skill(library,candidate)`, `seed_from_library(library,type,cfg)` — used identically across tasks.
- **Scope:** local-only (no central/community aggregation), entity-level mineable drivers (per-channel deferred), operator-ratified only, no new ingestion — all honored.
