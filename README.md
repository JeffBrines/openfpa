# openfpa

[![CI](https://github.com/JeffBrines/openfpa/actions/workflows/ci.yml/badge.svg)](https://github.com/JeffBrines/openfpa/actions/workflows/ci.yml)

**An AI-native FP&A toolkit.** Point an AI coding agent (Claude Code, Claude Cowork, Codex) at your numbers and it stands up a CFO-grade financial model — a 12-month P&L and cash-flow forecast, a 13-week cash-runway, and a board-ready briefing — in minutes.

`openfpa` is a deliberately **lean Python forecast engine** plus a **progressive Claude skillset** that encodes the methodology and judgment of a real finance team. The engine is small on purpose: it's the substrate an AI extends per-business, not an off-the-shelf app you configure by hand.

> Built by [Guiderail](https://guiderail.example). Open-source under MIT. The demo runs on synthetic data — no credentials required — and a second worked example validates the engine against a **real public company** (Fox Factory, NASDAQ: FOXF) straight from its SEC filings.

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

---

## What it does

```
config (YAML)  ─▶  revenue ─▶ cogs ─▶ opex ─▶ working capital ─▶ debt ─▶ cashflow
                                                                            │
   trial balance / P&L CSV ─▶ (ingestion)                                   ▼
   NetSuite · QuickBooks · Shopify ─▶ (adapters)              12-month P&L + cash flow
                                                                            │
   scheduled weekly flows ─▶ 13-week direct-method cash ─▶ runway           ▼
                                                              board-ready briefing (md / xlsx)
```

- **Monthly forecast engine** — config-driven (`EntityConfig`): revenue with seasonality + growth, channel-level COGS, fixed/variable OpEx, AR/AP/inventory working capital, multi-instrument debt, and an indirect-method cash flow with NOL-aware tax.
- **13-week cash forecast** — schedule-driven direct method (`Cash13Config`): per-week receipts and disbursements, raw cash position (no auto-draws, so the liquidity gap is visible), and a runway summary (`min_cash`, `min_week`, `first_negative_week`).
- **IO layer** — read a QuickBooks-style P&L CSV, render a markdown CFO briefing, export to Excel.
- **Data-source adapters** — `from_netsuite` / `from_quickbooks` / `from_shopify` return a normalized `{account: amount}`. Fixture-backed out of the box; each documents its live path (SuiteQL/OAuth, QuickBooks Online, Shopify Admin API). Credentials come from your environment — never committed.

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
| Monthly forecast engine (`pyfpa`) | ✅ Built |
| 13-week cash engine (`pyfpa.cash13`) | ✅ Built |
| IO layer + data-source adapters (`pyfpa.io`) | ✅ Built |
| Runnable demo (`examples/ridgeline`) | ✅ Built |
| Real public-company proof (`examples/foxfactory`) | ✅ Built |
| **Claude skillset** (the hero — see below) | ✅ Built |

**The skillset is the point.** The forecast engine is the substrate; the headline feature is a progressive Claude skillset (in [`skills/`](skills/), installable as a Claude plugin) that drives it across the lifecycle:

1. **`fpa-learn-business`** — interview + financials → a durable business profile, and *generate bespoke skills/agents* for that company (the self-extending part).
2. **`fpa-scaffold-model`** — build a runnable model from a trial balance.
3. **`fpa-configure-actuals`** — wire real numbers / connect a data source (NetSuite · QuickBooks · Shopify).
4. **Operate** — `fpa-monthly-close`, `fpa-cash-runway`, `fpa-board-briefing` — guided throughout by **`fpa-cfo-judgment`**, the encoded gotchas a real finance team knows (pre-close margins lie, EBITDA≈EBIT here, raw cash ≠ insolvency).

See [`docs/blog/launch.md`](docs/blog/launch.md) for the story — including a cold AI agent building a coffee-roaster forecast from a 10-minute intake and proposing its own bespoke skill.

## Development

```bash
pip install -e ".[dev]"
pytest -q          # 63 tests, all green
```

## License

MIT — see [LICENSE](LICENSE). Built and maintained by **Guiderail**.
