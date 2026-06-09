# The AI is the analyst. We built its toolbelt.

*Open-sourcing openfpa, an agent-native FP&A workbench. By [Guiderail](https://www.guiderail.io).*

---

Every founder has lived this: you don't need a full-time CFO yet, but you absolutely need CFO-grade answers. *When do we run out of cash? Can we afford this hire? What does the board need to see?* The honest answer is usually a spreadsheet someone built once, nobody fully trusts, and everyone is afraid to touch.

Here's the thing we eventually admitted to ourselves: the AI coding agents are already good enough to do this work. Claude Code or Codex, pointed at your books, can interview you, write a model, and explain a variance. The agent is the superhero. What it's missing is the toolbelt: the tested accounting math, the working method, the memory, and the checks that separate a real analyst from a very confident intern.

So instead of building another FP&A *app*, we built the toolbelt.

## What the toolbelt holds

openfpa gives the agent four things a bare chat session doesn't have:

- **A tested finance kernel.** Revenue, COGS, opex, working capital, debt, tax, and cash flow live in one regression-tested place, so the accounting is not re-derived (differently) every run.
- **An operating contract.** Rules for how the agent inspects evidence before asking questions, registers data sources, reconciles before forecasting, and asks a human before promoting anything.
- **Durable memory.** What it learns about your business, your corrections, its own forecast track record, all of it lives as plain files in your repo. The agent is not reset every session.
- **A research loop.** Forecast hypotheses are scored against held-out actuals, champion versus challenger. Weak challengers are kept as failed research. Promotion requires evidence and your sign-off.

The agent still does the thinking. It asks the questions, writes the company-specific code, and makes the judgment calls. The toolbelt makes that work auditable, repeatable, and cumulative.

## It re-tools itself for your business

The part that still surprises us: when the standard tools don't fit a company, the agent extends the toolbelt, in reviewable code, with the reasoning written down.

The committed proof lives in the Fox Factory example below. Fox reports segment Adjusted EBITDA under ASU 2023-07, not segment gross profit, which is a company shape the base kernel didn't ship with. The agent wrote itself a `segment-rollup` skill to handle it, citing the filing facts that justified the design. Self-extending, with a human gate; never self-executing.

## It thinks like a CFO, not a calculator

A model that's arithmetically perfect can still be wrong about reality. The judgment layer encodes the reflexes a seasoned finance person applies without thinking:

- *That month looks suspiciously profitable?* It's probably unposted COGS, not real margin. Don't celebrate a month that isn't closed.
- *EBITDA looks great?* EBITDA isn't cash. It ignores capex, the working-capital swing, and debt service. A banner EBITDA quarter can still burn cash.
- *Cash went negative in week 3?* That means "you need a credit line," not "you're insolvent." Say which.

## The cash-runway answer founders actually lose sleep over

The demo company, *Ridgeline Chair Co.* (a fictional premium camping-chair brand), shows the punchline. Its 13-week cash forecast goes **negative in week 3**, as the spring inventory build lands before the summer sell-through collects, troughs at **-$146K**, then recovers. The model doesn't paper over it with an automatic credit-line draw. It shows the raw hole, because the hole *is* the answer: size a roughly $150K to $200K line to bridge the build.

## "Couldn't I just point Claude at my 10-K myself?"

You could. Claude is a strong analyst. But a bare agent writes a *fresh* pile of pandas every run: no shared structure, no test, no audit trail. Correctness by luck of the run, and the wrong number looks right.

So we pushed the toolbelt at the opposite of a friendly demo: **Fox Factory (NASDAQ: FOXF)**, a real $1.5B public company with three segments, a debt-funded acquisition (Marucci), and a $557M goodwill impairment that turned a revenue-recovery year into a GAAP net loss. Pulled straight from its SEC filings, openfpa:

1. **Separated accounting reproduction from forecast validation.** Feeding the kernel Fox's reported drivers reproduces FY2024 and FY2025 operating mechanics, and the demo explicitly says this is an arithmetic check, not proof of predictive skill.
2. **Ran an FY2025 historical holdout.** Using FY2023 and FY2024 only, the research loop rejected an over-aggressive recovery hypothesis, refined it, and proposed a challenger that improved every weighted holdout metric.
3. **Was honest about the rest.** The impairment and Fox's discrete tax benefits are shown as an explicit bridge, not laundered through the model. A lean kernel should model the operating business and *say* what it doesn't.
4. **Forecast FY2026 and FY2027 at the segment level**, preserved working-capital continuity across the year boundary, and modeled a "what if Fox sells Marucci" cash-flow and leverage sensitivity.
5. **Extended itself**, writing the `segment-rollup` skill described above.

Here's the part a one-off analysis usually lacks: **the proof runs in CI.** Every push, on three Python versions, checks the arithmetic reproduction, historical holdout behavior, segment rollup, and forecast continuity.

And it earned that test. Mid-build, the kernel had a subtle bug: it added depreciation back into operating cash flow without ever expensing it, silently inflating cash. That is *exactly* the error a one-shot agent emits and nobody catches. openfpa caught it because the logic lives in one tested place; the fix landed once, and a test now guarantees it never comes back. That's the whole point of a substrate: correctness becomes a property of the system, not a coin flip on each run.

> Bare Claude is a capable analyst with a blank spreadsheet. openfpa is the tested model kernel, the encoded house methodology, and the review checklist. Rails to drive on, and gauges that catch the mistakes.

## Why open-source it?

Because the most credible thing you can say about being on the frontier is to show your work, and then let people check it. The kernel is regression-tested Python built to be read and extended by an agent, not an app you configure by hand. The demo runs on synthetic data. The Fox Factory proof runs on nothing but public SEC filings, fully source-traced. Adapters for NetSuite, QuickBooks, and Shopify ship as fixture-backed scaffolds that document their live paths, and the agent builds the real connector for whatever source you actually have. The whole thing installs as a Claude plugin.

Clone it. Point your agent at it. Hand it your numbers. See what they build together.

→ **github.com/JeffBrines/openfpa** · MIT licensed · built by [Guiderail](https://www.guiderail.io)

*The forecast kernel, the 13-week cash model, the data adapters, and the agent skills are regression-tested, including the Fox Factory actual-driver reproduction, historical holdout, and forecast-continuity checks. The Fox run above was a real run, not a script.*
