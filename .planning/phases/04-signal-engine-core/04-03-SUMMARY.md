---
phase: 04-signal-engine-core
plan: 03
subsystem: engine, api
tags: [pipeline, signals, fastapi, rest-api, tdd]

dependency-graph:
  requires:
    - phase: 04-signal-engine-core (Plan 01-02)
      provides: "Signal types, composite scoring, reasoning, gap/spread/trend factors, signal repository"
  provides:
    - "End-to-end signal pipeline: gap data → factors → composite → reasoning → Signal"
    - "GET /api/signals/current with mode param (saver/trader)"
    - "GET /api/signals/history with mode and days params"
  affects: [05-dashboard, 06-messenger-alerts]

tech-stack:
  added: []
  patterns:
    - "Sync pipeline function (compute_signal) wrapped in asyncio.to_thread for API use"
    - "Signal.__dict__ used for JSON serialization (dataclass, not Pydantic)"

key-files:
  created:
    - src/engine/pipeline.py
    - src/api/routes/signals.py
    - tests/test_pipeline.py
    - tests/test_signal_api.py
  modified:
    - src/api/main.py

key-decisions:
  - "Pipeline is pure sync function — no DB writes, no side effects, easy to test"
  - "Signal serialised via __dict__ since Signal is a dataclass, not a Pydantic model"
  - "503 returned when confidence==0 AND recommendation==HOLD (insufficient data)"

patterns-established:
  - "Sync compute function → asyncio.to_thread → API endpoint pattern"
  - "Signal API follows same router pattern as gap API (get_settings, _get_db_path, TestClient)"

requirements-completed: [SIG-01, SIG-02, SIG-06]

metrics:
  duration: 2min
  completed: 2026-03-25
---

# Phase 4 Plan 03: Signal Pipeline & API Summary

**End-to-end signal pipeline wiring gap→factors→composite→reasoning with REST API for current/historical signals**

## Performance

- **Duration:** 2 min
- **Started:** 2026-03-24T19:28:14Z
- **Completed:** 2026-03-24T19:30:22Z
- **Tasks:** 2 (4 TDD commits)
- **Files modified:** 5

## Accomplishments
- Signal pipeline orchestrator `compute_signal(db_path, mode)` wires gap data through all factors to a complete Signal
- `/api/signals/current?mode=saver|trader` returns live signal with recommendation, confidence, reasoning, and factors
- `/api/signals/history?mode=saver|trader&days=7` returns persisted signal records from the database
- Graceful 503 when insufficient data, 422 on invalid mode parameter

## Task Commits

1. **Task 1 RED: Failing pipeline tests** - `78c9d71` (test)
2. **Task 1 GREEN: Pipeline orchestrator** - `14b0835` (feat)
3. **Task 2 RED: Failing API tests** - `b2e6ef1` (test)
4. **Task 2 GREEN: Signal API + wiring** - `36332c8` (feat)

## Files Created/Modified
- `src/engine/pipeline.py` - End-to-end signal computation pipeline (gap→factors→composite→reasoning)
- `src/api/routes/signals.py` - GET /current and GET /history endpoints for signals
- `src/api/main.py` - Wired signals_router with /api/signals prefix
- `tests/test_pipeline.py` - 5 tests for pipeline orchestrator (data, no-data, factors, modes, gap values)
- `tests/test_signal_api.py` - 8 tests for signal API (current, history, 503, 422, mode filtering)

## Decisions Made
- Pipeline is a pure sync function (no DB writes, no side effects) — storage is handled separately by callers
- Signal dataclass serialized via `__dict__` for JSON response since Signal is a dataclass, not Pydantic
- 503 condition: confidence==0 AND recommendation==HOLD signals insufficient data (vs a genuine HOLD recommendation with real confidence)

## Deviations from Plan

None - plan executed exactly as written.

## Issues Encountered

None.

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness
- Signal pipeline and API fully functional — ready for dashboard (Phase 5) and messenger alerts (Phase 6)
- Dashboard can consume `/api/signals/current` for live signal display
- Telegram bot can poll `/api/signals/current` and alert on signal changes

## Self-Check: PASSED

All files exist, all 4 commits verified, 190/190 tests pass.

---
*Phase: 04-signal-engine-core*
*Completed: 2026-03-25*
