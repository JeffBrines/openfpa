# Portfolio Learning (Loop B) — Design

**Status:** Approved (design phase)
**Date:** 2026-06-08
**Topic:** Cross-client learning for a fractional CFO's own book — distill patterns
that generalize across the operator's clients into a reusable local library that
seeds new clients. All local; the practice compounds.

## Why

Loop A makes the model better at *one* client over time. Loop B makes the
*operator's practice* compound: client #10 starts smarter than client #1 because the
operator's library carries what generalized across #1–9. The target user is often a
fractional CFO with many clients — so "cross-client" means *their own book, on their
own machine*. Nothing phones home; the Mission's privacy promise holds.

The objective metric exists at the portfolio level: **does a pattern learned on some
clients improve (or at least not degrade) the backtest on the *other* clients?** —
a client-level train/test split that reuses Loop A's `holdout_backtest`/`score_forecast`.

## Decisions (locked)

| Decision | Choice |
| --- | --- |
| Aggregator | A fractional CFO's **own book, all local**. No central service, no phone-home. |
| Validation | **Graceful both**: recurrence surfaces candidates; cross-client holdout validates where enough clients exist; operator **always ratifies**. |
| Promote what | **Both** parametric priors (objective) and structural skills (recurrence + judgment). |
| Architecture | Snapshot-mining + cross-client holdout, local library, operator-ratified. Tested `pyfpa.portfolio` + `fpa-portfolio-learn` skill. |
| Mining sources | Loop A snapshots + applied parametric corrections (priors); generated skills + structural corrections (skills). |

## Portfolio & Library (local, operator-owned)

**Portfolio manifest** — `~/.fpa/portfolio.yaml`:
```yaml
library: ~/.fpa/library
clients:
  - { path: ~/clients/acme-bikes,  type: d2c-inventory }
  - { path: ~/clients/haulco,       type: trucking }
  - { path: ~/clients/brightsaas,   type: saas }
```
Each client = a workspace root (containing `.fpa/` and `skills/`) + a business-type tag
(the clustering key).

**Library** — `~/.fpa/library/`:
```
library/
  priors/d2c-inventory.yaml      # promoted parametric priors for this business-type
  skills/<name>/SKILL.md         # promoted structural skills
  library-log.md                 # audit: what, evidence (recurrence + holdout delta), date — reversible
```

## Components — `pyfpa/portfolio/` (lean, pure, tested)

`pyfpa/portfolio/manifest.py`
- `class ClientRef(BaseModel)`: `path: str`, `type: str`.
- `class Portfolio(BaseModel)`: `library: str`, `clients: list[ClientRef]`.
- `load_portfolio(path) -> Portfolio` (YAML).
- `clients_of_type(portfolio, business_type) -> list[ClientRef]`.

`pyfpa/portfolio/recover.py`
- `recover_actuals(snapshot: Snapshot) -> dict[str, float]` — invert the stored score:
  `actual = predicted / (1 + per_line_error)` for each scored line. Zero-touch to Loop A
  (no new Snapshot field needed). Only scored lines are recoverable (the rest weren't scored).
- `best_snapshot(client_path) -> Snapshot | None` — the lowest-fitness scored snapshot in
  `<client>/.fpa/forecasts/` (the assumptions that worked best for that client).

`pyfpa/portfolio/mine.py`
- `MINEABLE_DRIVERS = ["working_capital.dso_days", "working_capital.dio_days",
  "working_capital.dpo_days", "tax_rate", "da_monthly", "capex_monthly"]` (entity-level scalars;
  per-channel drivers are a documented extension).
- `class PriorCandidate(BaseModel)`: `business_type`, `driver`, `value`, `support: list[str]`
  (client paths/slugs it came from), `dispersion: float`.
- `mine_priors(portfolio, business_type, *, min_support=3, dispersion_max=0.15) -> list[PriorCandidate]` — for each
  client of the type, read `best_snapshot(...).assumptions` and applied parametric corrections;
  for each mineable driver, collect the per-client values; a driver clustering **tightly**
  (coefficient of variation ≤ `dispersion_max`, default 0.15) across ≥ `min_support` clients →
  a `PriorCandidate` at the **median**. Scattered → no candidate (not everything generalizes).
- `class SkillCandidate(BaseModel)`: `business_type`, `name`, `support: list[str]`, `source: str`.
- `find_recurring_skills(portfolio, business_type, *, min_support=3) -> list[SkillCandidate]` —
  scan each client's `skills/generated/` and structural corrections; a skill name recurring
  across ≥ `min_support` clients → a `SkillCandidate` (source = one client's copy).

`pyfpa/portfolio/validate.py`
- `class ValidationResult(BaseModel)`: `mean_delta: float`, `n_folds: int`, `validated: bool`.
- `validate_prior(driver: str, type_clients: list[ClientRef], *, tolerance=0.0) -> ValidationResult`
  — **leave-one-out** across the type's clients. For each client C: derive the prior value as the
  median of `driver` across the **other** type clients; take `best_snapshot(C)`, recover its actuals,
  apply the override `driver = that median` (`pyfpa.memory.apply_override` on the assumptions),
  re-run `cashflow_from_config` + `extract_lines`, `score_forecast` vs recovered actuals →
  `delta = new_fitness − snapshot_fitness`. `mean_delta` = mean over the folds.
  **A prior is `validated` if `mean_delta ≤ tolerance`** — i.e. a peer-derived value does not degrade
  the held-out client's fit (a robust default). Fewer than 2 usable clients →
  `validated=False, n_folds=<count>` (recurrence-only, judgment). Always produces an out-of-sample
  estimate when ≥2 clients have a scored snapshot — no dependence on the candidate's support set.

`pyfpa/portfolio/library.py`
- `load_library(library_path) -> dict` (priors by type + skill names) / writers:
- `promote_prior(library_path, candidate, validation) -> None` — append to
  `priors/<type>.yaml` with `value`, `support`, `cross_client_holdout_delta`, `date`; log it.
- `promote_skill(library_path, candidate) -> None` — copy the skill into `skills/<name>/`; log it.
- `seed_from_library(library_path, business_type, cfg: EntityConfig) -> EntityConfig` — apply the
  promoted priors for the type to a new client's starting config (a **new** cfg; the per-client
  Loop A refines from there). Priors are seeds, not mandates.

`pyfpa/portfolio/__init__.py` re-exports; `pyfpa/__init__.py` exposes the public names.

**Small `pyfpa.memory` touch-up:** promote the existing private `_set_by_path` to a public
`apply_override(data: dict, path: str, value: float) -> None` (same logic) so the portfolio
package doesn't reach into a private helper. `apply_corrections` keeps using it internally.

## Skill — `skills/fpa-portfolio-learn/SKILL.md`

Workflow: load manifest → for each business-type with ≥ `min_support` clients,
`mine_priors` + `find_recurring_skills` → `validate_prior` on held-out clients →
present ranked candidates (priors with cross-client delta + support; skills with recurrence)
→ **operator ratifies** → `promote_prior`/`promote_skill` + `library-log.md`. Reversible.

## The payoff — `fpa-learn-business` integration

When onboarding a new client tagged a business-type, `fpa-learn-business` calls
`seed_from_library(library, type, base_cfg)` to start the model from the operator's promoted
priors and offers the promoted skills. Client #10 inherits what generalized across #1–9.

## Guardrails

- **Local-only** — operates on operator-provided paths; no network; library is transparent files.
- **Min support** (default 3) — never generalize from 1–2 clients.
- **Dispersion gate** — only tight-clustering drivers become candidates.
- **Held-out validation** — a prior must not degrade clients it wasn't derived from
  (`mean_delta ≤ tolerance`), or it's flagged judgment-only.
- **Operator ratifies everything; priors are *seeds*** — the per-client Loop A always refines.
  Reversible via `library-log.md`.

## Success criteria

1. `mine_priors` returns a candidate at the median for a tight-clustering driver across
   ≥ `min_support` clients; a scattered driver yields no candidate.
2. `find_recurring_skills` returns a candidate for a skill name recurring across ≥ `min_support`
   clients; below that, none.
3. `validate_prior` computes the leave-one-out mean cross-client fitness delta (peer-derived
   value per fold) via `recover_actuals` + override + re-score; `validated` iff
   `mean_delta ≤ tolerance` with `n_folds ≥ 2`; fewer than 2 usable clients → `validated=False`.
4. `seed_from_library` applies promoted priors to a new client's config (new cfg, input unmutated).
5. Promotions are logged in `library-log.md`, reversible.
6. `pyfpa.portfolio` unit-tested (repo's 80% norm); full suite green; all local (no network).

## Testing

- `recover_actuals`: a snapshot with predicted + per_line error → recovered actuals invert exactly.
- `best_snapshot`: picks the lowest-fitness scored snapshot; no scored snapshots → None.
- `mine_priors`: synthetic portfolio where DIO clusters tight across 3 clients → one candidate at
  the median; a scattered driver → none; <min_support → none.
- `find_recurring_skills`: a generated skill name in 3 clients → candidate; in 1 → none.
- `validate_prior` (leave-one-out): 3 clients whose `driver` already clusters tight → peer-derived
  value per fold ≈ each client's own → `mean_delta ≈ 0`, validated; a portfolio where the driver is
  scattered → positive mean_delta, not validated; <2 usable clients → `validated=False`.
- `seed_from_library`: a promoted prior seeds the driver in a base cfg; input unmutated.
- `promote_*` + `load_library` round-trip; `library-log.md` written.

## Docs (README)

The implementation includes a README pass — not just a one-line roadmap row, but the
**compounding story** now that the full picture exists: engine → real-data proof (Fox) →
per-client self-improvement (Loop A) → human corrections/memory → **cross-client portfolio
learning (Loop B)**. Add `fpa-portfolio-learn` to the skillset list, a roadmap row
(`pyfpa.portfolio` + `fpa-portfolio-learn`), and a short "how it compounds" paragraph tying the
two loops together (a fractional CFO's practice gets smarter with every client).

## Scope boundaries (YAGNI)

- **Local-only** — no central aggregation, no community contribution, no phone-home (that was an
  earlier-rejected aggregator option).
- **Entity-level mineable drivers** in v1 (working capital, tax, D&A, capex); per-channel priors
  are a documented extension.
- **Operator-ratified only** — no autonomous promotion.
- **No new ingestion** — reads existing `.fpa/` snapshots/corrections + `skills/generated/`.
- **Structural-skill promotion is copy + judgment** — no automated cross-client skill *synthesis*.
