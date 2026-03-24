---
gsd_state_version: 1.0
milestone: v1.0
milestone_name: milestone
status: Complete
stopped_at: Completed 09-03-PLAN.md
last_updated: "2026-03-25T21:00:00.000Z"
progress:
  total_phases: 9
  completed_phases: 9
  total_plans: 27
  completed_plans: 27
---

# Project State

## Project Reference

See: .planning/PROJECT.md (updated 2026-03-25)

**Core value:** Users buy lower and sell higher than they would with blind timing, and they understand *why*.
**Current focus:** All phases complete — v1.0 milestone achieved

## Current Position

Phase: 9 (final)
Plan: 3 (complete)

## Performance Metrics

**Velocity:**

- Total plans completed: 27
- Total execution time: ~2 hours

**By Phase:**

| Phase | Plans | Total | Avg/Plan |
|-------|-------|-------|----------|
| 09 | 3 | 10 tasks | ~15 min |

## Accumulated Context

### Decisions

Decisions are logged in PROJECT.md Key Decisions table.
Recent decisions affecting current work:

- Roadmap: 9 phases at fine granularity, data-first dependency chain
- Stack: Python monolith (FastAPI + APScheduler + SQLite/DuckDB + Jinja2/HTMX)
- Signal engine: Deterministic (no LLM) for core computation; LLM deferred to enrichment
- [Phase 01]: No CORS middleware yet, added when dashboard needs it in Phase 5
- [Phase 01]: greenlet added as implicit dependency for SQLAlchemy async sessions
- [Phase 01]: yfinance calls wrapped in asyncio.to_thread() to avoid blocking event loop
- [Phase 01]: Repository functions accept AsyncSession as first arg for testability via dependency injection
- [Phase 01]: Quality checks run after every fetch (not periodically) per PITFALLS.md
- [Phase 01]: Timezone-naive datetime normalization via _ensure_aware for SQLite compatibility
- [Phase 02]: Scrapers use @retry decorator with max_retries=2 for resilience
- [Phase 02]: Normalizer uses source_name property for uniform Fetcher/Scraper name extraction
- [Phase 02]: Static HTML scraper pattern: httpx+BS4 for DOJI/PhuQuy, Playwright deferred for JS-rendered sites
- [Phase 02]: SJC/PNJ: use httpx JSON APIs instead of Playwright — all 4 dealers now use httpx pattern
- [Phase 02]: API discovery: inspect page JS source (goldprice.js, Next.js chunks) to find hidden endpoints
- [Phase 02]: BTMC JSON API unreachable from outside VN — implemented HTML table fallback at /Home/BGiaVang
- [Phase 02]: HTML prices in thousands VND/chỉ — multiply by 10,000 for VND/lượng (same convention as PNJ)
- [Phase 02]: Both VRTL bar and SJC bar from BTMC mapped to product_type='sjc_bar'
- [Phase 02]: Spread computed as sell - buy, None when either price is missing
- [Phase 03]: DuckDB with sqlite_scanner extension for analytical queries on SQLite data
- [Phase 03]: MA gating: 7d_ma requires 7 days, 30d_ma requires 30 days of history
- [Phase 03]: Sync DuckDB calls wrapped in asyncio.to_thread() to avoid blocking event loop
- [Phase 03]: Epoch-based bucketing via DuckDB to_timestamp for adaptive price chart resolution
- [Phase 03]: price_vnd field for xau_usd charts to match gap calculation convention
- [Phase 04]: Composite thresholds: Saver (0.05/-0.05), Trader (0.25/-0.25), default (0.15/-0.15)
- [Phase 04]: Reasoning uses f-string formatting — pure deterministic, no LLM
- [Phase 04]: MA fallback chain: 30d → 7d when 30d unavailable
- [Phase 04]: SignalRecord.factor_data stored as JSON string for simplicity
- [Phase 04]: Signal pipeline is pure sync function — no DB writes, no side effects
- [Phase 04]: Signal serialized via __dict__ for JSON API response
- [Phase 04]: 503 when confidence==0 AND recommendation==HOLD signals insufficient data
- [Phase 04]: calculate_dealer_spreads() uses DuckDB ROW_NUMBER for latest-per-dealer spread query
- [Phase 05]: Patch async_session at import location not module source for test mocking
- [Phase 05]: Gold/charcoal dark theme with DM Serif Display + DM Sans font pairing
- [Phase 05]: StaticFiles mounted before routes to prevent path conflicts
- [Phase 05]: HTMX loading spinners in dashboard partials, partial endpoints return 200 with empty-state on error
- [Phase 05]: Chart.js dark theme with gold accent palette: SJC=#D4AF37, Ring=#F5D76E, Intl=#4A90D9
- [Phase 05]: Mode toggle via htmx.ajax() re-fetching signal partial with ?mode= query param
- [Phase 05]: Auto-approved dashboard verification checkpoint per user autonomous execution request
- [Phase 06]: Bot runs in daemon thread (not asyncio) for simpler lifecycle with APScheduler
- [Phase 06]: Empty token = bot disabled with warning log, not crash
- [Phase 06]: ±20% confidence threshold and >2% price movement threshold for alerts
- [Phase 06]: First signal stored as baseline without alert (debounce)
- [Phase 06]: asyncio.new_event_loop() for sync-to-async dispatch in scheduler thread
- [Phase 06]: Separate scheduler job for alert dispatch (same interval as fetch)
- [Phase 07]: DXY fetched via yfinance ^DXY ticker, stored as product_type='dxy'
- [Phase 07]: Macro trend calculators use DuckDB window functions on existing price_history (no new table)
- [Phase 07]: 1% threshold for trend direction classification (up/down/neutral)
- [Phase 07]: Macro factors weighted at 0.1 each (low influence, supplementary to gap/spread/trend)
- [Phase 07]: Gap weight reduced (saver: 0.4→0.3, trader: 0.6→0.5) to accommodate macro factors
- [Phase 07]: Real interest rates deferred — DXY used as proxy for dollar strength
- [Phase 07]: Macro context appended to reasoning as separate clause
- [Phase 08]: Seasonal factor has zero direction/weight — only modifies confidence
- [Phase 08]: Tet (Jan-Feb) = 0.7 modifier, high-demand (Nov-Dec) = 0.85 modifier
- [Phase 08]: No Alembic — project uses Base.metadata.create_all() for all models
- [Phase 08]: Policy confidence caps: high=0.3, medium=0.6, low=1.0
- [Phase 08]: Policy override applied after seasonal modifier (policy takes priority)
- [Phase 08]: Seasonal badge only shown for high/very_high demand months
- [Phase 09]: News feed uses stdlib xml.etree for RSS/Atom parsing (no lxml needed)
- [Phase 09]: URL-based deduplication via SQLite ON CONFLICT DO NOTHING
- [Phase 09]: News is display-only, no LLM, no signal influence
- [Phase 09]: Admin manual news defaults category=state_bank for SBV announcements
- [Phase 09]: News fetch interval: 30 min (separate from 5-min price fetch)

### Pending Todos

None — v1.0 complete.

### Blockers/Concerns

None remaining — all phases complete.

## Session Continuity

Last session: 2026-03-25T21:00:00.000Z
Stopped at: Completed 09-03-PLAN.md (v1.0 complete)
Resume file: None
