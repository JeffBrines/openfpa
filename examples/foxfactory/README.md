# Fox Factory (FOXF) — a real public-company worked example

This runs the full openfpa toolkit against **Fox Factory Holding Corp.**
(NASDAQ: FOXF, SEC CIK 1424929) using only **public SEC filings**. It exists to
prove the engine on real, audited, messy numbers — not synthetic demo data.

```bash
python pull_edgar.py    # (re)pull actuals from SEC EDGAR → data/*.csv + SOURCES.md
python run_foxf.py      # run all three phases → output/
```

Every figure traces to a filing via [`data/SOURCES.md`](data/SOURCES.md).

## Three phases

**Phase A — reconciliation** ([`output/reconciliation.md`](output/reconciliation.md)).
The engine is driven with Fox's *actual* reported drivers (segment net sales,
blended COGS%, working-capital days, D&A, capex) and compared to the reported
figures. It reproduces **revenue, gross profit, Adjusted EBITDA and the
working-capital cash mechanic to the dollar** for FY2024 and FY2025.

**Phase B — forecast** ([`output/forecast-briefing.md`](output/forecast-briefing.md)
+ `output/foxf-forecast.xlsx`). Segment-level (PVG / AAG / SSG → consolidated)
FY2026–FY2027, anchored to the reported Q1 FY2026 print.

**Phase C — Marucci divestiture sensitivity**
([`output/divestiture.md`](output/divestiture.md)). What selling Marucci does to
free cash flow and leverage across sale timings and proceeds.

## Where the engine strains (and how it's handled)

This is the honest part — surfaced, not hidden.

1. **No segment layer in the base engine.** Fox reports three segments and, under
   ASU 2023-07, discloses segment **Adjusted EBITDA** (not gross profit or
   operating income). The `fpa-learn-business` phase generates a bespoke
   [`segment-rollup`](skills/generated/segment-rollup/SKILL.md) skill; the engine
   gained `pyfpa.analysis.segments` to support it.
2. **The $557M FY2025 goodwill impairment** (non-cash) drove a GAAP net loss even
   as revenue recovered. The lean engine models the operating business; the
   impairment is shown as a documented bridge, not forced through the engine.
3. **Discrete tax benefits.** Fox booked tax benefits in FY2024–FY2025 that the
   engine's positive-income tax model doesn't replicate — bridged, not reconciled.
4. **Marucci is not disclosed standalone.** It sits inside SSG, so Phase C rests on
   estimates anchored to the acquisition disclosures (Fox paid $567M). It is
   presented as a **labeled sensitivity**, not as precision.
5. **Monthly engine vs quarterly reporting.** Forecast runs at annual resolution
   (anchored to Q1); intra-year quarterly phasing is a deferred extension.

## Files

| File | What |
|---|---|
| `pull_edgar.py` | Reproducible EDGAR pull → `data/*.csv` + `SOURCES.md` |
| `foxf_model.py` | Driver derivation + Phase A/B/C model assembly (importable) |
| `run_foxf.py` | Orchestration → `output/` |
| `.fpa/business-profile.md` | `fpa-learn-business` output, grounded in the filings |
| `skills/generated/segment-rollup/` | The bespoke self-extension skill |
| `data/` | Committed actuals + source trail |
| `output/` | Generated reconciliation, forecast briefing, divestiture, Excel |
