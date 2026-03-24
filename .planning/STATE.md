---
gsd_state_version: 1.0
milestone: v1.0
milestone_name: milestone
status: Ready to plan
stopped_at: Completed 05-03-PLAN.md
last_updated: "2026-03-24T19:59:57.451Z"
progress:
  total_phases: 9
  completed_phases: 5
  total_plans: 15
  completed_plans: 15
---

# Project State

## Project Reference

See: .planning/PROJECT.md (updated 2026-03-25)

**Core value:** Users buy lower and sell higher than they would with blind timing, and they understand *why*.
**Current focus:** Phase 5 — web-dashboard

## Current Position

Phase: 6
Plan: Not started

## Performance Metrics

**Velocity:**

- Total plans completed: 0
- Average duration: —
- Total execution time: 0 hours

**By Phase:**

| Phase | Plans | Total | Avg/Plan |
|-------|-------|-------|----------|
| - | - | - | - |

**Recent Trend:**

- Last 5 plans: —
- Trend: —

*Updated after each plan completion*
| Phase 01 P02 | 5min | 2 tasks | 8 files |
| Phase 01 P03 | 5min | 2 tasks | 8 files |
| Phase 02 P02 | 5min | 2 tasks | 5 files |
| Phase 02 P03 | 5min | 2 tasks | 6 files |
| Phase 03 P01 | 475 | 2 tasks | 8 files |
| Phase 03 P02 | 205 | 2 tasks | 5 files |
| Phase 04 P02 | 152 | 2 tasks | 7 files |
| Phase 04 P03 | 2 | 2 tasks | 5 files |
| Phase 04 P04 | 2 | 1 tasks | 8 files |
| Phase 05 P01 | 4 | 2 tasks | 8 files |
| Phase 05 P02 | 3 | 2 tasks | 10 files |
| Phase 05 P03 | 0 | 1 tasks | 0 files |

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

### Pending Todos

None yet.

### Blockers/Concerns

- [Phase 1]: Vietnamese gold shop website structure unverified — each target site (sjc.com.vn, doji.vn, pnj.com.vn, btmc.vn) must be validated during planning
- [Phase 1]: Signal threshold calibration needs historical gap data analysis — cannot determine optimal thresholds from research alone
- [Phase 1]: International gold price API selection needed — multiple options (Kitco, MetalPriceAPI, free tiers), must evaluate limits and reliability

## Session Continuity

Last session: 2026-03-24T19:57:31.464Z
Stopped at: Completed 05-03-PLAN.md
Resume file: None
