# openfpa Agent Operating Contract

openfpa is an agent-native FP&A workbench, not a fixed application. The goal is
to help an AI build the finance system that fits one company while preserving a
small, trustworthy accounting kernel.

## Architecture

- `pyfpa/` is the stable kernel: schemas, accounting mechanics, reconciliation,
  scoring, persistence contracts, and reusable analysis helpers.
- `.fpa/` is company memory: business context, sources, mappings, corrections,
  forecasts, experiments, decisions, and accepted learnings.
- Company-specific code belongs in visible generated namespaces such as
  `models/generated/`, `connectors/generated/`, `skills/generated/`, and
  `agents/generated/`.
- Do not force a business into `EntityConfig` when its economics require a
  different model. Extend the company workspace and use the kernel where useful.

## Company Onboarding

- Trigger onboarding when `.fpa/intake.md` is incomplete and the user asks to
  build, configure, forecast, analyze, or learn the business.
- Do not force onboarding for a narrow task that can be completed independently.
- Use the machine-oriented CLI as the default workspace control surface:
  - `openfpa status <company-root>`
  - `openfpa init <company-root> --business-name "<name>"` when uninitialized
  - `openfpa inspect-data <data-root>` for each user-supplied data location
  - `openfpa source-profile <company-root> --file <source-file>` before mapping
  - `openfpa source-register <company-root> ...` for each relied-on source
  - `openfpa source-list <company-root>` before source-dependent work
  - `openfpa mapping-register <company-root> ...` for each exact mapping
  - `openfpa mapping-list <company-root> --source-id <source-id>` before modeling
  - `openfpa reconcile-source <company-root> ...` before using mapped totals
  - `openfpa connector-list <company-root>` before generating recurring access
  - `openfpa connector-scaffold <company-root> ...` from a redacted fixture
  - `openfpa connector-validate <company-root> --name <name>` after connector edits
  - `openfpa intake-next <company-root>` before asking intake questions
  - `openfpa intake-record <company-root> ...` for each established fact
  - `openfpa entrypoint-list <company-root>` before generated workflows
  - `openfpa entrypoint-register <company-root> ...` after validating a command
  - `openfpa doctor <company-root>` before relying on workspace state
- The CLI emits JSON and performs deterministic workspace operations. Read its
  output as evidence; do not treat it as the reasoning engine.
- If the console script is unavailable in a source checkout, use
  `python3 -m pyfpa.cli` with the same arguments.
- Inspect supplied local files before asking questions. Do not access external
  systems or connectors without user approval.
- Register every source used by a model with its entity, currency, periods,
  extraction method, and location. A file existing in the workspace is not
  sufficient lineage.
- Persist exact mappings, including deliberate ignores with rationale. Never
  infer an unmapped account into a model silently.
- Run `openfpa reconcile-source` for compatible account-amount CSV sources.
  For richer sources, build an equivalent tested reconciliation and register
  its command as an entrypoint.
- Generate a connector only when recurring access is useful and the architecture
  is approved. One-time local files do not need connector code.
- Scaffold connectors from explicit redacted fixtures only. Never copy a
  production export into `connectors/generated/` without confirming it is safe
  to commit.
- Treat `connector-validate` as a fixture-mode contract test. It must not access
  a live system. Implement live extraction separately using host-managed
  credentials, then register the tested recurring command as an entrypoint.
- Record source-derived and user-confirmed facts with citations and confidence
  using `openfpa intake-record`.
- Ask only unresolved questions returned by `pyfpa.next_intake_questions`, in
  rounds of at most three related questions.
- Record direct user answers immediately as confirmed facts. Ask for
  confirmation only when evidence conflicts or confidence is low.
- When `pyfpa.intake_ready` is true, write the business profile and
  `.fpa/decisions/initial-model-architecture.md` with
  `pyfpa.write_onboarding_outputs`.
- Stop before scaffolding connectors, models, skills, or agents until the user
  approves the architecture proposal.
- After a generated workflow has a tested command, register it in
  `.fpa/models/entrypoints.yaml`. Registration advertises the command but does
  not execute it.

## Adaptation Loop

1. Run `openfpa status` and `openfpa doctor`, then read `.fpa/MEMORY.md`, intake,
   the business profile, corrections, prior
   experiments, and source notes before changing a model.
2. Rebuild the memory index and retrieve a bounded context pack for the task.
3. Reconcile source data and report unmapped or unexplained amounts.
4. State a falsifiable financial hypothesis before editing code or assumptions.
5. Make the smallest company-specific change that can test the hypothesis.
6. Run relevant accounting checks, tests, and a holdout or scenario comparison.
7. Save a research epoch with evidence, changed files, before/after metrics,
   check results, and relevant memory sources.
8. Autonomously discard weak or failed challengers and preserve why they failed.
9. Present only promotion-eligible challengers for human ratification. Never
   replace the champion without explicit approval.

## Kernel Guardrails

- Never hide reconciliation differences, missing actuals, duplicate names, or
  unmapped accounts behind defaults.
- Never treat missing scoring evidence as perfect forecast performance.
- Never overwrite source data, correction history, or experiment history
  silently.
- Keep generated connectors fixture-tested and source-traceable.
- A change that improves a headline metric but breaks an accounting invariant is
  a failed experiment.
- Complexity is a cost. Prefer the smallest model that clears the company's
  objective and hard checks.
- Promote company-specific behavior into `pyfpa/` only after it is demonstrably
  reusable across businesses.

## Required Evidence

An accepted model change should identify:

- the hypothesis and CFO question;
- source evidence and periods used;
- files and assumptions changed;
- before/after metrics;
- reconciliation and accounting checks;
- holdout or scenario results where applicable;
- who accepted it, when, and why.
