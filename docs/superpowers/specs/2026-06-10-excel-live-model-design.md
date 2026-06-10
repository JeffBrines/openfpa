# Live-Formula Excel Export: Design

**Status:** Approved (design phase)
**Date:** 2026-06-10
**Topic:** Make "export my model to Excel with real working formulas" a native
toolbelt capability: a tested formula toolkit, one canonical monthly translator,
and a verification harness that proves any generated workbook reproduces the
engine. Cadence and layout stay agent territory.

## Why

Every finance professional ultimately wants the same artifact: a workbook where
changing an assumption recalculates the model. Today `forecast_to_excel` dumps
static values. A bare agent asked for "Excel with formulas" would improvise an
unverified workbook with whatever library it guessed at. The toolbelt should
hand the agent the writer, the building blocks, and a proof loop, so the
workbook that reaches a CFO is generated from the model structure and verified
against the engine, not pasted values or vibes.

Key architectural fact: live formulas cannot be derived from a DataFrame
(values carry no formula semantics). They must be compiled from the model
structure, which only the kernel knows. This is therefore a second compile
target for `EntityConfig`, and it belongs in the kernel.

## Decisions (locked)

| Decision | Choice |
| --- | --- |
| Writer library | **openpyxl** (already a runtime dependency; formulas as strings, named ranges, number formats; pure Python, CI-safe). |
| Evaluator library | **formulas** (PyPI name `formulas`), used ONLY for verification. Dev extra, not a runtime dependency. `xlcalculator` noted as fallback if `formulas` is ever abandoned. |
| Rejected | xlwings (requires a running Excel app; breaks CI and self-hosted ethos). XlsxWriter (second writer dependency, no new capability). |
| Kernel scope | Toolkit + ONE canonical translator (the standard monthly engine model) + verification harness. |
| Cadence | **Not a kernel concern.** Quarterly, weekly, per-segment, lender views: the agent generates company-specific exporters from the toolkit, registers them as entrypoints, and verifies them with the same harness. The user changes cadence by asking the AI. |
| Formula vocabulary | Restricted by design to arithmetic, `^`, `SUM`, `MIN`, `MAX`, `IF`. Everything the engine model needs, and everything the `formulas` evaluator handles reliably. |
| Verification bar | A workbook reproduces `cashflow_from_config` line by line, month by month, within 1e-6 relative. Enforced in CI on the Ridgeline config. |

## Components: `pyfpa/excel/` (new package, small files)

`pyfpa/excel/toolkit.py` (the composable pieces)
- `add_named_cell(ws, name, value, *, workbook)` and
  `add_named_row(ws, name, values, ...)`: write an assumption cell or row and
  register a workbook-scoped defined name for it.
- `formula_row(ws, row_label, template, n_cols, ...)`: fill a model row with a
  formula template referencing named assumptions and relative prior-column
  cells (e.g. running balances).
- Number-format helpers (money, percent, days) and a frozen-pane/header helper.
- Pure openpyxl; no engine imports. This is what generated exporters compose.

`pyfpa/excel/model_workbook.py` (the canonical translator)
- `model_to_excel(cfg: EntityConfig, path) -> None`: compile the standard
  monthly model to a two-sheet workbook.
  - **Assumptions sheet**: named cells/rows for every `EntityConfig` driver:
    per-channel annual revenue, growth rate, COGS pct, 12 seasonality weights;
    opex lines (kind, amount, pct); `dso_days`/`dio_days`/`dpo_days`;
    debt instruments (opening balance, annual rate, monthly principal);
    `tax_rate`, opening balances incl. NOL; `da_monthly`, `capex_monthly`.
  - **Model sheet**: months across columns (1..horizon), the full
    `cashflow_from_config` line stack down rows, every cell a formula:
    per-channel revenue (annual x normalized seasonality x growth^year),
    COGS, opex lines, EBITDA, D&A, term-loan/LOC balance rows with interest,
    NOL opening/used/closing rows feeding tax, net income, AR/AP/inventory
    balance and delta rows, wc cash impact, OCF, capex, FCF, principal,
    change in cash, ending cash (cumulative).
  - First-month edge cases (deltas vs opening balances) handled explicitly.

`pyfpa/excel/verify.py` (the proof loop)
- `verify_workbook(path, expected: pd.DataFrame, *, rel_tol=1e-6) -> VerifyReport`:
  evaluate the workbook with the `formulas` library, extract the model-sheet
  lines, compare to the expected frame per line per month. `VerifyReport` is a
  pydantic model (per-line max deviation, pass/fail, any unevaluated cells).
- Imports `formulas` lazily with a clear error naming the install command
  (`pip install formulas`) so the runtime package never requires it.

`pyfpa/excel/__init__.py` re-exports; `pyfpa/__init__.py` exposes
`model_to_excel` and `verify_workbook`.

## Surfaces

- **Public API:** `pyfpa.model_to_excel`, `pyfpa.verify_workbook`.
- **CLI:** `model-export <company-root> --config <yaml> --out <xlsx>` as a thin
  handler in the existing `cli_commands/` style (JSON output, module-form
  hints). Verification stays a Python/test concern, not a CLI command, in v1.
- **Contract (`AGENTS.md` + `CLAUDE.md`):** a short section: when the user
  wants live-formula Excel, use `model_to_excel` for the standard monthly
  model; for any other cadence or layout, generate a company-specific exporter
  in the generated namespace using `pyfpa.excel.toolkit`, register it with
  `entrypoint-register` (kind `report`), install `formulas`, and run
  `verify_workbook` before delivering. No workbook ships unverified.
- **Skill (new): `skills/fpa-excel-model/SKILL.md`.** Triggers on the way users
  actually ask ("export this to Excel", "a workbook with working formulas",
  "something I can hand my board that recalculates"). Encodes the workflow:
  use `model_to_excel` for the standard monthly model; for any other cadence
  or layout, generate a company-specific exporter in the generated namespace
  composing `pyfpa.excel.toolkit`, register it with `entrypoint-register`
  (kind `report`); always `pip install formulas` and run `verify_workbook`
  before delivering. Guardrails: no workbook ships unverified; formulas stay
  within the supported vocabulary; the workbook is generated from the model
  structure, never hand-edited values. `fpa-board-briefing` and
  `fpa-scaffold-model` get one-line pointers to it.
- **Ridgeline example:** `run_demo.py` also emits `model.xlsx` so a downloader
  opens a working formula model two commands after cloning.

## How it ties into the repo flow

1. User downloads the repo, opens it with Claude Code or Codex.
2. The contract and skills tell the agent the capability exists and how to
   prove its output.
3. "Give me this in Excel I can hand my board": agent calls `model_to_excel`.
4. "Make it quarterly with a tab per segment": agent writes
   `models/generated/<company>/excel_quarterly.py` composing
   `pyfpa.excel.toolkit`, registers the entrypoint, installs `formulas`, runs
   `verify_workbook` against the engine frame, and only then delivers.
5. CI keeps the canonical translator honest forever via the Ridgeline
   equivalence test.

## Error handling

- `model_to_excel` raises a clear `ValueError` for configs it cannot express
  (none expected for the current schema; the guard exists for future fields,
  naming the unsupported field).
- `verify_workbook` raises a clear `RuntimeError` if `formulas` is missing,
  with the install command in the message.
- Unevaluated cells or NaNs in verification are failures, never skipped.

## Success criteria

1. `model_to_excel(load_config("examples/ridgeline/config.yaml"), path)`
   produces a workbook that opens in Excel/LibreOffice with editable named
   assumptions, and changing an assumption recalculates the model.
2. CI proves the Ridgeline workbook reproduces `cashflow_from_config` line by
   line, month by month, within 1e-6 relative, via `verify_workbook`.
3. An edge config exercising NOL consumption, a term loan plus LOC, and
   multi-channel seasonality also verifies.
4. The toolkit is importable and documented well enough that a generated
   exporter composes it without copying kernel internals.
5. Runtime dependencies unchanged (openpyxl only); `formulas` confined to the
   dev extra.
6. The `fpa-excel-model` skill exists, triggers on Excel-shaped requests, and
   every `pyfpa.*` call it references resolves (the phantom-call audit bar).
7. Contract, skills, README updated; no em dashes; suite green.

## Testing

- Structure tests: defined names exist; model-sheet cells contain formulas
  (strings starting with `=`), not values; frozen panes and number formats set.
- Equivalence tests (require `formulas`, included in dev extras so CI runs
  them): Ridgeline config and the NOL/debt/seasonality edge config.
- Toolkit unit tests: named cell/row registration, formula_row templating,
  first-column vs subsequent-column references.
- `verify_workbook` failure path: a deliberately corrupted formula produces a
  failing `VerifyReport`, and the missing-`formulas` error message names the
  install command (tested with an import shim).
- CLI test for `model-export` in the established CLI test style.

## Scope boundaries (YAGNI)

- No 13-week cash sheet in the kernel translator (the agent can generate one;
  the weekly schedule expands fine through the toolkit).
- No charts, no VBA or macros, no xlwings, no template-file system.
- No styling pass beyond number formats, bold headers, frozen panes.
- No quarterly/weekly kernel variants, deliberately: cadence is agent work.
- `forecast_to_excel` (static values) remains unchanged for plain data dumps.
