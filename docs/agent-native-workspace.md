# Agent-Native Company Workspace

openfpa provides a stable financial kernel and a repeatable process for an AI to
build a bespoke FP&A system for one company. The company workspace is the
product. It should become more specific as the AI learns the business.

## Workspace Shape

```text
company/
├── .fpa/
│   ├── MEMORY.md
│   ├── intake.md
│   ├── business-profile.md
│   ├── sources/
│   │   └── registry.yaml
│   ├── mappings/
│   │   └── registry.yaml
│   ├── corrections/
│   ├── forecasts/
│   ├── experiments/
│   ├── decisions/
│   ├── models/
│   │   └── entrypoints.yaml
│   └── research/
├── connectors/generated/
├── models/generated/
├── skills/generated/
└── agents/generated/
```

`.fpa/` stores durable knowledge and evidence. Generated code remains visible,
reviewable, and testable outside the hidden memory directory.

`models/entrypoints.yaml` advertises tested company-specific commands for
forecasting, close, cash, research, reporting, connectors, or custom workflows.
The registry is discovery metadata. Registering a command never executes it.

`sources/registry.yaml` records provenance, entity, currency, period coverage,
location, and extraction method for every source used by the company model.
`mappings/registry.yaml` records exact normalized mappings and deliberate
ignores. Agents should profile, register, map, and reconcile sources before
using their totals. Richer tables may use a tested company-specific
reconciliation command registered as an entrypoint.

Generated connectors use a visible bundle contract:

```text
connectors/generated/<name>/
├── connector.yaml
├── connector.py
├── run.py
├── README.md
└── fixtures/source.csv
```

The manifest binds the connector to a registered source, authentication method,
redacted fixture, fixture command, normalized schema, and golden mapped totals.
`connector-validate` executes fixture mode and reconciles the normalized output.
It does not test or access live credentials. Live extraction remains
company-specific and uses host-managed authentication.

## Onboarding

Onboarding is task-gated. It begins when company memory is incomplete and the
user requests broad FP&A work such as setup, modeling, forecasting, or analysis.
A narrow request should proceed without forcing a company interview.

The agent inspects supplied local evidence first, records cited facts in
`intake.md`, and asks only unresolved questions. Questions arrive in related
rounds of at most three. Direct answers are immediately authoritative;
source-derived facts retain confidence and citations. Only conflicts and
low-confidence conclusions interrupt the user for confirmation.

Once the critical topics are known, onboarding writes the business profile and
an initial model architecture proposal under `decisions/`. Model and connector
generation waits for explicit approval.

## Active Memory

Canonical memory remains the readable Markdown and YAML in `.fpa/`. A
rebuildable lexical index supports bounded retrieval without making an opaque
vector store authoritative. For each task, the agent builds a context pack with
source links and excerpts. Embeddings or external memory systems may be added as
optional retrieval backends later; they must remain derived indexes.

Memory is task-specific: a cash-runway task should retrieve financing,
collections, corrections, and prior cash epochs instead of loading the entire
vault.

## Company Research

After the initial architecture is approved, the agent may run autonomous
champion/challenger epochs. The company owns its objective: weighted metrics,
hard accounting checks, minimum improvement, and a complexity penalty.

Weak challengers are discarded automatically but retained in `research/`.
Promotion-eligible challengers may be proposed. Replacing the active champion
requires a human approval record in the model registry.

## Stable Versus Adaptive

The stable kernel owns behavior that must be dependable across companies:

- accounting identities and model primitives;
- schema validation;
- reconciliation and scoring semantics;
- memory and experiment file contracts;
- reusable tests and reporting helpers.

The adaptive company layer may own anything specific to the business:

- source connectors and chart-of-accounts mappings;
- revenue, cohort, segment, project, fleet, or SKU models;
- close procedures and judgment rules;
- scenarios, decision analyses, and board reporting;
- generated skills and agents.

`EntityConfig` is one useful model shape, not a universal ontology.

## Experiment Contract

Every material model change should produce an experiment record. The record
captures:

- the hypothesis being tested;
- evidence and source references;
- training and holdout periods;
- files changed;
- metrics before and after;
- accounting and reconciliation checks;
- the human decision.

Accepted experiments require explicit ratification and passing checks. Rejected
and reverted experiments remain in the workspace as institutional memory.

## Mutation Rules

1. Read memory and prior experiments before editing.
2. Profile and register sources, persist mappings, and surface unknowns.
3. Prefer company-specific changes over expanding the kernel.
4. Test the hypothesis against history, a holdout, or a labeled scenario.
5. Fail loudly when evidence is insufficient.
6. Keep source provenance and human decisions in plain files.
7. Promote behavior into the kernel only after it generalizes.
