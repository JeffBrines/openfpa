# Fox Factory (FOXF) - a real public-company worked example

This runs the full openfpa toolkit against **Fox Factory Holding Corp.**
(NASDAQ: FOXF, SEC CIK 1424929) using only **public SEC filings**. It exists to
show the agent-native workflow on real, audited, messy numbers - not synthetic
demo data. The example separates accounting reproduction from independent
historical validation instead of presenting them as the same thing.

```bash
python3 pull_edgar.py   # (re)pull actuals from SEC EDGAR → data/*.csv + SOURCES.md
python3 run_foxf.py     # run all four phases → output/ + .fpa research memory
```

Every figure traces to a filing via [`data/SOURCES.md`](data/SOURCES.md).

## Four phases

**Phase A - actual-driver reproduction**
([`output/reconciliation.md`](output/reconciliation.md)).
The engine is driven with Fox's *actual* reported drivers (segment net sales,
blended COGS%, working-capital days, D&A, capex) and compared to the reported
figures. This verifies the accounting mechanics reproduce known outcomes. It is
not called a forecast proof because the target-year drivers are inputs.

**Phase B - historical holdout research**
([`output/historical-holdout.md`](output/historical-holdout.md)). The model uses
FY2023-FY2024 only and holds FY2025 out. An AutoResearch-style loop rejects a
broad mean-reversion challenger, refines the hypothesis, and proposes a
revenue-recovery / slow-margin-recovery challenger that improves every weighted
holdout metric. The challenger is recorded in `.fpa/research/` and remains
unpromoted pending human approval.

**Phase C - forecast** ([`output/forecast-briefing.md`](output/forecast-briefing.md)
+ `output/foxf-forecast.xlsx`). Segment-level (PVG / AAG / SSG → consolidated)
FY2026–FY2027, anchored to the reported Q1 FY2026 print.

**Phase D - Marucci divestiture sensitivity**
([`output/divestiture.md`](output/divestiture.md)). What selling Marucci does to
free cash flow and leverage across sale timings and proceeds.

## Where the engine strains (and how it's handled)

This is the honest part - surfaced, not hidden.

1. **No segment layer in the base engine.** Fox reports three segments and, under
   ASU 2023-07, discloses segment **Adjusted EBITDA** (not gross profit or
   operating income). The `fpa-learn-business` phase generates a bespoke
   [`segment-rollup`](skills/generated/segment-rollup/SKILL.md) skill; the engine
   gained `pyfpa.analysis.segments` to support it.
2. **The $557M FY2025 goodwill impairment** (non-cash) drove a GAAP net loss even
   as revenue recovered. The lean engine models the operating business; the
   impairment is shown as a documented bridge, not forced through the engine.
3. **Discrete tax benefits.** Fox booked tax benefits in FY2024–FY2025 that the
   engine's positive-income tax model doesn't replicate - bridged, not reconciled.
4. **Marucci is not disclosed standalone.** It sits inside SSG, so Phase D rests on
   estimates anchored to the acquisition disclosures (Fox paid $567M). It is
   presented as a **labeled sensitivity**, not as precision.
5. **Monthly engine vs quarterly reporting.** Forecast runs at annual resolution
   (anchored to Q1); intra-year quarterly phasing is a deferred extension.
6. **Limited holdout history.** Three annual observations are enough to
   demonstrate champion/challenger discipline, but not to claim statistical
   certainty. A real company workspace should use monthly or quarterly history.

## Files

| File | What |
|---|---|
| `pull_edgar.py` | Reproducible EDGAR pull → `data/*.csv` + `SOURCES.md` |
| `foxf_model.py` | Reproduction, holdout research, forecast, and sensitivity assembly |
| `run_foxf.py` | Orchestration → `output/` |
| `.fpa/business-profile.md` | `fpa-learn-business` output, grounded in the filings |
| `.fpa/intake.md` | Evidence-seeded company intake used by the agent toolbelt |
| `.fpa/decisions/initial-model-architecture.md` | Approved demo architecture |
| `.fpa/research/` | Objective + rejected/proposed historical holdout epochs |
| `.fpa/models/registry.yaml` | Flat champion + unpromoted recovery challenger |
| `.fpa/models/entrypoints.yaml` | Registered command for the complete Fox pipeline |
| `.fpa/sources/registry.yaml` | SEC extract provenance, entities, currencies, and period coverage |
| `.fpa/mappings/registry.yaml` | Explicit source-field to normalized-model mappings |
| `skills/generated/segment-rollup/` | The bespoke self-extension skill |
| `data/` | Committed actuals + source trail |
| `output/` | Generated reproduction, holdout, forecast, sensitivity, and Excel artifacts |
