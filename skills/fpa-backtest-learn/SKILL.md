---
name: fpa-backtest-learn
description: Use when you want the model to learn from how its past forecasts actually turned out - scoring forecasts against the company's real actuals, backtesting assumptions on history, and proposing ratified improvements. Runs at/after monthly close.
---

# Backtest & Learn (Operate)

## Overview

The model should get measurably better at this business over time. This skill
scores past forecasts against the company's actuals, surfaces what keeps missing,
and proposes improvements a human ratifies. The objective metric is reconciliation
error against the user's own books (`pyfpa.score_forecast`) - the FP&A analog of a
validation loss.

**Core principle:** self-experimenting, but never self-promoting. The AI may run
and discard bounded challengers autonomously; a human approves replacement of
the champion. Everything learned lives as plain files in `.fpa/`.

## Memory (`.fpa/`)

- `forecasts/<period>.snapshot.yaml` - each forecast's assumptions + predictions, and (after close) its score.
- `scorecard.md` - the running track record (rendered, never hand-edited).
- `experiments/<slug>.experiment.yaml` - each tested model change, its evidence,
  changed files, checks, before/after metrics, and decision.
- `learnings.md` - every accepted change: what, the evidence, the backtest delta, the date.

## Workflow

1. **Snapshot every forecast.** When you produce a forecast, persist it:
   `snapshot_forecast(cfg, forecast_df, label=<period>, created=<today>)` →
   `save_snapshot(..., ".fpa/forecasts/<period>.snapshot.yaml")`.
2. **Score at close.** When a period closes (actuals via **fpa-configure-actuals**),
   load that period's snapshot, `score_forecast(snap.predicted, actuals)`, write the
   score back into the snapshot, and re-render `scorecard.md` with `render_scorecard`.
3. **Attribute** each material per-line miss to a driver (volume / price / cost ratio
   / working-capital timing). **Run the fpa-cfo-judgment one-time-item screen first** -
   never blame the model for a one-off.
   - **Monitor applied corrections:** if a `type: parametric` correction's target line keeps missing, flag it as possibly stale (`applied → superseded`) for the human - never auto-revert.
4. **Create an experiment** before changing the model. State the financial
   hypothesis, CFO question, evidence, fit periods, holdout periods, and files
   expected to change. Save it with `pyfpa.save_experiment`.
5. **Propose**, tagged by type:
   - **Parametric** (an assumption change): re-score it with `holdout_backtest` on the
     company's history. Surface it **only if it lowers holdout fitness** (not in-sample),
     ranked by the delta. Clamp the proposed move with `magnitude_cap` (±25%/cycle).
   - **Structural** (a methodology/skill change, e.g. a revenue-recognition lag): surface
     **only** when `persistent_miss` is true for the line (same-signed across K≥2 closes)
     and it survived the one-time screen. Hand it to **fpa-learn-business** to generate the
     skill *on approval* - propose, don't auto-write.
6. **Evaluate.** Record before/after metrics and explicit checks in the experiment.
   A model change that breaks reconciliation or another accounting invariant is
   failed even if one headline metric improves.
7. **Ratify + log.** Present proposals; the human accepts/rejects. On accept, add
   an `ExperimentDecision`, set `status: accepted`, save with explicit
   `overwrite=True`, update the company model, and append to `learnings.md`.
   Rejected and reverted experiments remain in memory.
8. **Run `fpa-research-loop`** when the miss warrants multiple autonomous
   challenger epochs instead of one manually proposed change.

## Bootstrap (day one)

If the company already has ~12+ months of actuals, you don't have to wait: run
`holdout_backtest` immediately (fit on the earlier months, hold out the recent ones)
to report current accuracy and the first round of parametric proposals.

## Guardrails (always)

- Never score on data the model was fit on (`holdout_backtest` enforces this).
- No proposal off a single period - require a persistent, same-signed miss.
- A parametric change must improve **holdout** fitness, not in-sample fit.
- Cap how far any assumption moves per cycle (`magnitude_cap`).
- Human ratifies champion promotion; autonomous failed epochs are logged and reversible.
- Missing or zero actuals are insufficient evidence, not perfect forecast performance.

## Next

Scored + learned → **fpa-board-briefing** (report the forecast and how it's tracking).
