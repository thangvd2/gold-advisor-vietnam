---
phase: 03-gap-analysis-price-charts
plan: 01
subsystem: analysis
tags: [duckdb, gap-analysis, sqlite, fastapi, api]

dependency-graph:
  requires:
    - phase: 02-ingestion-scrapers
      provides: "price_history table with xau_usd + sjc_bar records"
  provides:
    - "DuckDB analytics layer (ATTACH SQLite, window functions)"
    - "Current gap calculation (VND absolute + percentage)"
    - "Historical gap with 7d/30d moving averages"
    - "Gap API endpoints (/api/gap/current, /api/gap/history)"
  affects: ["04-signals", "05-dashboard", "06-messenger-alerts"]

tech-stack:
  added: ["duckdb==1.5.1"]
  patterns:
    - "DuckDB ATTACH SQLite for analytical read-only queries"
    - "RANGE BETWEEN INTERVAL for time-series moving averages"
    - "5-minute bucketing via epoch floor division"
    - "MA gating on sufficient historical data depth"

key-files:
  created:
    - src/analysis/__init__.py
    - src/analysis/connection.py
    - src/analysis/gap.py
    - src/api/routes/gap.py
    - tests/test_gap.py
    - tests/test_gap_api.py
  modified:
    - pyproject.toml
    - src/api/main.py

key-decisions:
  - "DuckDB with sqlite_scanner extension to ATTACH SQLite for analytical queries"
  - "MAs gated on time-from-first-data: 7d_ma requires 7 days, 30d_ma requires 30 days"
  - "Sync DuckDB calls wrapped in asyncio.to_thread() to avoid blocking event loop"
  - "5-minute bucket granularity for historical gap time series"
  - "503 status code for insufficient data on /current endpoint"

patterns-established:
  - "DuckDB connection factory: get_duckdb_connection() creates in-memory DuckDB, ATTACHes SQLite read-only, caller closes"
  - "API test fixture pattern: patch get_settings in route module, create TestClient within patch context, yield to tests"

requirements-completed: [DATA-04]

metrics:
  duration: 8min
  completed: 2026-03-24T19:08:08Z
---

# Phase 3 Plan 1: Gap Analysis Engine Summary

**DuckDB analytics layer computing SJC-international price gap in VND absolute and percentage terms, with 7d/30d moving averages and REST API endpoints**

## Performance

- **Duration:** 8 min
- **Started:** 2026-03-24T18:59:53Z
- **Completed:** 2026-03-24T19:08:08Z
- **Tasks:** 2 (4 commits with TDD RED/GREEN phases)
- **Files modified:** 8

## Accomplishments
- DuckDB connection factory that ATTACHes SQLite databases read-only for analytical queries
- `calculate_current_gap()` computes live gap (avg domestic SJC sell - international price_vnd) with percentage
- `calculate_historical_gaps()` with 5-min time-bucketing, FULL OUTER JOIN for sparse data, and RANGE BETWEEN INTERVAL moving averages
- Two API endpoints: `GET /api/gap/current` (503 on insufficient data) and `GET /api/gap/history?range=1W|1M|3M|1Y`
- 13 new tests (8 gap calculator + 5 API endpoint) — all passing alongside 56 existing tests

## Task Commits

Each task was committed atomically:

1. **Task 1 RED: Failing tests for gap calculator** - `49dac39` (test)
2. **Task 1 GREEN: DuckDB connection + gap calculator** - `d396b5f` (feat)
3. **Task 2 RED: Failing tests for gap API** - `d4bfb59` (test)
4. **Task 2 GREEN: Gap API endpoints + router wiring** - `26a73b8` (feat)

## Files Created/Modified
- `src/analysis/__init__.py` - Analysis package marker
- `src/analysis/connection.py` - DuckDB connection factory (sqlite_scanner ATTACH)
- `src/analysis/gap.py` - Gap calculation: current gap + historical with MAs
- `src/api/routes/gap.py` - FastAPI router with /current and /history endpoints
- `src/api/main.py` - Wired gap_router with prefix=/api/gap
- `tests/test_gap.py` - 8 tests for gap calculation engine
- `tests/test_gap_api.py` - 5 tests for gap API endpoints
- `pyproject.toml` - Added duckdb==1.5.1

## Decisions Made
- **DuckDB sqlite_scanner extension** over direct pandas: Cleaner window function syntax with RANGE BETWEEN INTERVAL handles weekends/holidays correctly, no need to materialize intermediate data
- **MA gating**: Moving averages return None until sufficient historical depth exists (7d for ma_7d, 30d for ma_30d) — prevents misleading early signals
- **asyncio.to_thread()** for sync DuckDB: Consistent with Phase 1 yfinance pattern, avoids blocking the FastAPI event loop
- **503 Service Unavailable** for insufficient data: Semantically correct — the service exists but cannot produce the requested resource
- **Epoch floor division** for 5-min bucketing: `floor(epoch(timestamp) / 300) * 300` — simpler and more portable than date_trunc arithmetic

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] Fixed DuckDB fetchone() return type**
- **Found during:** Task 1 GREEN (gap calculator implementation)
- **Issue:** DuckDB's `fetchone()` returns a tuple, not a dict. `dict(result)` raises `TypeError`
- **Fix:** Used `cursor.description` to get column names, then `dict(zip(columns, result))`
- **Files modified:** src/analysis/gap.py
- **Committed in:** d396b5f

**2. [Rule 1 - Bug] Fixed test timestamp overflow in sparse data test**
- **Found during:** Task 1 GREEN (test execution)
- **Issue:** `range(0, 180, 5)` produces minutes up to 175; `now.replace(minute=175)` raises `ValueError`
- **Fix:** Used `base + timedelta(minutes=minute)` instead of `now.replace(minute=...)`
- **Files modified:** tests/test_gap.py
- **Committed in:** d396b5f

**3. [Rule 1 - Bug] Fixed test patch context scope for API tests**
- **Found during:** Task 2 GREEN (API endpoint tests)
- **Issue:** `unittest.mock.patch` context manager exited before `TestClient` was used, so `get_settings()` returned default database path instead of temp test path
- **Fix:** Moved patch into fixture's `yield` block so it stays active during test execution
- **Files modified:** tests/test_gap_api.py
- **Committed in:** 26a73b8

---

**Total deviations:** 3 auto-fixed (3 bugs)
**Impact on plan:** All auto-fixes necessary for correctness. No scope creep.

## Issues Encountered
- DuckDB Python client returns tuples from `fetchone()`, not dicts — resolved by manual column mapping
- Test monkeypatching with `patch()` context manager must encompass the full test lifecycle, not just TestClient creation

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness
- DuckDB analytics layer established and tested — ready for Phase 3 Plan 2 (price charts) or Phase 4 (signal engine)
- Gap API endpoints return JSON consumable by frontend (Chart.js/Plotly)
- Moving average infrastructure (RANGE BETWEEN INTERVAL) reusable for future time-series indicators

---
*Phase: 03-gap-analysis-price-charts*
*Completed: 2026-03-24*
