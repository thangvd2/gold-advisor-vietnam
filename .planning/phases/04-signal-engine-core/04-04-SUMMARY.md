---
phase: 04-signal-engine-core
plan: 04
subsystem: signal-engine
tags: [duckdb, signal-engine, tdd, mode-weights, spread-analysis]

dependency-graph:
  requires:
    - phase: 04-signal-engine-core
      plan: "01-03"
      provides: "gap/spread/trend signal factors, composite scoring, modes.py with weights and thresholds"
  provides:
    - Mode-specific factor weights wired into pipeline (SAVER: gap=0.4, spread=0.1, trend=0.5; TRADER: gap=0.6, spread=0.3, trend=0.1)
    - Per-dealer spread data flowing through calculate_dealer_spreads() to spread factor
    - Composite thresholds imported from modes.py (no duplicate THRESHOLDS dict)
  affects: [05-dashboard, 06-alerts]

tech-stack:
  added: []
  patterns:
    - "Mode-specific weight injection: pipeline calls get_mode_weights(mode) and passes to each compute_*_signal(weight=...)"
    - "Default weight parameters for backward compatibility: compute_*_signal(..., weight=0.5)"

key-files:
  created: []
  modified:
    - src/analysis/gap.py
    - src/engine/pipeline.py
    - src/engine/composite.py
    - src/engine/gap_signal.py
    - src/engine/spread_signal.py
    - src/engine/trend_signal.py
    - tests/test_pipeline.py
    - tests/test_composite.py

key-decisions:
  - "Weight param with defaults preserves backward compatibility for existing unit tests"
  - "calculate_dealer_spreads() uses DuckDB ROW_NUMBER window for latest-per-dealer query"
  - "Composite removes local THRESHOLDS dict entirely — single source of truth in modes.py"

requirements-completed: [SIG-01, SIG-06]

metrics:
  duration: 2min
  completed: 2026-03-24T19:38:29Z
---

# Phase 04 Plan 04: Gap Closure Summary

**Mode-specific factor weights and per-dealer spread data wired into the 3-factor signal pipeline, making SAVER and TRADER modes produce genuinely different signals.**

## Performance

- **Duration:** 2 min
- **Started:** 2026-03-24T19:35:53Z
- **Completed:** 2026-03-24T19:38:29Z
- **Tasks:** 1 (TDD: RED + GREEN)
- **Files modified:** 8

## Accomplishments
- `get_mode_weights()` is now called in pipeline.py, routing SAVER (trend-heavy) and TRADER (gap-heavy) weight distributions to each factor
- `calculate_dealer_spreads()` queries DuckDB for per-dealer spread percentages, feeding real data to the spread factor
- Composite `THRESHOLDS` dict eliminated — single source of truth is `modes.py`
- Full 3-factor analysis now active (gap, spread, trend all contribute real data)
- 199 tests pass (9 new, 190 existing — zero regressions)

## Task Commits

1. **Task 1: Wire mode weights + spread data into pipeline** - `cfb6a24` (test: RED), `c79b70b` (feat: GREEN)

## Files Created/Modified
- `src/analysis/gap.py` - Added `calculate_dealer_spreads()` function for per-dealer spread percentages via DuckDB
- `src/engine/pipeline.py` - Wired `get_mode_weights(mode)` and `calculate_dealer_spreads(db_path)` into signal computation
- `src/engine/composite.py` - Removed duplicate `THRESHOLDS` dict, imports `get_mode_thresholds()` from modes.py
- `src/engine/gap_signal.py` - Added `weight` parameter (default 0.5) to `compute_gap_signal()`
- `src/engine/spread_signal.py` - Added `weight` parameter (default 0.2) to `compute_spread_signal()`
- `src/engine/trend_signal.py` - Added `weight` parameter (default 0.3) to `compute_trend_signal()`
- `tests/test_pipeline.py` - Added 7 tests: mode weights wiring, spread data connection, calculate_dealer_spreads
- `tests/test_composite.py` - Added 2 tests: THRESHOLDS removal verification, mode threshold correctness

## Decisions Made
- **Weight param with defaults:** Factor functions accept `weight=0.5/0.2/0.3` defaults matching old hardcoded values, so existing unit tests pass unchanged
- **DuckDB ROW_NUMBER for latest-per-dealer:** `calculate_dealer_spreads()` partitions by source and picks the most recent row per dealer
- **No REFACTOR commit needed:** Code changes were minimal and clean — no post-GREEN cleanup required

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] Test seed data produced spread_pct in 0.5-2.0% range (direction=0.0)**
- **Found during:** Task 1 GREEN phase
- **Issue:** Original test seed had buy_price far below sell_price (e.g., buy=193M, sell=195M → 1.03%), which falls in the 0.5-2.0% band where spread_signal returns direction=0.0
- **Fix:** Adjusted dealer_prices to produce tight spreads (< 0.5%): buy=194.8M, sell=195M → 0.103%
- **Files modified:** tests/test_pipeline.py
- **Committed in:** `c79b70b` (part of GREEN commit)

---

**Total deviations:** 1 auto-fixed (1 bug)
**Impact on plan:** Fix necessary for test correctness — spread data was real but test assertion was wrong for the seed data chosen.

## Issues Encountered
None beyond the seed data issue above.

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness
- Signal engine fully functional with 3 factors, mode-specific weights, and proper threshold delegation
- Phase 05 (dashboard) can consume the complete Signal object with all factors populated
- Phase 06 (alerts) will use mode-specific confidence values for threshold-based alerting

## Verification Checks Passed
- `grep "get_mode_weights" src/engine/pipeline.py` — found (import + call)
- `grep "THRESHOLDS" src/engine/composite.py` — not found (removed)
- `grep "calculate_dealer_spreads" src/engine/pipeline.py` — found (import + call)
- `grep "compute_spread_signal(\[\])" src/engine/pipeline.py` — not found (bug fixed)
- Full suite: 199 tests pass

## Self-Check: PASSED

---
*Phase: 04-signal-engine-core*
*Completed: 2026-03-24*
