---
name: fpa-monthly-close
description: Use when running a month-end close, refreshing a forecast with the latest actuals, computing plan-vs-actual variance, or producing a "how did the month go" analysis in openfpa.
---

# Monthly Close (Operate)

## Overview

Fold the latest actuals into the model, refresh the forward forecast from the last closed position, and explain the variance. The output is a *narrative*, not just a variance table — what changed, why, and what it means forward.

**Core principle:** A close that only reports numbers isn't done. The value is the explanation.

## When to use

- Month-end actuals are available
- "How did we do vs plan?" / reforecast requests

## Workflow

1. **Ingest the closed month's actuals** (see **fpa-configure-actuals**).
2. **Establish the freeze line**: closed months use actuals; the forecast resumes from the last closed balance. Never let a not-yet-closed month drive conclusions (see **fpa-cfo-judgment**).
3. **Recompute the forecast**: `pyfpa.cashflow_from_config(cfg)` after updating config with the new closed position.
4. **Variance**: compare actual vs plan for revenue, gross margin, EBITDA, and ending cash. For each material variance, state the *driver* (volume, price, cost ratio, timing).
5. **Pick a reforecast posture** and say which you used:
   - **Plan** — frozen forecast unchanged
   - **Latest estimate** — actuals for closed months, plan forward from the last closed balance
   - **Run-rate** — project the YTD actual pace forward
6. **Write the narrative**: the 3 things that moved, the 3 risks forward.

## Judgment checks (always)

- Is the "closed" month actually closed, or are accruals/COGS still posting?
- Did any account move because of a one-time/timing item? Separate it from run-rate.
- Multi-entity: is intercompany eliminated before you total?

## Next

Close done → **fpa-cash-runway** (near-term liquidity) and **fpa-board-briefing** (the writeup) and **fpa-backtest-learn** (score this close against the prior forecast and learn from the miss).
