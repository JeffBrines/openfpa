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

## Workflow

1. **Interview + ingest.** Read whatever financials exist (`pyfpa.read_pl_csv`, the `pyfpa.io.adapters` for NetSuite/QuickBooks/Shopify), then ask the operator the questions a numbers don't answer:
   - What do you sell, and how do you bill (subscription, wholesale terms, D2C, projects)?
   - What's the cash cycle — when do you collect, when do you pay?
   - What's seasonal? What's lumpy (inventory buys, tax, payroll cadence)?
   - What financing is in place (LOC, term debt, factoring)?
   - What keeps you up at night?

2. **Write the business profile** to `.fpa/business-profile.md` (committed). Capture: entity structure, revenue model + channels, cost drivers, seasonality, working-capital rhythm, financing, and the quirks. This is the contract the rest of the toolkit reads.

3. **Identify gaps the 7 standard skills don't cover**, and propose bespoke skills/agents:
   - Product company with SKUs → a `sku-profitability` skill
   - SaaS → an `arr-waterfall` / cohort-retention skill
   - Logistics/fleet → a `driver-cost-scorecard` skill

4. **Generate them** following `superpowers:writing-skills` discipline, into `skills/generated/` (and `agents/generated/`). Each generated skill MUST cite the profile facts that justify it.

## Guardrails (self-extending, NOT self-executing)

- Generated artifacts go in `generated/` namespaces in the **client's own repo** — never the public openfpa template.
- **Human review gate:** propose each new skill/agent with its rationale and WAIT for approval before writing it.
- No profile fact → no generated skill. Speculation is not a justification.

## Next

Profile written and approved → **fpa-scaffold-model** to build the runnable model. Consult **fpa-cfo-judgment** throughout.
