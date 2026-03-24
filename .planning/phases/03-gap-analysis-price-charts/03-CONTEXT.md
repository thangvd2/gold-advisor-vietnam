# Phase 3: Gap Analysis & Price Charts - Context

**Gathered:** 2026-03-25 (auto-generated)
**Status:** Ready for planning

<domain>
## Phase Boundary

Compute and visualize the SJC-international price gap with historical context (1W/1M/3M/1Y). Display price charts for all gold products. This is where the core analytical value emerges — the gap is the primary timing metric.

</domain>

<decisions>
## Implementation Decisions

### Claude's Discretion
- Gap calculation methodology (average domestic price vs international, per-dealer gaps)
- Chart library choice (Chart.js lighter vs Plotly.js more capable) — STACK.md recommends Chart.js first
- Historical data aggregation (DuckDB vs pandas vs SQL window functions)
- API endpoints design for gap and chart data
- How to handle missing data points in charts

</decisions>

<canonical_refs>
## Canonical References

### Phase 1 & 2 Foundation
- `.planning/phases/01-project-foundation-international-data/01-02-SUMMARY.md` — International gold fetcher, FX conversion, repository
- `.planning/phases/02-vietnamese-gold-price-scraping/02-01-SUMMARY.md` — DOJI/Phú Quý scrapers
- `.planning/phases/02-vietnamese-gold-price-scraping/02-02-SUMMARY.md` — SJC/PNJ scrapers
- `.planning/phases/02-vietnamese-gold-price-scraping/02-03-SUMMARY.md` — BTMC scraper, spread calculation

### Architecture & Stack
- `.planning/research/STACK.md` — DuckDB for analytical queries, Chart.js for charts
- `.planning/research/ARCHITECTURE.md` — Pipeline pattern for signal computation
- `.planning/REQUIREMENTS.md` — DATA-04 (gap tracker), DATA-07 (price charts)

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- `src/storage/repository.py` — PriceRepository with time-range queries
- `src/storage/models.py` — price_history table with all dealer data
- `src/ingestion/fetchers/gold_price.py` — International gold in VND via conversion
- All 5 dealer scrapers feeding into price_history

### Established Patterns
- Adapter pattern for data sources
- TDD approach
- Atomic commits

</code_context>

<specifics>
## Specific Ideas

- International gold price is already stored in VND (converted via Vietcombank rate in Phase 1)
- Gap = average domestic SJC sell price - international gold price in VND (both per lượng)
- Per-dealer gap could also be useful for spread analysis later

</specifics>

<deferred>
## Deferred Ideas
None
</deferred>

---
*Phase: 03-gap-analysis-price-charts*
*Context gathered: 2026-03-25 (auto)*
