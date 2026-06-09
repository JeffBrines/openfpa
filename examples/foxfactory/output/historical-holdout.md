# Phase B — FY2025 historical holdout research

The research loop fits only on FY2023-FY2024 and holds FY2025 out.
The champion is a flat FY2024 run rate. Each challenger is scored on
revenue, gross profit, Adjusted EBITDA, and working-capital balances,
with accounting checks required and a complexity penalty applied.

| Epoch | Hypothesis | Status | Objective gain |
|---|---|---:|--:|
| foxf-fy2025-001-broad-mean-reversion | After the FY2024 trough, both segment revenue and margins recover halfway toward FY2023. | discarded | -530.0% |
| foxf-fy2025-002-slow-margin-recovery | After the FY2024 trough, segment revenue partially mean-reverts toward FY2023 while margins recover much more slowly. | proposed | +61.4% |

## What the loop learned

- **Epoch 1 was discarded.** It improved revenue and gross profit but
  over-recovered segment margins, worsening Adjusted EBITDA error from
  1.0%
  to 20.4%.
- **Epoch 2 separated sales recovery from margin recovery.** Revenue moves
  halfway toward FY2023, but margins recover only 5%. That challenger
  improves the weighted holdout objective by
  61.4% and passes every hard check.
- The challenger remains **proposed**, not promoted. A human would decide
  whether its recovery logic should become the champion.

## Champion vs strongest challenger

| Metric | Flat FY2024 champion | Recovery challenger |
|---|--:|--:|
| Revenue error | 5.0% | 2.6% |
| Gross profit error | 4.4% | 0.2% |
| Adjusted EBITDA error | 1.0% | 0.1% |
| Working-capital balance error | 7.0% | 6.3% |

> This is a deliberately small annual holdout with three historical years.
> It demonstrates the research discipline, not production-grade statistical certainty.
