# Phase 1: Project Foundation & International Data - Context

**Gathered:** 2026-03-25
**Status:** Ready for planning

<domain>
## Phase Boundary

System reliably ingests and stores international gold price data (XAUUSD) in both USD and VND, with data quality monitoring that flags stale or anomalous data. This is infrastructure only — no user-facing features, no scraping of Vietnamese gold shops (that's Phase 2).

Delivers: FastAPI app scaffold, APScheduler integration, international gold price fetching, USD/VND conversion, SQLite storage, data quality validation API, health check endpoint.

</domain>

<decisions>
## Implementation Decisions

### International Gold Price API
- **D-01:** Start with free sources (yfinance, Frankfurter, etc.) for XAUUSD. Only pay for a dedicated API (e.g., GoldAPI.io ~$10/mo) if free sources prove unreliable during testing.
- **D-02:** Use **market exchange rate** (Vietcombank or similar) for USD/VND conversion — not the official SBV rate. Market rate reflects what gold shops actually pay for imports. Official rate can diverge 4-5%, making gap calculation inaccurate.

### Claude's Discretion
- Specific free gold price API selection (yfinance vs others) — evaluate during research, pick the most reliable free option
- Data quality threshold values (anomaly detection %, staleness timeout) — set based on research findings and standard practices
- Database schema details (indexes, retention policy) — design based on time-series best practices from STACK.md
- Project directory structure — follow ARCHITECTURE.md recommended structure (`src/ingestion/`, `src/api/`, `src/storage/`)
- APScheduler integration pattern (BackgroundScheduler vs AsyncIOScheduler) — choose based on FastAPI compatibility

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Stack & Architecture
- `.planning/research/STACK.md` — Complete technology stack with versions, rationale, and installation commands. Python 3.12+, FastAPI, APScheduler 3.11.2, SQLite + DuckDB, httpx, pandas
- `.planning/research/ARCHITECTURE.md` — System architecture, component responsibilities, data flow, adapter pattern, recommended project structure (`src/ingestion/`, `src/api/`, `src/storage/`)

### Pitfalls (MUST address in this phase)
- `.planning/research/PITFALLS.md` §Pitfall 3 — "Scraped Vietnamese Gold Data Going Stale or Wrong Without Detection" — data quality infrastructure must be built before any analysis. Design for failure, schema validation on every record, freshness tracking
- `.planning/research/PITFALLS.md` §Pitfall 5 — "Overpromising Prediction Accuracy" — UX/wording decisions here set user expectations permanently. Use "signal strength" not "confidence" where appropriate
- `.planning/research/PITFALLS.md` §Integration Gotchas — "International gold APIs" — normalize all timestamps to UTC immediately, validate price format before storage

### Project Scope
- `.planning/PROJECT.md` — Core value, constraints (data fragility, no real-time feed, advice liability)
- `.planning/REQUIREMENTS.md` — DATA-03 (international gold price in USD + VND), DATA-06 (cross-source validation, flag stale/missing/anomalous data)
- `.planning/ROADMAP.md` — Phase 1 success criteria and dependency chain

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- None — greenfield project. Only `CLAUDE.md` and `.planning/` exist.

### Established Patterns
- No codebase patterns yet. First phase establishes conventions.

### Integration Points
- This phase creates the FastAPI app entry point, database models, and scheduler — all subsequent phases connect to these.

</code_context>

<specifics>
## Specific Ideas

- The adapter pattern from ARCHITECTURE.md should be used even for international API fetchers — makes adding fallback sources trivial
- ARCHITECTURE.md notes BTMC has an official JSON API (`api.btmc.vn/api/BTMCAPI/getpricebtmc`) — useful as a Vietnamese gold price reference later, not for this phase
- PITFALLS.md recommends: "If a small set of known SKUs/prices that you manually verify daily" — canary monitoring pattern

</specifics>

<deferred>
## Deferred Ideas

None — discussion stayed within phase scope.

</deferred>

---

*Phase: 01-project-foundation-international-data*
*Context gathered: 2026-03-25*
