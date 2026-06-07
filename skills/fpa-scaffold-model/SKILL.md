---
name: fpa-scaffold-model
description: Use when building a new openfpa forecast model from a company's financials — a trial balance, a P&L export, or a pasted income statement — and you need a runnable config to exist before any forecasting or analysis.
---

# Scaffold a Model (Phase 1)

## Overview

Turn a company's financials into a runnable `pyfpa` config. Read the business profile first (see **fpa-learn-business**), infer the chart-of-accounts → model-line mapping, and write a validated `EntityConfig` YAML following openfpa conventions. Output a runnable skeleton plus an explicit list of assumptions to confirm.

**Core principle:** Convention over invention. Map the real numbers onto the existing engine shape; don't design a new one.

## When to use

- A trial balance / P&L (CSV, XLSX, or pasted) needs to become a forecast model
- Onboarding follow-on after `.fpa/business-profile.md` exists

## Workflow

1. **Ingest** the financials: `pyfpa.read_pl_csv(path)` (or a `pyfpa.io.adapters` source) → `{account: amount}`.
2. **Map accounts to model lines** of the `EntityConfig` schema:
   - revenue accounts → `channels[]` (one `Channel` per channel/segment, with `annual_revenue`, a 12-month `seasonality` weight list, `growth_rate`, `cogs_pct`)
   - cost accounts → `opex[]` as `OpexLine(kind="fixed", monthly_amount=…)` or `kind="variable", pct_of_revenue=…`
   - debt → `debt[]` (`term_loan` with `monthly_principal`, or interest-only `loc`)
   - balance-sheet rhythm → `working_capital(dso_days, dpo_days, dio_days)` and `opening_balances`
3. **Write** `config.yaml` (validate by loading it: `pyfpa.load_config(path)` raises on any bad field).
4. **Run it**: `pyfpa.cashflow_from_config(cfg)` → a 12-month P&L + cash flow. Confirm it executes.
5. **Surface assumptions**: list the 6–10 inferences a human must confirm (seasonality shape, fixed vs variable splits, cogs_pct per channel, opening balances). Don't bury them.

## Conventions (match the engine)

- YAML is the source of truth; never hardcode numbers in code.
- Set `opening_balances` AR/AP/inventory to the DSO/DPO/DIO-implied steady state (see **fpa-cfo-judgment** working-capital seam), or the month-1 cash will swing on an artifact.
- `"total"` is a reserved channel/opex name (the engine adds a `total` column).

## Next

Runnable config confirmed → **fpa-configure-actuals** to wire live/real numbers, then the operate skills.
