# Sources

All figures pulled from SEC EDGAR for **Fox Factory Holding Corp. (CIK 1424929)**.
Regenerate with `python3 examples/foxfactory/pull_edgar.py`.

## Consolidated income statement, balance sheet, cash flow

XBRL company-concept API, e.g.:
`https://data.sec.gov/api/xbrl/companyconcept/CIK0001424929/us-gaap/<TAG>.json`

Filed in these 10-Ks:
- FY2023 (period end 2023-12-29): accession 000142492924000006
- FY2024 (period end 2025-01-03): accession 000142492925000007
- FY2025 (period end 2026-01-02): accession 000142492926000012
- Q1 FY2026 (period end 2026-04-03): latest 10-Q (most recent quarterly value per concept)

## Segment net sales + Adjusted EBITDA

FY2025 10-K segment footnote: https://www.sec.gov/Archives/edgar/data/1424929/000142492926000012/R106.htm
(Fox reports segment **Adjusted EBITDA** under ASU 2023-07 — not segment gross
profit or operating income. The table carries FY2023-FY2025.)

## Marucci acquisition anchor (Phase C divestiture)

FY2023 10-K acquisitions footnote: https://www.sec.gov/Archives/edgar/data/1424929/000142492924000006/R97.htm
- Acquired 2023-11-14; total consideration **$567,194K** (cash $567,092K).
- Goodwill $244,790K; finite-lived intangibles $279,100K; inventory $44,972K.
- Pro-forma (R98): combined FY2023 sales with full-year Marucci ~$1,632,076K.
