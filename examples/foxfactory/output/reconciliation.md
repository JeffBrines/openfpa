# Phase A — Actual-driver accounting reproduction

The pyfpa engine is driven with Fox Factory's **actual** reported drivers
(segment net sales, blended COGS%, working-capital days, D&A, capex) and
its output is compared to the reported figures. This proves the accounting
mechanics reproduce known outcomes; it is **not** an independent forecast
validation because the target-year drivers are inputs. Tolerance: 1%.

## FY2024

| Line | Model | Reported | Variance | Tie |
|---|--:|--:|--:|:--:|
| net_sales | $1,393.9M | $1,393.9M | -0.00% | yes |
| gross_profit | $423.6M | $423.6M | -0.00% | yes |
| adjusted_ebitda | $223.4M | $223.4M | +0.00% | yes |
| depreciation_amortization | $83.6M | $83.6M | -0.00% | yes |
| capex | $44.0M | $44.0M | +0.00% | yes |
| operating_cash_flow_before_tax | $227.4M | $227.4M | -0.00% | yes |

## FY2025

| Line | Model | Reported | Variance | Tie |
|---|--:|--:|--:|:--:|
| net_sales | $1,467.3M | $1,467.3M | +0.00% | yes |
| gross_profit | $443.2M | $443.2M | +0.00% | yes |
| adjusted_ebitda | $225.7M | $225.7M | +0.00% | yes |
| depreciation_amortization | $92.3M | $92.3M | +0.00% | yes |
| capex | $34.0M | $34.0M | +0.00% | yes |
| operating_cash_flow_before_tax | $222.5M | $222.5M | +0.00% | yes |

## What the engine does not model (documented bridge)

- **FY2025 goodwill impairment of $557.3M** (non-cash) — drove GAAP operating
  income to -$522.9M and a -$544.6M net loss even as revenue recovered. The
  lean engine models the operating business; the impairment is a discrete
  non-cash item shown here, not forced through the engine.
- **Discrete tax items** — Fox booked tax *benefits* in FY2024/FY2025; the
  engine's tax model only taxes positive income, so net income is bridged
  separately, not reconciled here.
- This phase therefore validates the **operating arithmetic and the
  working-capital cash mechanic**, while Phase B below provides the
  independent historical holdout.
