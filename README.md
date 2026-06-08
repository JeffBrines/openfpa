# openfpa

[![CI](https://github.com/JeffBrines/openfpa/actions/workflows/ci.yml/badge.svg)](https://github.com/JeffBrines/openfpa/actions/workflows/ci.yml)

**An AI-native FP&A toolkit.** Point an AI coding agent (Claude Code, Claude Cowork, Codex) at your numbers and it builds a working financial model — a 12-month P&L and cash-flow forecast, a 13-week cash runway, and a board-ready briefing.

`openfpa` is a deliberately **lean Python forecast engine** plus a **progressive Claude skillset** that encodes the methodology and judgment of a real finance team. The engine is small on purpose: it's the substrate an AI extends per-business, not an off-the-shelf app you configure by hand.

> Built by [Guiderail](https://guiderail.example). Open-source under MIT. The demo runs on synthetic data — no credentials required — and a second worked example validates the engine against a **real public company** (Fox Factory, NASDAQ: FOXF) straight from its SEC filings.

---

## Mission

Bring real FP&A to anyone with a spreadsheet — without the cost or the implementation project of Datarails, Cube, or Vena.

Those tools hand you connectors and a modeling layer, then leave the thinking to you. openfpa flips that: **connect your data — or just point it at your spreadsheets — and let the AI do the thinking.** It asks the questions a good CFO would, builds the model, surfaces what matters, and sharpens itself against your actuals every close.

Two things underneath, rarely combined:

- **Hundreds of hours of real FP&A engineering** — methodology distilled from production CFO work (a trucking fleet, a bicycle company, and more), not textbook finance.
- **A self-improving loop, inspired by [Karpathy's AutoResearch](https://github.com/karpathy/autoresearch)** — it scores itself against *your* actuals, aiming to get better over time. AutoResearch optimizes against validation loss; openfpa optimizes against reconciliation error on your own books.

Self-hosted, auditable, yours — what it learns lives as plain files in your repo, not someone else's cloud. An open-source experiment from [Guiderail](https://guiderail.example); we'd love your help making it the FP&A tool we all wish existed.

---

## Why not just point Claude at your books?

Fair question — Claude *can* write financial code from scratch. But every run is a one-off: ad-hoc pandas, no shared structure, no test, no audit trail. Correctness by luck-of-the-run. openfpa makes correctness a property of the **system**, not of any single chat:

- **A tested accounting substrate.** The plumbing (revenue → COGS → opex → working capital → debt → cash flow) is written once and **CI-verified to reconcile against a real, audited 10-K — to the dollar** ([Fox Factory](#proof-on-a-real-public-company-fox-factory-foxf), below). During this very build the engine caught a subtle bug — D&A was quietly inflating operating cash flow — fixed it once, and a test now guarantees it stays fixed. A from-scratch agent reproduces that kind of error on every run, and the wrong number looks right.
- **Encoded CFO judgment.** Reconcile-to-the-dollar-then-bridge-the-one-offs; "segment Adjusted EBITDA isn't gross profit under ASU 2023-07"; a goodwill impairment gets *bridged*, not forced through the model. The reflexes a senior finance person has and a generic agent doesn't.
- **Reproducible & auditable.** Config-driven, every figure source-traced to a filing, re-runnable — not a chat transcript you can't reproduce.
- **Self-extension *with guardrails*.** The agent re-tools a *known, tested* structure per business (it generated a bespoke `segment-rollup` skill for Fox's segments) instead of emitting throwaway scripts. Template-grade rigor **and** bespoke-grade fit.

The short version: bare Claude is a capable analyst with a blank spreadsheet. openfpa adds the tested model engine, the encoded methodology, and a review checklist — rails to drive on, and gauges that catch the mistakes.

---

## How it compounds

openfpa is designed to get better the more you use it — two loops, both keeping your data in your own repo:

- **Per client (Loop A).** Every close, it scores its last forecast against your actuals and proposes tweaks for you to accept or reject. Human corrections feed the same memory: the fixes you catch by eye, captured durably as plain markdown you own.
- **Across your book (Loop B).** For a fractional CFO with many clients, it looks for patterns that *generalize* — validated by leave-one-out cross-client backtesting (a pattern has to hold up on the clients it wasn't learned from) — and, with your sign-off, saves them to a local library that seeds the next client.

It borrows [Karpathy's AutoResearch](https://github.com/karpathy/autoresearch) idea: a cheap, objective fitness metric — *reconciliation error against your own books* — for the loops to optimize against, at the client level and across your book. Nothing phones home; you ratify every change.

---

## See it in 30 seconds

```bash
pip install -e .          # from a clone — or `pip install openfpa` once published
python examples/ridgeline/run_demo.py
```

That runs the full pipeline on a synthetic premium D2C brand (**Ridgeline Chair Co.**) and writes a CFO briefing. Here's the headline it produces:

> The distribution is **`openfpa`**; the importable package is **`pyfpa`** (`import pyfpa`).

```markdown
# Ridgeline Chair Co.

## Headline
- **Revenue:** $6,000,000
- **EBITDA:** $824,000
- **Net income:** $572,651
- **Ending cash:** $720,418

## 13-Week Cash Runway
- **Trough:** -$146,000 (week 7)
- **First negative week:** week 3
```

The story the model tells: a seasonal inventory business that **goes cash-negative in week 3** as the spring inventory build lands before sell-through collects, troughs at **−$146K**, then recovers — i.e. *"you need a ~$150–200K credit line to bridge the build."* That's the kind of insight this toolkit is built to surface automatically.

The full briefing (with the month-by-month table) is committed at [`docs/demo/briefing.md`](docs/demo/briefing.md).

---

## Proof on a real public company: Fox Factory (FOXF)

Ridgeline is synthetic. To show the engine on *real, messy, audited* numbers, [`examples/foxfactory/`](examples/foxfactory/) runs the whole toolkit against **Fox Factory Holding Corp.**, pulled live from SEC EDGAR (every figure traces to a filing in [`data/SOURCES.md`](examples/foxfactory/data/SOURCES.md)):

```bash
python examples/foxfactory/pull_edgar.py   # refresh actuals from SEC EDGAR
python examples/foxfactory/run_foxf.py     # reconcile + forecast + divestiture
```

- **Phase A — reconciliation.** Driven with Fox's actual segment net sales, COGS, working-capital days, D&A and capex, the engine reproduces reported **revenue, gross profit, Adjusted EBITDA and the working-capital cash mechanic to the dollar** for FY2024 and FY2025. The $557M FY2025 goodwill impairment and discrete tax benefits are shown as an explicit bridge — the lean engine models the operating business, not one-time non-cash charges.
- **Phase B — forecast.** A segment-level (PVG / AAG / SSG → consolidated) FY2026–FY2027 forecast, anchored to the reported Q1 FY2026 print.
- **Phase C — capital allocation.** A labeled sensitivity: what selling **Marucci** does to free cash flow and leverage across sale timings and proceeds.

It self-extends, too: Fox reports segment **Adjusted EBITDA** (ASU 2023-07), not segment gross profit, so the `fpa-learn-business` phase generates a bespoke [`segment-rollup`](examples/foxfactory/skills/generated/segment-rollup/SKILL.md) skill to fit — exactly the per-business re-tooling the skillset is built for.

**This reconciliation runs in CI.** Every push, on Python 3.11/3.12/3.13, verifies the engine still ties to Fox's reported FY2024–FY2025 numbers. It's not a marketing claim you take on faith — it's a test that goes red the moment it stops being true.

---

## Bring your numbers — any way you have them

openfpa is **not married to a connector.** Everything it ingests normalizes to one shape — `{account: amount}` — so the engine never cares where the numbers came from. And where no built-in path exists, **the AI writes the ingestion**: the Fox example's [`pull_edgar.py`](examples/foxfactory/pull_edgar.py) is exactly that — a SEC-EDGAR adapter the agent built from scratch.

So you connect however your numbers actually live:

- **Public filings** — a 10-K / 10-Q (the Fox Factory example).
- **Your accounting system, live** — QuickBooks or NetSuite, via their **MCP servers** (the MCP server owns the auth — openfpa never touches your credentials) or their APIs.
- **D2C ops** — Shopify.
- **Or just the spreadsheets on your laptop** — P&L, balance sheet, AR/AP aging, inventory. CSV/Excel in, model out. (`read_pl_csv` reads any `Account, Amount` export; richer tables like aged AR or item-level inventory get parsed to what the model needs — DSO, DIO, DPO.)

No data team, no implementation project, no "is my connector supported?" The agent meets your data where it is and builds the bridge. That's the whole point of a substrate an AI extends per-business.

---

## What it does

```
config (YAML)  ─▶  revenue ─▶ cogs ─▶ opex ─▶ working capital ─▶ debt ─▶ cashflow
                                                                            │
   spreadsheets (P&L/BS/AR/AP/inventory) ─▶ (ingestion)                     ▼
   QuickBooks·NetSuite (MCP/API) · 10-K · Shopify ─▶ (adapters)  12-month P&L + cash flow
                                                                            │
   scheduled weekly flows ─▶ 13-week direct-method cash ─▶ runway           ▼
                                                              board-ready briefing (md / xlsx)
```

- **Monthly forecast engine** — config-driven (`EntityConfig`): revenue with seasonality + growth, channel-level COGS, fixed/variable OpEx, AR/AP/inventory working capital, multi-instrument debt, and an indirect-method cash flow with NOL-aware tax.
- **13-week cash forecast** — schedule-driven direct method (`Cash13Config`): per-week receipts and disbursements, raw cash position (no auto-draws, so the liquidity gap is visible), and a runway summary (`min_cash`, `min_week`, `first_negative_week`).
- **IO layer** — `read_pl_csv` reads any `Account, Amount` statement export (P&L, balance sheet, …) to `{account: amount}`; render a markdown CFO briefing; export to Excel.
- **Data-source adapters** — `from_netsuite` / `from_quickbooks` / `from_shopify` return a normalized `{account: amount}` (fixture-backed scaffolds; each documents its live path). But the toolkit isn't limited to these — connect QuickBooks/NetSuite **via MCP**, pull a 10-K, or point it at local spreadsheets, and the agent **builds the ingestion for that source** (see [`pull_edgar.py`](examples/foxfactory/pull_edgar.py)). Credentials come from the host/MCP server — never committed.

## Use it as a library

```python
import pyfpa

cfg = pyfpa.load_config("examples/ridgeline/config.yaml")
monthly = pyfpa.cashflow_from_config(cfg)            # 12-month P&L + cash flow

from pyfpa.io.loaders import load_cash13_config
weekly = pyfpa.cash13_forecast(load_cash13_config("examples/ridgeline/cash13.yaml"))
runway = pyfpa.runway_summary(weekly)                # {'min_cash': -146000.0, 'min_week': 7, ...}

from pyfpa.io.reporting import to_briefing_md
print(to_briefing_md(monthly, title="My Company", runway=runway))
```

## Design principles

- **Lean by intent.** Small, pure `*_from_config` functions; immutable pandas; pydantic-validated config; disk I/O confined to the `io/` layer. The engine is meant to be *read and extended by an AI*, so it stays small and conventional.
- **Config is the source of truth.** Every number lives in YAML.
- **Honest cash.** The 13-week forecast shows the raw, unfinanced position — it never hides a shortfall behind an automatic LOC draw.
- **Zero real *client* data.** The demo company is fictional and adapters ship with synthetic fixtures. The one real-data example (Fox Factory) uses **only public SEC filings**, fetched on demand and fully source-traced.

## Project status & roadmap

| Component | Status |
|---|---|
| Monthly forecast engine (`pyfpa`) | Built |
| 13-week cash engine (`pyfpa.cash13`) | Built |
| IO layer + data-source adapters (`pyfpa.io`) | Built |
| Runnable demo (`examples/ridgeline`) | Built |
| Real public-company proof (`examples/foxfactory`) | Built |
| Claude skillset (see below) | Built |
| Self-improving backtest loop (`pyfpa.backtest` + `fpa-backtest-learn`) | Built |
| Human corrections + vault memory (`pyfpa.memory` + `fpa-capture-correction`) | Built |
| Cross-client portfolio learning (`pyfpa.portfolio` + `fpa-portfolio-learn`) | Built |

**The skillset is the point.** The forecast engine is the substrate; the headline feature is a progressive Claude skillset (in [`skills/`](skills/), installable as a Claude plugin) that drives it across the lifecycle:

1. **`fpa-learn-business`** — interview + financials → a durable business profile, and *generate bespoke skills/agents* for that company (the self-extending part).
2. **`fpa-scaffold-model`** — build a runnable model from a trial balance.
3. **`fpa-configure-actuals`** — wire in real numbers from wherever they live: local spreadsheets, QuickBooks/NetSuite via MCP or API, a 10-K, and so on.
4. **Operate** — `fpa-monthly-close`, `fpa-cash-runway`, `fpa-board-briefing`, **`fpa-backtest-learn`** (scores past forecasts against your actuals and proposes ratified improvements — the self-improving loop), **`fpa-capture-correction`** (turns a human's "that's off because X" into durable memory that grounds every future forecast), and **`fpa-portfolio-learn`** (distills what generalizes across your whole book into a reusable library that seeds new clients — cross-client learning) — guided throughout by **`fpa-cfo-judgment`**, the encoded gotchas a real finance team knows (pre-close margins lie, D&A is a real expense — not a cash-flow freebie, a goodwill impairment is non-cash — bridge it, raw cash ≠ insolvency).

See [`docs/blog/launch.md`](docs/blog/launch.md) for the story — a cold AI agent building a coffee-roaster forecast from a 10-minute intake and writing its own bespoke skill, *and* the same toolkit reconciling Fox Factory's real 10-K to the dollar.

## Development

```bash
pip install -e ".[dev]"
pytest -q          # the full test suite
```

## License

MIT — see [LICENSE](LICENSE). Built and maintained by **Guiderail**.
