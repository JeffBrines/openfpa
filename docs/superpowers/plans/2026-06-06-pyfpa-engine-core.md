# pyfpa Engine Core Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build the lean, config-driven `pyfpa` forecast engine: a pydantic-validated YAML config flows through six pure model layers (revenue → cogs → opex → working_capital → debt → cashflow) to produce a 12-month financial forecast DataFrame.

**Architecture:** Pure functions, no hidden state. Each model layer is a `*_from_config(...)` factory that does no file I/O and returns an immutable-style pandas DataFrame (built with `.assign`, never mutated in place). Config is the single source of truth, validated at load via pydantic. The `cashflow_from_config` assembler composes the other five layers into the full indirect-method forecast.

**Tech Stack:** Python 3.11+, pandas, pydantic v2, pyyaml, pytest.

---

## File Structure

```
pyfpa/
├── __init__.py                  # public API exports
├── config/
│   ├── __init__.py
│   ├── schemas.py               # pydantic models (EntityConfig + parts)
│   └── loader.py                # load_config(path) -> EntityConfig
└── models/
    ├── __init__.py
    ├── periods.py               # month_index(start_month, horizon) -> PeriodIndex
    ├── revenue.py               # revenue_from_config(cfg)
    ├── cogs.py                  # cogs_from_config(cfg, revenue_df)
    ├── opex.py                  # opex_from_config(cfg, revenue_df)
    ├── working_capital.py       # working_capital_from_config(cfg, revenue_df, cogs_df)
    ├── debt.py                  # debt_from_config(cfg)
    └── cashflow.py              # cashflow_from_config(cfg) — the assembler
tests/
├── conftest.py                  # sample_config fixture (hand-computable numbers)
├── test_periods.py
├── test_revenue.py
├── test_cogs.py
├── test_opex.py
├── test_working_capital.py
├── test_debt.py
├── test_cashflow.py
└── test_loader.py
examples/ridgeline/config.yaml   # minimal config used as a load+run integration fixture
pyproject.toml
pytest.ini
```

**Module responsibilities:**
- `config/schemas.py` — the data contract. Every number the engine consumes is a validated field.
- `models/periods.py` — the one shared helper (monthly date index) every layer uses.
- `models/*.py` — one financial concept per file; each imports only schemas + periods + pandas.
- `models/cashflow.py` — the only module that composes other layers.

---

## Task 0: Project scaffold

**Files:**
- Create: `pyproject.toml`
- Create: `pytest.ini`
- Create: `pyfpa/__init__.py` (empty for now)
- Create: `pyfpa/config/__init__.py` (empty)
- Create: `pyfpa/models/__init__.py` (empty)

- [ ] **Step 1: Create `pyproject.toml`**

```toml
[project]
name = "pyfpa"
version = "0.1.0"
description = "Lean, config-driven FP&A forecast engine"
requires-python = ">=3.11"
dependencies = [
    "pandas>=2.0",
    "pydantic>=2.5",
    "pyyaml>=6.0",
]

[project.optional-dependencies]
dev = ["pytest>=8.0"]

[build-system]
requires = ["setuptools>=68"]
build-backend = "setuptools.build_meta"

[tool.setuptools.packages.find]
include = ["pyfpa*"]
```

- [ ] **Step 2: Create `pytest.ini`**

```ini
[pytest]
testpaths = tests
python_files = test_*.py
addopts = -q
```

- [ ] **Step 3: Create empty package init files**

Create `pyfpa/__init__.py`, `pyfpa/config/__init__.py`, `pyfpa/models/__init__.py` — each an empty file (one blank line is fine).

- [ ] **Step 4: Create and activate a venv, install editable**

Run:
```bash
cd /Volumes/Crucial/openfpa
python3 -m venv .venv
.venv/bin/pip install -e ".[dev]"
```
Expected: ends with `Successfully installed pyfpa-0.1.0 ...`

- [ ] **Step 5: Commit**

```bash
git add pyproject.toml pytest.ini pyfpa/
git commit -m "chore: scaffold pyfpa package and tooling"
```

---

## Task 1: Period index helper

**Files:**
- Create: `pyfpa/models/periods.py`
- Test: `tests/test_periods.py`

- [ ] **Step 1: Write the failing test**

```python
# tests/test_periods.py
import pandas as pd
from pyfpa.models.periods import month_index


def test_month_index_length_and_start():
    idx = month_index("2026-01", 12)
    assert len(idx) == 12
    assert idx[0] == pd.Period("2026-01", freq="M")
    assert idx[-1] == pd.Period("2026-12", freq="M")


def test_month_index_crosses_year_boundary():
    idx = month_index("2026-11", 3)
    assert list(idx) == [
        pd.Period("2026-11", freq="M"),
        pd.Period("2026-12", freq="M"),
        pd.Period("2027-01", freq="M"),
    ]
```

- [ ] **Step 2: Run test to verify it fails**

Run: `.venv/bin/pytest tests/test_periods.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'pyfpa.models.periods'`

- [ ] **Step 3: Write minimal implementation**

```python
# pyfpa/models/periods.py
from __future__ import annotations

import pandas as pd


def month_index(start_month: str, horizon_months: int) -> pd.PeriodIndex:
    """Monthly PeriodIndex of length `horizon_months` starting at `start_month` (YYYY-MM)."""
    start = pd.Period(start_month, freq="M")
    return pd.period_range(start=start, periods=horizon_months, freq="M")
```

- [ ] **Step 4: Run test to verify it passes**

Run: `.venv/bin/pytest tests/test_periods.py -v`
Expected: PASS (2 passed)

- [ ] **Step 5: Commit**

```bash
git add pyfpa/models/periods.py tests/test_periods.py
git commit -m "feat: add monthly period index helper"
```

---

## Task 2: Config schemas

**Files:**
- Create: `pyfpa/config/schemas.py`
- Test: `tests/test_loader.py` (schema-validation portion; loader added in Task 3)

- [ ] **Step 1: Write the failing test**

```python
# tests/test_loader.py
import pytest
from pydantic import ValidationError
from pyfpa.config.schemas import (
    EntityConfig, Channel, WorkingCapitalConfig,
)


def _minimal_kwargs():
    return dict(
        name="X",
        start_month="2026-01",
        channels=[Channel(name="D2C", annual_revenue=1200.0,
                          seasonality=[1.0] * 12, cogs_pct=0.5)],
        working_capital=WorkingCapitalConfig(dso_days=30, dpo_days=30, dio_days=0),
    )


def test_entity_config_defaults():
    cfg = EntityConfig(**_minimal_kwargs())
    assert cfg.horizon_months == 12
    assert cfg.tax_rate == 0.21
    assert cfg.opening_balances.cash == 0.0


def test_seasonality_must_be_twelve():
    with pytest.raises(ValidationError):
        Channel(name="D2C", annual_revenue=1.0, seasonality=[1.0] * 11, cogs_pct=0.5)


def test_cogs_pct_bounded():
    with pytest.raises(ValidationError):
        Channel(name="D2C", annual_revenue=1.0, seasonality=[1.0] * 12, cogs_pct=1.5)


def test_bad_start_month_rejected():
    kwargs = _minimal_kwargs() | {"start_month": "not-a-month"}
    with pytest.raises(ValidationError):
        EntityConfig(**kwargs)
```

- [ ] **Step 2: Run test to verify it fails**

Run: `.venv/bin/pytest tests/test_loader.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'pyfpa.config.schemas'`

- [ ] **Step 3: Write minimal implementation**

```python
# pyfpa/config/schemas.py
from __future__ import annotations

from typing import Literal

import pandas as pd
from pydantic import BaseModel, Field, field_validator


class Channel(BaseModel):
    name: str
    annual_revenue: float = Field(ge=0)
    growth_rate: float = 0.0          # annual YoY, compounded per forecast year
    seasonality: list[float] = Field(min_length=12, max_length=12)
    cogs_pct: float = Field(ge=0, le=1)

    @field_validator("seasonality")
    @classmethod
    def _weights_positive(cls, v: list[float]) -> list[float]:
        if sum(v) <= 0:
            raise ValueError("seasonality weights must sum to a positive number")
        return v


class OpexLine(BaseModel):
    name: str
    kind: Literal["fixed", "variable"]
    monthly_amount: float = 0.0       # used when kind == "fixed"
    pct_of_revenue: float = 0.0       # used when kind == "variable"


class DebtInstrument(BaseModel):
    name: str
    kind: Literal["term_loan", "loc"]
    opening_balance: float = Field(ge=0)
    annual_rate: float = Field(ge=0)
    monthly_principal: float = Field(default=0.0, ge=0)  # term_loan only


class WorkingCapitalConfig(BaseModel):
    dso_days: float = Field(ge=0)
    dpo_days: float = Field(ge=0)
    dio_days: float = Field(ge=0)


class OpeningBalances(BaseModel):
    cash: float = 0.0
    ar: float = 0.0
    ap: float = 0.0
    inventory: float = 0.0
    nol: float = Field(default=0.0, ge=0)  # net operating loss carryforward


class EntityConfig(BaseModel):
    name: str
    start_month: str
    horizon_months: int = Field(default=12, ge=1, le=120)
    tax_rate: float = Field(default=0.21, ge=0, le=1)
    channels: list[Channel]
    opex: list[OpexLine] = Field(default_factory=list)
    debt: list[DebtInstrument] = Field(default_factory=list)
    working_capital: WorkingCapitalConfig
    opening_balances: OpeningBalances = Field(default_factory=OpeningBalances)

    @field_validator("start_month")
    @classmethod
    def _valid_month(cls, v: str) -> str:
        try:
            pd.Period(v, freq="M")
        except Exception as e:  # noqa: BLE001 - re-raised as ValueError for pydantic
            raise ValueError(f"start_month must be YYYY-MM, got {v!r}") from e
        return v
```

- [ ] **Step 4: Run test to verify it passes**

Run: `.venv/bin/pytest tests/test_loader.py -v`
Expected: PASS (4 passed)

- [ ] **Step 5: Commit**

```bash
git add pyfpa/config/schemas.py tests/test_loader.py
git commit -m "feat: add pydantic config schemas"
```

---

## Task 3: Config loader

**Files:**
- Create: `pyfpa/config/loader.py`
- Modify: `tests/test_loader.py` (append loader tests)
- Create: `examples/ridgeline/config.yaml` (minimal fixture)

- [ ] **Step 1: Create the minimal fixture config**

```yaml
# examples/ridgeline/config.yaml
name: Ridgeline Chair Co.
start_month: "2026-01"
horizon_months: 12
tax_rate: 0.21
channels:
  - name: D2C
    annual_revenue: 3000000
    growth_rate: 0.10
    seasonality: [0.6, 0.6, 0.8, 1.0, 1.4, 1.6, 1.4, 1.2, 0.9, 0.8, 0.9, 0.8]
    cogs_pct: 0.42
  - name: Amazon
    annual_revenue: 2000000
    growth_rate: 0.05
    seasonality: [0.7, 0.7, 0.9, 1.0, 1.3, 1.5, 1.3, 1.1, 0.9, 0.9, 0.9, 0.8]
    cogs_pct: 0.50
  - name: Wholesale
    annual_revenue: 1000000
    growth_rate: 0.03
    seasonality: [1.4, 1.6, 1.2, 1.0, 0.8, 0.6, 0.6, 0.7, 0.9, 1.0, 1.1, 1.1]
    cogs_pct: 0.60
opex:
  - {name: Marketing, kind: variable, pct_of_revenue: 0.12}
  - {name: Payroll, kind: fixed, monthly_amount: 110000}
  - {name: Software & Tools, kind: fixed, monthly_amount: 9000}
  - {name: Rent & Facilities, kind: fixed, monthly_amount: 14000}
debt:
  - {name: LOC, kind: loc, opening_balance: 600000, annual_rate: 0.105}
  - {name: Term Loan, kind: term_loan, opening_balance: 480000, annual_rate: 0.085, monthly_principal: 10000}
working_capital:
  dso_days: 38
  dpo_days: 32
  dio_days: 95
opening_balances:
  cash: 350000
  ar: 520000
  ap: 410000
  inventory: 1100000
  nol: 0
```

- [ ] **Step 2: Write the failing test (append to `tests/test_loader.py`)**

```python
# --- append to tests/test_loader.py ---
from pathlib import Path
from pyfpa.config.loader import load_config

REPO_ROOT = Path(__file__).resolve().parents[1]


def test_load_ridgeline_config():
    cfg = load_config(REPO_ROOT / "examples/ridgeline/config.yaml")
    assert cfg.name == "Ridgeline Chair Co."
    assert len(cfg.channels) == 3
    assert cfg.horizon_months == 12


def test_load_missing_file_raises():
    with pytest.raises(FileNotFoundError):
        load_config(REPO_ROOT / "examples/does_not_exist.yaml")
```

- [ ] **Step 3: Run test to verify it fails**

Run: `.venv/bin/pytest tests/test_loader.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'pyfpa.config.loader'`

- [ ] **Step 4: Write minimal implementation**

```python
# pyfpa/config/loader.py
from __future__ import annotations

from pathlib import Path

import yaml

from pyfpa.config.schemas import EntityConfig


def load_config(path: str | Path) -> EntityConfig:
    """Load and validate an EntityConfig from a YAML file."""
    p = Path(path)
    if not p.exists():
        raise FileNotFoundError(f"config not found: {p}")
    with p.open() as f:
        raw = yaml.safe_load(f)
    return EntityConfig.model_validate(raw)
```

- [ ] **Step 5: Run test to verify it passes**

Run: `.venv/bin/pytest tests/test_loader.py -v`
Expected: PASS (6 passed)

- [ ] **Step 6: Commit**

```bash
git add pyfpa/config/loader.py tests/test_loader.py examples/ridgeline/config.yaml
git commit -m "feat: add YAML config loader and ridgeline fixture"
```

---

## Task 4: Shared test fixture

**Files:**
- Create: `tests/conftest.py`

This fixture uses deliberately simple, hand-computable numbers so every downstream test asserts exact values. With flat seasonality `[1]*12`, `annual_revenue=1200` distributes to **100/month**; `cogs_pct=0.5` → **50/month COGS**; fixed opex **100/month**; term loan opening **1200** at **12%/yr = 1%/mo**; `tax_rate=0.0` so net income equals pre-tax income.

- [ ] **Step 1: Create the fixture**

```python
# tests/conftest.py
import pytest

from pyfpa.config.schemas import (
    Channel, DebtInstrument, EntityConfig, OpeningBalances, OpexLine,
    WorkingCapitalConfig,
)


@pytest.fixture
def sample_config() -> EntityConfig:
    return EntityConfig(
        name="Test Co",
        start_month="2026-01",
        horizon_months=12,
        tax_rate=0.0,
        channels=[
            Channel(name="D2C", annual_revenue=1200.0, growth_rate=0.0,
                    seasonality=[1.0] * 12, cogs_pct=0.5),
        ],
        opex=[OpexLine(name="Rent", kind="fixed", monthly_amount=100.0)],
        debt=[DebtInstrument(name="Term", kind="term_loan", opening_balance=1200.0,
                             annual_rate=0.12, monthly_principal=100.0)],
        working_capital=WorkingCapitalConfig(dso_days=30, dpo_days=30, dio_days=0),
        opening_balances=OpeningBalances(cash=500.0, ar=0.0, ap=0.0, inventory=0.0),
    )
```

- [ ] **Step 2: Verify fixture imports cleanly**

Run: `.venv/bin/pytest tests/ -q`
Expected: PASS (existing tests still pass; no new tests yet — 6 passed)

- [ ] **Step 3: Commit**

```bash
git add tests/conftest.py
git commit -m "test: add hand-computable sample_config fixture"
```

---

## Task 5: Revenue model

**Files:**
- Create: `pyfpa/models/revenue.py`
- Test: `tests/test_revenue.py`

- [ ] **Step 1: Write the failing test**

```python
# tests/test_revenue.py
import pandas as pd
from pyfpa.models.revenue import revenue_from_config


def test_revenue_flat_seasonality(sample_config):
    df = revenue_from_config(sample_config)
    assert len(df) == 12
    assert list(df.columns) == ["D2C", "total"]
    # 1200 / 12 = 100 per month with flat seasonality
    assert df["D2C"].round(6).tolist() == [100.0] * 12
    assert df["total"].sum().round(6) == 1200.0


def test_revenue_growth_compounds_in_year_two():
    from pyfpa.config.schemas import (Channel, EntityConfig, WorkingCapitalConfig)
    cfg = EntityConfig(
        name="G", start_month="2026-01", horizon_months=24,
        channels=[Channel(name="C", annual_revenue=1200.0, growth_rate=0.10,
                          seasonality=[1.0] * 12, cogs_pct=0.5)],
        working_capital=WorkingCapitalConfig(dso_days=0, dpo_days=0, dio_days=0),
    )
    df = revenue_from_config(cfg)
    # year 1 month = 100; year 2 month = 100 * 1.10 = 110
    assert round(df["C"].iloc[0], 6) == 100.0
    assert round(df["C"].iloc[12], 6) == 110.0
```

- [ ] **Step 2: Run test to verify it fails**

Run: `.venv/bin/pytest tests/test_revenue.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'pyfpa.models.revenue'`

- [ ] **Step 3: Write minimal implementation**

```python
# pyfpa/models/revenue.py
from __future__ import annotations

import pandas as pd

from pyfpa.config.schemas import EntityConfig
from pyfpa.models.periods import month_index


def revenue_from_config(cfg: EntityConfig) -> pd.DataFrame:
    """Monthly revenue per channel + total. Seasonality is by calendar month;
    growth compounds per forecast year (every 12 months from start)."""
    idx = month_index(cfg.start_month, cfg.horizon_months)
    data: dict[str, list[float]] = {}
    for ch in cfg.channels:
        total_w = sum(ch.seasonality)
        norm = [w / total_w for w in ch.seasonality]
        series = []
        for i, period in enumerate(idx):
            year_offset = i // 12
            month_pos = period.month - 1
            growth = (1.0 + ch.growth_rate) ** year_offset
            series.append(ch.annual_revenue * norm[month_pos] * growth)
        data[ch.name] = series
    df = pd.DataFrame(data, index=idx)
    return df.assign(total=df.sum(axis=1))
```

- [ ] **Step 4: Run test to verify it passes**

Run: `.venv/bin/pytest tests/test_revenue.py -v`
Expected: PASS (2 passed)

- [ ] **Step 5: Commit**

```bash
git add pyfpa/models/revenue.py tests/test_revenue.py
git commit -m "feat: add revenue model"
```

---

## Task 6: COGS model

**Files:**
- Create: `pyfpa/models/cogs.py`
- Test: `tests/test_cogs.py`

- [ ] **Step 1: Write the failing test**

```python
# tests/test_cogs.py
from pyfpa.models.revenue import revenue_from_config
from pyfpa.models.cogs import cogs_from_config


def test_cogs_applies_per_channel_pct(sample_config):
    rev = revenue_from_config(sample_config)
    df = cogs_from_config(sample_config, rev)
    assert list(df.columns) == ["D2C", "total"]
    # 100 revenue * 0.5 = 50 per month
    assert df["D2C"].round(6).tolist() == [50.0] * 12
    assert df["total"].round(6).tolist() == [50.0] * 12
```

- [ ] **Step 2: Run test to verify it fails**

Run: `.venv/bin/pytest tests/test_cogs.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'pyfpa.models.cogs'`

- [ ] **Step 3: Write minimal implementation**

```python
# pyfpa/models/cogs.py
from __future__ import annotations

import pandas as pd

from pyfpa.config.schemas import EntityConfig


def cogs_from_config(cfg: EntityConfig, revenue_df: pd.DataFrame) -> pd.DataFrame:
    """Monthly COGS per channel (revenue * cogs_pct) + total."""
    data = {ch.name: revenue_df[ch.name] * ch.cogs_pct for ch in cfg.channels}
    df = pd.DataFrame(data, index=revenue_df.index)
    return df.assign(total=df.sum(axis=1))
```

- [ ] **Step 4: Run test to verify it passes**

Run: `.venv/bin/pytest tests/test_cogs.py -v`
Expected: PASS (1 passed)

- [ ] **Step 5: Commit**

```bash
git add pyfpa/models/cogs.py tests/test_cogs.py
git commit -m "feat: add cogs model"
```

---

## Task 7: OpEx model

**Files:**
- Create: `pyfpa/models/opex.py`
- Test: `tests/test_opex.py`

- [ ] **Step 1: Write the failing test**

```python
# tests/test_opex.py
from pyfpa.config.schemas import (Channel, EntityConfig, OpexLine,
                                  WorkingCapitalConfig)
from pyfpa.models.revenue import revenue_from_config
from pyfpa.models.opex import opex_from_config


def test_fixed_opex_constant(sample_config):
    rev = revenue_from_config(sample_config)
    df = opex_from_config(sample_config, rev)
    assert df["Rent"].round(6).tolist() == [100.0] * 12
    assert df["total"].round(6).tolist() == [100.0] * 12


def test_variable_opex_scales_with_revenue():
    cfg = EntityConfig(
        name="V", start_month="2026-01",
        channels=[Channel(name="C", annual_revenue=1200.0,
                          seasonality=[1.0] * 12, cogs_pct=0.5)],
        opex=[OpexLine(name="Ads", kind="variable", pct_of_revenue=0.10)],
        working_capital=WorkingCapitalConfig(dso_days=0, dpo_days=0, dio_days=0),
    )
    rev = revenue_from_config(cfg)
    df = opex_from_config(cfg, rev)
    # 100 revenue * 0.10 = 10 per month
    assert df["Ads"].round(6).tolist() == [10.0] * 12
```

- [ ] **Step 2: Run test to verify it fails**

Run: `.venv/bin/pytest tests/test_opex.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'pyfpa.models.opex'`

- [ ] **Step 3: Write minimal implementation**

```python
# pyfpa/models/opex.py
from __future__ import annotations

import pandas as pd

from pyfpa.config.schemas import EntityConfig


def opex_from_config(cfg: EntityConfig, revenue_df: pd.DataFrame) -> pd.DataFrame:
    """Monthly opex per line + total. Fixed lines are constant; variable lines
    scale with total revenue."""
    idx = revenue_df.index
    cols: dict[str, pd.Series] = {}
    for line in cfg.opex:
        if line.kind == "fixed":
            cols[line.name] = pd.Series(line.monthly_amount, index=idx, dtype="float64")
        else:  # variable
            cols[line.name] = revenue_df["total"] * line.pct_of_revenue
    df = pd.DataFrame(cols, index=idx)
    if df.empty:
        df = pd.DataFrame(index=idx)
    return df.assign(total=df.sum(axis=1))
```

- [ ] **Step 4: Run test to verify it passes**

Run: `.venv/bin/pytest tests/test_opex.py -v`
Expected: PASS (2 passed)

- [ ] **Step 5: Commit**

```bash
git add pyfpa/models/opex.py tests/test_opex.py
git commit -m "feat: add opex model"
```

---

## Task 8: Working capital model

**Files:**
- Create: `pyfpa/models/working_capital.py`
- Test: `tests/test_working_capital.py`

Balances use a 30-day month convention: `AR = revenue * dso/30`, `AP = cogs * dpo/30`, `inventory = cogs * dio/30`. Period-over-period deltas drive cash: rising AR or inventory **uses** cash; rising AP **frees** cash. First-period delta is measured against opening balances.

- [ ] **Step 1: Write the failing test**

```python
# tests/test_working_capital.py
from pyfpa.models.revenue import revenue_from_config
from pyfpa.models.cogs import cogs_from_config
from pyfpa.models.working_capital import working_capital_from_config


def test_working_capital_balances_and_cash_impact(sample_config):
    rev = revenue_from_config(sample_config)
    cogs = cogs_from_config(sample_config, rev)
    df = working_capital_from_config(sample_config, rev, cogs)

    # dso=30 -> AR = revenue(100) * 30/30 = 100 every month
    assert df["ar"].round(6).tolist() == [100.0] * 12
    # dpo=30 -> AP = cogs(50) * 30/30 = 50 every month
    assert df["ap"].round(6).tolist() == [50.0] * 12
    # dio=0 -> inventory 0
    assert df["inventory"].round(6).tolist() == [0.0] * 12

    # Month 1 deltas vs opening (all opening = 0): d_ar=100, d_ap=50, d_inv=0
    assert round(df["d_ar"].iloc[0], 6) == 100.0
    assert round(df["d_ap"].iloc[0], 6) == 50.0
    # cash impact month 1 = -100 + 50 - 0 = -50
    assert round(df["wc_cash_impact"].iloc[0], 6) == -50.0
    # month 2 balances flat -> deltas 0 -> cash impact 0
    assert round(df["wc_cash_impact"].iloc[1], 6) == 0.0
```

- [ ] **Step 2: Run test to verify it fails**

Run: `.venv/bin/pytest tests/test_working_capital.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'pyfpa.models.working_capital'`

- [ ] **Step 3: Write minimal implementation**

```python
# pyfpa/models/working_capital.py
from __future__ import annotations

import pandas as pd

from pyfpa.config.schemas import EntityConfig

_DAYS_PER_MONTH = 30.0


def working_capital_from_config(
    cfg: EntityConfig, revenue_df: pd.DataFrame, cogs_df: pd.DataFrame
) -> pd.DataFrame:
    """AR/AP/inventory balances and their cash impact (rising AR/inventory uses
    cash; rising AP frees cash). First-period delta is vs opening balances."""
    idx = revenue_df.index
    wc = cfg.working_capital
    ob = cfg.opening_balances

    ar = revenue_df["total"] * (wc.dso_days / _DAYS_PER_MONTH)
    ap = cogs_df["total"] * (wc.dpo_days / _DAYS_PER_MONTH)
    inventory = cogs_df["total"] * (wc.dio_days / _DAYS_PER_MONTH)

    df = pd.DataFrame({"ar": ar, "ap": ap, "inventory": inventory}, index=idx)
    df = df.assign(
        d_ar=df["ar"].diff().fillna(df["ar"] - ob.ar),
        d_ap=df["ap"].diff().fillna(df["ap"] - ob.ap),
        d_inventory=df["inventory"].diff().fillna(df["inventory"] - ob.inventory),
    )
    return df.assign(
        wc_cash_impact=(-df["d_ar"] + df["d_ap"] - df["d_inventory"])
    )
```

- [ ] **Step 4: Run test to verify it passes**

Run: `.venv/bin/pytest tests/test_working_capital.py -v`
Expected: PASS (1 passed)

- [ ] **Step 5: Commit**

```bash
git add pyfpa/models/working_capital.py tests/test_working_capital.py
git commit -m "feat: add working capital model"
```

---

## Task 9: Debt model

**Files:**
- Create: `pyfpa/models/debt.py`
- Test: `tests/test_debt.py`

Interest accrues monthly on the opening balance for that month (`annual_rate / 12`). Term loans amortize by `monthly_principal` (capped at the remaining balance); LOC carries interest only (no scheduled principal in the core engine — draws/repays are a cash13 concern, Plan 2).

- [ ] **Step 1: Write the failing test**

```python
# tests/test_debt.py
from pyfpa.models.debt import debt_from_config


def test_term_loan_amortization(sample_config):
    df = debt_from_config(sample_config)
    assert list(df.columns) == ["interest", "principal", "ending_debt"]
    # opening 1200 @ 1%/mo: month1 interest 12, principal 100, ending 1100
    assert round(df["interest"].iloc[0], 6) == 12.0
    assert round(df["principal"].iloc[0], 6) == 100.0
    assert round(df["ending_debt"].iloc[0], 6) == 1100.0
    # month2: interest 1100*1% = 11, ending 1000
    assert round(df["interest"].iloc[1], 6) == 11.0
    assert round(df["ending_debt"].iloc[1], 6) == 1000.0


def test_loc_is_interest_only():
    from pyfpa.config.schemas import (DebtInstrument, EntityConfig, Channel,
                                      WorkingCapitalConfig)
    cfg = EntityConfig(
        name="L", start_month="2026-01", horizon_months=3,
        channels=[Channel(name="C", annual_revenue=12.0,
                          seasonality=[1.0] * 12, cogs_pct=0.5)],
        debt=[DebtInstrument(name="LOC", kind="loc", opening_balance=1000.0,
                             annual_rate=0.12)],
        working_capital=WorkingCapitalConfig(dso_days=0, dpo_days=0, dio_days=0),
    )
    df = debt_from_config(cfg)
    assert df["principal"].round(6).tolist() == [0.0, 0.0, 0.0]
    assert df["ending_debt"].round(6).tolist() == [1000.0, 1000.0, 1000.0]
    assert round(df["interest"].iloc[0], 6) == 10.0  # 1000 * 1%
```

- [ ] **Step 2: Run test to verify it fails**

Run: `.venv/bin/pytest tests/test_debt.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'pyfpa.models.debt'`

- [ ] **Step 3: Write minimal implementation**

```python
# pyfpa/models/debt.py
from __future__ import annotations

import pandas as pd

from pyfpa.config.schemas import EntityConfig
from pyfpa.models.periods import month_index


def debt_from_config(cfg: EntityConfig) -> pd.DataFrame:
    """Monthly interest, principal, and ending balance summed across all
    instruments. Term loans amortize by monthly_principal; LOCs are interest-only."""
    idx = month_index(cfg.start_month, cfg.horizon_months)
    interest = pd.Series(0.0, index=idx)
    principal = pd.Series(0.0, index=idx)
    ending = pd.Series(0.0, index=idx)

    for inst in cfg.debt:
        balance = inst.opening_balance
        monthly_rate = inst.annual_rate / 12.0
        for period in idx:
            month_interest = balance * monthly_rate
            month_principal = (
                min(inst.monthly_principal, balance) if inst.kind == "term_loan" else 0.0
            )
            balance -= month_principal
            interest[period] += month_interest
            principal[period] += month_principal
            ending[period] += balance

    return pd.DataFrame(
        {"interest": interest, "principal": principal, "ending_debt": ending}, index=idx
    )
```

- [ ] **Step 4: Run test to verify it passes**

Run: `.venv/bin/pytest tests/test_debt.py -v`
Expected: PASS (2 passed)

- [ ] **Step 5: Commit**

```bash
git add pyfpa/models/debt.py tests/test_debt.py
git commit -m "feat: add debt model"
```

---

## Task 10: Cash flow assembler

**Files:**
- Create: `pyfpa/models/cashflow.py`
- Test: `tests/test_cashflow.py`

Assembles the full forecast. EBITDA ≈ EBIT in this lean model (no D&A line). Tax applies `tax_rate` to taxable income after consuming any NOL carryforward against positive pre-tax income. Cash flow is indirect: `change_in_cash = net_income + wc_cash_impact - principal`; `ending_cash` cumulates from opening cash.

Hand-computed expectations for `sample_config` (tax_rate=0): per month EBITDA = GP(50) - opex(100) = -50. Month 1: interest 12 → pretax -62 → NI -62; wc_cash_impact -50; principal 100 → change_in_cash = -62 -50 -100 = -212; ending_cash = 500 - 212 = 288. Month 2: interest 11 → pretax -61 → NI -61; wc impact 0; principal 100 → change = -161; ending = 288 - 161 = 127.

- [ ] **Step 1: Write the failing test**

```python
# tests/test_cashflow.py
from pyfpa.models.cashflow import cashflow_from_config


def test_cashflow_full_forecast(sample_config):
    df = cashflow_from_config(sample_config)
    assert len(df) == 12
    for col in ["revenue", "cogs", "gross_profit", "opex", "ebitda", "interest",
                "pretax_income", "tax", "net_income", "wc_cash_impact",
                "principal", "change_in_cash", "ending_cash"]:
        assert col in df.columns

    assert round(df["gross_profit"].iloc[0], 6) == 50.0
    assert round(df["ebitda"].iloc[0], 6) == -50.0
    assert round(df["pretax_income"].iloc[0], 6) == -62.0
    assert round(df["net_income"].iloc[0], 6) == -62.0
    assert round(df["change_in_cash"].iloc[0], 6) == -212.0
    assert round(df["ending_cash"].iloc[0], 6) == 288.0
    assert round(df["ending_cash"].iloc[1], 6) == 127.0


def test_nol_shelters_tax():
    from pyfpa.config.schemas import (Channel, EntityConfig, OpeningBalances,
                                      WorkingCapitalConfig)
    cfg = EntityConfig(
        name="P", start_month="2026-01", horizon_months=12, tax_rate=0.25,
        channels=[Channel(name="C", annual_revenue=2400.0,
                          seasonality=[1.0] * 12, cogs_pct=0.0)],
        working_capital=WorkingCapitalConfig(dso_days=0, dpo_days=0, dio_days=0),
        opening_balances=OpeningBalances(nol=100.0),
    )
    df = cashflow_from_config(cfg)
    # Month 1 pretax = 200 (rev 200, no cogs/opex/interest). NOL 100 shelters
    # 100 -> taxable 100 -> tax 25.
    assert round(df["pretax_income"].iloc[0], 6) == 200.0
    assert round(df["tax"].iloc[0], 6) == 25.0
    # Month 2: NOL exhausted -> taxable 200 -> tax 50.
    assert round(df["tax"].iloc[1], 6) == 50.0


def test_ridgeline_config_runs_end_to_end():
    from pathlib import Path
    from pyfpa.config.loader import load_config
    repo_root = Path(__file__).resolve().parents[1]
    cfg = load_config(repo_root / "examples/ridgeline/config.yaml")
    df = cashflow_from_config(cfg)
    assert len(df) == 12
    assert df["ending_cash"].notna().all()
    assert df["revenue"].iloc[0] > 0
```

- [ ] **Step 2: Run test to verify it fails**

Run: `.venv/bin/pytest tests/test_cashflow.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'pyfpa.models.cashflow'`

- [ ] **Step 3: Write minimal implementation**

```python
# pyfpa/models/cashflow.py
from __future__ import annotations

import pandas as pd

from pyfpa.config.schemas import EntityConfig
from pyfpa.models.cogs import cogs_from_config
from pyfpa.models.debt import debt_from_config
from pyfpa.models.opex import opex_from_config
from pyfpa.models.revenue import revenue_from_config
from pyfpa.models.working_capital import working_capital_from_config


def _tax_series(pretax: pd.Series, opening_nol: float, tax_rate: float) -> pd.Series:
    """Apply tax_rate to positive pre-tax income after consuming NOL carryforward."""
    nol = opening_nol
    out = []
    for value in pretax:
        positive = max(0.0, value)
        used = min(nol, positive)
        nol -= used
        taxable = positive - used
        out.append(taxable * tax_rate)
    return pd.Series(out, index=pretax.index)


def cashflow_from_config(cfg: EntityConfig) -> pd.DataFrame:
    """Compose all model layers into the full monthly forecast (P&L + cash)."""
    revenue = revenue_from_config(cfg)
    cogs = cogs_from_config(cfg, revenue)
    opex = opex_from_config(cfg, revenue)
    wc = working_capital_from_config(cfg, revenue, cogs)
    debt = debt_from_config(cfg)

    gross_profit = revenue["total"] - cogs["total"]
    ebitda = gross_profit - opex["total"]
    interest = debt["interest"]
    pretax = ebitda - interest
    tax = _tax_series(pretax, cfg.opening_balances.nol, cfg.tax_rate)
    net_income = pretax - tax

    change_in_cash = net_income + wc["wc_cash_impact"] - debt["principal"]
    ending_cash = change_in_cash.cumsum() + cfg.opening_balances.cash

    return pd.DataFrame(
        {
            "revenue": revenue["total"],
            "cogs": cogs["total"],
            "gross_profit": gross_profit,
            "opex": opex["total"],
            "ebitda": ebitda,
            "interest": interest,
            "pretax_income": pretax,
            "tax": tax,
            "net_income": net_income,
            "wc_cash_impact": wc["wc_cash_impact"],
            "principal": debt["principal"],
            "change_in_cash": change_in_cash,
            "ending_cash": ending_cash,
        },
        index=revenue.index,
    )
```

- [ ] **Step 4: Run test to verify it passes**

Run: `.venv/bin/pytest tests/test_cashflow.py -v`
Expected: PASS (3 passed)

- [ ] **Step 5: Commit**

```bash
git add pyfpa/models/cashflow.py tests/test_cashflow.py
git commit -m "feat: add cash flow assembler"
```

---

## Task 11: Public API surface

**Files:**
- Modify: `pyfpa/__init__.py`
- Test: `tests/test_public_api.py`

- [ ] **Step 1: Write the failing test**

```python
# tests/test_public_api.py
import pyfpa


def test_public_api_exports():
    for name in [
        "EntityConfig", "Channel", "OpexLine", "DebtInstrument",
        "WorkingCapitalConfig", "OpeningBalances", "load_config",
        "revenue_from_config", "cogs_from_config", "opex_from_config",
        "working_capital_from_config", "debt_from_config", "cashflow_from_config",
    ]:
        assert hasattr(pyfpa, name), f"missing public export: {name}"


def test_top_level_smoke():
    from pathlib import Path
    repo_root = Path(__file__).resolve().parents[1]
    cfg = pyfpa.load_config(repo_root / "examples/ridgeline/config.yaml")
    df = pyfpa.cashflow_from_config(cfg)
    assert len(df) == 12
```

- [ ] **Step 2: Run test to verify it fails**

Run: `.venv/bin/pytest tests/test_public_api.py -v`
Expected: FAIL with `AttributeError: module 'pyfpa' has no attribute 'EntityConfig'`

- [ ] **Step 3: Write the implementation**

```python
# pyfpa/__init__.py
from pyfpa.config.loader import load_config
from pyfpa.config.schemas import (
    Channel, DebtInstrument, EntityConfig, OpeningBalances, OpexLine,
    WorkingCapitalConfig,
)
from pyfpa.models.cashflow import cashflow_from_config
from pyfpa.models.cogs import cogs_from_config
from pyfpa.models.debt import debt_from_config
from pyfpa.models.opex import opex_from_config
from pyfpa.models.revenue import revenue_from_config
from pyfpa.models.working_capital import working_capital_from_config

__all__ = [
    "EntityConfig", "Channel", "OpexLine", "DebtInstrument",
    "WorkingCapitalConfig", "OpeningBalances", "load_config",
    "revenue_from_config", "cogs_from_config", "opex_from_config",
    "working_capital_from_config", "debt_from_config", "cashflow_from_config",
]
```

- [ ] **Step 4: Run test to verify it passes**

Run: `.venv/bin/pytest tests/test_public_api.py -v`
Expected: PASS (2 passed)

- [ ] **Step 5: Run the full suite**

Run: `.venv/bin/pytest -q`
Expected: PASS (all tests green — 18+ passed)

- [ ] **Step 6: Commit**

```bash
git add pyfpa/__init__.py tests/test_public_api.py
git commit -m "feat: expose public pyfpa API"
```

---

## Definition of Done

- [ ] `.venv/bin/pytest -q` is fully green.
- [ ] `python -c "import pyfpa; print(pyfpa.cashflow_from_config(pyfpa.load_config('examples/ridgeline/config.yaml')).round(0))"` prints a 12-row forecast.
- [ ] Every model layer is a pure `*_from_config` function with no file I/O (only `loader.py` touches disk).
- [ ] No DataFrame is mutated in place (all derived columns via `.assign`).

---

## Notes for Plans 2–4 (not in scope here)

- **Plan 2:** `pyfpa/cash13/` (13-week direct method) + `pyfpa/io/` (CSV/XLSX in, Excel/briefing-md out, adapter stubs). cash13 reconciles to this monthly engine within tolerance.
- **Plan 3:** full Ridgeline demo dataset (QuickBooks-style export CSV) + golden-output snapshot test.
- **Plan 4:** the 7 skills, `.claude-plugin/plugin.json`, README, MIT LICENSE, launch blog post.
