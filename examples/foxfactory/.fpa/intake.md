---
schema_version: 1
business_name: Fox Factory Holding Corp.
facts:
- key: business_model
  topic: business
  question: What does the company sell, and who are the primary customers?
  answer: Fox designs and manufactures premium ride-dynamics products and sports equipment
    for OEM, aftermarket, and specialty-sports customers.
  status: inferred
  confidence: 0.85
  source_type: local_file
  sources:
  - data/SOURCES.md
  - .fpa/business-profile.md
  alternatives: []
- key: revenue_model
  topic: business
  question: How is revenue earned and billed, including pricing and payment terms?
  answer: Revenue is primarily product sales reported across PVG, AAG, and SSG; detailed
    customer billing terms are not publicly disclosed.
  status: inferred
  confidence: 0.85
  source_type: local_file
  sources:
  - data/SOURCES.md
  - .fpa/business-profile.md
  alternatives: []
- key: customer_channels
  topic: business
  question: Which channels, products, or segments should the model distinguish?
  answer: Model PVG, AAG, and SSG as distinct operating segments.
  status: inferred
  confidence: 0.85
  source_type: local_file
  sources:
  - data/SOURCES.md
  - .fpa/business-profile.md
  alternatives: []
- key: collections
  topic: cash_cycle
  question: When do customers usually pay, and what causes collections to vary?
  answer: FY2025 year-end receivables imply about 47 days sales outstanding; customer-level
    collection timing is not public.
  status: inferred
  confidence: 0.85
  source_type: local_file
  sources:
  - data/SOURCES.md
  - .fpa/business-profile.md
  alternatives: []
- key: supplier_payments
  topic: cash_cycle
  question: When are suppliers, payroll, inventory, and other major obligations paid?
  answer: FY2025 payables imply about 50 days payable outstanding, with a material
    inventory purchasing cycle.
  status: inferred
  confidence: 0.85
  source_type: local_file
  sources:
  - data/SOURCES.md
  - .fpa/business-profile.md
  alternatives: []
- key: seasonality
  topic: cash_cycle
  question: What is seasonal or lumpy across revenue, costs, inventory, and cash?
  answer: Demand is cyclical and exposed to powersports and bicycle channel inventory
    cycles; the public demo has limited intra-year history.
  status: inferred
  confidence: 0.85
  source_type: local_file
  sources:
  - data/SOURCES.md
  - .fpa/business-profile.md
  alternatives: []
- key: entities
  topic: finance_structure
  question: Which legal entities, currencies, and intercompany relationships matter?
  answer: The demo models the consolidated USD public company on its 52/53-week fiscal
    calendar.
  status: inferred
  confidence: 0.85
  source_type: local_file
  sources:
  - data/SOURCES.md
  - .fpa/business-profile.md
  alternatives: []
- key: financing
  topic: finance_structure
  question: What debt, credit lines, covenants, or other financing is in place?
  answer: Fox uses a term loan and revolver and ended FY2025 with about $524M of total
    debt.
  status: inferred
  confidence: 0.85
  source_type: local_file
  sources:
  - data/SOURCES.md
  - .fpa/business-profile.md
  alternatives: []
- key: data_sources
  topic: finance_structure
  question: Which systems and files contain the financial and operating actuals?
  answer: Committed CSV files derived from source-traced SEC 10-K and 10-Q filings.
  status: inferred
  confidence: 0.85
  source_type: local_file
  sources:
  - data/SOURCES.md
  - .fpa/business-profile.md
  alternatives: []
- key: planning_cadence
  topic: planning
  question: How often do you close, reforecast, report, and make planning decisions?
  answer: The public evidence supports quarterly reporting and annual forecasting;
    Fox's internal planning cadence is not public.
  status: inferred
  confidence: 0.85
  source_type: local_file
  sources:
  - data/SOURCES.md
  - .fpa/business-profile.md
  alternatives: []
- key: cfo_priorities
  topic: planning
  question: Which decisions, risks, or questions matter most to the CFO right now?
  answer: Restore segment margins, deleverage after the Marucci acquisition, and evaluate
    portfolio allocation.
  status: inferred
  confidence: 0.85
  source_type: local_file
  sources:
  - data/SOURCES.md
  - .fpa/business-profile.md
  alternatives: []
---
