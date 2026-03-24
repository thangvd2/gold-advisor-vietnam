# Phase 2: Vietnamese Gold Price Scraping - Context

**Gathered:** 2026-03-25 (auto-generated)
**Status:** Ready for planning

<domain>
## Phase Boundary

System reliably scrapes buy/sell prices from 5+ Vietnamese gold dealers for SJC bars, ring gold (nhẫn trơn), and dealer buy/sell spreads. Builds on Phase 1's adapter pattern, repository layer, and data quality infrastructure. Individual scraper failures must not crash the system.

</domain>

<decisions>
## Implementation Decisions

### Scraper Strategy
- **D-01:** Start with httpx + BeautifulSoup for static HTML sites. Only escalate to Playwright for JS-rendered sites (check during research which sites need it).
- **D-02:** Use the adapter pattern established in Phase 1 — each dealer implements the DataSource interface. This was already designed into the architecture.
- **D-03:** Cross-source validation from Phase 1 (DATA-06) applies to Vietnamese sources too — each scraped price should be validated against the same quality checks.

### Claude's Discretion
- Which dealers to scrape first vs later (SJC, Doji, PNJ, BTMC, Phú Quý, Mi Hồng) — prioritize based on ease of scraping and data reliability
- Scrape frequency (1-5 min from requirements) — pick based on how often dealers update
- Whether any dealers need Playwright vs httpx — evaluate during research
- Retry logic, timeout values, User-Agent rotation strategy
- Specific HTML selectors and parsing patterns for each dealer site

</decisions>

<canonical_refs>
## Canonical References

### Phase 1 Foundation (MUST read)
- `.planning/phases/01-project-foundation-international-data/01-01-SUMMARY.md` — App scaffold, DB models, existing patterns
- `.planning/phases/01-project-foundation-international-data/01-02-SUMMARY.md` — Fetcher adapter pattern, FetchedPrice model, repository layer
- `.planning/phases/01-project-foundation-international-data/01-03-SUMMARY.md` — Data quality checks, normalizer pipeline, scheduler

### Architecture & Stack
- `.planning/research/ARCHITECTURE.md` — Adapter pattern, DataSource interface, recommended project structure
- `.planning/research/STACK.md` — httpx + BeautifulSoup + lxml for static, Playwright for JS-heavy
- `.planning/research/PITFALLS.md` §Pitfall 3 — Stale/wrong data detection (critical for Vietnamese sources)
- `.planning/research/PITFALLS.md` §Integration Gotchas — SJC.com.vn scraping specifics, BTMC API

### Project Scope
- `.planning/PROJECT.md` — Data fragility constraint
- `.planning/REQUIREMENTS.md` — DATA-01 (5+ dealers), DATA-02 (ring gold), DATA-05 (spreads)
- `.planning/ROADMAP.md` — Phase 2 success criteria

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- `src/ingestion/fetchers/base.py` — DataSource base class with adapter pattern (from Phase 1)
- `src/ingestion/models.py` — FetchedPrice model for normalized price records
- `src/storage/repository.py` — Repository CRUD for price_history table
- `src/ingestion/quality.py` — Data quality checks (staleness, anomaly, missing)
- `src/ingestion/normalizer.py` — Pipeline that orchestrates fetch→store→quality-check
- `src/storage/models.py` — SQLAlchemy models (price_history, data_quality_alerts)

### Established Patterns
- Adapter pattern: each source implements `DataSource` with `async fetch() -> list[FetchedPrice]`
- TDD: tests written first, then implementation
- Atomic commits per task with descriptive messages

### Integration Points
- New scrapers plug into existing normalizer pipeline via DataSource interface
- Scheduler already has 5-min interval — just register new fetchers
- Quality checks apply automatically via normalizer pipeline

</code_context>

<specifics>
## Specific Ideas

- ARCHITECTURE.md notes: SJC.com.vn has `giavang/textContent.php` endpoint (simple HTML table, stable for years)
- ARCHITECTURE.md notes: BTMC has official JSON API (`api.btmc.vn/api/BTMCAPI/getpricebtmc`) — prefer over scraping
- ARCHITECTURE.md notes: PNJ often has JavaScript-rendered content — may need Playwright
- ARCHITECTURE.md notes: Doji — check for JSON API endpoint first before scraping HTML

</specifics>

<deferred>
## Deferred Ideas

None — discussion stayed within phase scope.

</deferred>

---
*Phase: 02-vietnamese-gold-price-scraping*
*Context gathered: 2026-03-25 (auto)*
