---
phase: 04-signal-engine-core
plan: 01
subsystem: signal-engine
tags: [signal, gap, spread, trend, composite, tdd, dataclass]

dependency-graph:
  requires: []
  provides:
    - Signal types (Signal, Recommendation, SignalMode, SignalFactor)
    - Gap signal factor calculator
    - Spread signal factor calculator
    - Trend signal factor calculator
    - Composite scorer with Saver/Trader mode thresholds
  affects: [04-02-signal-reasoning, 04-03-signal-integration, 05-dashboard, 06-alerts]

tech-stack:
  added: []
  patterns:
    - "TDD RED-GREEN for each signal module"
    - "SignalFactor with clamped direction/weight/confidence via __post_init__"
    - "Weighted composite scoring with mode-dependent thresholds"

key-files:
  created:
    - src/engine/__init__.py
    - src/engine/types.py
    - src/engine/gap_signal.py
    - src/engine/spread_signal.py
    - src/engine/trend_signal.py
    - src/engine/composite.py
    - tests/test_gap_signal.py
    - tests/test_spread_signal.py
    - tests/test_trend_signal.py
    - tests/test_composite.py
  modified: []

key-decisions:
  - "SignalFactor direction clamped in __post_init__ to prevent downstream bugs"
  - "Composite scorer uses separate Saver (0.05/-0.05) and Trader (0.25/-0.25) thresholds"
  - "Trend signal combines half-split comparison (70%) with MA crossover signal (30%)"
  - "Spread signal maps to [-0.5, 0.5] range as secondary modulating factor"

patterns-established:
  - "SignalFactor dataclass with auto-clamping validation"
  - "TDD workflow: RED (test commit) → GREEN (impl commit) per module"
  - "No LLM code in src/engine/ — all computation is pure deterministic Python"

requirements-completed: [SIG-01]

metrics:
  duration: 3min
  completed: 2026-03-25T02:23:47Z
---

# Phase 4 Plan 1: Signal Engine Core Summary

**Deterministic signal engine with three independent factors (gap, spread, trend) and weighted composite scorer producing Buy/Hold/Sell recommendations with 0-100 confidence scores**

## Performance

- **Duration:** 3 min
- **Started:** 2026-03-24T19:20:37Z
- **Completed:** 2026-03-25T02:23:47Z
- **Tasks:** 3
- **Files modified:** 10
- **New test cases:** 35

## Accomplishments
- Signal type contracts: Recommendation (BUY/HOLD/SELL), SignalMode (SAVER/TRADER), SignalFactor, Signal dataclasses
- Three independent signal factors: gap (weight 0.5), spread (weight 0.2), trend (weight 0.3)
- Composite scorer combining factors with mode-dependent thresholds into actionable recommendations
- Full TDD coverage with 35 test cases covering edge cases and boundary conditions

## Task Commits

Each task was committed atomically:

1. **Task 0: Define signal type contracts** - `89a3478` (feat)
2. **Task 1 RED: Gap + spread failing tests** - `1c33ca7` (test)
3. **Task 1 GREEN: Gap + spread implementation** - `a7a8cac` (feat)
4. **Task 2 RED: Trend + composite failing tests** - `b2dc979` (test)
5. **Task 2 GREEN: Trend + composite implementation** - `d31607a` (feat)

## Files Created/Modified
- `src/engine/__init__.py` - Package marker
- `src/engine/types.py` - Signal, Recommendation, SignalMode, SignalFactor dataclasses with auto-clamping
- `src/engine/gap_signal.py` - Gap factor: compares gap_pct vs 30d/7d moving averages
- `src/engine/spread_signal.py` - Spread factor: maps dealer spread width to directional signal
- `src/engine/trend_signal.py` - Trend factor: half-split trend + MA crossover detection
- `src/engine/composite.py` - Composite scorer: weighted sum with Saver/Trader mode thresholds
- `tests/test_gap_signal.py` - 7 test cases for gap signal factor
- `tests/test_spread_signal.py` - 6 test cases for spread signal factor
- `tests/test_trend_signal.py` - 14 test cases (6 trend + 8 composite)
- `tests/test_composite.py` - 8 test cases for composite scorer

## Decisions Made
- SignalFactor uses frozen=True for immutability; clamping in __post_init__ since frozen prevents attribute assignment — used object.__setattr__ as workaround
- Gap signal scales direction by 5x the deviation percentage for meaningful signal separation
- Trend signal weights raw trend (70%) higher than MA crossover (30%) since crossover is a derived signal
- Spread signal uses step-function mapping (<0.5%, 0.5-1%, 1-2%, 2-3%, >3%) rather than linear interpolation for clearer interpretability

## Deviations from Plan

None - plan executed exactly as written.

## Issues Encountered
None

## Known Stubs
- `Signal.reasoning` is always empty string `""` — intentional, filled by Plan 02 (signal reasoning module with LLM integration)

## User Setup Required
None - no external service configuration required.

## Next Phase Readiness
- All signal types and factor calculators ready for Plan 02 (signal reasoning)
- Plan 02 will wire LLM reasoning into Signal.reasoning field
- Plan 03 will integrate signal engine with API endpoints
- No blockers

## Self-Check: PASSED

---
*Phase: 04-signal-engine-core*
*Completed: 2026-03-25*
