---
phase: 01-project-foundation-international-data
plan: 02
subsystem: ingestion, storage
tags: [yfinance, httpx, pydantic, sqlalchemy, abc, retry, vietcombank, fx-rate]

dependency-graph:
  requires:
    - phase: 01-01
      provides: "PriceRecord ORM model, async database engine, Settings class"
  provides:
    - "FetchedPrice Pydantic model for normalized price data"
    - "DataSource ABC with retry decorator for extensible data sources"
    - "YFinanceGoldFetcher for XAUUSD spot price via yfinance (GC=F / XAUUSD=X)"
    - "VietcombankFxRateFetcher for USD/VND market selling rate"
    - "USD→VND per lượng conversion function"
    - "Repository CRUD: save_price, get_latest_prices, get_prices_since, save_quality_alert, get_recent_alerts"
  affects:
    - 01-03 (scheduler will use fetchers and repository)
    - 02-01 through 02-03 (gap analysis and signals need stored prices)

tech-stack:
  added: []
  patterns: ["adapter pattern for data sources", "Pydantic ingestion models separate from ORM", "AsyncSession dependency injection for repository testability"]

key-files:
  created: [src/ingestion/models.py, src/ingestion/fetchers/base.py, src/ingestion/fetchers/gold_price.py, src/ingestion/fetchers/fx_rate.py, src/ingestion/fetchers/vietcombank.py, src/storage/repository.py, tests/test_fetchers.py, tests/test_repository.py]
  modified: []

key-decisions:
  - "Corrected conversion factor: VND/lượng = (USD/oz / 31.1034768) × 37.5 × VND/USD (plan had wrong 1.09714 divisor)"
  - "Vietcombank sellingRate field checked with sellRate fallback for API compatibility"
  - "httpx for async FX fetch, yfinance wrapped in asyncio.to_thread to avoid blocking event loop"

patterns-established:
  - "Data sources: extend DataSource ABC, return list[FetchedPrice]"
  - "Retry decorator: exponential backoff with configurable max_retries and backoff_factor"
  - "Repository: all functions accept AsyncSession as first argument for testability"
  - "FetchedPrice→PriceRecord: Pydantic model converted to ORM model in repository layer"

requirements-completed: [DATA-03]

metrics:
  duration: 8min
  completed: 2026-03-25
---

# Phase 1 Plan 2: International Data Fetchers Summary

**YFinance gold price fetcher with GC=F/XAUUSD=X fallback, Vietcombank USD/VND FX fetcher, and SQLite repository with FetchedPrice→PriceRecord conversion**

## Performance

- **Duration:** 8 min
- **Started:** 2026-03-24T18:07:33Z
- **Completed:** 2026-03-24T18:15:33Z
- **Tasks:** 2
- **Files modified:** 8

## Accomplishments
- FetchedPrice Pydantic model with positive price validators and automatic fetched_at timestamp
- DataSource ABC with configurable retry decorator (exponential backoff)
- YFinanceGoldFetcher using GC=F primary ticker with XAUUSD=X fallback, wrapped in asyncio.to_thread
- VietcombankFxRateFetcher using httpx async client with sellingRate/sellRate field fallback
- Correct USD→VND per lượng conversion using 31.1034768g/oz and 37.5g/lượng
- Repository with save_price, get_latest_prices, get_prices_since, save_quality_alert, get_recent_alerts
- 23 new passing tests (34 total across project)

## Task Commits

1. **Task 1 RED: Failing tests** - `27652fd` (test)
2. **Task 1 GREEN: Models, base, fetcher** - `b434651` (feat)
3. **Task 2 RED: Failing tests** - `40f8fe9` (test)
4. **Task 2 GREEN: FX fetcher, repository** - `7ded846` (feat)
5. **Lint fix: unused import** - `f88c361` (fix)

## Files Created/Modified
- `src/ingestion/__init__.py` - Package init
- `src/ingestion/models.py` - FetchedPrice model, ProductType enum, convert_usd_to_vnd_per_luong
- `src/ingestion/fetchers/__init__.py` - Package init
- `src/ingestion/fetchers/base.py` - DataSource ABC with retry decorator
- `src/ingestion/fetchers/gold_price.py` - YFinanceGoldFetcher with dual-ticker fallback
- `src/ingestion/fetchers/fx_rate.py` - FxRateFetcher ABC
- `src/ingestion/fetchers/vietcombank.py` - VietcombankFxRateFetcher via httpx
- `src/storage/repository.py` - CRUD operations for price_history and data_quality_alerts
- `tests/test_fetchers.py` - 13 tests for models, base, gold fetcher, conversion
- `tests/test_repository.py` - 10 tests for FX fetcher and repository

## Decisions Made
- Corrected the plan's oz→lượng conversion factor from 1.09714286 to the mathematically correct (37.5/31.1034768) ratio
- Used Vietcombank sellingRate field with sellRate fallback for API resilience
- yfinance calls wrapped in asyncio.to_thread() to avoid blocking the FastAPI event loop
- Repository functions accept AsyncSession for dependency injection and testability

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] Fixed incorrect oz→lượng conversion factor in plan**
- **Found during:** Task 1 GREEN (conversion function tests)
- **Issue:** Plan specified 1 oz = 1.09714286 lượng (mathematically incorrect). Correct: 1 oz = 31.1034768g, 1 lượng = 37.5g, so 1 oz ≈ 0.8294 lượng
- **Fix:** Used correct formula: VND/lượng = (USD/oz / 31.1034768) × 37.5 × VND/USD
- **Files modified:** src/ingestion/models.py, tests/test_fetchers.py
- **Verification:** Round-trip test passes — converting back yields original USD/oz within 0.01 precision
- **Committed in:** `b434651`

**2. [Rule 1 - Bug] Fixed httpx response.json() mock as AsyncMock instead of MagicMock**
- **Found during:** Task 2 GREEN (Vietcombank fetcher tests)
- **Issue:** httpx Response.json() is synchronous but test used AsyncMock, causing coroutine error
- **Fix:** Changed mock_response from AsyncMock to MagicMock (json() is sync in httpx)
- **Files modified:** tests/test_repository.py
- **Verification:** All 4 Vietcombank fetcher tests pass
- **Committed in:** `7ded846`

**3. [Rule 3 - Blocking] Added pytest_asyncio.fixture for async db_session**
- **Found during:** Task 2 GREEN (repository tests)
- **Issue:** pytest-asyncio strict mode requires explicit @pytest_asyncio.fixture for async fixtures
- **Fix:** Added pytest_asyncio import and used @pytest_asyncio.fixture decorator
- **Files modified:** tests/test_repository.py
- **Verification:** All 6 repository tests pass
- **Committed in:** `7ded846`

---

**Total deviations:** 3 auto-fixed (2 bugs, 1 blocking)
**Impact on plan:** All auto-fixes necessary for correctness. No scope creep.

## Issues Encountered
- SQLite strips timezone info from DateTime columns — tests adjusted to avoid naive/aware comparison errors. This is a known SQLite limitation that should be addressed when migrating to PostgreSQL.

## User Setup Required
None - no external service configuration required.

## Next Phase Readiness
- Fetchers ready for 01-03 (scheduler orchestration)
- Repository ready for saving fetched prices on schedule
- Conversion function ready for gap calculation in Phase 02
- Note: Vietcombank API endpoint may need verification against real response format in production

## Self-Check: PASSED

All 8 files verified. All 5 commits verified (27652fd, b434651, 40f8fe9, 7ded846, f88c361). 34 tests pass. ruff clean.

---
*Phase: 01-project-foundation-international-data*
*Completed: 2026-03-25*
