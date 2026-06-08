# Human Corrections & Vault-Friendly Memory — Design

**Status:** Approved (design phase)
**Date:** 2026-06-08
**Topic:** Capture unprompted human corrections as durable, structured memory that
grounds future forecasts — and make the `.fpa/` memory a coherent, Obsidian-friendly
vault. The highest-signal feedback channel, and the foundation Loop B mines.

## Why

The system learns from two signals today: **actuals** (the backtest — objective but
*lagging*) and **accept/reject** of its own proposals. It does *not* capture the
richest signal: a human reviewing a forecast who catches something off
("December always spikes," "you're double-counting deferred revenue"). That is
*leading* signal carrying domain knowledge the backtest can't see, and it's
currently lost. Memory is the core of this product; this makes human judgment a
first-class, durable, compounding part of it.

## Decisions (locked)

| Decision | Choice |
| --- | --- |
| Capture | **Both, skill-primary** — a conversational skill structures the correction; the file is plain markdown also hand-editable. |
| Correction types | **parametric** (driver override), **structural** (methodology/skill), **context** (one-time-item note). |
| Storage | **Vault-native markdown** in `.fpa/corrections/`, one file per correction (frontmatter + body). |
| Application | A tested `apply_corrections(cfg, …)` applies only `applied` + `parametric` overrides; structural/context are routed, not applied. |
| Authority | Human corrections apply on human authority (interpretation confirmed once at capture); the backtest **monitors** but never auto-reverts. |
| Module home | New `pyfpa/memory/` package (memory earns its own home). |
| Privacy | All local markdown the user owns; Obsidian is an optional UI, **never required**. |

## Correction file format (vault-native)

`.fpa/corrections/2026-06-08-december-seasonality.md`:
```markdown
---
type: parametric
target: channels[*].seasonality[11]
status: applied
date: 2026-06-08
override: { path: "channels[*].seasonality[11]", value: 2.0 }
---
**Was off:** the model spread revenue evenly; our December runs ~2× a normal month.

**Correction:** December seasonality weight ≈ 2.0.

**Why:** [[business-profile#seasonality]] — Nov/Dec is ~35% of annual, every year.
```
Frontmatter is the machine-readable contract (`type`, `target`, `status`, `date`,
`override`); the body is human narrative (`[[wikilinks]]` to the assumption/profile
it corrects). The engine reads frontmatter only — it never parses prose.

## Components

### Engine — `pyfpa/memory/` (lean, pure, tested)

`pyfpa/memory/corrections.py`
- `class Override(BaseModel)`: `path: str`, `value: float`.
- `class Correction(BaseModel)`: `slug: str`, `type: Literal["parametric","structural","context"]`,
  `target: str`, `status: Literal["open","applied","superseded"] = "open"`, `date: str`,
  `override: Override | None = None`, `notes: str = ""` (the markdown body).
- `load_corrections(dir: str | Path) -> list[Correction]` — parse every `*.md` in the dir
  (frontmatter → fields, body → `notes`); slug = filename stem. Missing dir → `[]`.
- `save_correction(correction, dir)` — write `<slug>.md` (frontmatter + body).
- `apply_corrections(cfg: EntityConfig, corrections) -> EntityConfig` — for each correction
  with `status == "applied"` and `type == "parametric"` and an `override`, apply the override
  to `cfg.model_dump()` and re-validate. Returns a **new** config; input never mutated.
  Structural/context corrections are ignored here.

`pyfpa/memory/paths.py`
- `_set_by_path(data: dict, path: str, value: float) -> None` (internal, used by apply):
  dotted-path setter supporting `name`, `name[n]` (index), and `name[*]` (every list item).
  An unresolvable path raises a descriptive `ValueError`.

`pyfpa/memory/__init__.py` re-exports; `pyfpa/__init__.py` exposes the public names.

### Skill — `skills/fpa-capture-correction/SKILL.md`

Conversational capture: the human says "this is off because X"; the skill (1) classifies
the type, (2) identifies the `target`, (3) for parametric drafts the concrete `override`,
(4) writes the correction file, and (5) **echoes its interpretation back and waits for
confirmation** before setting `status: applied`. The file remains hand-editable.

### Integrations (existing skills)

- **fpa-learn-business** — when building/refreshing a client model, `apply_corrections`
  the parametric ones; route `structural` corrections to its skill-generation path as
  *pre-ratified* proposals (the human authored them — no waiting for K backtest misses).
- **fpa-cfo-judgment** — its one-time-item screen reads `context` corrections so the
  backtest's attribution skips known one-offs.
- **fpa-monthly-close / fpa-backtest-learn** — *monitor* applied parametric corrections:
  if a corrected line keeps missing, flag the correction as possibly stale (human decides;
  `applied → superseded`). Never auto-revert.

## Vault-friendliness

- Corrections are fully vault-native (frontmatter + `[[wikilinks]]`).
- Existing memory (`business-profile.md`, `learnings.md`, `scorecard.md`, snapshots) gains
  light frontmatter + cross-links on the high-value connections (correction ↔ assumption ↔
  profile) — not a blanket retrofit.
- A `.fpa/MEMORY.md` index documents the vault layout so a human, Obsidian, or Claude can
  navigate it. The capture/learn skills keep it current.
- Result: `.fpa/` is one navigable knowledge base — Obsidian-openable, hand-editable,
  Claude-readable. Obsidian is never required.

## The loop-back

Corrections apply on human authority, but Loop A's backtest monitors them: a parametric
correction whose target line keeps missing gets flagged (`"December set to 2×; last two
came in ~1.4× — revisit?"`). Human judgment leads; the backtest verifies; nothing reverts
silently. This completes the feedback story (leading + lagging signals reinforce).

## Feeds Loop B

Because corrections are typed and structured (frontmatter), Loop B mines them like
snapshots: a parametric correction recurring across the operator's clients of a type →
portfolio prior candidate; a recurring structural correction → portfolio skill candidate.
This spec only guarantees the **minable format**; Loop B consumes it.

## Guardrails

- Human authority, but interpretation **confirmed once** at capture before `applied`.
- **Reversible**: `status` + the file; superseding is explicit; nothing silently overwritten.
- **Transparent**: plain markdown the user owns; no hidden state; any editor works.
- `apply_corrections` is deterministic and acts **only** on `applied` + `parametric`.
- Backtest **flags, never reverts** a human correction.
- Obsidian optional — no hard dependency.

## Success criteria

1. A correction round-trips through `save_correction`/`load_corrections` preserving all
   frontmatter fields and the body.
2. `apply_corrections` changes exactly the targeted driver(s) in a **new** config; input
   unmutated; `*`-for-all-channels resolves; a bad path raises a clear `ValueError`.
3. Structural/context corrections are **not** applied to the config.
4. The three correction types are documented and routed (skill); `.fpa/MEMORY.md` exists
   and describes the vault.
5. `pyfpa.memory` is unit-tested (repo's 80% norm); full suite green.
6. Everything is plain markdown the user owns; no Obsidian dependency.

## Testing

- **round-trip**: parametric correction with an override and a `[[wikilink]]` body →
  save → load → identical fields + notes.
- **apply_corrections**: a `channels[*].seasonality[11] = 2.0` override sets month-12
  weight on every channel in a new cfg; `working_capital.dio_days = 45` sets that scalar;
  input cfg unchanged.
- **path grammar**: `name`, `name[n]`, `name[*]` resolve; an unknown segment → `ValueError`.
- **routing**: a dir of mixed-type corrections → only `applied` + `parametric` change the
  config; `open` parametric and `structural`/`context` are ignored.
- **load empty/missing dir** → `[]`.

## Scope boundaries (YAGNI)

- **No Obsidian plugin or integration** — we only make memory vault-*compatible* (markdown +
  frontmatter + wikilinks). The user opens their own vault if they want.
- **No automatic correction generation** — humans author corrections; the skill structures
  them. (The backtest *flags*, it does not author.)
- **No Loop B mining here** — Loop B consumes the format; that's its own spec.
- **No blanket retrofit** of every memory file — establish the vault convention and the
  `MEMORY.md` index; deep-link only where it earns its keep.
- **Override grammar stays small** — dotted paths with `[n]`/`[*]` and a scalar value; no
  arithmetic/expressions.
