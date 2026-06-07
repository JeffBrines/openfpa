# Open FP&A Copilot — Design Spec

**Date:** 2026-06-06
**Status:** Draft for review
**Owner:** Jeff Brines (Guiderail)

---

## 1. Purpose & Positioning

An open-source, AI-native FP&A toolkit: a **Claude skillset** (Claude Code + Claude Cowork)
riding on a deliberately **lean Python engine**. A user points Claude at it, hands over a
trial balance / QuickBooks export / spreadsheet, and Claude stands up a CFO-grade forecast —
and, more strikingly, **re-tools itself** for that specific business by generating bespoke
skills and agents.

**Audience & job-to-be-done.** The primary audience is **VCs and Jeff's professional network**.
The artifact's job is a credibility flex — "these people are on the frontier of what AI can do
in finance." Most companies will never adopt it; the win is the reaction. Secondary audience:
any SMB on NetSuite or QuickBooks (but it must also work off a plain spreadsheet/CSV).

**Primary deliverables:**
1. A public GitHub repo (the credibility anchor) — installable as a Claude plugin.
2. A LinkedIn launch post + blog post (first-class deliverables, not afterthoughts).
3. A fast-follow content series (one post per new demo industry).

**Source material.** Extracted clean-room from two private production FP&A codebases:
- **a logistics FP&A model ("the logistics model")** — single-entity trucking model; standout = 13-week direct-method cash
  forecast (payment lags, AR/AP lookback pipelines), actuals overlay, Excel-with-live-formulas.
- **a consumer-products FP&A model ("the consumer-products model")** — multi-entity; standout = clean pip-installable engine
  architecture (chained `*_from_config` model layers, `DataProvider` injection), NetSuite
  ingestion, and a flagship `cfo-financial-analysis` skill encoding analytical judgment.

**Hard constraint — clean room.** Zero real the logistics client / Hive data, names, credentials, or account
numbers (e.g., NetSuite account `REDACTED`). Everything ships against synthetic demo data only.
Integration adapters are documented and shipped with synthetic fixtures, never live secrets.

---

## 2. Approach (chosen)

**"The Open FP&A Copilot" — skillset-first plugin + lean engine.** One repo that is both a
Claude Code/Cowork plugin and a lean Python package, with a synthetic demo company.

Explicitly rejected:
- **Reference Application** (full Streamlit app + live URL) — a UI dilutes the AI-native story
  and is the heaviest to maintain / strip of proprietary data.
- **Content-led thin repo** — a technical VC clicking into a thin repo deflates the "robust" claim.

**Scope boundaries (deliberately out):**
- ❌ No Streamlit / web UI.
- ❌ No live credentials in-repo; adapters ship with synthetic fixtures and run offline.
- ❌ No multi-entity / FX in the engine core (the skill layer may still *discuss* it).
- ✅ Engine stays lean; depth concentrates in the operate-phase skills.

---

## 3. Repository Architecture

```
openfpa/                          # public name TBD (candidates: "CFO Copilot", "Ledgerline") — "by Guiderail"
├── README.md                     # storefront: hero demo, 30-sec pitch, Guiderail attribution
├── LICENSE                       # MIT
├── .claude-plugin/
│   └── plugin.json               # installable as a Claude Code / Cowork plugin
├── skills/                       # THE HERO — progressive skillset (§4)
│   ├── fpa-learn-business/
│   ├── fpa-scaffold-model/
│   ├── fpa-configure-actuals/
│   ├── fpa-monthly-close/
│   ├── fpa-cash-runway/
│   ├── fpa-board-briefing/
│   └── fpa-cfo-judgment/
├── pyfpa/                        # the lean engine (§5)
│   ├── config/                   # pydantic schemas + YAML loader (source of truth)
│   ├── models/                   # revenue, cogs, opex, working_capital, debt, cashflow
│   ├── cash13/                   # 13-week direct-method engine
│   └── io/                       # csv/xlsx in; excel + briefing-md out; adapter stubs
├── examples/
│   └── ridgeline/                # synthetic D2C demo company (flagship)
├── docs/
│   ├── blog/                     # version-controlled blog posts
│   └── superpowers/specs/        # this spec
└── tests/
```

---

## 4. The Skillset (hero)

Seven skills across a progressive lifecycle: **learn → scaffold → configure → operate**, with
`fpa-cfo-judgment` consulted throughout. Depth is front-loaded into learn + operate.

### Phase 0 — Discover (the headliner)

**`fpa-learn-business`** — runs before everything. Inputs: the financials + a short structured
interview Claude conducts. Outputs:
1. **A durable business profile** — `.fpa/business-profile.md`, committed and version-controlled.
   The persistent memory of *this* company (entity structure, revenue model, cost drivers,
   seasonality, financing, quirks). Every other skill reads it first.
2. **Bespoke skills + agents, generated on demand.** Identifies gaps the standard skills don't
   cover and authors new ones into `skills/generated/` and `agents/generated/`, following the
   `superpowers:writing-skills` discipline (proper frontmatter, tight triggers, tested — not stubs).
   - D2C → spawns `sku-profitability` + a CAC/contribution-margin skill.
   - SaaS → spawns `arr-waterfall` / cohort-retention.
   - Trucking → spawns `driver-cost-scorecard`.

   **Guardrails:** generated artifacts land in `generated/` namespaces in the *client's* repo,
   never the public template; a **human review gate** — Claude proposes with rationale and waits
   for approval before writing (self-extending, not self-executing); each generated skill must
   cite the profile facts that justify it.

### Phase 1 — Scaffold (thin)

**`fpa-scaffold-model`** — takes a trial balance / P&L export (CSV, XLSX, pasted), infers the
chart-of-accounts → model-line mapping, and generates a `pyfpa` config + any per-client model
extensions following encoded conventions. Output: a runnable skeleton + a "confirm these
assumptions" summary.

### Phase 2 — Configure (thin)

**`fpa-configure-actuals`** — wires real numbers in. Offline path: map a spreadsheet/CSV into
the actuals format. Live path: documented NetSuite (SuiteQL/OAuth) and QuickBooks adapters with
synthetic fixtures. Establishes the freeze-line / actuals-overlay convention.

### Phase 3 — Operate (deep — the moat)

**`fpa-monthly-close`** — ingest latest actuals, refresh forecast from the last closed balance
sheet, compute plan-vs-actual variance, select reforecast mode (Plan / Latest-Estimate /
Run-Rate). Produces a variance *narrative*, not just a table.

**`fpa-cash-runway`** — 13-week direct-method cash forecast: per-category payment lags, AR/AP
lookback pipelines, raw cash position with no auto-draws so the liquidity gap is visible. The
"when do we run out of money" answer.

**`fpa-board-briefing`** — turns model output into a board/investor briefing (markdown + Excel):
EBITDA bridge, cash trajectory, the 3 things that changed, the 3 risks.

**`fpa-cfo-judgment`** — *not a workflow; a judgment layer* Claude consults during any analysis.
Encodes the gotchas: pre-close margins untrustworthy (COGS posts late); data seams between
ingestion periods; intercompany not eliminated; flash-cash vs GL-cash; "a suspiciously
profitable month is usually unposted costs." Separates "AI that does math" from "AI that thinks
like a CFO."

**Chain:** learn → scaffold → configure → (close ↻ cash-runway ↻ board-briefing), judgment throughout.

---

## 5. The Lean Engine (`pyfpa`)

**Principle:** the smallest thing that is still a *real* CFO tool, built to be read and extended
by an AI. Small pure functions, immutable pandas (`.assign`/`.copy`/`.pipe` — never mutate),
pydantic-validated config, no hidden state, YAML as source of truth.

- `pyfpa/config/` — pydantic schemas (`EntityConfig`, `Channel`, `CostLine`, `DebtInstrument`)
  + YAML loader.
- `pyfpa/models/` — six pure layers chained `revenue → cogs → opex → working_capital → debt →
  cashflow`; each exposes a `*_from_config(cfg)` factory that does no I/O. Output: monthly DataFrame.
  - `working_capital` includes AR/AP **and inventory (DIO)** — required by the D2C hero demo.
- `pyfpa/cash13/` — 13-week direct-method engine: payment-lag config, AR/AP lookback pipelines,
  raw cash position.
- `pyfpa/io/` — `read_pl_csv` / `read_xlsx` in; `to_excel` (live-formula workbook) +
  `to_briefing_md` out; adapter stubs `netsuite.py`, `quickbooks.py` with synthetic fixtures.

Everything heavier (UI, DB, live auth, multi-entity/FX) is intentionally absent.

---

## 6. Demo Company (flagship) + Content Series

**Ridgeline Flask Co.** (name TBD — also Thornwood Goods / Basin & Range Supply) — a fictional
premium D2C drinkware/outdoor brand, ~$6M revenue, three channels (D2C site, Amazon, wholesale),
real inventory cycle, seasonal Q4 spike, a working-capital LOC. Ships as `examples/ridgeline/`:
raw QuickBooks-style P&L export CSV, generated config, and a **golden-output forecast** so
`pytest` asserts the demo always works.

**Industry-pack fast-follow series** — the content engine. Each post adds one
`examples/<industry>/` company and the hook is the *same skillset re-tooling itself*:

| Order | Industry | Bespoke skill spawned | Hook |
|------|----------|----------------------|------|
| 1 (launch) | D2C drinkware | sku-profitability, CAC/contribution | "Claude built itself a CFO for my brand" |
| 2 | Logistics | driver-cost-scorecard | cash-runway drama |
| 3 | SaaS | arr-waterfall, cohort-retention | "same toolkit, zero new code from me" |
| 4 | Professional services | utilization / realization | |
| 5 | Restaurant group | prime-cost / unit economics | |

Fast-follows are cheap: engine and core skills don't change — only demo data and the *spawned*
skill change, which is the product demonstrating itself.

---

## 7. Error Handling & Validation Conventions

- **Config:** all inputs validated via pydantic at load; a malformed YAML/config fails loudly
  with a specific message naming the offending field, never a silent default.
- **Ingestion:** CSV/XLSX parsers validate expected columns and surface a clear remediation
  message ("expected an Amount column; found ..."). Pre-close months flagged as low-trust per
  `fpa-cfo-judgment`.
- **Engine:** pure functions raise on impossible states (negative inventory, unbalanced BS);
  the balance sheet must reconcile (A = L + E) within tolerance or the run errors.
- **Skills:** the learn-business generation step is gated behind explicit human approval;
  generated skills that fail their own tests are not written.
- **No secrets:** adapters read credentials only from env vars and refuse to run against
  anything but fixtures unless explicitly configured.

---

## 8. Testing Strategy

- **Unit:** each `pyfpa` model layer tested in isolation against hand-computed expectations.
- **Golden-output:** the Ridgeline demo forecast is snapshotted; `pytest` fails if engine
  changes alter it unexpectedly (protects the demo that backs the public claims).
- **Config validation:** malformed configs assert the right pydantic errors.
- **Ingestion:** sample CSV/XLSX fixtures parse to expected actuals dicts.
- **Skill smoke tests:** generated-skill frontmatter validates; `cash13` reconciles to the
  monthly indirect method within tolerance.
- Target: meaningful coverage on the engine (the part that must be correct); skills are
  exercised via the demo walkthrough.

---

## 9. Open Decisions (confirm during review)

1. **Public product name** — engine stays `pyfpa`; product/plugin name TBD ("CFO Copilot",
   "Ledgerline", other) with "by Guiderail" attribution.
2. **Demo company name** — Ridgeline Flask Co. vs alternatives.
3. **Repo name / final home** — currently scaffolded at `/Volumes/Crucial/openfpa`.

---

## 10. Build Sequence (high level — full plan in writing-plans step)

1. Engine core (`pyfpa/config` + `models`) with unit tests.
2. `cash13` engine + reconciliation test.
3. `io` (CSV/XLSX in, Excel/briefing out) + adapter stubs/fixtures.
4. Ridgeline synthetic demo + golden-output test.
5. The seven core skills (operate-phase depth first).
6. `fpa-learn-business` + generation guardrails + review gate.
7. Plugin packaging (`.claude-plugin/plugin.json`), README, MIT license.
8. Launch blog + LinkedIn post; then industry-pack fast-follows.
```
