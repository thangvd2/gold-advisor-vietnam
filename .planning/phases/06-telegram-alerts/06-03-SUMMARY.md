---
phase: 06-telegram-alerts
plan: 03
subsystem: alerts, api, scheduler
tags: [telegram, scheduler, apscheduler, lifecycle, pipeline]

dependency-graph:
  requires:
    - phase: 06-telegram-alerts-01
      provides: "Bot module with start_bot/stop_bot lifecycle"
    - phase: 06-telegram-alerts-02
      provides: "AlertDispatcher with check_signal/check_price_movement"
  provides:
    - "check_and_dispatch_alerts() in scheduler — runs on fetch interval"
    - "Bot lifecycle wired into FastAPI lifespan"
    - "End-to-end: scheduler → signal → dispatcher → Telegram message"
  affects: []

tech-stack:
  added: []
  patterns:
    - "asyncio.new_event_loop() for sync-to-async dispatch in scheduler thread"
    - "Module-level dispatcher singleton with per-test reset"

key-files:
  created:
    - tests/test_alert_pipeline.py
  modified:
    - src/ingestion/scheduler.py
    - src/api/main.py

key-decisions:
  - "Separate scheduler job for alert dispatch (same interval as fetch)"
  - "Bot starts after DB init, before yield; stops before scheduler stop"
  - "asyncio.new_event_loop() instead of get_event_loop() for thread safety"

patterns-established:
  - "Alert dispatch is best-effort: errors logged, never crash scheduler"

requirements-completed: [DEL-02]

metrics:
  duration: 4min
  completed: 2026-03-25T20:10:00Z
---

# Phase 6 Plan 03: Alert Pipeline Integration Summary

**Telegram bot and alert dispatcher wired into scheduler pipeline and FastAPI lifespan for end-to-end alert delivery on signal changes and price movements**

## Performance

- **Duration:** 4 min
- **Started:** 2026-03-25T20:08:00Z
- **Completed:** 2026-03-25T20:10:00Z
- **Tasks:** 1
- **Files modified:** 3

## Accomplishments
- Alert dispatcher integrated into APScheduler as interval job
- Bot lifecycle (start/stop) wired into FastAPI lifespan
- End-to-end: scheduler → compute signal → check changes → send Telegram alert
- Error isolation: dispatch failures don't break scheduler
- 7 integration tests covering dispatch, scheduler, and lifespan wiring

## Task Commits

1. **Task 1: Pipeline wiring (TDD RED)** - `dee3d8e` (test)
2. **Task 1: Pipeline wiring (TDD GREEN)** - `1a7fe47` (feat)

## Files Created/Modified
- `src/ingestion/scheduler.py` - Added check_and_dispatch_alerts function and alert_dispatch job
- `src/api/main.py` - Added start_bot/stop_bot calls in lifespan
- `tests/test_alert_pipeline.py` - 7 integration tests

## Decisions Made
- Separate scheduler job for alert dispatch (same interval as fetch) rather than chaining after fetch — simpler, dispatcher handles dedup internally
- `asyncio.new_event_loop()` for sync-to-async dispatch in BackgroundScheduler thread — avoids deprecation warnings and thread safety issues
- Bot starts after DB init (needs database_url from settings) and stops before scheduler

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] Fixed patch targets for locally-imported modules**
- **Found during:** Task 1 (GREEN phase)
- **Issue:** Tests patched `src.ingestion.scheduler.compute_signal` but imports are local inside function
- **Fix:** Changed patch targets to source modules (`src.engine.pipeline.compute_signal`, `src.alerts.dispatcher.AlertDispatcher`)
- **Files modified:** tests/test_alert_pipeline.py
- **Verification:** All 7 tests pass
- **Committed in:** `1a7fe47`

**2. [Rule 1 - Bug] Fixed dispatcher singleton leaking between tests**
- **Found during:** Task 1 (GREEN phase)
- **Issue:** Module-level `_dispatcher` persisted between tests, causing mock to not be used
- **Fix:** Added autouse fixture to reset `sched._dispatcher = None` before/after each test
- **Files modified:** tests/test_alert_pipeline.py
- **Verification:** All 7 tests pass
- **Committed in:** `1a7fe47`

**3. [Rule 1 - Bug] Fixed asyncio deprecation warning**
- **Found during:** Task 1 (GREEN phase)
- **Issue:** `asyncio.get_event_loop()` raises DeprecationWarning in Python 3.12
- **Fix:** Changed to `asyncio.new_event_loop()` with explicit close in finally block
- **Files modified:** src/ingestion/scheduler.py
- **Verification:** No warnings, all tests pass
- **Committed in:** `1a7fe47`

**4. [Rule 1 - Bug] Fixed lifespan test to use async context manager**
- **Found during:** Task 1 (GREEN phase)
- **Issue:** FastAPI lifespan is async context manager, test used sync `with`
- **Fix:** Changed test to async with `@pytest.mark.asyncio` and `async with`
- **Files modified:** tests/test_alert_pipeline.py
- **Verification:** All 7 tests pass
- **Committed in:** `1a7fe47`

---

**Total deviations:** 4 auto-fixed (4 bugs — all test/implementation fixes)
**Impact on plan:** All fixes were test corrections and runtime compatibility. No scope creep.

## Issues Encountered
None beyond the standard TDD test-first corrections.

## Known Stubs
None — full pipeline is wired and operational.

## User Setup Required

Set `TELEGRAM_BOT_TOKEN` environment variable to enable Telegram alerts. Without it, the bot is disabled (warning logged) but the scheduler still runs fetches and signal computation.

## Next Phase Readiness
- Complete alert pipeline operational: fetch → signal → detect change → Telegram notification
- Phase 6 fully delivers DEL-02 (Telegram push notifications on signal changes and price movements)
- Ready for Phase 7 (Macro Indicators) which can also feed into alert dispatch

---
*Phase: 06-telegram-alerts*
*Completed: 2026-03-25*

## Self-Check: PASSED
