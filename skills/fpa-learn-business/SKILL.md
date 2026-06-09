---
name: fpa-learn-business
description: Use when starting FP&A work for a new company, onboarding a business into openfpa, or asked to "understand my business / set up a model for us" before any forecasting — produces a durable business profile and generates business-specific skills.
---

# Learn the Business (Phase 0)

## Overview

Before scaffolding any model, learn the business. This produces two artifacts: a **durable business profile** that every other openfpa skill reads first, and — where the standard skills don't fit — **bespoke skills/agents generated for this specific company**. The toolkit re-tools itself per business instead of forcing a generic template.

**Core principle:** A forecast is only as good as the business understanding behind it. Encode that understanding once, explicitly, so it grounds everything downstream.

## When to use

- A new company is being onboarded into openfpa
- You're asked to "build us a model" / "understand our business" before forecasting
- An existing `.fpa/business-profile.md` is missing or stale

Do not force this workflow when the user asks for a narrow task that can be
completed without understanding the whole company.

## Workflow

1. **Check and initialize the workspace.** Run
   `openfpa status <company-root>`. If it is uninitialized, run
   `openfpa init <company-root> --business-name "<name>"`. Then run
   `openfpa doctor <company-root>`. The CLI emits JSON. If the console script is
   unavailable in a source checkout, use `python3 -m pyfpa.cli`.

2. **Inspect local evidence first.** Run `openfpa inspect-data <data-root>` for
   every user-supplied folder, then read the relevant financials, operating
   files, documentation, and existing model code before asking questions.
   Record each fact with `openfpa intake-record <company-root>`, including file
   references and confidence. Never access an external MCP/API system without
   the user's approval.

3. **Ask only what remains unknown.** Run
   `openfpa intake-next <company-root>` and ask that related round of at most
   three questions. After every response, call `openfpa intake-record` with
   `--source-type user`. Direct answers are confirmed immediately. Only ask the
   user to resolve conflicting or low-confidence inferred facts.

4. **Repeat short rounds** until `pyfpa.intake_ready(intake)` is true. Do not ask
   questions already answered by local evidence or earlier conversation.

5. **Propose the company architecture.** Build a `pyfpa.ArchitectureProposal`
   covering the model objective, connectors, company-specific model components,
   generated skills, risks, and validation checks. Call
   `pyfpa.write_onboarding_outputs(intake, workspace, proposal)` to write:
   - `.fpa/business-profile.md`
   - `.fpa/decisions/initial-model-architecture.md`

6. **Stop for approval.** Summarize known facts, remaining unknowns, and the
   proposed architecture. Do not scaffold or generate artifacts until the user
   approves the proposal.

7. **After approval, seed from the portfolio library.** If one exists, start the
   model from what generalized across same-type clients. Priors are seeds; this
   client's learning loop refines them.

8. **Identify gaps the standard skills don't cover**, and propose bespoke skills/agents:
   - Product company with SKUs → a `sku-profitability` skill
   - SaaS → an `arr-waterfall` / cohort-retention skill
   - Logistics/fleet → a `driver-cost-scorecard` skill

9. **Generate approved artifacts** using the repository's agent operating contract and local
   skill format, into `skills/generated/` (and `agents/generated/`). Company
   models and connectors belong in `models/generated/` and
   `connectors/generated/`. Each generated artifact MUST cite the profile facts
   that justify it and include a focused test or reconciliation check.

10. **Apply existing corrections.** Before forecasting, fold in human corrections: `pyfpa.apply_corrections(cfg, pyfpa.load_corrections('.fpa/corrections'))`. Route any `type: structural` corrections through this skill's skill-generation path as *pre-ratified* proposals (the human already authored them — don't wait for backtest misses).

## Guardrails (self-extending, NOT self-executing)

- Generated artifacts go in `generated/` namespaces in the **client's own repo** — never the public openfpa template.
- **Human review gate:** propose each new skill/agent with its rationale and WAIT for approval before writing it.
- No profile fact → no generated skill. Speculation is not a justification.
- Record material generated changes as `pyfpa.Experiment` files in
  `.fpa/experiments/`; preserve rejected and reverted experiments.

## Next

After architecture approval, use **fpa-scaffold-model** to build the runnable
model. Consult **fpa-cfo-judgment** throughout.
