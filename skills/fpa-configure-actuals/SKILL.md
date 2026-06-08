---
name: fpa-configure-actuals
description: Use when wiring a company's real numbers into an openfpa model — from local spreadsheets (P&L, balance sheet, AR/AP aging, inventory), a live system via MCP or API (QuickBooks, NetSuite), public filings (10-K/10-Q), or anything else. Not married to one source — build the ingestion for whatever the company has; produces one normalized account-amount shape the rest of the toolkit reads.
---

# Configure Actuals & Data Sources (Phase 2)

## Overview

Connect the model to real data — from wherever it lives. openfpa is **not married to a connector**: everything normalizes to one shape (`{account: amount}`), and where no built-in path exists, **you build the ingestion for this source**. That's the job, not a workaround — see `examples/foxfactory/pull_edgar.py`, a SEC-EDGAR adapter the agent wrote from scratch because no built-in one existed.

**Core principle:** one normalized shape regardless of source, so the engine never cares where the numbers came from — and the agent meets the data where it is.

## The data can come from anywhere

- **Local spreadsheets** (always works, no credentials). A P&L, balance sheet, AR/AP aging, or inventory export. `pyfpa.read_pl_csv(path)` reads any two-column `Account, Amount` CSV (handles `$`, commas, `(parens)` negatives) → `{account: amount}` — it is generic, not P&L-only. For **richer tables** (aged AR/AP buckets, item-level inventory) there is no rigid reader by design: parse the file to what the model needs — derive **DSO** from AR aging, **DIO** from inventory, **DPO** from AP aging.
- **A live accounting system via MCP** — the cleanest live path. If a **QuickBooks** or **NetSuite** MCP server is connected, pull the trial balance / P&L / balance sheet through it and map the result to `{account: amount}`. openfpa never handles credentials — the MCP server owns auth.
- **A live system via API** — `pyfpa.io.adapters.from_quickbooks()` / `from_netsuite()` / `from_shopify()` are starting points (fixture-backed; each docstring documents the live SuiteQL/OAuth or QuickBooks Online / Shopify Admin call). Flesh out the live call when you go that route.
- **Public filings** — a 10-K / 10-Q from SEC EDGAR (curl + a compliant User-Agent), as in the Fox Factory example.
- **Anything else** — if the source isn't covered, write a small ingestion that returns `{account: amount}` (or parses the richer statement to the drivers the model needs). That is the toolkit working exactly as intended.

## Workflow

1. **Pull** actuals via whatever path fits the source.
2. **Map** source accounts onto the model's channels / opex / working-capital lines (reuse the mapping from **fpa-scaffold-model**).
3. **Reconcile** — do source totals match what the model expects? Flag unmapped accounts; never silently drop them.
4. **Judgment** — apply **fpa-cfo-judgment** (pre-close months, flash-vs-GL cash, one-time items).

## Credentials

Never commit secrets. Live API credentials come from the host environment; MCP servers own their own auth. openfpa ships only synthetic fixtures.

## Next

Actuals wired → operate: **fpa-monthly-close**, **fpa-cash-runway**, **fpa-board-briefing**.
