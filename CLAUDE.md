# openfpa Agent Instructions

Follow `AGENTS.md` as the repository operating contract.

For broad company work such as setup, modeling, forecasting, or FP&A analysis:

1. Run `openfpa status <company-root>`.
2. If needed, run `openfpa init <company-root> --business-name "<name>"`.
3. Run `openfpa doctor <company-root>`.
4. Run `openfpa inspect-data <data-root>` for each supplied data location.
5. Profile relied-on tables with `openfpa source-profile`, then register each
   source with `openfpa source-register`.
6. Register explicit account or field mappings with
   `openfpa mapping-register`, then reconcile compatible sources with
   `openfpa reconcile-source`.
7. Inspect the identified local evidence before asking questions.
8. Run `openfpa intake-next <company-root>` to retrieve the next unresolved
   question round.
9. Record each source-derived or user-confirmed fact with
   `openfpa intake-record <company-root>`.
10. Ask no more than three related unresolved questions per round.
11. Treat direct user answers as confirmed. Preserve citations and confidence
   for inferred facts; confirm only conflicts or low-confidence conclusions.
12. When intake is ready, create the business profile and initial architecture
   proposal, then wait for approval before scaffolding.

The CLI is a deterministic agent toolbelt and emits JSON. Claude remains the
reasoning and conversation layer. If `openfpa` is unavailable in a source
checkout, use `python3 -m pyfpa.cli`.

Before running a generated company workflow, call
`openfpa entrypoint-list <company-root>`. After creating and validating a new
workflow command, publish it with `openfpa entrypoint-register`.

Before building recurring data access, call `openfpa connector-list`. Use
`openfpa connector-scaffold` only after source registration, mapping,
reconciliation, and architecture approval. Supply an explicitly redacted CSV
fixture. Run `openfpa connector-validate` after every connector change.
Fixture validation must never access the live system.

Before using source-derived totals, call `openfpa source-list` and
`openfpa mapping-list`. Do not treat file presence as lineage or silently accept
unmapped values. If `reconcile-source` cannot represent a richer table, build
and register a tested company-specific reconciliation command.

Do not force onboarding for a narrow request. Ask before accessing external
systems or connectors.

After the initial architecture is approved, use `fpa-research-loop` for bounded
autonomous improvement. You may generate, evaluate, and discard challengers
without asking for approval each time. Human approval is required for promotion
before a challenger replaces the champion.
