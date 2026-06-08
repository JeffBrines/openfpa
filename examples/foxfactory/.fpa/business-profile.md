# Business Profile — Fox Factory Holding Corp. (NASDAQ: FOXF)

> Produced by the `fpa-learn-business` phase. Every openfpa skill reads this
> first. Grounded entirely in Fox's SEC filings (CIK 1424929); figures trace to
> `data/SOURCES.md`.

## Entity

Fox Factory Holding Corp. designs and manufactures premium ride-dynamics products
(suspension, components) and, since 2023, premium baseball/softball equipment.
52/53-week fiscal year ending the Sunday nearest Dec 31. Reports in three segments.

## Segments (ASU 2023-07: net sales + Adjusted EBITDA disclosed; no segment COGS)

| Segment | What it sells | FY2025 net sales | FY2025 Adj EBITDA margin |
|---|---|--:|--:|
| **PVG** — Powered Vehicles Group | Off-road / powersports OEM + aftermarket shocks | $488M | 12.8% |
| **AAG** — Aftermarket Applications Group | Custom vehicle suspension, lift kits, upfitting, wheels & tires | $470M | 11.9% |
| **SSG** — Specialty Sports Group | Performance mountain/e-bike/gravel components **+ Marucci** baseball/softball | $509M | 21.1% |

## The trajectory that drives everything

Net sales: FY2021 $1,299M → **FY2022 $1,602M (peak)** → FY2023 $1,464M →
**FY2024 $1,394M (trough)** → FY2025 $1,467M (recovery). A classic post-COVID
powersports + bike **destocking** cycle. Two segment stories matter most:

- **AAG air pocket:** Adjusted EBITDA collapsed from $127M (FY2023) to $52M
  (FY2024) — the aftermarket/powersports demand and channel-inventory correction.
  Only a partial recovery to $56M in FY2025.
- **SSG held flat only because of Marucci:** the bike market fell hard, but the
  Nov-2023 Marucci acquisition backfilled net sales (SSG $389M → $511M → $509M).

## Marucci acquisition (Nov 14, 2023)

Total consideration **$567.2M** (cash), adding $244.8M goodwill and $279.1M of
finite-lived intangibles. Debt-funded — interest expense jumped from $19M (FY2023)
to $55M (FY2024) and the term-loan balance to ~$552M. Marucci is **not reported
standalone**; it lives inside SSG.

## The FY2025 impairment

A **$557.3M non-cash goodwill impairment** drove GAAP operating income to -$522.9M
and a -$544.6M net loss in FY2025 — *even though revenue recovered*. Goodwill fell
from $639.5M to $83.6M. This is the single biggest "watch out" in the financials:
the headline loss is non-cash and must be separated from operating performance.

## Cost structure & working capital

- Blended gross margin ~30% (FY2025 COGS $1,024M on $1,467M sales).
- Opex: G&A $152M, R&D $69M (FY2025), plus selling and amortization.
- D&A ~$92M (elevated by Marucci intangible amortization); capex ~$34-47M.
- Working capital is inventory-heavy (the destocking story): inventory ran
  $350-405M. Implied FY2025 days: DSO ~47, DIO ~137, DPO ~50 (360-day basis).

## Financing

Term loan + revolver, ~$524M total debt at FY2025 (down from $552M FY2024 as Fox
deleverages). Effective all-in interest cost ~10% including fees; ~$25M/yr
scheduled amortization. Deleveraging is a stated priority post-Marucci.

## What keeps the CFO up at night

1. Restoring AAG/powersports margins to mid-cycle.
2. Deleveraging the Marucci debt while demand is soft.
3. Whether SSG (bikes + Marucci) is the right portfolio — the capital-allocation
   question the Phase C divestiture sensitivity frames.

## Gaps the standard skills don't cover → bespoke skills generated

- Multi-segment company with no segment COGS → **`segment-rollup`** skill
  (net sales + Adjusted EBITDA per segment → consolidated). See
  `skills/generated/segment-rollup/`.
