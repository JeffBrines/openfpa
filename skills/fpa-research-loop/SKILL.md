---
name: fpa-research-loop
description: Use after forecasts have scored actual outcomes and you want the AI to run bounded autonomous champion/challenger research epochs, discard weak candidates, and propose only evidence-backed model promotions.
---

# Company Research Loop

## Purpose

Run an AutoResearch-style loop against the company's own forecast history. The
AI may generate, test, and discard challengers autonomously. Only promotion to
the active champion requires human approval.

## Memory And State

- `.fpa/research/objective.yaml`: company-specific metrics, weights, hard checks,
  minimum improvement, and complexity penalty.
- `.fpa/research/*.epoch.yaml`: every hypothesis and evaluated epoch, including
  discarded candidates.
- `.fpa/models/registry.yaml`: current champion, challengers, retired champions,
  and human-approved promotion history.
- `.fpa/index.yaml`: rebuildable lexical memory index.
- `.fpa/context-pack.md`: temporary task-specific retrieval output, never
  canonical memory.

## Workflow

1. **Discover the company command.** Run
   `openfpa entrypoint-list <company-root> --kind research`. Use a registered
   research runner when one exists.
2. **Retrieve context.** Rebuild memory with `pyfpa.build_memory_index(".fpa")`,
   then create a context pack for the miss being investigated. Read prior failed
   epochs before proposing a repeated hypothesis.
3. **Load the objective and registry.** The objective is CFO-specific. It should
   include forecast-error metrics by decision importance, hard accounting checks,
   a minimum improvement, and a complexity penalty.
4. **Run bounded epochs.** Default to at most five challengers in one run. For
   each:
   - state one falsifiable financial hypothesis;
   - generate the smallest company-specific change;
   - use rolling or holdout periods not used to fit the candidate;
   - run every hard check;
   - call `pyfpa.evaluate_challenger`;
   - persist the final `ResearchEpoch`.
5. **Discard autonomously.** Mark failed or weak candidates `discarded`. Preserve
   their code reference, evidence, metrics, and rejection reason so future agents
   do not repeat them without new evidence.
6. **Propose the strongest challenger.** Register only promotion-eligible
   challengers. Mark the strongest epoch `proposed` and explain the objective
   gain, tradeoffs, complexity cost, and relevant memory.
7. **Promote only after approval.** On explicit human acceptance, call
   `pyfpa.promote_challenger`, update the epoch to `promoted`, and save both with
   explicit overwrite. The prior champion moves to retired history.

## Guardrails

- The AI may experiment autonomously after the initial architecture is approved.
- Never tune or score on the same periods.
- Hard accounting and reconciliation checks override metric improvement.
- Do not promote a larger model unless improvement exceeds its complexity cost.
- No evidence means no experiment; no holdout means no promotion.
- Human approval is required only for champion promotion, not each epoch.
