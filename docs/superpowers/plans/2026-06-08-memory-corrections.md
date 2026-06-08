# Human Corrections & Vault-Friendly Memory — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Capture unprompted human corrections as typed, vault-native markdown memory that grounds future forecasts — a lean tested `pyfpa.memory` package + an `fpa-capture-correction` skill + integration into the existing skills.

**Architecture:** Hybrid. `pyfpa/memory/` owns the deterministic mechanics (a dotted-path config setter, the `Correction` model, markdown round-trip, and `apply_corrections`). The `fpa-capture-correction` skill owns judgment (classify the correction, draft the override, confirm interpretation). Corrections are plain markdown the user owns; Obsidian is an optional viewer, never required. All new code is pure, immutable, typed, unit-tested.

**Tech Stack:** Python 3.11+, pydantic v2, PyYAML (existing deps).

**Spec:** `docs/superpowers/specs/2026-06-08-memory-corrections-design.md`

---

## File Structure

| Path | Responsibility |
| --- | --- |
| `pyfpa/memory/__init__.py` (create) | Re-export the package's public names. |
| `pyfpa/memory/paths.py` (create) | `_set_by_path` — dotted-path setter with `[n]`/`[*]` support. |
| `pyfpa/memory/corrections.py` (create) | `Override`, `Correction`, `load_corrections`, `save_correction`, `apply_corrections`. |
| `pyfpa/__init__.py` (modify) | Export the public memory symbols. |
| `skills/fpa-capture-correction/SKILL.md` (create) | Conversational capture + the `.fpa/MEMORY.md` convention. |
| `skills/fpa-learn-business/SKILL.md` (modify) | Apply parametric corrections; route structural ones. |
| `skills/fpa-cfo-judgment/SKILL.md` (modify) | One-time screen reads `context` corrections. |
| `skills/fpa-backtest-learn/SKILL.md` (modify) | Monitor applied corrections; flag stale. |
| `README.md` (modify) | Surface the capture skill + memory in the skillset/roadmap. |
| `tests/test_memory_paths.py` (create) | Unit tests for the path setter. |
| `tests/test_memory_corrections.py` (create) | Unit tests for model, round-trip, apply. |
| `tests/test_public_api.py` (modify) | Keep the `__all__` contract test in sync. |

Conventions: immutability (return new objects), small focused files, clear names, pydantic v2. Tests live FLAT in `tests/`. Use `python3 -m pytest`.

---

## Group 1 — Dotted-path setter (`pyfpa/memory/paths.py`)

### Task 1: `_set_by_path`

Supports `name`, `name[n]` (list index), and `name[*]` (every list item). Used by `apply_corrections` to write a correction's override into a config dict.

**Files:**
- Create: `pyfpa/memory/__init__.py` (empty for now), `pyfpa/memory/paths.py`
- Test: `tests/test_memory_paths.py`

- [ ] **Step 1: Write the failing test**

```python
# tests/test_memory_paths.py
import pytest
from pyfpa.memory.paths import _set_by_path


def test_set_nested_scalar():
    data = {"working_capital": {"dio_days": 30.0}}
    _set_by_path(data, "working_capital.dio_days", 45.0)
    assert data["working_capital"]["dio_days"] == 45.0


def test_set_list_index():
    data = {"channels": [{"seasonality": [1.0] * 12}]}
    _set_by_path(data, "channels[0].seasonality[11]", 2.0)
    assert data["channels"][0]["seasonality"][11] == 2.0


def test_set_star_applies_to_all_list_items():
    data = {"channels": [{"cogs_pct": 0.5}, {"cogs_pct": 0.4}]}
    _set_by_path(data, "channels[*].cogs_pct", 0.6)
    assert [c["cogs_pct"] for c in data["channels"]] == [0.6, 0.6]


def test_bad_path_raises_valueerror():
    with pytest.raises(ValueError):
        _set_by_path({"a": {}}, "a.missing.deep", 1.0)
    with pytest.raises(ValueError):
        _set_by_path({"a": 1}, "a[", 1.0)  # malformed segment
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python3 -m pytest tests/test_memory_paths.py -v`
Expected: FAIL (`ModuleNotFoundError: pyfpa.memory`).

- [ ] **Step 3: Implement**

Create empty `pyfpa/memory/__init__.py`. Then `pyfpa/memory/paths.py`:

```python
from __future__ import annotations

import re

_SEGMENT = re.compile(r"^(\w+)(?:\[(\*|\d+)\])?$")


def _parse_path(path: str) -> list[tuple[str, str | int | None]]:
    parsed: list[tuple[str, str | int | None]] = []
    for segment in path.split("."):
        match = _SEGMENT.match(segment)
        if not match:
            raise ValueError(f"malformed override path segment: {segment!r}")
        key, index = match.group(1), match.group(2)
        if index is None:
            parsed.append((key, None))
        elif index == "*":
            parsed.append((key, "*"))
        else:
            parsed.append((key, int(index)))
    return parsed


def _set_segments(node, segments, value) -> None:
    (key, index), rest = segments[0], segments[1:]
    if not isinstance(node, dict) or key not in node:
        raise ValueError(f"override path key not found: {key!r}")
    if index is None:
        if rest:
            _set_segments(node[key], rest, value)
        else:
            node[key] = value
        return
    target = node[key]
    items = range(len(target)) if index == "*" else [int(index)]
    for i in items:
        if rest:
            _set_segments(target[i], rest, value)
        else:
            target[i] = value


def _set_by_path(data: dict, path: str, value: float) -> None:
    """Set `value` at `path` in `data` (in place). Supports dotted keys, `[n]`
    list indices, and `[*]` (every item of a list). Raises ValueError on any
    unresolvable or malformed path."""
    try:
        _set_segments(data, _parse_path(path), value)
    except (KeyError, IndexError, TypeError) as exc:
        raise ValueError(f"cannot apply override path {path!r}: {exc}") from exc
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `python3 -m pytest tests/test_memory_paths.py -v`
Expected: PASS (all four).

- [ ] **Step 5: Commit**

```bash
git add pyfpa/memory/__init__.py pyfpa/memory/paths.py tests/test_memory_paths.py
git commit -m "feat: dotted-path config setter for corrections (name, [n], [*])"
```

---

## Group 2 — Correction model + markdown round-trip (`pyfpa/memory/corrections.py`)

### Task 2: `Override` + `Correction` + `save_correction` / `load_corrections`

**Files:**
- Create: `pyfpa/memory/corrections.py`
- Test: `tests/test_memory_corrections.py`

- [ ] **Step 1: Write the failing test**

```python
# tests/test_memory_corrections.py
import pytest
from pyfpa.memory.corrections import (
    Override, Correction, save_correction, load_corrections,
)


def _correction():
    return Correction(
        slug="2026-06-08-december-seasonality",
        type="parametric",
        target="channels[*].seasonality[11]",
        status="applied",
        date="2026-06-08",
        override=Override(path="channels[*].seasonality[11]", value=2.0),
        notes="**Was off:** even spread.\n\n**Why:** [[business-profile#seasonality]]",
    )


def test_correction_round_trip(tmp_path):
    save_correction(_correction(), tmp_path)
    loaded = load_corrections(tmp_path)
    assert len(loaded) == 1
    c = loaded[0]
    assert c.slug == "2026-06-08-december-seasonality"
    assert c.type == "parametric"
    assert c.status == "applied"
    assert c.override == Override(path="channels[*].seasonality[11]", value=2.0)
    assert "Was off" in c.notes
    assert "[[business-profile#seasonality]]" in c.notes


def test_load_missing_dir_is_empty(tmp_path):
    assert load_corrections(tmp_path / "nope") == []


def test_structural_correction_has_no_override(tmp_path):
    c = Correction(slug="defrev", type="structural", target="revenue",
                   status="open", date="2026-06-08",
                   notes="**Was off:** double-counting deferred revenue.")
    save_correction(c, tmp_path)
    back = load_corrections(tmp_path)[0]
    assert back.type == "structural"
    assert back.override is None
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python3 -m pytest tests/test_memory_corrections.py -v`
Expected: FAIL (`ModuleNotFoundError`).

- [ ] **Step 3: Implement**

```python
# pyfpa/memory/corrections.py
from __future__ import annotations

from pathlib import Path
from typing import Literal

import yaml
from pydantic import BaseModel

CorrectionType = Literal["parametric", "structural", "context"]
CorrectionStatus = Literal["open", "applied", "superseded"]


class Override(BaseModel):
    path: str
    value: float


class Correction(BaseModel):
    """One human correction. Frontmatter fields are the machine-readable contract;
    `notes` is the human-readable markdown body."""
    slug: str
    type: CorrectionType
    target: str
    status: CorrectionStatus = "open"
    date: str
    override: Override | None = None
    notes: str = ""


def _split_frontmatter(text: str) -> tuple[dict, str]:
    if text.startswith("---"):
        _, frontmatter, body = text.split("---", 2)
        return yaml.safe_load(frontmatter) or {}, body.strip()
    return {}, text.strip()


def save_correction(correction: Correction, directory: str | Path) -> None:
    """Write `<slug>.md` (YAML frontmatter + markdown body) into `directory`."""
    directory = Path(directory)
    directory.mkdir(parents=True, exist_ok=True)
    data = correction.model_dump(exclude_none=True)
    body = data.pop("notes", "")
    data.pop("slug")
    text = "---\n" + yaml.safe_dump(data, sort_keys=False) + "---\n" + body + "\n"
    (directory / f"{correction.slug}.md").write_text(text)


def load_corrections(directory: str | Path) -> list[Correction]:
    """Load every `*.md` correction in `directory` (slug = filename stem).
    A missing directory returns an empty list."""
    directory = Path(directory)
    if not directory.exists():
        return []
    out: list[Correction] = []
    for path in sorted(directory.glob("*.md")):
        frontmatter, body = _split_frontmatter(path.read_text())
        out.append(Correction.model_validate({**frontmatter, "slug": path.stem, "notes": body}))
    return out
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `python3 -m pytest tests/test_memory_corrections.py -v`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add pyfpa/memory/corrections.py tests/test_memory_corrections.py
git commit -m "feat: Correction model + vault-native markdown round-trip"
```

---

## Group 3 — `apply_corrections`

### Task 3: apply parametric corrections to a config

**Files:**
- Modify: `pyfpa/memory/corrections.py`
- Test: `tests/test_memory_corrections.py`

- [ ] **Step 1: Write the failing test**

```python
# append to tests/test_memory_corrections.py
from pyfpa.config.schemas import EntityConfig
from pyfpa.memory.corrections import apply_corrections


def _cfg():
    return EntityConfig.model_validate({
        "name": "T", "start_month": "2026-01", "horizon_months": 12, "tax_rate": 0.0,
        "channels": [{"name": "C", "annual_revenue": 1_200_000.0, "growth_rate": 0.0,
                      "seasonality": [1.0] * 12, "cogs_pct": 0.5}],
        "opex": [], "debt": [],
        "working_capital": {"dso_days": 30.0, "dpo_days": 30.0, "dio_days": 30.0},
        "opening_balances": {"cash": 0.0},
    })


def test_apply_parametric_override_returns_new_cfg():
    cfg = _cfg()
    corr = Correction(slug="dio", type="parametric", target="working_capital.dio_days",
                      status="applied", date="2026-06-08",
                      override=Override(path="working_capital.dio_days", value=45.0))
    out = apply_corrections(cfg, [corr])
    assert out.working_capital.dio_days == 45.0
    assert cfg.working_capital.dio_days == 30.0          # input unmutated


def test_apply_star_seasonality():
    cfg = _cfg()
    corr = Correction(slug="dec", type="parametric", target="channels[*].seasonality[11]",
                      status="applied", date="2026-06-08",
                      override=Override(path="channels[*].seasonality[11]", value=2.0))
    out = apply_corrections(cfg, [corr])
    assert out.channels[0].seasonality[11] == 2.0


def test_apply_ignores_open_structural_context():
    cfg = _cfg()
    corrections = [
        Correction(slug="a", type="parametric", target="working_capital.dio_days",
                   status="open", date="2026-06-08",
                   override=Override(path="working_capital.dio_days", value=99.0)),
        Correction(slug="b", type="structural", target="revenue", status="applied",
                   date="2026-06-08"),
        Correction(slug="c", type="context", target="revenue", status="applied",
                   date="2026-06-08"),
    ]
    out = apply_corrections(cfg, corrections)
    assert out.working_capital.dio_days == 30.0          # nothing applied
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python3 -m pytest tests/test_memory_corrections.py::test_apply_parametric_override_returns_new_cfg -v`
Expected: FAIL (`ImportError`).

- [ ] **Step 3: Implement**

Add to the top of `pyfpa/memory/corrections.py`:

```python
from pyfpa.config.schemas import EntityConfig
from pyfpa.memory.paths import _set_by_path
```

Append:

```python
def apply_corrections(cfg: EntityConfig, corrections: list[Correction]) -> EntityConfig:
    """Return a NEW config with every `applied` + `parametric` correction's override
    written in. `open`, `structural`, and `context` corrections are ignored (the
    latter two are routed by the skill, not applied to the model). Input unmutated."""
    data = cfg.model_dump()
    for correction in corrections:
        if correction.status == "applied" and correction.type == "parametric" and correction.override:
            _set_by_path(data, correction.override.path, correction.override.value)
    return EntityConfig.model_validate(data)
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `python3 -m pytest tests/test_memory_corrections.py -v`
Expected: PASS (all six). Then full suite `python3 -m pytest -q`, no regressions.

- [ ] **Step 5: Commit**

```bash
git add pyfpa/memory/corrections.py tests/test_memory_corrections.py
git commit -m "feat: apply_corrections — parametric overrides into a new config"
```

---

## Group 4 — Package wiring

### Task 4: Re-export + public API

**Files:**
- Modify: `pyfpa/memory/__init__.py`, `pyfpa/__init__.py`, `tests/test_public_api.py`

- [ ] **Step 1: Fill `pyfpa/memory/__init__.py`**

```python
from pyfpa.memory.corrections import (
    Override, Correction, load_corrections, save_correction, apply_corrections,
)

__all__ = [
    "Override", "Correction", "load_corrections", "save_correction", "apply_corrections",
]
```

- [ ] **Step 2: Export from `pyfpa/__init__.py`** — after the existing `from pyfpa.backtest import ...` block add:

```python
from pyfpa.memory import (
    Override, Correction, load_corrections, save_correction, apply_corrections,
)
```

And extend `pyfpa/__init__.py`'s `__all__` with:

```python
    "Override", "Correction", "load_corrections", "save_correction", "apply_corrections",
```

- [ ] **Step 3: Sync the contract test** — `tests/test_public_api.py` asserts `set(pyfpa.__all__) == {expected}` (exact-set-equality). Add the same five names to that expected set. Read the test first; do NOT weaken the assertion.

- [ ] **Step 4: Verify + full suite**

Run: `python3 -c "import pyfpa; print(pyfpa.Correction, pyfpa.apply_corrections, pyfpa.load_corrections)"`
Expected: prints the three symbols.
Run: `python3 -m pytest -q`
Expected: all pass.

- [ ] **Step 5: Commit**

```bash
git add pyfpa/memory/__init__.py pyfpa/__init__.py tests/test_public_api.py
git commit -m "feat: export pyfpa.memory public API"
```

---

## Group 5 — Capture skill + integrations

### Task 5: `fpa-capture-correction` skill + the MEMORY.md convention

**Files:**
- Create: `skills/fpa-capture-correction/SKILL.md`

- [ ] **Step 1: Write `skills/fpa-capture-correction/SKILL.md`** with this content:

```markdown
---
name: fpa-capture-correction
description: Use when a human reviewing a forecast catches something off ("December always spikes", "you're double-counting deferred revenue", "that Q3 number was a one-time contract") — captures it as a durable, typed correction in the company's memory so future forecasts are grounded by it.
---

# Capture a Correction (Operate)

## Overview

A human reviewing a forecast is the highest-signal feedback there is — they catch
structural errors and domain knowledge the backtest can't see, and catch them *now*.
This skill turns that into durable memory: a typed correction in `.fpa/corrections/`
that grounds every future forecast.

**Core principle:** the human is the authority; capture, confirm interpretation once,
then it persists. Everything is plain markdown the user owns.

## The three correction types

- **parametric** — a concrete driver fix ("December runs ~2× a normal month"). Becomes
  an `override` (a config path + value) applied to every future forecast via
  `pyfpa.apply_corrections`.
- **structural** — a methodology fix ("you're double-counting deferred revenue"). A
  *pre-ratified* structural proposal (the human authored it) — route it to
  **fpa-learn-business** to generate the skill/model change; do NOT wait for backtest misses.
- **context** — a one-time-item note ("that Q3 spike was a one-off contract"). Annotates so
  **fpa-cfo-judgment**'s one-time screen keeps the backtest from "learning" a one-off.

## Workflow

1. **Classify** the correction (parametric / structural / context).
2. **Identify the target** — the driver path (e.g. `channels[*].seasonality[11]`,
   `working_capital.dio_days`), line, or profile area. For parametric, draft the concrete
   `override: {path, value}`.
3. **Write** the correction file `.fpa/corrections/<date>-<slug>.md`
   (`pyfpa.save_correction`) with frontmatter (`type`, `target`, `status`, `date`,
   `override`) and a markdown body (`**Was off:** … **Correction:** … **Why:** [[…]]`).
   Link the body to the assumption/profile it corrects with `[[wikilinks]]`.
4. **Confirm interpretation.** Echo back the concrete change ("I'll set December
   seasonality to 2.0 on all channels — right?"). Only on confirmation set
   `status: applied`.
5. **Keep `.fpa/MEMORY.md` current** — the vault index (see below).

## Applying corrections

When building any forecast, `pyfpa.apply_corrections(cfg, load_corrections(".fpa/corrections"))`
folds the applied parametric corrections into the config. The per-client loop refines from
there — corrections are *seeds*, not mandates.

## The `.fpa/` vault (`MEMORY.md` index)

Keep a `.fpa/MEMORY.md` that orients a human, Obsidian, or Claude:
- `business-profile.md` — what we know about the business.
- `corrections/` — human corrections (this skill).
- `forecasts/*.snapshot.yaml`, `scorecard.md` — forecast snapshots + backtest track record.
- `learnings.md` — accepted model changes.
All plain markdown — open it in Obsidian if you like, but never required.

## Guardrails

- Confirm interpretation before `applied`. Reversible via `status` (`open`/`applied`/`superseded`).
- The backtest *monitors* applied corrections and may flag a stale one — it never reverts;
  the human decides.

## Next

Correction captured → **fpa-monthly-close** / **fpa-board-briefing** (re-run grounded by it).
```

- [ ] **Step 2: Commit**

```bash
git add skills/fpa-capture-correction/
git commit -m "feat: fpa-capture-correction skill + .fpa vault (MEMORY.md) convention"
```

### Task 6: Wire corrections into the existing skills

**Files:**
- Modify: `skills/fpa-learn-business/SKILL.md`, `skills/fpa-cfo-judgment/SKILL.md`, `skills/fpa-backtest-learn/SKILL.md`

- [ ] **Step 1: fpa-learn-business** — in its workflow (after a model/config is built or refreshed), add a step:
  `Apply any existing corrections: `pyfpa.apply_corrections(cfg, pyfpa.load_corrections(".fpa/corrections"))` before forecasting; route `type: structural` corrections through this skill's generation path as pre-ratified proposals (the human already authored them).`
  Place it as a numbered step or a clearly-labeled paragraph consistent with the file's existing style (read the file first).

- [ ] **Step 2: fpa-cfo-judgment** — add a row to its judgment table (the markdown table of gotchas):
  `| **Known one-offs are flagged** | Read `.fpa/corrections/` for `type: context` notes (e.g. "Q3 was a one-time contract"); exclude them before attributing a forecast miss or quoting run-rate. |`

- [ ] **Step 2b: fpa-backtest-learn** — in its workflow (the score/attribute step), add a bullet:
  `Monitor applied corrections: if a `type: parametric` correction's target line keeps missing, flag it as possibly stale (`applied → superseded`) for the human — never auto-revert.`

- [ ] **Step 3: Verify the skills still parse** — each SKILL.md must keep valid YAML frontmatter:

Run: `python3 -c "import pathlib,yaml; [yaml.safe_load(p.read_text().split('---')[1]) for p in pathlib.Path('skills').glob('*/SKILL.md')]; print('ok')"`
Expected: `ok`.

- [ ] **Step 4: Commit**

```bash
git add skills/fpa-learn-business/SKILL.md skills/fpa-cfo-judgment/SKILL.md skills/fpa-backtest-learn/SKILL.md
git commit -m "feat: wire corrections into learn-business, cfo-judgment, backtest-learn"
```

---

## Group 6 — Docs + final

### Task 7: README surfacing

**Files:**
- Modify: `README.md`

- [ ] **Step 1: Add the skill to the skillset list** — in the "The skillset is the point" numbered list, add `fpa-capture-correction` to the **Operate** item with a gloss: "and **`fpa-capture-correction`** — turns a human's 'that's off because X' into durable memory that grounds future forecasts."

- [ ] **Step 2: Add a roadmap row** — in the "Project status & roadmap" table add:
  `| Human corrections + vault memory (\`pyfpa.memory\` + \`fpa-capture-correction\`) | ✅ Built |`

- [ ] **Step 3: Commit**

```bash
git add README.md
git commit -m "docs: surface human corrections + vault memory in the README"
```

### Task 8: Final verification + PR

- [ ] **Step 1: Full suite**

Run: `python3 -m pytest -q`
Expected: all green.

- [ ] **Step 2: Open the PR** (stacked on `feat/backtest-learning-loop`)

```bash
git push -u origin feat/memory-corrections
gh pr create --base feat/backtest-learning-loop --head feat/memory-corrections \
  --title "feat: human corrections + vault-friendly memory (pyfpa.memory + fpa-capture-correction)" \
  --body "Captures unprompted human corrections as typed, vault-native markdown in .fpa/corrections/. Parametric corrections apply to every future forecast via apply_corrections; structural become pre-ratified skill proposals; context annotates the one-time screen. Lean tested pyfpa.memory + fpa-capture-correction skill, wired into learn-business/cfo-judgment/backtest-learn. Obsidian-friendly, never required. Spec: docs/superpowers/specs/2026-06-08-memory-corrections-design.md. Stacked on the backtest loop."
```

Expected: PR opened. Jeff reviews/merges.

---

## Self-Review notes

- **Spec coverage:** Correction model + file format → Task 2. Three types + routing → Tasks 2,3,5,6. `apply_corrections` (applied+parametric only) → Task 3. Path grammar → Task 1. Capture skill + confirm-interpretation → Task 5. Vault `MEMORY.md` → Task 5. Integrations (learn-business apply+structural, cfo-judgment context, backtest monitor) → Task 6. README → Task 7. Loop-back (backtest flags, never reverts) → Task 6 step 2b. Guardrails → Tasks 3 (applied+parametric only), 5 (confirm), 6 (flag-not-revert). Testing list → Tasks 1,2,3.
- **Signature consistency:** `_set_by_path(data, path, value)`, `Override(path, value)`, `Correction(slug, type, target, status, date, override, notes)`, `load_corrections(dir)`, `save_correction(correction, dir)`, `apply_corrections(cfg, corrections)` — used identically across tasks.
- **Scope:** no Obsidian plugin, no auto-generation of corrections, no Loop B mining, no blanket retrofit, override grammar stays `[n]`/`[*]` + scalar — all honored.
