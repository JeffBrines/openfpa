# Initial Model Architecture

**Status:** Approved for the public Fox Factory worked example.

## Objective

Demonstrate a source-traced public-company workflow with separate accounting
reproduction, historical holdout research, forward forecasting, and capital
allocation sensitivity.

## Data Access

- Committed CSV extracts sourced from SEC 10-K and 10-Q filings.
- `pull_edgar.py` refreshes the public source data.
- `data/SOURCES.md` preserves the filing trail.

## Model Components

- Consolidated finance kernel for revenue, COGS, working capital, debt, and cash.
- Generated PVG, AAG, and SSG segment rollup.
- FY2025 champion and challenger holdout evaluation.
- FY2026-FY2027 forward forecast.
- Marucci divestiture sensitivity.

## Validation

- Source and segment rollups.
- Actual-driver accounting reproduction.
- Held-out FY2025 forecast metrics.
- Working-capital continuity across forecast years.
- Full regression suite in CI.
