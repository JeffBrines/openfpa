---
name: fpa-configure-actuals
description: Use when wiring a company's real numbers into an openfpa model — mapping a spreadsheet/CSV export into actuals, or connecting a live data source (NetSuite, QuickBooks, Shopify) — after a model config exists.
---

# Configure Actuals & Data Sources (Phase 2)

## Overview

Connect the model to real data. Two paths: an **offline** spreadsheet/CSV mapping, or a **live** source adapter. Either way you produce a normalized `{account: amount}` and reconcile it against the model's expected lines.

**Core principle:** One normalized shape (`{account: amount}`) regardless of source, so the rest of the toolkit doesn't care where numbers came from.

## When to use

- Replacing scaffolded estimates with the company's actual numbers
- "Connect my QuickBooks / NetSuite / Shopify" requests
- Standing up the monthly refresh

## Paths

**Offline (always works, no credentials):**
```python
from pyfpa import read_pl_csv
actuals = read_pl_csv("path/to/export.csv")   # {account: amount}
```
Handles `$`, thousands commas, and `(parens)` negatives. Two columns: `Account`, `Amount`.

**Live source adapters:**
```python
from pyfpa.io import adapters
gl = adapters.from_netsuite()      # SuiteQL / OAuth 1.0a
gl = adapters.from_quickbooks()    # QuickBooks Online API
ops = adapters.from_shopify()      # Shopify Admin API (D2C ops, not a full GL)
```
Each returns `{account: amount}`. **Without credentials they read bundled synthetic fixtures** — set real credentials in the host environment to go live (see each adapter's docstring). Credentials are never committed.

## Workflow

1. Pull actuals via the chosen path.
2. Map source accounts onto the model's channels/opex lines (reuse the mapping from **fpa-scaffold-model**).
3. **Reconcile**: do the source totals match what the model expects? Flag unmapped accounts rather than silently dropping them.
4. Apply the judgment checks from **fpa-cfo-judgment** — especially pre-close months and flash-vs-GL cash.

## Next

Actuals wired → operate: **fpa-monthly-close**, **fpa-cash-runway**, **fpa-board-briefing**.
