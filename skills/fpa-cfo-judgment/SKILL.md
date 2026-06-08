---
name: fpa-cfo-judgment
description: Use when interpreting financial actuals, reviewing margins or cash, drawing conclusions from a P&L or balance sheet, or about to tell someone a number means something — the judgment layer that separates "AI that does math" from "AI that thinks like a CFO."
---

# CFO Judgment

## Overview

A forecast that's arithmetically correct can still be wrong about reality. This is the judgment layer: the gotchas a seasoned CFO checks reflexively before trusting a number. Consult it during **any** analysis — close, briefing, runway, scenario.

**Core principle:** Numbers lie by omission. Before reporting a figure, ask what's *not* in it yet.

## The reflexes

| Trap | What a CFO checks |
|------|-------------------|
| **Pre-close months look great** | COGS and accruals post late. A high gross margin in a not-yet-closed month is usually unposted cost, not real profit. Exclude pre-close months from conclusions, or flag them loudly. |
| **A suspiciously profitable month** | Same root cause — almost always a timing/posting artifact. Reconcile before celebrating. |
| **Data seams** | When two ingestion sources or periods meet (e.g. actuals → forecast handoff), look for double-counts and gaps at the boundary. |
| **Flash cash vs GL cash** | The bank balance and the GL cash rarely tie out intraday (in-flight deposits, uncleared checks). Know which one you're quoting. |
| **Intercompany not eliminated** | Multi-entity totals double-count unless IC revenue/expense is eliminated. A "profitable" entity may just be billing its sibling. |
| **Working-capital seam** | openfpa assumes opening AR/AP/inventory sit at the modeled steady state. If real opening balances differ, the whole gap dumps into month 1 as a one-time cash swing — investigate before reporting it as operating performance. |
| **D&A is a real expense** | The engine models D&A: `ebitda` is true EBITDA, EBIT = EBITDA − D&A (set `da_monthly`), and D&A is added back in operating cash flow — never let an add-back inflate cash without first expensing it in the P&L. |
| **Impairments are non-cash** | A goodwill/asset impairment craters GAAP operating income but doesn't touch cash. Bridge it explicitly (model the operating business, show the impairment separately) — don't force a one-time write-down through an operating model. |
| **Cash is raw** | The 13-week forecast shows the unfinanced position — a negative trough means "needs a draw," not "is insolvent." Say which. |
| **Known one-offs are flagged** | Read `.fpa/corrections/` for `type: context` notes (e.g. "Q3 was a one-time contract"); exclude them before attributing a forecast miss or quoting run-rate. |

## How to apply

1. Before stating a conclusion, run the relevant rows above against the number.
2. If a figure depends on a not-yet-closed month or an un-eliminated total, **lead with the caveat**, don't bury it.
3. When a result looks too good, assume a timing artifact until proven otherwise.

## Red flags — stop and reconcile

- "Margin jumped this month" (is the month closed?)
- "We're profitable" (intercompany eliminated? D&A included?)
- "We have $X in cash" (bank flash or GL? unfinanced or post-draw?)
- A month-1 cash swing far larger than operating activity (working-capital seam)
