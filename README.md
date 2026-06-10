# openfpa

[![CI](https://github.com/JeffBrines/openfpa/actions/workflows/ci.yml/badge.svg)](https://github.com/JeffBrines/openfpa/actions/workflows/ci.yml)

**openfpa is an agent-native FP&A workbench.** It gives an AI coding agent a
tested finance kernel, an operating contract, durable company memory, and a
research loop for building the FP&A system that fits one company.

If Codex or Claude Code is the reasoning engine, openfpa is the FP&A toolbelt it
straps on. The agent still thinks, asks questions, writes code, and makes
judgments. openfpa gives it the finance-specific tools, memory, checks, and
working method required to do that work well.

It is not a fixed FP&A application. It is not a catalog of prebuilt connectors.
It is not a universal financial model.

The intended workflow is:

1. Open a company workspace with an AI coding agent such as Codex or Claude Code.
2. Let the agent inspect the files already available.
3. Answer a short set of unresolved business and data questions.
4. Review the proposed model and data architecture.
5. Let the agent build the company-specific models, mappings, connectors, skills,
   and reports.
6. Score forecasts against actual outcomes and iterate toward a better result.

The company workspace is the product. The Python package is the stable kernel
inside it. The human points the agent toward the relevant data and business
context. The agent uses the toolbelt to learn the company, ask the right
questions, build the right FP&A system, and improve it as actual outcomes arrive.

## Why this exists

Traditional FP&A software asks a company to configure itself inside a fixed
application. openfpa takes the opposite approach. It gives an AI enough finance
structure, memory, and guardrails to learn the business and build what that CFO
or FP&A team actually needs.

A generic AI can write a forecast from scratch, but each run tends to produce a
new pile of code with no shared accounting logic, durable context, test history,
or promotion process. openfpa adds:

- **A tested finance kernel.** Revenue, COGS, operating expenses, working
  capital, debt, tax, cash flow, reconciliation, and reporting primitives live
  in `pyfpa`.
- **An agent operating contract.** `AGENTS.md`, `CLAUDE.md`, and the skills in
  `skills/` define how the agent should inspect evidence, ask questions, make
  changes, and validate its work.
- **Durable company memory.** Business facts, sources, mappings, corrections,
  forecasts, experiments, decisions, and model history live in `.fpa/`.
- **Evidence-gated iteration.** Champion and challenger models are evaluated on
  held-out actuals and accounting checks. Weak challengers are retained as
  failed research. Promotion requires human approval.
- **Visible adaptation.** Company-specific code belongs in generated namespaces,
  where it can be reviewed, tested, and changed.

The goal is not deterministic software that produces the same template for
every company. The goal is a dependable process that helps the AI produce a
better company-specific result over time.

## How onboarding works

For broad company work, the agent starts by inspecting local evidence. It does
not begin with a long generic questionnaire.

It records what it can establish, including sources and confidence, then asks
only unresolved questions in short rounds. Typical questions cover:

- business model, products, customers, segments, and revenue drivers;
- seasonality, pricing, unit economics, and major operating constraints;
- legal entities, reporting periods, currencies, and consolidation needs;
- debt, liquidity, capital spending, and working-capital behavior;
- the decisions the CFO needs the model to support;
- available systems, exports, folders, and credentials.

The first durable outputs are:

- `.fpa/intake.md`;
- `.fpa/business-profile.md`;
- `.fpa/decisions/initial-model-architecture.md`.

The agent waits for approval before generating a model or accessing an external
system. Narrow requests do not force a full company interview.

## Data access is agent-built

openfpa does not aim to maintain a conventional connector marketplace. The AI
should help the user reach the data that already exists, then build the smallest
reliable ingestion path for that company.

The agent should first ask where the relevant evidence lives:

- QuickBooks, Xero, NetSuite, or another accounting system;
- local CSV, Excel, or Google Sheets files;
- a shared folder containing monthly financial packages;
- P&L and balance-sheet exports;
- AR and AP aging reports;
- inventory balances, item detail, or purchasing data;
- payroll, CRM, billing, bank, or operational systems;
- public filings when the company is public.

It should then choose an access path:

1. Read local files already supplied by the user.
2. Use an existing host tool, MCP server, or authenticated command if available.
3. Ask the user to export a report when that is the safest and fastest path.
4. Build a company-specific API or file connector when recurring access matters.

Generated connector code belongs in `connectors/generated/`. It should include:

- the expected source and authentication method;
- a fixture or redacted sample;
- explicit field and account mappings;
- source totals and reconciliation checks;
- failure behavior for missing, duplicate, or unmapped records;
- tests that do not require production credentials.

The small functions in `pyfpa.io.adapters` are fixture-backed examples, not live
QuickBooks, NetSuite, or Shopify integrations. Credentials stay with the host
tool or environment and are never committed.

## The company workspace

```text
company/
|-- .fpa/
|   |-- MEMORY.md
|   |-- intake.md
|   |-- business-profile.md
|   |-- sources/
|   |-- mappings/
|   |-- corrections/
|   |-- forecasts/
|   |-- experiments/
|   |-- decisions/
|   |-- models/
|   `-- research/
|-- connectors/generated/
|-- models/generated/
|-- skills/generated/
`-- agents/generated/
```

Canonical memory remains readable Markdown and YAML. A rebuildable local index
supports task-specific retrieval, but the index is not the source of truth.

Memory and learning are different:

- **Memory** preserves what the system knows, where it learned it, and what
  humans corrected or approved.
- **Learning** evaluates model changes against actual outcomes and retains the
  evidence from accepted and rejected experiments.

See [`docs/agent-native-workspace.md`](docs/agent-native-workspace.md) for the
workspace and mutation contract.

## The research loop

The iteration model is inspired by
[Karpathy's AutoResearch](https://github.com/karpathy/autoresearch): define an
objective, run bounded experiments, keep measurable improvements, and preserve
failed attempts so they are not repeated without new evidence.

For FP&A, the objective is not simple in-sample reconciliation. A candidate
should improve forecast performance on held-out actuals while passing hard
checks such as:

- source reconciliation;
- accounting identities;
- segment or entity rollups;
- working-capital continuity;
- fit and holdout separation;
- scenario coherence.

The AI may generate, evaluate, and discard challengers after the initial
architecture is approved. A promotion-eligible challenger is presented to the
human with its metrics, tradeoffs, complexity cost, and evidence. The active
champion changes only after explicit approval.

## Agent toolbelt CLI

The `openfpa` command is a machine-oriented control surface for Codex, Claude
Code, and other capable coding agents. It emits JSON, performs deterministic
workspace operations, and leaves reasoning and conversation to the host agent.

The command set is:

```text
openfpa init
openfpa inspect-data
openfpa status
openfpa source-profile
openfpa source-register
openfpa source-list
openfpa mapping-register
openfpa mapping-list
openfpa reconcile-source
openfpa connector-scaffold
openfpa connector-list
openfpa connector-validate
openfpa intake-next
openfpa intake-record
openfpa doctor
openfpa entrypoint-list
openfpa entrypoint-register
openfpa correction-record
openfpa correction-list
openfpa scorecard-render
openfpa experiment-list
openfpa context-pack
openfpa onboarding-render
openfpa model-export
```

In a source checkout without the `openfpa` console script installed, every
command also works as `python3 -m pyfpa.cli <command>`.

The CLI can:

- initialize and validate the workspace;
- inventory local files and likely financial artifacts;
- profile CSV, TSV, and Excel tables without changing them;
- register source provenance, coverage, entities, and currencies;
- persist exact source-to-model mappings and deliberate ignores;
- reconcile account-amount CSV files while surfacing duplicates and unmapped values;
- scaffold company connector bundles from redacted fixtures;
- execute fixture-mode connector contracts and compare golden mapped totals;
- show unresolved intake questions;
- expose source, mapping, model, and research status;
- run deterministic checks and reports;
- provide structured context for the AI to continue the work;
- support non-interactive automation where the operation is deterministic.

The AI should still decide what questions matter, what data path to use, what
model fits the business, and what experiment to run next.

All commands return a versioned JSON envelope. Exit code `0` means success, `1`
means the requested operation or a diagnostic check failed, and `2` means the
command arguments were invalid.

`intake-record` writes one sourced fact to `.fpa/intake.md`. Generated company
workflows are published in `.fpa/models/entrypoints.yaml` with
`entrypoint-register`. The registry lets an agent discover the tested command,
working directory, inputs, and outputs. Registration does not execute the
command.

```bash
openfpa source-register . \
  --source-id monthly-pl \
  --kind local_file \
  --location data/monthly-pl.csv \
  --entity "Acme Inc." \
  --currency USD \
  --period 2026-05 \
  --extraction-method "Controller export from the accounting system"

openfpa mapping-register . \
  --source-id monthly-pl \
  --source-value "Product Revenue" \
  --target income_statement.product_revenue

openfpa reconcile-source . \
  --source-id monthly-pl \
  --account-column Account \
  --amount-column Amount

openfpa connector-scaffold . \
  --name accounting-pl \
  --source-id monthly-pl \
  --description "Pull and normalize the monthly P&L" \
  --auth-method host_environment \
  --fixture fixtures/redacted-monthly-pl.csv

openfpa connector-validate . --name accounting-pl

openfpa intake-record . \
  --key business_model \
  --answer "Commercial coffee roasting" \
  --source-type user

openfpa entrypoint-register . \
  --name forecast \
  --kind forecast \
  --description "Run the approved monthly forecast" \
  --command-json '["python3", "models/generated/run_forecast.py"]' \
  --input data/actuals.csv \
  --output output/forecast.xlsx
```

`connector-scaffold` creates:

```text
connectors/generated/accounting-pl/
|-- connector.yaml
|-- connector.py
|-- run.py
|-- README.md
`-- fixtures/source.csv
```

The scaffold requires a registered source, complete mappings, and a redacted
CSV fixture with no duplicate or unmapped accounts. It stores golden mapped
totals in `connector.yaml`. `connector-validate` runs fixture mode only,
normalizes the output to `Account,Amount`, and reconciles it against those
totals. It does not contact a live system.

The generated `extract_live()` function intentionally fails until the agent
implements host-authenticated access. After the live path has its own
fixture-backed tests and safe failure behavior, register the recurring command
with `entrypoint-register --kind connector`.

## Current quick start

Clone the repository and install it into a Python 3.11 or newer environment:

```bash
git clone https://github.com/JeffBrines/openfpa
cd openfpa
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -e ".[dev]"
```

Then open the repository in Codex or Claude Code and ask:

```text
Help me onboard this company into openfpa.
The financial files are in ./company-data.
Inspect them first, then ask me only what you cannot determine.
```

The repository instructions tell the agent to initialize `.fpa/`, inspect local
evidence, conduct the intake, and stop for architecture approval.

## Runnable examples

### Ridgeline Chair Co.

[`examples/ridgeline/`](examples/ridgeline/) is a synthetic product-company
example with a monthly forecast, a 13-week cash forecast, and reporting output.

```bash
python3 examples/ridgeline/run_demo.py
```

The example shows an inventory build creating a near-term liquidity gap before
seasonal collections arrive.

### Fox Factory

[`examples/foxfactory/`](examples/foxfactory/) applies the workflow to public,
source-traced SEC data for Fox Factory Holding Corp.

```bash
python3 examples/foxfactory/run_foxf.py
```

The example has four distinct phases:

1. **Actual-driver reproduction.** The engine reproduces known accounting
   mechanics using reported drivers. This validates arithmetic, not forecast
   skill.
2. **Historical holdout research.** A FY2025 holdout rejects an aggressive
   recovery challenger and proposes a better revenue-recovery and slow-margin
   challenger.
3. **Forward forecast.** A FY2026-FY2027 segment forecast is anchored to the
   reported Q1 FY2026 result.
4. **Capital allocation sensitivity.** A labeled Marucci divestiture scenario
   shows the tradeoff between free cash flow and leverage.

The full proof runs in CI across Python 3.11, 3.12, and 3.13. See
[`examples/foxfactory/README.md`](examples/foxfactory/README.md) for the
methodology and limitations.

## Python kernel

The importable package is `pyfpa`. The distribution name is `openfpa`.

```python
import pyfpa

config = pyfpa.load_config("examples/ridgeline/config.yaml")
monthly = pyfpa.cashflow_from_config(config)

cash_config = pyfpa.load_cash13_config("examples/ridgeline/cash13.yaml")
weekly = pyfpa.cash13_forecast(cash_config)
runway = pyfpa.runway_summary(weekly)

print(pyfpa.to_briefing_md(monthly, title="My Company", runway=runway))
```

The base kernel includes:

- monthly P&L and indirect cash-flow modeling;
- 13-week direct-method cash forecasting;
- revenue, COGS, operating-expense, debt, tax, and working-capital primitives;
- reconciliation, segment, SKU, and divestiture analysis helpers;
- CSV ingestion and Markdown or Excel reporting: static value export via
  `forecast_to_excel`, and a live-formula model workbook via `model_to_excel`
  (named assumption cells, real formulas, verified against the engine in CI);
- forecast snapshots, scoring, and holdout backtests;
- workspace, intake, correction, experiment, retrieval, and research records;
- experimental cross-company prior and skill mining.

`EntityConfig` is a useful starting model, not a required ontology. A company
with cohorts, projects, contracts, fleets, stores, or complex inventory may need
a different generated model.

The `model_to_excel` function compiles an `EntityConfig` into a two-sheet workbook:
an Assumptions sheet of named, editable driver cells and a Model sheet where every
P&L and cash-flow line is a real formula referencing those names. The `verify_workbook`
function evaluates the workbook with a Python formula engine and compares every line
and month to `cashflow_from_config`, so the workbook is verified against the engine
before it is used. For cadences or layouts the kernel does not cover, compose
`pyfpa.excel.toolkit` in a company-specific exporter and verify it the same way.

## Skills

The repository includes skills for:

- learning the business;
- scaffolding an initial model;
- configuring actuals and data access;
- running monthly close and cash runway analysis;
- producing board briefings;
- capturing human corrections;
- applying CFO judgment;
- running company research epochs;
- learning cautiously across a portfolio.

The skills are repo-native instructions for capable coding agents. The
`.claude-plugin/` manifest also supports Claude plugin installation, but the
underlying workflow is not intended to be Claude-only.

## Project status

| Component | Status |
|---|---|
| Finance kernel and reporting | Built |
| 13-week cash model | Built |
| Agent onboarding contract | Built |
| Durable `.fpa` workspace | Built |
| Active memory retrieval | Built |
| Champion and challenger research records | Built |
| Human-gated model promotion | Built |
| Generated workflow registry | Built |
| Generated connector contracts and fixture validation | Built |
| Synthetic Ridgeline example | Built |
| Public-data Fox Factory example | Built |
| Fixture-backed adapter examples | Built |
| Live company-specific connectors | Generated per company |
| Cross-company portfolio learning | Experimental |
| Machine-oriented agent CLI | Built |

## Design principles

- **Stable kernel, adaptive company.** Shared accounting and persistence
  contracts stay dependable. Company-specific models and connectors can change.
- **Inspect before asking.** Use supplied evidence before interrupting the user.
- **No hidden reconciliation gaps.** Missing, duplicate, conflicting, and
  unmapped data should fail visibly.
- **No evidence, no promotion.** A model change needs a hypothesis, source
  evidence, holdout result, and passing checks.
- **Human control at consequential boundaries.** External access, architecture
  approval, and champion promotion require explicit approval.
- **Complexity has a cost.** Prefer the smallest model that answers the CFO's
  decision and clears the objective.
- **Plain files remain authoritative.** Memory, evidence, and decisions should be
  readable without a proprietary service.

## Development

```bash
python3 -m pip install -e ".[dev]"
python3 -m pytest -q
```

## Contributing

Useful contributions include stronger finance primitives, source-ingestion
recipes, industry-specific skills, reconciliation checks, research objectives,
and additional public-company proofs. Never commit real client data or
credentials.

See [`CONTRIBUTING.md`](CONTRIBUTING.md) for the development workflow.

## License

MIT. See [`LICENSE`](LICENSE). Built and maintained by [Guiderail](https://www.guiderail.io).
