# Self-Improving Backtest Loop — Design

**Status:** Approved (design phase)
**Date:** 2026-06-08
**Topic:** A per-client loop that scores past forecasts against the user's actuals
and proposes ratified improvements — the self-improvement engine behind openfpa's
mission ("it sharpens itself against your actuals every close").

## Why

openfpa's differentiator is that the model **gets measurably better at your
business over time**. Karpathy's AutoResearch self-improves only because it has a
cheap, objective fitness function (validation loss). FP&A's equivalent is
**reconciliation error against the user's own actuals** — exactly the metric the
Fox Factory work proved out (`pyfpa.analysis.reconcile`). Today, forecasts are
ephemeral: nothing persists a forecast, scores it once the period closes, or
remembers which assumptions keep missing. This builds that loop.

## Decisions (locked)

| Decision | Choice |
| --- | --- |
| Autonomy | **Score + propose; human ratifies.** No autonomous apply. |
| Bootstrap | **Holdout backtest on existing history** (immediate value) + forward accumulation. |
| Learning scope | Both **parametric** (assumption tuning, auto-scored) and **structural** (methodology/skill proposals, human-judged) — one evidence trail. |
| Architecture | **Hybrid:** lean tested `pyfpa.backtest` (objective scoring) + `fpa-backtest-learn` skill (judgment). |
| Memory | **Transparent files in `.fpa/`** — the user owns and can audit/edit them. |
| Fitness metric | **Weighted MAPE** across decision-critical lines (ending cash, EBITDA, revenue, gross margin). |

## Memory layout (`.fpa/`)

```
.fpa/
  business-profile.md          # (existing)
  forecasts/
    2026-01.snapshot.yaml      # assumptions + predicted lines, and (after close) the score
    2026-02.snapshot.yaml
  scorecard.md                 # rendered running track record: fitness + per-line error, per period
  learnings.md                 # accepted changes: what, evidence, backtest delta, date (reversible)
```

A **snapshot** is the full record of one forecast: the assumptions (config drivers)
it used, the lines it predicted, and — added once the period closes — the realized
`score`. `scorecard.md` is rendered from the scored snapshots (single source of
truth per period; no duplicate store). `learnings.md` is the audit log of every
ratified change.

## Components

### Engine — `pyfpa/backtest/` (lean, pure, tested)

`pyfpa/backtest/snapshot.py`
- `class Snapshot(BaseModel)`: `label: str`, `created: str`, `assumptions: dict`
  (the serialized `EntityConfig`), `predicted: dict[str, float]` (scored lines for
  the forecast period), `score: ScoreResult | None = None`.
- `snapshot_forecast(cfg: EntityConfig, forecast_df: pd.DataFrame, *, label: str, created: str, score_lines: list[str]) -> Snapshot` — pure; captures assumptions + the annual/aggregate predicted values for `score_lines`.
- `save_snapshot(snapshot, path)` / `load_snapshot(path) -> Snapshot` — YAML round-trip.
  (`created` is passed in, never generated — keeps the engine deterministic.)

`pyfpa/backtest/score.py`
- `class ScoreResult(BaseModel)`: `fitness: float` (weighted MAPE; lower better),
  `per_line: dict[str, float]` (signed error %, `predicted/actual - 1`), `weights: dict[str, float]`.
- `DEFAULT_WEIGHTS = {"ending_cash": 0.4, "ebitda": 0.3, "revenue": 0.2, "gross_margin": 0.1}`.
- `score_forecast(predicted: Mapping[str, float], actual: Mapping[str, float], *, weights=DEFAULT_WEIGHTS) -> ScoreResult` — built on `reconcile`; `fitness = Σ wᵢ·|predictedᵢ/actualᵢ − 1|` over lines present in both (weights renormalized over present lines).

`pyfpa/backtest/holdout.py`
- `holdout_backtest(actuals_by_period: dict[str, dict[str, float]], build_cfg_fn: Callable[[dict[str, dict[str, float]]], EntityConfig], *, holdout: int, score_lines: list[str], weights=DEFAULT_WEIGHTS) -> ScoreResult` — split periods into fit (all but last `holdout`) and holdout (last `holdout`); `build_cfg_fn(fit_actuals)` → config; `cashflow_from_config` → predicted; score predicted vs the held-out actuals. The engine owns the split/score harness; the business-specific `build_cfg_fn` (actuals → assumptions) is supplied by the caller, never hardcoded.

`pyfpa/backtest/__init__.py` re-exports the public names; `pyfpa/__init__.py` exposes them.

### Skill — `skills/fpa-backtest-learn/SKILL.md` (judgment; hooks into `fpa-monthly-close`)

Responsibilities (methodology, not code):
1. **Snapshot** every forecast it produces into `.fpa/forecasts/`.
2. **Score at close** — when a period closes (actuals via `fpa-configure-actuals`), load that period's snapshot, `score_forecast`, write the `score` back, re-render `scorecard.md`.
3. **Attribute** each material per-line miss to a driver (volume / price / cost ratio / WC timing), running the `fpa-cfo-judgment` one-time-item screen first.
4. **Propose**, tagged by type:
   - *Parametric* — a concrete assumption change, each re-scored via `holdout_backtest` and shown with its **holdout** fitness delta; only surfaced if it improves out-of-sample.
   - *Structural* — only when a per-line miss is persistent and same-signed across **K closes** and survives the one-time screen; proposed as a methodology/skill change (e.g. a revenue-recognition lag), handed to the existing `fpa-learn-business` skill-generation path on approval.
5. **Ratify + log** — the human accepts/rejects; accepted changes update the config and append to `learnings.md` with evidence, the backtest delta, and the date.

## Data flow

```
forecast ──▶ snapshot_forecast() ──▶ .fpa/forecasts/<period>.snapshot.yaml
period closes (actuals) ──▶ score_forecast() ──▶ snapshot.score ──▶ scorecard.md
                                   │
        attribute miss (after one-time screen)
                                   ▼
   parametric proposal ──(re-score via holdout_backtest)──▶ holdout delta
   structural proposal ──(persistent K-close signed miss)──▶ surfaced
                                   ▼
            human ratifies ──▶ config update + learnings.md ──▶ next forecast better
```

## Guardrails (anti-overfitting / trust)

1. **Holdout separation** — `holdout_backtest` never scores on fit data.
2. **Persistence threshold `K`** (default 2) — no proposal off a single period; a miss must repeat same-signed across `K` closes.
3. **One-time-item screen** — `fpa-cfo-judgment` check before attributing a miss to the model.
4. **Improve-out-of-sample gate** — a parametric change must lower **holdout** fitness, not in-sample.
5. **Magnitude cap** — limit how far any single assumption moves per cycle (default ±25% relative) to prevent overcorrection.
6. **Human ratify + audit** — nothing is applied without acceptance; every change is logged in `learnings.md` and is reversible.

## Success criteria

1. `holdout_backtest` returns a fitness number from `≥ holdout + 1` periods of actuals, reusing `reconcile`.
2. Snapshots round-trip (save/load); scoring writes the `score` block back; `scorecard.md` renders from scored snapshots.
3. Parametric proposals appear **only** when they improve holdout fitness, ranked by delta.
4. Structural proposals appear **only** on a persistent same-signed miss that passes the one-time screen.
5. Every accepted change is logged in `learnings.md` with evidence + date and is reversible.
6. All `.fpa/` artifacts are plain, human-readable files — no hidden state.
7. `pyfpa.backtest` is unit-tested (repo's 80% norm); full suite green.

## Testing

- **snapshot** round-trip preserves assumptions + predictions.
- **score_forecast**: known predicted/actual → known weighted MAPE; absent lines renormalize weights.
- **holdout_backtest**: synthetic series with a *known* best assumption — the harness must score the correct config better than a wrong one (proves the metric discriminates).
- **guardrails**: single-period miss → no proposal; persistent same-signed miss → proposal; a change that improves in-sample but not holdout → rejected; assumption move beyond the cap → clamped.
- **scenario**: a synthetic series with a built-in revenue lag → backtest surfaces a persistent signed miss (the structural-proposal trigger).

## Scope boundaries (YAGNI)

- **No autonomous search** (the variant-search version of AutoResearch) — human-ratified only; the harness is built so search can be added later.
- **No cross-client pattern library** (promoting learnings into shared industry skills) — that's a separate future subsystem with its own review bar.
- **No new ingestion or output formats** — uses the existing `fpa-configure-actuals` path and `.fpa/` files.
- **Structural proposals are surfaced, not auto-written** — consistent with "self-extending, not self-executing": the loop proposes; skill generation happens on approval via the existing `fpa-learn-business` path.
