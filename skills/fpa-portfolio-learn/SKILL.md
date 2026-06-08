---
name: fpa-portfolio-learn
description: Use when you run FP&A for several clients and want your practice to compound — mines patterns that generalize across your same-type clients, validates them by leave-one-out cross-client backtesting, and promotes ratified priors and skills into a local library that seeds every new client. All local; nothing leaves your machine.
---

# Portfolio Learn (Loop B)

## Overview

Loop A makes the model better at one client. This makes your *practice* compound:
client #10 starts smarter than client #1 because your library carries what generalized
across #1–9. Everything is local — your own book, on your own machine.

**Core principle:** self-improving, never self-ratifying — propose, you accept. The
objective metric is cross-client: does a pattern learned on some clients fail to
degrade the *others*' backtest?

## Setup

A portfolio manifest `~/.fpa/portfolio.yaml` lists your clients + a business-type tag:

```yaml
library: ~/.fpa/library
clients:
  - { path: ~/clients/acme,  type: d2c-inventory }
  - { path: ~/clients/peak,  type: d2c-inventory }
  - { path: ~/clients/haul,  type: trucking }
```

## Workflow

1. **Load** the manifest (`pyfpa.load_portfolio`).
2. For each business-type with at least 3 clients:
   - **Priors:** let `type_clients = pyfpa.portfolio.clients_of_type(portfolio, type)`.
     `pyfpa.mine_priors(portfolio, type)` finds drivers that cluster tightly; validate each
     with `pyfpa.validate_prior(driver, type_clients)` (leave-one-out). Surface validated
     ones first (by cross-client delta), then unvalidated/judgment.
   - **Skills:** `pyfpa.find_recurring_skills(portfolio, type)` for recurring generated
     skills. Also weigh recurring **structural corrections** across clients (read each
     `.fpa/corrections/` for `type: structural`) — a human-authored pattern that repeats
     is strong signal.
3. **Present** candidates ranked by evidence (support count + cross-client delta).
4. **Ratify.** On your acceptance, `pyfpa.promote_prior` / `pyfpa.promote_skill` writes the
   `~/.fpa/library/` and `library-log.md`. Reversible.

## Guardrails

- Local-only; nothing phones home.
- At least 3 clients to propose; tight-cluster only; a prior must not degrade held-out clients.
- You ratify everything; priors are *seeds*, not mandates — each client's Loop A refines.

## The payoff

New clients inherit the library: **fpa-learn-business** seeds their starting model from
your promoted priors (`pyfpa.seed_from_library`) and offers the promoted skills.

## Next

Promoted → the next new client onboarded via **fpa-learn-business** starts smarter.
