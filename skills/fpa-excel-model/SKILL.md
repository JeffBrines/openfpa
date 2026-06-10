---
name: fpa-excel-model
description: Use when the user wants their model in Excel with real working formulas - "export this to Excel", "a workbook I can hand my board", "something that recalculates when I change an assumption". Produces a live-formula workbook generated from the model structure and verified against the engine before delivery.
---

# Live-Formula Excel Model (Operate)

## Overview

Finance professionals ultimately want a workbook where changing an assumption
recalculates the model. This skill produces one from the model structure, with
named assumption cells and real formulas, then proves it reproduces the engine
before it ships. Static value dumps stay with `forecast_to_excel`; this skill
is for living models.

**Core principle:** no workbook ships unverified. The workbook is generated
from the model, never hand-edited values.

## The standard model

For the kernel's monthly model, one call:

```python
import pyfpa
cfg = pyfpa.load_config("config.yaml")
pyfpa.model_to_excel(cfg, "model.xlsx")
```

Or via CLI: `python3 -m pyfpa.cli model-export <company-root> --config config.yaml --out model.xlsx`.

The workbook has an Assumptions sheet (every driver a named, editable cell:
growth, COGS pct, seasonality, DSO/DIO/DPO, debt, tax, D&A, capex) and a Model
sheet where every line of the monthly P&L and cash flow is a formula
referencing those names.

## Any other cadence or layout

Quarterly, weekly, a tab per segment, a lender view: these are YOUR work, not
kernel variants. Compose `pyfpa.excel.toolkit` (`add_named_cell`,
`add_named_row`, `fill_formula_row`, formats) in a company-specific exporter
under the generated namespace (`models/generated/<name>/`), then register it:
`python3 -m pyfpa.cli entrypoint-register <root> --name excel-quarterly --kind report ...`.
Keep formulas within the supported vocabulary (arithmetic, `^`, `SUM`, `MIN`,
`MAX`, `IF`) so verification works.

## Verify before delivering (always)

1. `pip install formulas` (verification-only dependency, not shipped at runtime).
2. ```python
   report = pyfpa.verify_workbook("model.xlsx", pyfpa.cashflow_from_config(cfg))
   assert report.passed, report.failures
   ```
3. For a bespoke exporter, verify against the frame your exporter is meant to
   reproduce (the engine frame, or its quarterly/weekly aggregation).
4. A failing report means the exporter is wrong. Fix the formulas, never the
   tolerance, and never deliver an unverified workbook.

## Guardrails

- No workbook ships unverified.
- Generated from model structure; never paste computed values into formula cells.
- Supported formula vocabulary only; if you need a function outside it, restructure
  the formula (helper rows are fine) rather than expanding the vocabulary.
- Company-specific exporters live in generated namespaces and get tests like any
  other generated code.

## Next

Workbook delivered, then **fpa-board-briefing** (the narrative that goes with it).
