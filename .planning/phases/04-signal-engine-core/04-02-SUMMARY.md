---
phase: 04-signal-engine-core
plan: 02
subsystem: signal-engine
tags: [reasoning, modes, sqlalchemy, persistence, tdd]

dependency-graph:
  requires:
    - phase: 04-01
      provides: "Signal dataclass, SignalMode, SignalFactor, Recommendation types; composite signal computation"
  provides:
    - "generate_reasoning() — deterministic one-line signal explanations with actual data values"
    - "get_mode_weights/get_mode_thresholds — SAVER vs TRADER interpretation"
    - "SignalRecord SQLAlchemy model for signal persistence"
    - "save_signal/get_latest_signal/get_signals_since repository functions"
  affects: [04-03, 05-dashboard, 08-accuracy-tracking]

tech-stack:
  added: []
  patterns:
    - "TDD RED→GREEN for reasoning and mode modules"
    - "Deterministic reasoning via f-string formatting — no LLM"
    - "Observational language enforcement (no prediction words)"
    - "Factor serialization to JSON string in SignalRecord"
    - "Mode-scoped queries with optional mode filter (None = any mode)"

key-files:
  created:
    - src/engine/reasoning.py
    - src/engine/modes.py
    - tests/test_reasoning.py
    - tests/test_modes.py
    - tests/test_signal_repository.py
  modified:
    - src/storage/models.py
    - src/storage/repository.py

key-decisions:
  - "Reasoning uses f-strings with conditional logic — pure deterministic, no LLM"
  - "MA fallback chain: 30d → 7d when 30d unavailable"
  - "Observational language only: 'observed', 'tracks at' — forbidden: 'will', 'expected', 'predict'"
  - "Mode prefix prepended to reasoning body for user-facing context"
  - "SignalRecord.factor_data stored as JSON string (not separate table) for simplicity"

patterns-established:
  - "Reasoning pattern: extract data → build body → prepend mode prefix"
  - "Signal persistence: serialize factors to JSON → store in single table"

requirements-completed: [SIG-02, SIG-06]

metrics:
  duration: 3min
  completed: 2026-03-24
---

# Phase 04 Plan 02: Reasoning + Modes + Signal Persistence Summary

**Deterministic reasoning generator with mode-specific prefixes, mode weight/threshold interpreter, and SignalRecord persistence with JSON factor serialization**

## Performance

- **Duration:** 3 min
- **Started:** 2026-03-24T19:24:42Z
- **Completed:** 2026-03-24T19:27:14Z
- **Tasks:** 2
- **Files modified:** 7

## Accomplishments
- `generate_reasoning()` produces grounded one-line explanations using actual gap_pct and MA values
- Observational language enforced — reasoning never uses prediction words
- Saver mode adds "For long-term accumulation:" prefix; Trader adds "For timing-precision:"
- MA fallback chain: 30d → 7d when 30d unavailable
- Mode weights and thresholds centralized in modes.py (SAVER: trend-heavy, TRADER: gap-heavy)
- SignalRecord model with JSON-serialized factor_data for full signal context persistence
- 25 new test cases with TDD RED→GREEN flow

## Task Commits

Each task was committed atomically via TDD:

1. **Task 1 RED: Reasoning + Mode tests** - `c0da3d4` (test)
2. **Task 1 GREEN: Reasoning + Mode implementation** - `1525b07` (feat)
3. **Task 2 RED: Signal repository tests** - `8d943d3` (test)
4. **Task 2 GREEN: SignalRecord model + repository** - `14f0e75` (feat)

**Plan metadata:** pending (docs: complete plan)

## Files Created/Modified
- `src/engine/reasoning.py` — generate_reasoning() with mode prefix, MA fallback, observational language
- `src/engine/modes.py` — get_mode_weights(), get_mode_thresholds() for SAVER/TRADER
- `src/storage/models.py` — Added SignalRecord model with factor_data JSON column
- `src/storage/repository.py` — Added save_signal(), get_latest_signal(), get_signals_since()
- `tests/test_reasoning.py` — 10 tests for reasoning generation
- `tests/test_modes.py` — 6 tests for mode weights/thresholds
- `tests/test_signal_repository.py` — 9 tests for signal persistence

## Decisions Made
- Reasoning uses pure f-string formatting with conditional logic — no LLM, fully deterministic
- MA fallback chain prioritizes 30d average, falls back to 7d when 30d unavailable
- Mode prefix prepended to body rather than appended — reads more naturally
- SignalRecord uses single table with JSON factor_data rather than normalized factor table — simpler for this data volume

## Deviations from Plan

None - plan executed exactly as written.

## Issues Encountered
None

## User Setup Required
None - no external service configuration required.

## Next Phase Readiness
- Reasoning generator ready to be called from composite signal pipeline (Plan 03)
- Mode weights/thresholds available for composite signal computation
- SignalRecord model and repository ready for signal persistence in production pipeline
- All 177 tests pass (25 new + 152 existing)

---
*Phase: 04-signal-engine-core*
*Completed: 2026-03-24*
