---
name: fpa-capture-correction
description: Use when a human reviewing a forecast catches something off ("December always spikes", "you're double-counting deferred revenue", "that Q3 number was a one-time contract") — captures it as a durable, typed correction in the company's memory so future forecasts are grounded by it.
---

# Capture a Correction (Operate)

## Overview

A human reviewing a forecast is the highest-signal feedback there is — they catch
structural errors and domain knowledge the backtest can't see, and catch them *now*.
This skill turns that into durable memory: a typed correction in `.fpa/corrections/`
that grounds every future forecast.

**Core principle:** the human is the authority; capture, confirm interpretation once,
then it persists. Everything is plain markdown the user owns.

## The three correction types

- **parametric** — a concrete driver fix ("December runs ~2× a normal month"). Becomes
  an `override` (a config path + value) applied to every future forecast via
  `pyfpa.apply_corrections`.
- **structural** — a methodology fix ("you're double-counting deferred revenue"). A
  *pre-ratified* structural proposal (the human authored it) — route it to
  **fpa-learn-business** to generate the skill/model change; do NOT wait for backtest misses.
- **context** — a one-time-item note ("that Q3 spike was a one-off contract"). Annotates so
  **fpa-cfo-judgment**'s one-time screen keeps the backtest from "learning" a one-off.

## Workflow

1. **Classify** the correction (parametric / structural / context).
2. **Identify the target** — the driver path (e.g. `channels[*].seasonality[11]`,
   `working_capital.dio_days`), line, or profile area. For parametric, draft the concrete
   `override: {path, value}`.
3. **Write** the correction file `.fpa/corrections/<date>-<slug>.md`
   (`pyfpa.save_correction`) with frontmatter (`type`, `target`, `status`, `date`,
   `override`) and a markdown body (`**Was off:** … **Correction:** … **Why:** [[…]]`).
   Link the body to the assumption/profile it corrects with `[[wikilinks]]`.
4. **Confirm interpretation.** Echo back the concrete change ("I'll set December
   seasonality to 2.0 on all channels — right?"). Only on confirmation set
   `status: applied`.
5. **Keep `.fpa/MEMORY.md` current** — the vault index (see below).

## Applying corrections

When building any forecast, `pyfpa.apply_corrections(cfg, load_corrections(".fpa/corrections"))`
folds the applied parametric corrections into the config. The per-client loop refines from
there — corrections are *seeds*, not mandates.

## The `.fpa/` vault (`MEMORY.md` index)

Keep a `.fpa/MEMORY.md` that orients a human, Obsidian, or Claude:
- `business-profile.md` — what we know about the business.
- `corrections/` — human corrections (this skill).
- `forecasts/*.snapshot.yaml`, `scorecard.md` — forecast snapshots + backtest track record.
- `learnings.md` — accepted model changes.
All plain markdown — open it in Obsidian if you like, but never required.

## Guardrails

- Confirm interpretation before `applied`. Reversible via `status` (`open`/`applied`/`superseded`).
- The backtest *monitors* applied corrections and may flag a stale one — it never reverts;
  the human decides.

## Next

Correction captured → **fpa-monthly-close** / **fpa-board-briefing** (re-run grounded by it).
