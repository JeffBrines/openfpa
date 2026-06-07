# openfpa

**An AI-native FP&A toolkit.** Point an AI coding agent (Claude Code, Claude Cowork, Codex) at your numbers and it stands up a CFO-grade financial model — a 12-month P&L and cash-flow forecast, a 13-week cash-runway, and a board-ready briefing — in minutes.

`openfpa` is a deliberately **lean Python forecast engine** plus (coming next) a **progressive Claude skillset** that encodes the methodology and judgment of a real finance team. The engine is small on purpose: it's the substrate an AI extends per-business, not an off-the-shelf app you configure by hand.

> Built by [Guiderail](https://guiderail.example). Open-source under MIT. Runs entirely on synthetic demo data — no credentials required.

---

## See it in 30 seconds

```bash
pip install -e .
python examples/ridgeline/run_demo.py
```

That runs the full pipeline on a synthetic premium D2C brand (**Ridgeline Chair Co.**) and writes a CFO briefing. Here's the headline it produces:

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
- **Synthetic-only in the repo.** Zero real client data. The demo company is fictional; adapters ship with synthetic fixtures.

## Project status & roadmap

| Component | Status |
|---|---|
| Monthly forecast engine (`pyfpa`) | ✅ Built |
| 13-week cash engine (`pyfpa.cash13`) | ✅ Built |
| IO layer + data-source adapters (`pyfpa.io`) | ✅ Built |
| Runnable demo (`examples/ridgeline`) | ✅ Built |
| **Claude skillset** (the hero — see below) | 🚧 Coming next |

**The skillset is the point.** The forecast engine is the substrate; the headline feature is a progressive Claude skillset that drives it across the lifecycle:

1. **Learn the business** — interview + financials → a durable business profile, and *generate bespoke skills/agents* for that company (the self-extending part).
2. **Scaffold** a model from a trial balance.
3. **Configure** real numbers / connect a data source.
4. **Operate** — monthly close, cash-runway, board briefings — guided by an encoded *CFO-judgment* layer (the gotchas a real finance team knows).

## Development

```bash
pip install -e ".[dev]"
pytest -q          # 63 tests, all green
```

## License

MIT — see [LICENSE](LICENSE). Built and maintained by **Guiderail**.
