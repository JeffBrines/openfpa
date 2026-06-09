---
name: segment-rollup
description: Use when modeling a multi-segment company that discloses segment net sales and segment Adjusted EBITDA (ASU 2023-07) but not segment COGS or operating income - rolls segment P&Ls into a consolidated forecast and reconciles total segment Adjusted EBITDA to the disclosed total. Generated for Fox Factory (PVG/AAG/SSG).
---

# Segment Roll-Up (generated for Fox Factory)

## Why this skill exists

The standard openfpa skills model a single entity. Fox Factory reports **three
segments** (PVG, AAG, SSG) and, under ASU 2023-07, discloses **net sales and
Adjusted EBITDA per segment - but not segment COGS or operating income**
(`.fpa/business-profile.md`). The base engine has no segment concept, so this
skill was generated to bridge the gap. It cites these profile facts:

- Three reportable segments; segment metric is **Adjusted EBITDA**, not gross profit.
- Segment-level working capital, debt, and tax are **not disclosed** - those stay
  consolidated. So segments drive the P&L down to Adjusted EBITDA only; the
  consolidated layer owns everything below.

## The model shape

```
segment net sales + Adj EBITDA margin  (PVG, AAG, SSG)
        │  roll_up_segments()            → total net sales + total Adj EBITDA
        │  segments_to_channels(cogs_pct)→ revenue channels for the engine
        ▼
consolidated EntityConfig (blended COGS%, opex, D&A, capex, WC days, debt, tax)
        │  cashflow_from_config()
        ▼
consolidated P&L + indirect cash flow (revenue → … → FCF)
```

## How to use

1. Build one `pyfpa.Segment` per segment from disclosed **net sales** and
   **Adjusted-EBITDA margin** (`adjusted_ebitda / net_sales`).
2. `roll_up_segments(segments)` → total net sales + total Adjusted EBITDA.
   **Reconcile that total to the disclosed segment-footnote total** - it must tie.
3. `segments_to_channels(segments, cogs_pct=<consolidated blended rate>)` → revenue
   channels. The blended COGS% is applied to every segment (segment COGS isn't
   disclosed), so the channels sum back to consolidated COGS by construction.
4. Feed the channels into a consolidated `EntityConfig` and run
   `cashflow_from_config`. Set the single `adjusted_opex` line to
   `gross_profit − total_adjusted_ebitda` so engine EBITDA ties to segment Adj EBITDA.
5. Keep the goodwill impairment and discrete tax items **out** of the engine and
   in a documented bridge to GAAP net income - the lean engine models the
   operating business, not one-time non-cash charges.

## Reference implementation

`examples/foxfactory/foxf_model.py` (`reconciliation_config`, `phase_a_model`,
`forecast_year`) and `pyfpa.analysis.segments`.

## Guardrail

This skill lives in the **client's** `skills/generated/` namespace - it is specific
to a three-segment, Adjusted-EBITDA-reporting company and must never be promoted
into the public openfpa template.
