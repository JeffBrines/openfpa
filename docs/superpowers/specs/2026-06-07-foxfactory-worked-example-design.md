# Fox Factory Worked Example — Design

**Status:** Approved (design phase)
**Date:** 2026-06-07
**Author:** openfpa
**Topic:** A real public-company worked example that reconciles the `pyfpa` engine
against audited actuals, then forecasts forward at the segment level via the
skillset.

## Why

Ridgeline Chair Co. (the existing demo) is synthetic. It proves the pipeline runs
but not that the engine's accounting is correct against reality or that the
self-extending skillset survives a genuinely messy business. **Fox Factory
Holding Corp. (NASDAQ: FOXF)** is the opposite: public, audited, segment-reported,
mid-acquisition, and cyclical. Running openfpa against it is a credibility flex —
the audience includes a sophisticated FP&A reader (potentially Fox's own CFO), so
the bar is **source-auditable and honest about limitations**, not impressive-looking.

## Decisions (locked)

| Decision | Choice |
| --- | --- |
| Proof structure | Two phases: (A) reconcile engine vs actuals, then (B) forecast forward |
| Granularity | Segment-level P&L (PVG / AAG / SSG), consolidated working capital + debt + tax |
| Home | Public repo worked-example: `examples/foxfactory/` |
| Data source | SEC EDGAR (CIK 1424929), pulled via curl with a compliant User-Agent |
| Forecast horizon | FY2026 + FY2027 |
| FY2026 anchor | Anchor to Q1 FY2026 reported actuals (Q1 actual + remaining quarters forecast) |
| Cash tool | Indirect (annual) cash flow. **`cash13` deliberately not used** — wrong tool for a $1.5B audited public company |

## Background facts (from EDGAR, to be re-verified by the pull script)

- **CIK:** 1424929. Fiscal year ends late Dec / early Jan (52/53-week).
- **Three reportable segments:**
  - **PVG** — Powered Vehicles Group: off-road / powersports OEM + aftermarket shocks.
  - **AAG** — Aftermarket and Automotive Group: custom vehicle suspension, lift kits,
    upfitting, wheels & tires.
  - **SSG** — Specialty Sports Group: performance mountain/e-bike/gravel components,
    plus premium baseball/softball equipment (**Marucci**, acquired Nov 2023).
- **Revenue arc (consolidated net sales, EDGAR-confirmed):** FY2021 $1,299M →
  FY2022 $1,602M (peak) → FY2023 $1,464M → FY2024 $1,394M (trough) →
  FY2025 $1,467M (recovery). Narrative: powersports + bike destocking through 2024,
  Marucci full-year contribution aiding 2025.
- **Marucci** was debt-funded → material term-loan + revolver balance and interest
  expense; deleveraging path matters to the forecast.

## Architecture

Real-CFO model shape. Segment data only exists down to the P&L (Fox discloses
segment net sales and segment income); working capital, debt, interest, and tax are
**consolidated-only** disclosures. The model mirrors that exactly:

```
segment P&L (PVG, AAG, SSG)  →  roll up  →  consolidated P&L
                                              ↓
        consolidated working capital (DSO/DPO/DIO) + debt + tax
                                              ↓
                       indirect cash flow + ending balances
```

### Directory layout — `examples/foxfactory/`

| Path | Purpose |
| --- | --- |
| `pull_edgar.py` | Reproducible EDGAR pull (curl + User-Agent). Writes raw figures with source accession + URL stamped on each. Re-runnable; no live API client beyond this. |
| `data/income_statement.csv` | Consolidated IS, FY2023–FY2025 + Q1 FY2026. |
| `data/balance_sheet.csv` | Consolidated BS, FY2023–FY2025. |
| `data/cash_flow.csv` | Consolidated CF, FY2023–FY2025. |
| `data/segments.csv` | Segment net sales + segment income, FY2023–FY2025 + Q1 FY2026. |
| `data/SOURCES.md` | Accession numbers + URLs for every filing used (audit trail). |
| `.fpa/business-profile.md` | Output of `fpa-learn-business`, grounded in the 10-K. |
| `skills/generated/segment-rollup/SKILL.md` | Bespoke skill spawned by the headliner to roll segment P&Ls into the consolidated model. The hero artifact. |
| `config/pvg.yaml`, `aag.yaml`, `ssg.yaml` | Per-segment P&L drivers. |
| `config/consolidated.yaml` | Working-capital days, debt instruments, tax rate, opening balances. |
| `run_foxf.py` | Full pipeline → reconciliation report + forecast briefing + Excel. |

### Engine support (new code in `pyfpa/`)

The segment roll-up is a genuine capability gap, so it lands as a small, tested
module in the public engine (not just example glue), surfaced as the worked example
of self-extension:

- `pyfpa/analysis/segments.py` — `Segment`, `roll_up_segments(...)` → consolidated
  P&L from a list of segment P&Ls. Pure, immutable, typed.
- `pyfpa/io/` loader for the `data/*.csv` actuals → engine inputs.
- Reconciliation helper: `reconcile(model, actual, tolerance)` → variance rows.

## Phase A — Reconciliation (engine math)

Configure the engine with Fox's **actual** FY2023–FY2025 drivers (segment revenue,
segment COGS%/gross profit, consolidated opex, working-capital days implied by the
filed balance sheets, actual debt + rate, actual effective tax). Run the engine and
confirm it reproduces the **reported** figures within tolerance:

- Gross profit, operating income, net income (P&L mechanics).
- Change in working capital and ending cash (indirect cash flow mechanics).

**Output:** a variance table (model vs filed, per line, per year) with residuals
explained. Tolerance target: within ~1% on major lines; any larger residual gets a
written reason (e.g., one-time impairment, stock comp, discrete tax item the lean
engine doesn't model). Being explicit about residuals is the point.

## Phase B — Forecast (skillset)

Segment-level FY2026 + FY2027. FY2026 anchored to Q1 FY2026 actuals (Q1 reported +
Q2–Q4 forecast). Explicit, defensible assumptions:

- Per-segment revenue growth + gross-margin path (organic, with Marucci normalized).
- Consolidated DSO / DPO / DIO (carry recent actuals, note any normalization).
- Term-loan amortization + revolver; effective tax rate.

**Output:** board briefing (`docs/demo/foxf-briefing.md`-style via `to_briefing_md`)
+ `forecast.xlsx`.

## "Where the engine strains" (documented in the deliverable)

Honest limitations, surfaced not hidden:

1. **No segment layer** in the base engine → solved by the generated `segment-rollup`
   skill + `pyfpa/analysis/segments.py`.
2. **No M&A modeling** → Marucci's Nov-2023 stub distorts FY23→FY24 SSG YoY; we
   separate organic vs acquired growth and state it.
3. **Monthly engine vs quarterly reporting** → we run annual forecast years;
   intra-year quarterly phasing is a noted deferral (FY2026 still anchored to the Q1
   print, but Q2–Q4 are modeled in aggregate, not individually seasonalized).
4. **Segment working capital / debt undisclosed** → consolidated-only by design,
   matching real practice.

## Scope boundaries (YAGNI)

- No valuation / DCF (outside openfpa's remit).
- No intra-year quarterly seasonality model.
- No live streaming API client — one re-runnable pull script is enough.
- No per-segment balance sheet (not disclosed by Fox).
- No restatement of pre-2023 segment history (segment structure differs).

## Success criteria

1. `pull_edgar.py` re-pulls every figure from EDGAR and `data/SOURCES.md` lets a
   reader trace any number to a filing.
2. Phase A: reconciliation table shows the engine reproduces reported P&L + cash
   mechanics within tolerance, residuals explained.
3. Phase B: a coherent segment-level FY2026–FY2027 forecast with explicit
   assumptions, anchored to Q1 FY2026.
4. The generated `segment-rollup` skill is real and cites profile facts (proves
   self-extension on a hard case).
5. `pyfpa/analysis/segments.py` is unit-tested (repo's 80% norm); full suite green.
6. A reader-grade briefing + Excel a CFO would respect — and an honest limitations
   section.

## Testing

- Unit tests for `roll_up_segments`, the actuals loader, and `reconcile`.
- A reconciliation assertion test: engine output vs committed FY2024 actuals within
  tolerance (acts as a regression guard on the engine's accounting).
- Existing suite stays green.
