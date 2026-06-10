# Live-Formula Excel Export Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** A native toolbelt capability for live-formula Excel: `pyfpa/excel/` (formula toolkit, canonical monthly translator, verification harness), an `fpa-excel-model` skill, a `model-export` CLI command, and CI proof that the workbook reproduces the engine to the dollar.

**Architecture:** `model_to_excel(cfg, path)` is a second compile target for `EntityConfig`: an Assumptions sheet of named driver cells plus a Model sheet whose cells are real Excel formulas referencing those names. The translator bakes structural facts (calendar-month seasonality references, growth-year exponents, instrument layout) at generation time so the formula vocabulary stays within arithmetic, `^`, `SUM`, `MIN`, `MAX`, `IF`. `verify_workbook` evaluates the workbook with the `formulas` library and compares every line and month to `cashflow_from_config`. Cadence variants are agent work composed from the toolkit, never kernel variants.

**Tech Stack:** Python 3.11+, openpyxl (existing runtime dep), `formulas` (new DEV-ONLY extra for verification), pydantic v2, pandas.

**Spec:** `docs/superpowers/specs/2026-06-10-excel-live-model-design.md`

House rules: tests FLAT in `tests/`; no em dashes anywhere; pure/immutable; small files; `python3 -m pytest`.

---

## File Structure

| Path | Responsibility |
| --- | --- |
| `pyfpa/excel/__init__.py` (create) | Re-export `model_to_excel`, `verify_workbook`, toolkit names. |
| `pyfpa/excel/toolkit.py` (create) | Named cells/rows, formula filling, formats. Pure openpyxl, no engine imports. |
| `pyfpa/excel/model_workbook.py` (create) | The canonical monthly translator. |
| `pyfpa/excel/verify.py` (create) | `VerifyReport`, `verify_workbook` (lazy `formulas` import). |
| `pyfpa/__init__.py` (modify) | Export `model_to_excel`, `verify_workbook`. |
| `pyproject.toml` (modify) | Add `formulas` to the dev extra. |
| `pyfpa/cli_commands/learning.py` or new `cli_commands/reporting.py` (create) | `model-export` handler (thin). |
| `pyfpa/cli.py` (modify) | Register `model-export`. |
| `skills/fpa-excel-model/SKILL.md` (create) | The workflow skill. |
| `skills/fpa-board-briefing/SKILL.md`, `skills/fpa-scaffold-model/SKILL.md` (modify) | One-line pointers. |
| `AGENTS.md`, `CLAUDE.md`, `README.md` (modify) | Contract section + README mention. |
| `examples/ridgeline/run_demo.py` (modify) | Also emit `model.xlsx`. |
| `tests/test_excel_toolkit.py`, `tests/test_excel_model_structure.py`, `tests/test_excel_verify.py`, `tests/test_excel_equivalence.py`, `tests/test_cli_model_export.py` (create) | Tests. |
| `tests/test_public_api.py` (modify) | Contract-test sync. |

---

## Group 1: the toolkit

### Task 1: `pyfpa/excel/toolkit.py`

**Files:**
- Create: `pyfpa/excel/__init__.py` (empty for now), `pyfpa/excel/toolkit.py`
- Test: `tests/test_excel_toolkit.py`

- [ ] **Step 1: Write the failing test**

```python
# tests/test_excel_toolkit.py
from openpyxl import Workbook, load_workbook

from pyfpa.excel.toolkit import (
    add_named_cell, add_named_row, fill_formula_row, money_format, percent_format,
)


def test_add_named_cell_registers_defined_name(tmp_path):
    wb = Workbook()
    ws = wb.active
    ws.title = "Assumptions"
    add_named_cell(wb, ws, name="tax_rate", row=2, col=2, value=0.21, number_format=percent_format())
    path = tmp_path / "t.xlsx"
    wb.save(path)
    back = load_workbook(path)
    assert "tax_rate" in back.defined_names
    assert back["Assumptions"].cell(row=2, column=2).value == 0.21


def test_add_named_row_registers_range(tmp_path):
    wb = Workbook()
    ws = wb.active
    ws.title = "Assumptions"
    add_named_row(wb, ws, name="seasonality_ch1", row=3, start_col=2,
                  values=[1.0] * 12, number_format=None)
    path = tmp_path / "t.xlsx"
    wb.save(path)
    back = load_workbook(path)
    assert "seasonality_ch1" in back.defined_names
    assert back["Assumptions"].cell(row=3, column=13).value == 1.0


def test_fill_formula_row_writes_formula_strings():
    wb = Workbook()
    ws = wb.active
    ws.title = "Model"
    # template receives 1-based month index and the column letter for that month
    fill_formula_row(
        ws, row=5, label="gross_profit", start_col=2, n_cols=3,
        template=lambda m, col: f"={col}3-{col}4",
    )
    assert ws.cell(row=5, column=1).value == "gross_profit"
    assert ws.cell(row=5, column=2).value == "=B3-B4"
    assert ws.cell(row=5, column=4).value == "=D3-D4"


def test_money_and_percent_formats_are_strings():
    assert isinstance(money_format(), str)
    assert isinstance(percent_format(), str)
```

- [ ] **Step 2: Run, confirm fail** (`ModuleNotFoundError: pyfpa.excel`).

Run: `python3 -m pytest tests/test_excel_toolkit.py -v`

- [ ] **Step 3: Implement** `pyfpa/excel/toolkit.py`:

```python
from __future__ import annotations

from collections.abc import Callable, Sequence

from openpyxl.utils import get_column_letter
from openpyxl.workbook import Workbook
from openpyxl.workbook.defined_name import DefinedName
from openpyxl.worksheet.worksheet import Worksheet


def money_format() -> str:
    return "#,##0"


def percent_format() -> str:
    return "0.0%"


def days_format() -> str:
    return "0.0"


def add_named_cell(
    wb: Workbook,
    ws: Worksheet,
    *,
    name: str,
    row: int,
    col: int,
    value: float,
    number_format: str | None = None,
) -> None:
    """Write a value and register a workbook-scoped defined name for the cell."""
    cell = ws.cell(row=row, column=col, value=value)
    if number_format:
        cell.number_format = number_format
    ref = f"'{ws.title}'!${get_column_letter(col)}${row}"
    wb.defined_names[name] = DefinedName(name=name, attr_text=ref)


def add_named_row(
    wb: Workbook,
    ws: Worksheet,
    *,
    name: str,
    row: int,
    start_col: int,
    values: Sequence[float],
    number_format: str | None = None,
) -> None:
    """Write a horizontal run of values and register a defined name for the range."""
    for offset, value in enumerate(values):
        cell = ws.cell(row=row, column=start_col + offset, value=value)
        if number_format:
            cell.number_format = number_format
    first = f"${get_column_letter(start_col)}${row}"
    last = f"${get_column_letter(start_col + len(values) - 1)}${row}"
    wb.defined_names[name] = DefinedName(
        name=name, attr_text=f"'{ws.title}'!{first}:{last}"
    )


def fill_formula_row(
    ws: Worksheet,
    *,
    row: int,
    label: str,
    start_col: int,
    n_cols: int,
    template: Callable[[int, str], str],
    number_format: str | None = None,
) -> None:
    """Label column A, then fill each month cell with template(month_index, column_letter).

    template receives the 1-based month index and that month's column letter and
    must return a full formula string starting with '='."""
    ws.cell(row=row, column=1, value=label)
    for m in range(1, n_cols + 1):
        col = get_column_letter(start_col + m - 1)
        cell = ws.cell(row=row, column=start_col + m - 1, value=template(m, col))
        if number_format:
            cell.number_format = number_format


def freeze_header(ws: Worksheet, *, first_data_cell: str = "B2") -> None:
    ws.freeze_panes = first_data_cell
```

- [ ] **Step 4: Run, confirm pass.** Then full suite, no regressions.

- [ ] **Step 5: Commit**

```bash
git add pyfpa/excel/ tests/test_excel_toolkit.py
git commit -m "feat: excel formula toolkit (named cells/rows, formula fill, formats)"
```

---

## Group 2: the canonical translator

### Task 2: Assumptions sheet + Model sheet structure

**Files:**
- Create: `pyfpa/excel/model_workbook.py`
- Test: `tests/test_excel_model_structure.py`

The translator compiles `EntityConfig` to a two-sheet workbook. Layout contract
(the structure test pins this):

**Assumptions sheet** (defined names; one block per concern):
- Per channel i (1-based): `rev_annual_ch{i}`, `growth_ch{i}`, `cogs_pct_ch{i}`
  (cells) and `seasonality_ch{i}` (12-cell named row).
- Per opex line j: fixed lines get `opex_amount_{j}`; variable lines get
  `opex_pct_{j}`.
- Cells: `dso_days`, `dio_days`, `dpo_days`, `tax_rate`, `da_monthly`,
  `capex_monthly`, `open_cash`, `open_ar`, `open_ap`, `open_inventory`,
  `open_nol`.
- Per debt instrument k: `debt_open_{k}`, `debt_rate_{k}`, `debt_prin_{k}`.

**Model sheet** (months across columns B..; labels in column A; every data cell
a formula). Row map, in order, with the exact formula pattern each row uses
(month m, column letter C; `[C-1]` means the previous month's column; literals
baked at generation time are marked BAKED):

| Row label | Formula pattern (per month cell) |
| --- | --- |
| `revenue_ch{i}` | `=rev_annual_ch{i}*(W/SUM(seasonality_ch{i}))*(1+growth_ch{i})^Y` where `W` is the direct cell reference into `seasonality_ch{i}` for this month's CALENDAR month (BAKED: the translator computes the calendar month from cfg.start_month, matching `revenue_from_config`'s `period.month` indexing) and `Y = (m-1)//12` (BAKED literal). |
| `revenue_total` | `=SUM(C{first_ch_row}:C{last_ch_row})` over the channel rows. |
| `cogs_total` | `=` sum of `revenue_ch{i}*cogs_pct_ch{i}` terms (explicit `+` chain over channels, BAKED row refs). |
| `gross_profit` | `=C{revenue_total}-C{cogs_total}` |
| `opex_{j}` (fixed) | `=opex_amount_{j}` |
| `opex_{j}` (variable) | `=C{revenue_total}*opex_pct_{j}` |
| `opex_total` | `=SUM(...)` over opex rows (or `=0` when no opex lines). |
| `ebitda` | `=C{gross_profit}-C{opex_total}` |
| `da` | `=da_monthly` |
| `debt_balance_{k}` (term loan) | month 1: `=debt_open_{k}-MIN(debt_prin_{k},debt_open_{k})`; else `=[C-1]{row}-MIN(debt_prin_{k},[C-1]{row})` (balance AFTER payment; interest reads the PRE-payment balance, below). |
| `debt_balance_{k}` (loc) | month 1: `=debt_open_{k}`; else `=[C-1]{row}` |
| `interest_{k}` | month 1: `=debt_open_{k}*debt_rate_{k}/12`; else `=[C-1]{bal_row}*debt_rate_{k}/12` (matches engine: interest on balance before this month's principal). |
| `principal_{k}` (term loan) | month 1: `=MIN(debt_prin_{k},debt_open_{k})`; else `=MIN(debt_prin_{k},[C-1]{bal_row})`; (loc) `=0` |
| `interest_total` / `principal_total` | `=SUM(...)` over instrument rows (or `=0`). |
| `pretax_income` | `=C{ebitda}-C{da}-C{interest_total}` (engine: EBIT minus interest; D&A is expensed). NOTE: read `pyfpa/models/cashflow.py` first and mirror EXACTLY (`pretax = ebit - interest` where `ebit = ebitda - da`). |
| `nol_opening` | month 1: `=open_nol`; else `=[C-1]{nol_closing}` |
| `nol_used` | `=MIN(C{nol_opening},MAX(0,C{pretax_income}))` |
| `nol_closing` | `=C{nol_opening}-C{nol_used}` |
| `tax` | `=(MAX(0,C{pretax_income})-C{nol_used})*tax_rate` |
| `net_income` | `=C{pretax_income}-C{tax}` |
| `ar_balance` | `=C{revenue_total}*dso_days/30` |
| `ap_balance` | `=C{cogs_total}*dpo_days/30` |
| `inv_balance` | `=C{cogs_total}*dio_days/30` |
| `wc_cash_impact` | month 1: `=-(C{ar}-open_ar)+(C{ap}-open_ap)-(C{inv}-open_inventory)`; else `=-(C{ar}-[C-1]{ar})+(C{ap}-[C-1]{ap})-(C{inv}-[C-1]{inv})` |
| `operating_cash_flow` | `=C{net_income}+C{da}+C{wc_cash_impact}` |
| `capex` | `=capex_monthly` |
| `free_cash_flow` | `=C{operating_cash_flow}-C{capex}` |
| `change_in_cash` | `=C{free_cash_flow}-C{principal_total}` |
| `ending_cash` | month 1: `=open_cash+C{change_in_cash}`; else `=[C-1]{ending_cash}+C{change_in_cash}` |

Implementation notes for the engineer:
- Build the row map as data first (a list of row specs), then emit; keep
  `model_workbook.py` under 400 lines by composing `toolkit.fill_formula_row`.
- BEFORE writing formulas, read `pyfpa/models/{revenue,cogs,opex,working_capital,debt,cashflow}.py`
  and mirror semantics exactly. The equivalence test in Group 3 is the referee.
- Header row 1 of the Model sheet: month labels from `month_index(cfg.start_month, cfg.horizon_months)`.
- Apply `money_format()` to currency rows, `percent_format()` where sensible,
  `freeze_header`.

- [ ] **Step 1: Write the failing structure test**

```python
# tests/test_excel_model_structure.py
from openpyxl import load_workbook

from pyfpa.config.schemas import EntityConfig
from pyfpa.excel.model_workbook import model_to_excel


def _cfg():
    return EntityConfig.model_validate({
        "name": "T", "start_month": "2026-01", "horizon_months": 12, "tax_rate": 0.21,
        "channels": [
            {"name": "A", "annual_revenue": 1_200_000.0, "growth_rate": 0.10,
             "seasonality": [1.0] * 12, "cogs_pct": 0.5},
            {"name": "B", "annual_revenue": 600_000.0, "growth_rate": 0.0,
             "seasonality": [1, 1, 1, 1, 1, 1, 2, 2, 2, 1, 1, 1], "cogs_pct": 0.4},
        ],
        "opex": [
            {"name": "salaries", "kind": "fixed", "monthly_amount": 30_000.0},
            {"name": "marketing", "kind": "variable", "pct_of_revenue": 0.05},
        ],
        "debt": [
            {"name": "term", "kind": "term_loan", "opening_balance": 500_000.0,
             "annual_rate": 0.08, "monthly_principal": 10_000.0},
            {"name": "loc", "kind": "loc", "opening_balance": 100_000.0, "annual_rate": 0.10},
        ],
        "working_capital": {"dso_days": 45.0, "dpo_days": 30.0, "dio_days": 60.0},
        "opening_balances": {"cash": 50_000.0, "ar": 100_000.0, "ap": 60_000.0,
                              "inventory": 120_000.0, "nol": 40_000.0},
        "da_monthly": 2_000.0, "capex_monthly": 5_000.0,
    })


def test_workbook_has_named_assumptions_and_formula_cells(tmp_path):
    path = tmp_path / "model.xlsx"
    model_to_excel(_cfg(), path)
    wb = load_workbook(path)
    assert set(wb.sheetnames) == {"Assumptions", "Model"}
    for name in ["rev_annual_ch1", "growth_ch1", "cogs_pct_ch1", "seasonality_ch1",
                 "rev_annual_ch2", "dso_days", "dio_days", "dpo_days", "tax_rate",
                 "da_monthly", "capex_monthly", "open_cash", "open_nol",
                 "debt_open_1", "debt_rate_1", "debt_prin_1", "debt_open_2",
                 "opex_amount_1", "opex_pct_2"]:
        assert name in wb.defined_names, f"missing defined name: {name}"
    model = wb["Model"]
    labels = [model.cell(row=r, column=1).value for r in range(2, model.max_row + 1)]
    for required in ["revenue_total", "gross_profit", "ebitda", "pretax_income",
                     "tax", "net_income", "wc_cash_impact", "operating_cash_flow",
                     "free_cash_flow", "change_in_cash", "ending_cash"]:
        assert required in labels, f"missing model row: {required}"
    # every data cell in a known row is a formula string, not a value
    row_idx = labels.index("ending_cash") + 2
    for col in range(2, 2 + 12):
        v = model.cell(row=row_idx, column=col).value
        assert isinstance(v, str) and v.startswith("="), f"not a formula: {v!r}"


def test_formula_vocabulary_is_restricted(tmp_path):
    import re
    path = tmp_path / "model.xlsx"
    model_to_excel(_cfg(), path)
    wb = load_workbook(path)
    model = wb["Model"]
    allowed = {"SUM", "MIN", "MAX", "IF"}
    for row in model.iter_rows(min_row=2, min_col=2):
        for cell in row:
            if isinstance(cell.value, str) and cell.value.startswith("="):
                for fn in re.findall(r"([A-Z]{2,})\s*\(", cell.value):
                    assert fn in allowed, f"forbidden function {fn} in {cell.value}"
```

- [ ] **Step 2: Run, confirm fail** (`ModuleNotFoundError`).

- [ ] **Step 3: Implement `model_to_excel`** per the layout contract and notes
above. Keep it composed from the toolkit; row-spec list first, then two
emit passes (assumptions, model).

- [ ] **Step 4: Run the structure tests, then the full suite.**

- [ ] **Step 5: Commit**

```bash
git add pyfpa/excel/model_workbook.py tests/test_excel_model_structure.py
git commit -m "feat: canonical monthly model-to-excel translator (live formulas)"
```

---

## Group 3: verification harness + equivalence proof

### Task 3: `verify.py` + dev extra

**Files:**
- Create: `pyfpa/excel/verify.py`
- Modify: `pyproject.toml` (dev extra)
- Test: `tests/test_excel_verify.py`

- [ ] **Step 1: Add `formulas` to the dev extra in `pyproject.toml`** (read the
file; extend the existing `[project.optional-dependencies] dev` list with
`"formulas>=1.2"`). Then `pip install formulas` locally.

- [ ] **Step 2: Write the failing test**

```python
# tests/test_excel_verify.py
import pandas as pd
import pytest

pytest.importorskip("formulas")

from pyfpa.config.schemas import EntityConfig
from pyfpa.excel.model_workbook import model_to_excel
from pyfpa.excel.verify import verify_workbook
from pyfpa.models.cashflow import cashflow_from_config


def _simple_cfg():
    return EntityConfig.model_validate({
        "name": "T", "start_month": "2026-01", "horizon_months": 6, "tax_rate": 0.0,
        "channels": [{"name": "A", "annual_revenue": 120_000.0, "growth_rate": 0.0,
                      "seasonality": [1.0] * 12, "cogs_pct": 0.5}],
        "opex": [], "debt": [],
        "working_capital": {"dso_days": 0.0, "dpo_days": 0.0, "dio_days": 0.0},
        "opening_balances": {"cash": 0.0},
    })


def test_verify_passes_on_faithful_workbook(tmp_path):
    cfg = _simple_cfg()
    path = tmp_path / "m.xlsx"
    model_to_excel(cfg, path)
    report = verify_workbook(path, cashflow_from_config(cfg))
    assert report.passed, report.failures


def test_verify_fails_on_corrupted_formula(tmp_path):
    from openpyxl import load_workbook
    cfg = _simple_cfg()
    path = tmp_path / "m.xlsx"
    model_to_excel(cfg, path)
    wb = load_workbook(path)
    model = wb["Model"]
    labels = {model.cell(row=r, column=1).value: r for r in range(2, model.max_row + 1)}
    model.cell(row=labels["gross_profit"], column=3, value="=1234567")
    wb.save(path)
    report = verify_workbook(path, cashflow_from_config(cfg))
    assert not report.passed
    assert any("gross_profit" in f for f in report.failures)


def test_missing_formulas_dependency_message():
    # exercised via the lazy-import shim: patch the import to raise and assert
    # the error names the install command
    import pyfpa.excel.verify as v
    import builtins
    real_import = builtins.__import__

    def fake_import(name, *args, **kwargs):
        if name == "formulas":
            raise ImportError("nope")
        return real_import(name, *args, **kwargs)

    builtins.__import__ = fake_import
    try:
        with pytest.raises(RuntimeError, match="pip install formulas"):
            v._load_formulas()
    finally:
        builtins.__import__ = real_import
```

- [ ] **Step 3: Implement** `pyfpa/excel/verify.py`:

```python
from __future__ import annotations

from pathlib import Path

import pandas as pd
from pydantic import BaseModel

from openpyxl import load_workbook


class VerifyReport(BaseModel):
    passed: bool
    failures: list[str]
    max_rel_deviation: float
    lines_checked: int


def _load_formulas():
    try:
        import formulas  # noqa: PLC0415 (lazy on purpose: dev-only dependency)
    except ImportError as exc:
        raise RuntimeError(
            "workbook verification requires the 'formulas' package: pip install formulas"
        ) from exc
    return formulas


def verify_workbook(
    path: str | Path,
    expected: pd.DataFrame,
    *,
    rel_tol: float = 1e-6,
) -> VerifyReport:
    """Evaluate the workbook's formulas in Python and compare every Model-sheet
    line that matches a column of `expected`, month by month. NaN or
    unevaluated cells are failures, never skipped."""
    formulas = _load_formulas()
    path = Path(path)
    solution = formulas.ExcelModel().loads(str(path)).finish().calculate()

    wb = load_workbook(path)
    model = wb["Model"]
    labels = {model.cell(row=r, column=1).value: r for r in range(2, model.max_row + 1)}

    book_key = path.name.upper()
    failures: list[str] = []
    max_dev = 0.0
    lines = 0
    for line in expected.columns:
        if line not in labels:
            continue
        lines += 1
        row = labels[line]
        for m in range(len(expected.index)):
            col = 2 + m
            from openpyxl.utils import get_column_letter
            ref = f"'[{book_key}]MODEL'!{get_column_letter(col)}{row}"
            key = next((k for k in solution if k.upper() == ref.upper()), None)
            if key is None:
                failures.append(f"{line} month {m + 1}: cell not evaluated")
                continue
            got = float(solution[key].value[0, 0])
            want = float(expected[line].iloc[m])
            denom = max(abs(want), 1.0)
            dev = abs(got - want) / denom
            max_dev = max(max_dev, dev)
            if not dev <= rel_tol:
                failures.append(f"{line} month {m + 1}: workbook {got!r} vs engine {want!r}")
    return VerifyReport(
        passed=not failures and lines > 0,
        failures=failures,
        max_rel_deviation=max_dev,
        lines_checked=lines,
    )
```

NOTE for the engineer: the `formulas` solution-key format above is the
documented shape but MUST be confirmed against the installed version (print a
few keys in a scratch run). Adjust the lookup, never the assertion bar. If the
library proves unable to evaluate a needed construct, simplify the emitted
formula in the translator rather than weakening verification.

- [ ] **Step 4: Run, confirm pass. Full suite.**

- [ ] **Step 5: Commit**

```bash
git add pyfpa/excel/verify.py pyproject.toml tests/test_excel_verify.py
git commit -m "feat: workbook verification harness (formulas evaluator, dev-only dep)"
```

### Task 4: the equivalence proof (CI)

**Files:**
- Test: `tests/test_excel_equivalence.py`

- [ ] **Step 1: Write the test** (this is the spec's success criterion 2 and 3):

```python
# tests/test_excel_equivalence.py
import pytest

pytest.importorskip("formulas")

from pyfpa.config.loader import load_config
from pyfpa.config.schemas import EntityConfig
from pyfpa.excel.model_workbook import model_to_excel
from pyfpa.excel.verify import verify_workbook
from pyfpa.models.cashflow import cashflow_from_config


def test_ridgeline_workbook_reproduces_engine(tmp_path):
    cfg = load_config("examples/ridgeline/config.yaml")
    path = tmp_path / "ridgeline.xlsx"
    model_to_excel(cfg, path)
    report = verify_workbook(path, cashflow_from_config(cfg))
    assert report.passed, report.failures[:10]
    assert report.lines_checked >= 10


def test_edge_config_nol_debt_seasonality_reproduces_engine(tmp_path):
    cfg = EntityConfig.model_validate({
        "name": "Edge", "start_month": "2026-04", "horizon_months": 24, "tax_rate": 0.25,
        "channels": [
            {"name": "A", "annual_revenue": 2_400_000.0, "growth_rate": 0.12,
             "seasonality": [1, 1, 2, 3, 2, 1, 1, 1, 2, 3, 4, 3], "cogs_pct": 0.55},
            {"name": "B", "annual_revenue": 900_000.0, "growth_rate": -0.05,
             "seasonality": [2, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 2], "cogs_pct": 0.35},
        ],
        "opex": [
            {"name": "fixed_g_a", "kind": "fixed", "monthly_amount": 80_000.0},
            {"name": "var_mktg", "kind": "variable", "pct_of_revenue": 0.07},
        ],
        "debt": [
            {"name": "term", "kind": "term_loan", "opening_balance": 240_000.0,
             "annual_rate": 0.09, "monthly_principal": 25_000.0},
            {"name": "loc", "kind": "loc", "opening_balance": 150_000.0, "annual_rate": 0.11},
        ],
        "working_capital": {"dso_days": 38.0, "dpo_days": 42.0, "dio_days": 75.0},
        "opening_balances": {"cash": 25_000.0, "ar": 180_000.0, "ap": 110_000.0,
                              "inventory": 260_000.0, "nol": 500_000.0},
        "da_monthly": 6_000.0, "capex_monthly": 9_000.0,
    })
    path = tmp_path / "edge.xlsx"
    model_to_excel(cfg, path)
    report = verify_workbook(path, cashflow_from_config(cfg))
    assert report.passed, report.failures[:10]
```

The edge config deliberately exercises: term loan that fully amortizes inside
the horizon (240k at 25k/month exhausts in month 10, hitting the `MIN` branch),
NOL consumed across months, off-January start month (calendar seasonality
indexing), negative growth, and a 24-month horizon (year-offset exponent > 0).

- [ ] **Step 2: Run.** Expected: both PASS. Any mismatch is a translator bug;
fix the translator (or its baked references), never the tolerance.

- [ ] **Step 3: Full suite, commit**

```bash
git add tests/test_excel_equivalence.py
git commit -m "test: CI proof that live-formula workbooks reproduce the engine"
```

---

## Group 4: exports + CLI

### Task 5: public API + `model-export`

**Files:**
- Modify: `pyfpa/excel/__init__.py`, `pyfpa/__init__.py`, `tests/test_public_api.py`
- Create: `pyfpa/cli_commands/reporting.py`
- Modify: `pyfpa/cli.py`
- Test: `tests/test_cli_model_export.py`

- [ ] **Step 1: Fill `pyfpa/excel/__init__.py`**

```python
from pyfpa.excel.toolkit import (
    add_named_cell, add_named_row, fill_formula_row, freeze_header,
    money_format, percent_format, days_format,
)
from pyfpa.excel.model_workbook import model_to_excel
from pyfpa.excel.verify import VerifyReport, verify_workbook

__all__ = [
    "add_named_cell", "add_named_row", "fill_formula_row", "freeze_header",
    "money_format", "percent_format", "days_format",
    "model_to_excel", "VerifyReport", "verify_workbook",
]
```

Export `model_to_excel` and `verify_workbook` from `pyfpa/__init__.py` and add
both names to the exact-set assertion in `tests/test_public_api.py` (read it;
keep exact-set equality).

- [ ] **Step 2: CLI command.** Create `pyfpa/cli_commands/reporting.py` with a
`command_model_export(args)` handler in the established `cli_commands/learning.py`
style (workspace validation, JSON `_success` output): flags
`<company-root> --config <path-to-EntityConfig-yaml> --out <xlsx-path>`;
loads via `pyfpa.config.loader.load_config`, calls `model_to_excel`, reports
the written path and sheet names. Register `model-export` in `pyfpa/cli.py`
following how the other `cli_commands` handlers are registered. Read both
files first and match exactly.

- [ ] **Step 3: CLI test** `tests/test_cli_model_export.py` in the established
CLI-test style (read `tests/test_cli*.py` first): init a tmp workspace, copy or
point at `examples/ridgeline/config.yaml`, run `model-export`, assert JSON
`ok=true` and the xlsx exists with both sheets.

- [ ] **Step 4: Full suite; `python3 -c "import pyfpa; print(pyfpa.model_to_excel, pyfpa.verify_workbook)"`.**

- [ ] **Step 5: Commit**

```bash
git add pyfpa/excel/__init__.py pyfpa/__init__.py pyfpa/cli_commands/reporting.py pyfpa/cli.py tests/test_public_api.py tests/test_cli_model_export.py
git commit -m "feat: export excel API + model-export CLI command"
```

---

## Group 5: skill + contract + demo

### Task 6: `fpa-excel-model` skill + pointers

**Files:**
- Create: `skills/fpa-excel-model/SKILL.md`
- Modify: `skills/fpa-board-briefing/SKILL.md`, `skills/fpa-scaffold-model/SKILL.md`, `AGENTS.md`, `CLAUDE.md`

- [ ] **Step 1: Write `skills/fpa-excel-model/SKILL.md`** with this content
(frontmatter description must avoid colons inside the YAML value; no em dashes):

```markdown
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
```

- [ ] **Step 2: Pointers.** In `fpa-board-briefing/SKILL.md` add one line in its
workflow: "If the audience wants the model itself, produce the live-formula
workbook via **fpa-excel-model** alongside the briefing." In
`fpa-scaffold-model/SKILL.md` add: "A live-formula Excel edition of the model is
available via **fpa-excel-model**."

- [ ] **Step 3: Contract.** In `AGENTS.md` (and a matching short line in
`CLAUDE.md`), add a paragraph in the style of the existing connector/entrypoint
rules: "When the user wants Excel output with working formulas, use
`model_to_excel` for the standard monthly model. For any other cadence or
layout, generate a company-specific exporter from `pyfpa.excel.toolkit` in the
generated namespace and register it as a report entrypoint. Install `formulas`
and run `verify_workbook` before delivering. No workbook ships unverified."

- [ ] **Step 4: Frontmatter validation**

Run: `python3 -c "import pathlib,yaml; [yaml.safe_load(p.read_text().split('---')[1]) for p in pathlib.Path('skills').rglob('SKILL.md')]; print('ok')"`

- [ ] **Step 5: Commit**

```bash
git add skills/ AGENTS.md CLAUDE.md
git commit -m "feat: fpa-excel-model skill + contract rules (no workbook ships unverified)"
```

### Task 7: Ridgeline demo + README + final

**Files:**
- Modify: `examples/ridgeline/run_demo.py`, `README.md`

- [ ] **Step 1: Demo.** Read `examples/ridgeline/run_demo.py`; after the existing
outputs, add `model_to_excel(cfg, <output dir>/"model.xlsx")` and a printed line
naming the file. Run the demo; confirm the file exists and opens (load_workbook).

- [ ] **Step 2: README.** In the kernel/IO bullet list, replace the
`forecast_to_excel` mention with both: static export (`forecast_to_excel`) and
live-formula model workbook (`model_to_excel`, verified against the engine in
CI). Add `model-export` to the CLI command list. One short paragraph in the
appropriate section; no em dashes; humble tone.

- [ ] **Step 3: Full suite + dash sweep**

Run: `python3 -m pytest -q` and
`python3 - <<'EOF'\nimport pathlib\nbad=[p for p in pathlib.Path('.').rglob('*') if p.suffix in {'.py','.md','.yaml'} and '.git' not in str(p) and 'docs/superpowers' not in str(p) and p.is_file() and chr(8212) in p.read_text(errors='ignore')]\nprint(bad or 'CLEAN')\nEOF`

- [ ] **Step 4: Commit, push, PR**

```bash
git add examples/ridgeline/run_demo.py README.md
git commit -m "docs: ridgeline demo emits live-formula workbook; README surfaces excel capability"
git push -u origin feat/excel-live-model
gh pr create --base main --title "feat: live-formula Excel export (toolkit + canonical translator + verification)" \
  --body "Native live-formula Excel: pyfpa/excel toolkit, model_to_excel canonical monthly translator (named assumptions, real formulas), verify_workbook harness (formulas evaluator, dev-only dep), model-export CLI, fpa-excel-model skill with the no-unverified-workbook guardrail, CI equivalence proof on Ridgeline + an NOL/debt/seasonality edge config. Cadence variants are agent work composed from the toolkit. Spec: docs/superpowers/specs/2026-06-10-excel-live-model-design.md"
```

Expected: PR opened, CI green. Jeff merges.

---

## Self-Review notes

- **Spec coverage:** toolkit -> Task 1; translator + layout/vocabulary -> Task 2;
  verify + lazy import + dev extra -> Task 3; CI equivalence (success criteria
  2 and 3, incl. NOL/term-loan-exhaustion/off-January start) -> Task 4; public
  API + CLI -> Task 5; skill + pointers + contract -> Task 6; demo + README +
  dash sweep -> Task 7. Error handling: unsupported-config guard lives in the
  translator (Task 2 implementation note), missing-formulas message tested in
  Task 3, NaN/unevaluated-cells-fail in verify implementation.
- **Type consistency:** `model_to_excel(cfg, path)`, `verify_workbook(path,
  expected, *, rel_tol)`, `VerifyReport(passed, failures, max_rel_deviation,
  lines_checked)`, toolkit signatures used identically across tasks.
- **Honest uncertainty, flagged where it lives:** the `formulas` solution-key
  format (Task 3 note) is verify-against-installed-version work, with the rule
  "adjust the lookup, never the assertion bar."
