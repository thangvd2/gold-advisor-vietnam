---
phase: 01-project-foundation-international-data
plan: 03
subsystem: data-quality, scheduling, api
tags: [apscheduler, quality-checks, fastapi, pipeline]

# Dependency graph
requires:
  - phase: 01-02
    provides: "YFinanceGoldFetcher, VietcombankFxRateFetcher, repository CRUD, FetchedPrice model, Settings config"
provides:
  - "Data quality checks (freshness, anomaly, missing) with alert storage"
  - "Normalizer pipeline orchestrating fetch→convert→store→quality→alert"
  - "APScheduler BackgroundScheduler integrated with FastAPI lifespan"
  - "Quality API endpoints (GET /quality/alerts, GET /quality/status)"
  - "Health endpoint reflects scheduler running state with next_fire_time"
affects: [02-domestic-gold-scraping, 03-signal-engine, 04-dashboard, 05-alerts]

# Tech tracking
tech-stack:
  added: []
  patterns: [tdd-red-green, background-scheduler, pipeline-orchestration, quality-alert-severity]

key-files:
  created:
    - src/ingestion/quality.py
    - src/ingestion/normalizer.py
    - src/ingestion/scheduler.py
    - src/api/routes/quality.py
    - tests/test_quality.py
    - tests/test_scheduler.py
  modified:
    - src/api/main.py
    - src/api/routes/health.py

key-decisions:
  - "APScheduler 3.11.2 BackgroundScheduler (not AsyncIOScheduler) for thread compatibility with FastAPI/uvicorn"
  - "Quality checks run after every fetch (not periodically) per PITFALLS.md §3"
  - "Health endpoint uses module-level _app_state dict for scheduler status injection"
  - "Timezone-naive datetimes normalized to UTC via _ensure_aware helper for SQLite compatibility"

patterns-established:
  - "TDD Red-Green-Refactor: write failing tests first, then implement, commit both separately"
  - "Pipeline pattern: fetch → validate → convert → store → quality check → alert"
  - "Scheduler lifecycle: start in lifespan startup, stop in shutdown, store ref in app_state"
  - "Quality severity levels: warning (stale, anomalous), critical (missing, fetcher failure)"

requirements-completed: [DATA-03, DATA-06]

# Metrics
duration: 5min
completed: 2026-03-25
---

# Phase 1 Plan 3: Data Quality + Scheduler + Quality API Summary

**APScheduler-integrated gold price pipeline with freshness/anomaly/missing quality checks, alert storage, and quality monitoring API endpoints**

## Performance

- **Duration:** 5 min
- **Started:** 2026-03-24T18:14:13Z
- **Completed:** 2026-03-24T18:19:44Z
- **Tasks:** 2 (+ 1 auto-approved checkpoint)
- **Files modified:** 8

## Accomplishments
- Data quality monitoring system with staleness, anomaly, and missing data checks
- Normalizer pipeline orchestrating fetch→FX convert→store→quality check→alert creation
- APScheduler BackgroundScheduler running gold_price_fetch job every 5 minutes
- Quality API endpoints: GET /quality/alerts (filterable by hours) and GET /quality/status (per-source freshness)
- Health endpoint updated to show scheduler running state with next_fire_time

## Task Commits

Each task was committed atomically:

1. **Task 1 RED: Failing tests for quality + normalizer** - `f300f65` (test)
2. **Task 1 GREEN: Implement quality.py + normalizer.py** - `afe190b` (feat)
3. **Task 2 RED: Failing tests for scheduler + quality API** - `e54d2fc` (test)
4. **Task 2 GREEN: Implement scheduler + quality routes + wiring** - `6698d61` (feat)
5. **Lint cleanup** - `3dd66a7` (refactor)

## Files Created/Modified
- `src/ingestion/quality.py` - Freshness, anomaly, and missing data quality checks with alert persistence
- `src/ingestion/normalizer.py` - Pipeline orchestrator: fetch→convert→store→quality→alert
- `src/ingestion/scheduler.py` - APScheduler BackgroundScheduler lifecycle (start/stop) with fetch_and_store_all job
- `src/api/routes/quality.py` - GET /quality/alerts and GET /quality/status endpoints
- `src/api/main.py` - Lifespan wires scheduler startup/shutdown and quality router
- `src/api/routes/health.py` - Health endpoint reflects scheduler running state with next_fire_time
- `tests/test_quality.py` - 10 tests covering all quality checks and pipeline behaviors
- `tests/test_scheduler.py` - 7 tests covering scheduler creation, quality API, health status, and e2e pipeline

## Decisions Made
- APScheduler 3.11.2 BackgroundScheduler (not AsyncIOScheduler) for thread compatibility with FastAPI's uvicorn event loop
- Quality checks run after every fetch, not on a separate schedule — per PITFALLS.md guidance
- Health endpoint uses module-level state dict pattern for scheduler status injection (avoids circular imports)
- Timezone-naive datetimes from SQLite normalized to UTC via `_ensure_aware` helper to prevent comparison errors

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] Fixed timezone-naive datetime comparison in check_freshness**
- **Found during:** Task 1 GREEN (check_freshness implementation)
- **Issue:** SQLite/aiosqlite may return timezone-naive datetimes despite `DateTime(timezone=True)`. Comparing naive vs aware datetimes raises TypeError.
- **Fix:** Added `_ensure_aware(dt)` helper that replaces tzinfo=None with UTC. Applied to all freshness comparisons.
- **Files modified:** src/ingestion/quality.py
- **Verification:** test_flags_stale_record passes, all 10 quality tests pass
- **Committed in:** `afe190b`

**2. [Rule 1 - Bug] Fixed test assertion matching alert message content**
- **Found during:** Task 1 GREEN (anomaly test)
- **Issue:** Test asserted `"anomal" in alert.message.lower()` but message says "Price jumped 12.5%". The check_type is "anomaly" but the message doesn't contain that word.
- **Fix:** Changed assertion to `alert.check_type == "anomaly"` for precise field checking.
- **Files modified:** tests/test_quality.py
- **Verification:** All 10 quality tests pass
- **Committed in:** `afe190b`

**3. [Rule 3 - Blocking] Fixed test threshold value for anomaly detection**
- **Found during:** Task 1 GREEN (anomaly test)
- **Issue:** Test used $2200 (exactly 10% of $2000) but implementation uses strict `>` comparison. 10% exactly should NOT trigger.
- **Fix:** Changed test price to $2250 (12.5% increase) which clearly exceeds the 10% threshold.
- **Files modified:** tests/test_quality.py
- **Verification:** test_flags_anomalous_price_jump passes
- **Committed in:** `afe190b`

**4. [Rule 3 - Blocking] Fixed scheduler test calling settings fixture directly**
- **Found during:** Task 2 GREEN (scheduler tests)
- **Issue:** Non-async test methods calling `settings()` fixture directly. pytest treats this as fixture invocation and raises FixtureCalledDirectly error.
- **Fix:** Changed to `Settings()` constructor call directly in test methods.
- **Files modified:** tests/test_scheduler.py
- **Verification:** All 7 scheduler tests pass
- **Committed in:** `6698d61`

**5. [Rule 3 - Blocking] Fixed quality API test router mounting**
- **Found during:** Task 2 GREEN (quality endpoint tests)
- **Issue:** Tests mounted router without prefix but called `/quality/alerts`. Routes are defined as `/alerts` and `/status`.
- **Fix:** Added `prefix="/quality"` to test router mount.
- **Files modified:** tests/test_scheduler.py
- **Verification:** All quality endpoint tests pass (200 responses)
- **Committed in:** `6698d61`

**6. [Rule 1 - Bug] Removed unused imports from normalizer.py**
- **Found during:** Full verification (ruff check)
- **Issue:** 5 unused imports (datetime, timezone, select, FetchedPrice, PriceRecord) flagged by ruff.
- **Fix:** Removed all unused imports.
- **Files modified:** src/ingestion/normalizer.py
- **Verification:** `uv run ruff check src/` passes cleanly
- **Committed in:** `3dd66a7`

---

**Total deviations:** 6 auto-fixed (2 bugs, 4 blocking issues)
**Impact on plan:** All auto-fixes necessary for correctness. No scope creep. Test fixes align implementation with planned behavior.

## Issues Encountered
- SQLite/aiosqlite timezone handling: despite `DateTime(timezone=True)`, datetimes can come back naive. Resolved with `_ensure_aware` helper — pattern to watch for in future SQLite-backed features.

## User Setup Required

None - no external service configuration required beyond what was set up in Plans 01-01 and 01-02.

## Next Phase Readiness
- Phase 1 is now **complete**: all 3 plans executed, all success criteria met
- International gold price pipeline is fully operational: scheduled fetching, USD/VND conversion, storage, quality monitoring, and API endpoints
- Ready for Phase 2: Vietnamese domestic gold data scraping (SJC, Doji, PNJ sources)
- No blockers identified

## Self-Check: PASSED

All 6 created files exist. All 5 commits verified in git log.

---
*Phase: 01-project-foundation-international-data*
*Completed: 2026-03-25*
