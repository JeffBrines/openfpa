---
name: sku-profitability
description: Use when analyzing which products make or lose money, ranking SKUs by margin or contribution, running a Pareto/80-20 on a product line, or deciding which SKUs to cut, reprice, or push in a product business.
---

# SKU Profitability

> **Generated skill (example).** This is the kind of bespoke skill `fpa-learn-business`
> proposes when the business profile says *"product company with a discrete SKU set."*
> It lives in `skills/generated/` - in a real engagement it would be written into the
> client's repo after human approval, citing the profile facts that justify it (here:
> a limited-SKU D2C brand where per-product economics drive the mix decision).

## Overview

The channel-level forecast tells you the business is healthy; it doesn't tell you *which products* carry it. This skill computes per-SKU economics and the Pareto curve so you can see the 80/20, find margin-dilutive SKUs, and make cut/reprice/push calls.

**Core principle:** Revenue flatters; margin and contribution decide. Rank by gross profit, not by sales.

## When to use

- "Which products actually make money?" / "what should we cut?"
- Product-mix, pricing, or assortment-rationalization decisions
- Any product business with a discrete SKU set (especially limited-SKU brands)

## Workflow

1. **Load the SKUs** (annual units, price, unit cost):
   ```python
   import pyfpa
   skus = pyfpa.load_skus("examples/ridgeline/skus.yaml")   # or build [Sku(...)] inline
   df = pyfpa.sku_profitability(skus)
   ```
   `df` is sorted by gross profit (desc), indexed by SKU, with columns: `units, revenue,
   cogs, gross_profit, gross_margin, revenue_share, cumulative_revenue_pct`.

2. **Find the 80/20**:
   ```python
   n = pyfpa.pareto_breakpoint(df, threshold=0.8)   # SKUs that make 80% of revenue
   ```

3. **Read the signals**:
   - **Top of the list** (high gross profit) - protect and push these.
   - **High revenue, low `gross_margin`** - reprice or renegotiate cost; they're buying share with your margin.
   - **Low `revenue_share` AND low margin** - candidates to cut (carrying cost without contribution).
   - **The Pareto tail** - if the bottom SKUs add complexity (SKUs to manage, inventory to hold) without margin, rationalize them.

4. **Recommend** in business terms: which SKUs to push, reprice, or discontinue, and the margin impact of each move.

## Judgment checks (see fpa-cfo-judgment)

- `gross_margin` here is **per-unit price minus unit cost** - it excludes channel fees, returns, and fulfillment. A D2C SKU and a wholesale SKU at the same listed margin are not equally profitable once channel economics hit.
- A "high-margin" SKU with tiny volume may not be worth the operational complexity it adds. Weigh contribution dollars, not just the percentage.
