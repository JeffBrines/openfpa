---
name: fpa-cash-runway
description: Use when answering "when do we run out of cash", building a 13-week cash forecast, sizing a credit line, or analyzing near-term liquidity and payment timing in openfpa.
---

# Cash Runway (Operate)

## Overview

Build the 13-week direct-method cash forecast — the operator's near-term liquidity view. Schedule the known weekly receipts and disbursements, show the **raw** cash position (no automatic LOC draws), and report the trough and first negative week.

**Core principle:** Show the unfinanced position. A visible shortfall is the whole point — it sizes the credit line.

## When to use

- "When do we run out of money?" / runway questions
- Sizing or stress-testing a working-capital line
- Lumpy near-term cash events (inventory buys, tax, payroll cadence)

## Workflow

1. **Build the schedule** as a `Cash13Config`: `opening_cash`, `weeks` (default 13), and `receipts`/`disbursements` lists of `WeeklyFlow(name, amount, start_week, recurrence)`. Recurrence is `once`, `weekly`, or `biweekly`. Model what you actually know: AR collections on their expected weeks, payroll on its cadence, inventory POs on their due dates, quarterly tax.
2. **Forecast**:
   ```python
   import pyfpa
   from pyfpa.io.loaders import load_cash13_config
   weekly = pyfpa.cash13_forecast(load_cash13_config("examples/ridgeline/cash13.yaml"))
   runway = pyfpa.runway_summary(weekly)
   # {'min_cash': -146000.0, 'min_week': 7, 'first_negative_week': 3}
   ```
3. **Interpret** (see **fpa-cfo-judgment**): a negative `min_cash` means "needs a draw of at least this much," not "insolvent." `first_negative_week` is the deadline to act. Size the credit line to the trough plus a buffer.
4. **Report**: trough amount + week, first-negative week, and the recommended line size / action.

## Common mistakes

- Smoothing monthly numbers into weeks instead of scheduling the real lumpy items — the lumps are the signal.
- Auto-covering the shortfall with a draw and hiding the gap. Don't; show it.

## Next

Feed `runway` into **fpa-board-briefing** for the writeup.
