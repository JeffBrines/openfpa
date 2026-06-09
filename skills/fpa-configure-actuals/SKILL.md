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
- **A live system via API** — build a company-specific connector around the
  source API and its actual report shape. The functions in `pyfpa.io.adapters`
  are fixture-backed examples only, not live QuickBooks, NetSuite, or Shopify
  clients.
- **Public filings** — a 10-K / 10-Q from SEC EDGAR (curl + a compliant User-Agent), as in the Fox Factory example.
- **Anything else** — if the source isn't covered, write a small ingestion that returns `{account: amount}` (or parses the richer statement to the drivers the model needs). That is the toolkit working exactly as intended.

## Workflow

1. **Discover existing access.** Run
   `openfpa entrypoint-list <company-root> --kind connector`. Reuse a tested
   company connector when one exists.
2. **Pull** actuals via whatever path fits the source.
3. **Profile the source.** Run
   `openfpa source-profile <company-root> --file <source-file>` for supported
   local tables. Inspect the columns, empty values, and duplicate rows.
4. **Register the source.** Use `openfpa source-register` with a stable source
   ID, entity, currency, period coverage, extraction method, and location.
5. **Map** source accounts onto the company model with
   `openfpa mapping-register`. Register deliberate ignores with `--status
   ignored` and a rationale. Review with `openfpa mapping-list`.
6. **Reconcile** compatible account-amount CSV files with
   `openfpa reconcile-source`. Flag duplicate and unmapped accounts; never
   silently drop or overwrite them. For richer tables, build a tested
   company-specific reconciliation that provides equivalent evidence.
7. **Register recurring access.** If you built a repeatable connector command,
   first run `openfpa connector-list`. Scaffold a bundle with
   `openfpa connector-scaffold` from an explicitly redacted CSV fixture. Edit
   the generated `extract_live()` path, keep credentials in the host, and run
   `openfpa connector-validate` after every change. Fixture validation must
   remain offline. Once the live command has separate fixture-backed coverage,
   publish it with `openfpa entrypoint-register --kind connector`.
8. **Judgment**: apply **fpa-cfo-judgment** (pre-close months, flash-vs-GL cash, one-time items).

## Credentials

Never commit secrets. Live API credentials come from the host environment; MCP servers own their own auth. openfpa ships only synthetic fixtures.

## Next

Actuals wired → operate: **fpa-monthly-close**, **fpa-cash-runway**, **fpa-board-briefing**.
