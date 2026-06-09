# openfpa

[![CI](https://github.com/JeffBrines/openfpa/actions/workflows/ci.yml/badge.svg)](https://github.com/JeffBrines/openfpa/actions/workflows/ci.yml)

**openfpa is an open-source FP&A toolkit for finance professionals.** Point an AI coding agent (Claude Code, Claude Cowork, Codex) at your numbers and it builds a working financial model: a 12-month P&L and cash-flow forecast, a 13-week cash runway, and a board-ready briefing.

Three things set it apart. It **improves over time** against your own actuals. It has a real **memory** of your business. And it's **agnostic about where your numbers come from**. Each is covered below.

It's also a model you *work with*, alongside the agent, not a static report it hands back. Ask "what if we delay the hire a quarter," challenge an assumption, point out something that's off, and the agent edits the model, re-runs it, and explains what moved. You're pair-modeling, not waiting on a deliverable.

Under the hood, `openfpa` is a deliberately **lean Python forecast engine** plus a **progressive Claude skillset** that encodes the methodology and judgment of a real finance team. The engine is small on purpose. It's the substrate an AI extends per business, not an off-the-shelf app you configure by hand.

> Built by [Guiderail](https://guiderail.example). Open-source under MIT. The demo runs on synthetic data, no credentials required. A second worked example validates the engine against a **real public company** (Fox Factory, NASDAQ: FOXF) straight from its SEC filings.

---

## Mission

Bring real FP&A to anyone with a spreadsheet, without the cost or the implementation project of Datarails, Cube, or Vena.

Those tools hand you connectors and a modeling layer, then leave the thinking to you. openfpa flips that: **connect your data, or just point it at your spreadsheets, and let the AI do the thinking.** It asks the questions a good CFO would, builds the model, and surfaces what matters. The methodology underneath is distilled from hundreds of hours of production CFO work (a trucking fleet, a bicycle company, and more), not textbook finance.

Self-hosted, auditable, yours. What it learns lives as plain files in your repo, not someone else's cloud. This is an open-source experiment from [Guiderail](https://guiderail.example), and we'd love your help making it the FP&A tool we all wish existed.

---

## Why not just point Claude at your books?

Fair question. Claude *can* write financial code from scratch. But every run is a one-off: ad-hoc pandas, no shared structure, no test, no audit trail. Correctness by luck of the run. openfpa makes correctness a property of the **system**, not of any single chat:

- **A tested accounting substrate.** The plumbing (revenue, COGS, opex, working capital, debt, cash flow) is written once and CI-verified to reconcile against a real, audited 10-K, to the dollar ([Fox Factory](#proof-on-a-real-public-company-fox-factory-foxf), below). During this very build the engine caught a subtle bug, where depreciation was quietly inflating operating cash flow. It got fixed once, and a test now guarantees it stays fixed. A from-scratch agent reproduces that kind of error on every run, and the wrong number looks right.
- **Encoded CFO judgment.** Reconcile to the dollar, then bridge the one-offs. "Segment Adjusted EBITDA isn't gross profit under ASU 2023-07." A goodwill impairment gets *bridged*, not forced through the model. The reflexes a senior finance person has and a generic agent doesn't.
- **Reproducible and auditable.** Config-driven, every figure source-traced to a filing, re-runnable. Not a chat transcript you can't reproduce.
- **Self-extension with guardrails.** The agent re-tools a *known, tested* structure per business (it generated a bespoke `segment-rollup` skill for Fox's segments) instead of emitting throwaway scripts. Template-grade rigor and bespoke-grade fit.

The short version: bare Claude is a capable analyst with a blank spreadsheet. openfpa adds the tested model engine, the encoded methodology, and a review checklist. Rails to drive on, and gauges that catch the mistakes.

---

## It improves over time

openfpa is designed to get better the more you use it. The idea is borrowed from [Karpathy's AutoResearch](https://github.com/karpathy/autoresearch), which self-improves a model by iterating against a cheap, objective fitness metric: it edits the training code, keeps the changes that lower validation loss, and repeats. openfpa applies the same idea to FP&A, where the fitness metric is **reconciliation error against your own actuals**. Two loops run on that metric, and you ratify every change:

- **Per client (Loop A).** Every close, it scores its last forecast against your actuals and proposes adjustments that improve the backtest, for you to accept or reject. Over time the model gets better at *this* business.
- **Across your book (Loop B).** For a fractional CFO with many clients, it looks for assumptions that *generalize*, validated by leave-one-out cross-client backtesting (a pattern has to hold up on the clients it was not learned from). With your sign-off, it saves them to a reusable library that seeds the next client.

Nothing phones home, and every proposed change is yours to approve or reject. This is distinct from memory below: improvement is the *process* of getting better against a metric; memory is the durable *state* the process reads from and writes to.

---

## It remembers

The model is not reset every chat. What it learns about a business persists as plain files in that client's repo, which you can read, edit, and audit:

- `business-profile.md`: what the system knows about the business (segments, channels, seasonality, financing, the quirks).
- `corrections/`: the fixes you make by hand, typed and durable, so a correction you make once grounds every forecast after it.
- `forecasts/` and `scorecard.md`: each past forecast and how it actually scored against the close.
- `learnings.md`: the model changes you've accepted, with their evidence.
- a portfolio library: the patterns that generalized across your clients.

It's an Obsidian-friendly vault (plain markdown and YAML with a `MEMORY.md` index), but it never requires Obsidian. The point is that context accumulates and stays yours, rather than living in a chat history you can't reproduce or a vendor's cloud.

---

## Bring your numbers, any way you have them

openfpa is not married to a connector. Everything it ingests normalizes to one shape, `{account: amount}`, so the engine never cares where the numbers came from. And where no built-in path exists, the AI writes the ingestion. The Fox example's [`pull_edgar.py`](examples/foxfactory/pull_edgar.py) is exactly that: a SEC-EDGAR adapter the agent built from scratch.

So you connect however your numbers actually live:

- **Public filings:** a 10-K or 10-Q (the Fox Factory example).
- **Your accounting system, live:** QuickBooks or NetSuite, via their **MCP servers** (the MCP server owns the auth, so openfpa never touches your credentials) or their APIs.
- **D2C ops:** Shopify.
- **Or just the spreadsheets on your laptop:** P&L, balance sheet, AR/AP aging, inventory. CSV or Excel in, model out. (`read_pl_csv` reads any `Account, Amount` export; richer tables like aged AR or item-level inventory get parsed to what the model needs, such as DSO, DIO, and DPO.)

No data team, no implementation project, no "is my connector supported?" The agent meets your data where it is and builds the bridge. That is the whole point of a substrate an AI extends per business.

---

## See it in 30 seconds

```bash
pip install -e .          # from a clone, or `pip install openfpa` once published
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

The story the model tells: a seasonal inventory business that **goes cash-negative in week 3**, as the spring inventory build lands before sell-through collects, troughs at **-$146K**, then recovers. In other words, "you need a roughly $150,000 to $200,000 credit line to bridge the build." That's the kind of insight this toolkit is built to surface automatically.

The full briefing (with the month-by-month table) is committed at [`docs/demo/briefing.md`](docs/demo/briefing.md).

---

## Proof on a real public company: Fox Factory (FOXF)

Ridgeline is synthetic. To show the engine on *real, messy, audited* numbers, [`examples/foxfactory/`](examples/foxfactory/) runs the whole toolkit against **Fox Factory Holding Corp.**, pulled live from SEC EDGAR (every figure traces to a filing in [`data/SOURCES.md`](examples/foxfactory/data/SOURCES.md)):

```bash
python examples/foxfactory/pull_edgar.py   # refresh actuals from SEC EDGAR
python examples/foxfactory/run_foxf.py     # reconcile + forecast + divestiture
```

- **Phase A, reconciliation.** Driven with Fox's actual segment net sales, COGS, working-capital days, depreciation and capex, the engine reproduces reported **revenue, gross profit, Adjusted EBITDA, and the working-capital cash mechanic to the dollar** for FY2024 and FY2025. The $557M FY2025 goodwill impairment and discrete tax benefits are shown as an explicit bridge, because the lean engine models the operating business, not one-time non-cash charges.
- **Phase B, forecast.** A segment-level forecast (PVG, AAG, and SSG rolled up to consolidated) for FY2026 and FY2027, anchored to the reported Q1 FY2026 print.
- **Phase C, capital allocation.** A labeled sensitivity: what selling **Marucci** does to free cash flow and leverage across sale timings and proceeds.

It self-extends, too. Fox reports segment **Adjusted EBITDA** (ASU 2023-07), not segment gross profit, so the `fpa-learn-business` phase generates a bespoke [`segment-rollup`](examples/foxfactory/skills/generated/segment-rollup/SKILL.md) skill to fit. That is exactly the per-business re-tooling the skillset is built for.

**This reconciliation runs in CI.** Every push, on Python 3.11, 3.12, and 3.13, verifies the engine still ties to Fox's reported FY2024 and FY2025 numbers. It's not a marketing claim you take on faith. It's a test that goes red the moment it stops being true.

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

- **Monthly forecast engine:** config-driven (`EntityConfig`) with revenue seasonality and growth, channel-level COGS, fixed and variable OpEx, AR/AP/inventory working capital, multi-instrument debt, and an indirect-method cash flow with NOL-aware tax.
- **13-week cash forecast:** schedule-driven direct method (`Cash13Config`) with per-week receipts and disbursements, a raw cash position (no auto-draws, so the liquidity gap stays visible), and a runway summary (`min_cash`, `min_week`, `first_negative_week`).
- **IO layer:** `read_pl_csv` reads any `Account, Amount` statement export (P&L, balance sheet, and so on) into `{account: amount}`; render a markdown CFO briefing; export to Excel.
- **Data-source adapters:** `from_netsuite`, `from_quickbooks`, and `from_shopify` return a normalized `{account: amount}` (fixture-backed scaffolds, each documenting its live path). The toolkit is not limited to these. Connect QuickBooks or NetSuite via MCP, pull a 10-K, or point it at local spreadsheets, and the agent builds the ingestion for that source (see [`pull_edgar.py`](examples/foxfactory/pull_edgar.py)). Credentials come from the host or MCP server, never committed.

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

- **Lean by intent.** Small, pure `*_from_config` functions, immutable pandas, pydantic-validated config, and disk I/O confined to the `io/` layer. The engine is meant to be read and extended by an AI, so it stays small and conventional.
- **Config is the source of truth.** Every number lives in YAML.
- **Honest cash.** The 13-week forecast shows the raw, unfinanced position. It never hides a shortfall behind an automatic credit-line draw.
- **Zero real *client* data.** The demo company is fictional and the adapters ship with synthetic fixtures. The one real-data example (Fox Factory) uses only public SEC filings, fetched on demand and fully source-traced.

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

The forecast engine is the substrate; the skillset is where the work is. It's a progressive Claude skillset (in [`skills/`](skills/), installable as a Claude plugin) that drives the engine across the lifecycle:

1. **`fpa-learn-business`:** an interview plus financials become a durable business profile, and it generates bespoke skills and agents for that company (the self-extending part).
2. **`fpa-scaffold-model`:** build a runnable model from a trial balance.
3. **`fpa-configure-actuals`:** wire in real numbers from wherever they live (local spreadsheets, QuickBooks or NetSuite via MCP or API, a 10-K, and so on).
4. **Operate:** `fpa-monthly-close`, `fpa-cash-runway`, `fpa-board-briefing`, plus `fpa-backtest-learn` (scores past forecasts against your actuals and proposes ratified improvements, the per-client loop), `fpa-capture-correction` (turns a human's "that's off because X" into durable memory that grounds future forecasts), and `fpa-portfolio-learn` (distills what generalizes across your book into a reusable library that seeds new clients). All of it is guided by `fpa-cfo-judgment`, the encoded gotchas a real finance team knows: pre-close margins lie; depreciation is a real expense, not a cash-flow freebie; a goodwill impairment is non-cash, so bridge it; raw cash is not insolvency.

See [`docs/blog/launch.md`](docs/blog/launch.md) for the story: a cold AI agent building a coffee-roaster forecast from a 10-minute intake and writing its own bespoke skill, and the same toolkit reconciling Fox Factory's real 10-K to the dollar.

## Development

```bash
pip install -e ".[dev]"
pytest -q          # the full test suite
```

## Contributing

It's early and help is welcome: bug reports, a sharper piece of CFO judgment, a new data-source ingestion, or a whole industry pack. See [`CONTRIBUTING.md`](CONTRIBUTING.md) for setup, the workflow, and what's most useful to work on.

## License

MIT. See [LICENSE](LICENSE). Built and maintained by **Guiderail**.
