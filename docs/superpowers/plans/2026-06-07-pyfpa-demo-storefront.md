# Storefront & Runnable Demo Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development to implement the testable tasks. Prose tasks (README, LICENSE) are authored directly by the controller.

**Goal:** Make the repo a presentable, runnable storefront — the thing a VC/CFO clones and runs in one command and goes "oh shit." Add a one-command demo runner, an end-to-end output test, a MIT LICENSE, and a README that sells the project.

**Architecture:** A `run_demo(output_dir)` function wires the full pipeline (config → monthly forecast → cash13 → runway → briefing → Excel) and writes artifacts. The README documents quickstart, the demo, architecture, the "connect your stack" story, and the roadmap, with Guiderail attribution.

**Tech Stack:** existing `pyfpa` (engine + cash13 + io). No new deps.

---

## File Structure

```
examples/ridgeline/
└── run_demo.py            # run_demo(output_dir) -> dict ; __main__ block
tests/
└── test_demo_runner.py    # asserts run_demo writes briefing.md + forecast.xlsx with locked headline
README.md                  # the storefront (authored directly)
LICENSE                    # MIT (authored directly)
docs/demo/
└── ridgeline_briefing.md  # committed sample output (so people see it without running)
```

---

## Task 1: Demo runner + end-to-end test

**Files:**
- Create: `examples/ridgeline/run_demo.py`
- Test: `tests/test_demo_runner.py`

`run_demo(output_dir)` loads the Ridgeline config + cash13 schedule, builds the monthly forecast, the 13-week forecast, and the runway summary, renders the briefing markdown, writes `briefing.md` and `forecast.xlsx` into `output_dir`, and returns a dict of the key figures (so it's testable). The `__main__` block writes into `docs/demo/`.

- [ ] **Step 1: Write the failing test `tests/test_demo_runner.py`**

```python
import importlib.util
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
_SPEC = importlib.util.spec_from_file_location(
    "run_demo", REPO_ROOT / "examples/ridgeline/run_demo.py"
)


def _load_run_demo():
    module = importlib.util.module_from_spec(_SPEC)
    _SPEC.loader.exec_module(module)
    return module.run_demo


def test_run_demo_writes_artifacts(tmp_path):
    run_demo = _load_run_demo()
    result = run_demo(tmp_path)
    briefing = tmp_path / "briefing.md"
    excel = tmp_path / "forecast.xlsx"
    assert briefing.exists()
    assert excel.exists()
    # returned figures match the locked golden numbers
    assert result["revenue_total"] == 6_000_000
    assert result["runway_min_cash"] == -146_000
    assert result["runway_first_negative_week"] == 3
    # briefing file contains the headline and runway section
    text = briefing.read_text()
    assert "# Ridgeline Chair Co." in text
    assert "## 13-Week Cash Runway" in text
```

- [ ] **Step 2: Run test to verify it fails**

Run: `.venv/bin/pytest tests/test_demo_runner.py -v`
Expected: FAIL with `FileNotFoundError`/`AttributeError` (run_demo.py doesn't exist)

- [ ] **Step 3: Write `examples/ridgeline/run_demo.py`**

```python
"""Run the full pyfpa pipeline on the synthetic Ridgeline Chair Co. demo.

Usage:
    python examples/ridgeline/run_demo.py
Writes a markdown CFO briefing and an Excel forecast into docs/demo/.
"""
from __future__ import annotations

from pathlib import Path

import pyfpa
from pyfpa.io.loaders import load_cash13_config
from pyfpa.io.reporting import forecast_to_excel, to_briefing_md

_HERE = Path(__file__).resolve().parent
_REPO_ROOT = _HERE.parents[1]
_TITLE = "Ridgeline Chair Co."


def run_demo(output_dir: str | Path) -> dict:
    """Build the monthly + 13-week forecasts, render the briefing, and write
    briefing.md + forecast.xlsx into output_dir. Returns key figures."""
    out = Path(output_dir)
    out.mkdir(parents=True, exist_ok=True)

    monthly = pyfpa.cashflow_from_config(
        pyfpa.load_config(_HERE / "config.yaml")
    )
    cash13 = pyfpa.cash13_forecast(load_cash13_config(_HERE / "cash13.yaml"))
    runway = pyfpa.runway_summary(cash13)

    briefing = to_briefing_md(monthly, title=_TITLE, runway=runway)
    (out / "briefing.md").write_text(briefing)
    forecast_to_excel(monthly, out / "forecast.xlsx")

    return {
        "revenue_total": round(monthly["revenue"].sum()),
        "ebitda_total": round(monthly["ebitda"].sum()),
        "net_income_total": round(monthly["net_income"].sum()),
        "ending_cash_dec": round(monthly["ending_cash"].iloc[-1]),
        "runway_min_cash": round(runway["min_cash"]),
        "runway_min_week": runway["min_week"],
        "runway_first_negative_week": runway["first_negative_week"],
    }


if __name__ == "__main__":
    figures = run_demo(_REPO_ROOT / "docs/demo")
    print(f"Wrote briefing.md + forecast.xlsx to docs/demo/")
    for key, value in figures.items():
        print(f"  {key}: {value}")
```

- [ ] **Step 4: Run test to verify it passes**

Run: `.venv/bin/pytest tests/test_demo_runner.py -v`
Expected: PASS (1 passed)

- [ ] **Step 5: Generate the committed sample output**

Run: `.venv/bin/python examples/ridgeline/run_demo.py`
Expected: prints the figures and writes `docs/demo/briefing.md` + `docs/demo/forecast.xlsx`.

- [ ] **Step 6: Commit** (do NOT commit the generated .xlsx — keep only the markdown sample)

```bash
printf '\ndocs/demo/*.xlsx\n' >> .gitignore
git add examples/ridgeline/run_demo.py tests/test_demo_runner.py docs/demo/briefing.md .gitignore
git commit -m "feat: add one-command Ridgeline demo runner + sample briefing"
```

---

## Task 2: MIT LICENSE (authored directly by controller)

- [ ] Create `LICENSE` with the standard MIT license text, copyright "Guiderail".
- [ ] Commit: `git add LICENSE && git commit -m "docs: add MIT license"`

---

## Task 3: README storefront (authored directly by controller)

- [ ] Create `README.md` covering: one-line pitch + the "oh shit" hook; what it is (AI-native FP&A toolkit — skillset + lean engine); quickstart (`pip install -e .` + `python examples/ridgeline/run_demo.py`); the demo (paste the briefing headline + runway); architecture (engine layers + cash13 + io); "connect your real stack" (NetSuite/QuickBooks/Shopify adapters); roadmap (skills coming); MIT + "by Guiderail" attribution.
- [ ] Keep claims accurate to what's built (engine, cash13, io, demo). Mark the skillset as "coming next" — do not claim it exists yet.
- [ ] Commit: `git add README.md && git commit -m "docs: add storefront README"`

---

## Definition of Done

- [ ] `.venv/bin/pytest -q` green (63 tests).
- [ ] `python examples/ridgeline/run_demo.py` writes `docs/demo/briefing.md` + `docs/demo/forecast.xlsx` and prints locked figures.
- [ ] README renders the pitch, quickstart, demo output, and roadmap; LICENSE present.
- [ ] No generated `.xlsx` committed (gitignored); the sample `briefing.md` IS committed.

---

## Notes for the final plan (Plan 5 — the hero)

The 7 skills (`fpa-learn-business` headliner → scaffold → configure → operate + `fpa-cfo-judgment`), `.claude-plugin/plugin.json`, plugin packaging, and the launch blog post. The README's "coming next" section gets upgraded to "here's the skillset" then.
