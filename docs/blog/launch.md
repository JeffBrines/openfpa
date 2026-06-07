# I gave Claude a 10-minute intake call and it built itself a CFO

*Open-sourcing openfpa — an AI-native FP&A toolkit. By Guiderail.*

---

Every founder has lived this: you don't need a full-time CFO yet, but you absolutely need CFO-grade answers. *When do we run out of cash? Can we afford this hire? What does the board need to see?* The honest answer is usually a spreadsheet someone built once, nobody fully trusts, and everyone is afraid to touch.

So I tried something. Instead of building another FP&A *app*, I built an FP&A **skillset** — and handed it to an AI.

## The toolkit re-tools itself for your business

The headline isn't the forecast engine. It's this: **the toolkit writes its own tooling for your company.**

The first skill, `fpa-learn-business`, runs before any modeling. It interviews the operator, reads whatever financials exist, and writes a durable *business profile*. Then it does the part that still surprises me — it looks at *your* business and proposes new, bespoke skills that the generic toolkit doesn't ship.

To prove this wasn't a demo rigged for one company, I spun up a **fresh AI agent with zero context** — it had never seen the repo — and gave it a 10-minute intake for a fictional coffee roaster, *Harbor & Vine*. With nothing but the skillset, it:

1. Wrote the business profile from the conversation.
2. Built a runnable financial model (two channels, holiday-skewed D2C, an equipment loan, a 60-day green-coffee inventory cycle) and produced a clean 12-month P&L and cash forecast — **$3.6M revenue, 10.7% EBITDA**.
3. Generated a board-ready briefing.
4. And then proposed a skill I never wrote: a **`green-coffee-cogs-model`** — because, it reasoned, "green coffee is a commodity purchased forward; a fixed COGS percentage will be wrong every time the ICE arabica market moves, and they hold 60 days of inventory, so future COGS is already largely locked in."

That's a real finance insight about a business it learned about ten minutes earlier — and a correct instinct to extend its own tooling to handle it. It even refused to *write* the skill without human approval, exactly as designed. Self-extending, not self-executing.

## It thinks like a CFO, not a calculator

A model that's arithmetically perfect can still be wrong about reality. The skill I'm proudest of is `fpa-cfo-judgment` — the reflexes a seasoned finance person applies without thinking:

- *That month looks suspiciously profitable* → it's probably unposted COGS, not real margin. Don't celebrate a month that isn't closed.
- *EBITDA looks great* → this lean model has no D&A line, so that's really EBIT — don't quote it to a lender doing DSCR math.
- *Cash went negative in week 3* → that's "you need a credit line," not "you're insolvent." Say which.

The cold agent caught the working-capital timing trap on Harbor & Vine on its own, using exactly these checks. That's the difference between AI that does math and AI that does finance.

## The cash-runway answer founders actually lose sleep over

The demo company, *Ridgeline Chair Co.* (a fictional premium camping-chair brand), shows the punchline. Its 13-week cash forecast goes **negative in week 3** — the spring inventory build lands before the summer sell-through collects — troughs at **−$146K**, then recovers. The model doesn't paper over it with an automatic credit-line draw. It shows the raw hole, because the hole *is* the answer: *size a ~$150–200K line to bridge the build.*

## Why open-source it?

Because the most credible thing you can say about being on the frontier is to show your work. The engine is deliberately lean — a few hundred lines of pure, tested Python — because it's a substrate for an AI to extend, not an app to configure. It runs entirely on synthetic data; it speaks NetSuite, QuickBooks, and Shopify when you connect them; and the whole thing installs as a Claude plugin.

Clone it. Point Claude at it. Hand it your numbers. Watch it build you a CFO.

→ **github.com/JeffBrines/openfpa** · MIT licensed · built by Guiderail

*The forecast engine, the 13-week cash model, the data adapters, and all seven skills were built test-first with adversarial review at every step. 63 tests, all green. The cold-agent walkthrough above was a real run, not a script.*
