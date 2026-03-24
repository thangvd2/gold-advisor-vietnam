---
phase: 03-gap-analysis-price-charts
plan: 02
subsystem: api, analysis
tags: [duckdb, fastapi, chart-data, time-series, price-history]

# Dependency graph
requires:
  - phase: 03-01
    provides: "DuckDB connection factory (get_duckdb_connection), price_history table schema"
provides:
  - "Price chart data service (get_price_series) with adaptive time bucketing"
  - "GET /api/prices/history endpoint for Chart.js consumption"
affects: [05-dashboard, future-charting]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "DuckDB epoch-based time bucketing (to_timestamp + floor/epoch)"
    - "asyncio.to_thread wrapping for sync DuckDB in async endpoints"
    - "Chart.js-ready {x, y} response format"

key-files:
  created:
    - src/analysis/prices.py
    - src/api/routes/prices.py
    - tests/test_price_history.py
    - tests/test_price_api.py
  modified:
    - src/api/main.py

key-decisions:
  - "Epoch-based bucketing via DuckDB to_timestamp(floor(epoch(ts)/N)*N) for adaptive resolution"
  - "Reused _get_db_path() pattern from gap.py (2-line duplication acceptable at this scale)"
  - "price_vnd for xau_usd charts (not sell_price) to match gap calculation convention"

patterns-established:
  - "Price service functions return list[dict] with {x: ISO timestamp, y: float|None} for chart libraries"
  - "API routes wrap DuckDB sync calls in asyncio.to_thread()"

requirements-completed: [DATA-07]

# Metrics
duration: 3min
completed: 2026-03-25
---

# Phase 3 Plan 2: Price Chart Data Service Summary

**DuckDB time-bucketed price series service with adaptive resolution (5min/15min/1hr) and Chart.js-ready API endpoint for SJC bars, ring gold, and international gold**

## Performance

- **Duration:** 3 min
- **Started:** 2026-03-24T19:09:29Z
- **Completed:** 2026-03-24T19:12:28Z
- **Tasks:** 2
- **Files modified:** 5

## Accomplishments
- Price history service with DuckDB analytical queries across 3 product types
- Adaptive time bucket sizing: 5min (1D), 15min (1W), 1hour (1M/1Y)
- Dealer price averaging for domestic products, price_vnd selection for international
- RESTful API with enum validation for product_type and range parameters
- 13 new tests (7 service + 6 API), all 117 project tests passing

## Task Commits

Each task was committed atomically via TDD (RED → GREEN):

1. **Task 1: Price History Chart Data Service** - `c48ca62` (test RED), `0392505` (feat GREEN)
2. **Task 2: Price Chart API Endpoint + Router Wiring** - `561be09` (test RED), `b04f734` (feat GREEN)

## Files Created/Modified
- `src/analysis/prices.py` - Price series query service with DuckDB time bucketing
- `src/api/routes/prices.py` - FastAPI router with GET /api/prices/history endpoint
- `src/api/main.py` - Registered prices router at /api/prices prefix
- `tests/test_price_history.py` - 7 tests for service layer (format, averaging, field selection, filtering, range, empty, bucket granularity)
- `tests/test_price_api.py` - 6 tests for API layer (response shape, xau_usd, validation, defaults)

## Decisions Made
- Used DuckDB `to_timestamp(floor(epoch(cast(timestamp as timestamp)) / N) * N)` for time bucketing — same pattern as gap module for consistency
- Duplicated `_get_db_path()` helper from gap.py rather than extracting shared module — 2-line duplication is acceptable, extraction can happen if a third consumer appears
- Selected `price_vnd` field for xau_usd charts (not sell_price) to maintain consistency with gap calculation where sell_price represents previous close

## Deviations from Plan

None - plan executed exactly as written.

## Issues Encountered
None

## User Setup Required
None - no external service configuration required.

## Next Phase Readiness
- Phase 3 (gap-analysis-price-charts) complete — both gap analysis and price chart data available
- Phase 4 (signal-engine) can consume gap historical data for buy/sell signal generation
- Phase 5 (dashboard) can consume /api/prices/history for Chart.js price charts
- /api/gap/current, /api/gap/history, and /api/prices/history endpoints all operational

## Self-Check: PASSED

All files verified, all commits confirmed, 117 tests passing.

---
*Phase: 03-gap-analysis-price-charts*
*Completed: 2026-03-25*
