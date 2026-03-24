---
phase: 04-signal-engine-core
verified: 2026-03-25T14:30:00Z
status: passed
score: 4/4 must-haves verified
re_verification:
  previous_status: gaps_found
  previous_score: 3/4
  gaps_closed:
    - "Saver/Trader mode produces different confidence weighting via mode-specific factor weights"
    - "Signal engine uses multi-factor analysis (gap, spread, trend)"
  gaps_remaining: []
  regressions: []
---

# Phase 4: Signal Engine Core Verification Report

**Phase Goal:** Generate Buy/Hold/Sell signals with confidence, reasoning, Saver/Trader modes
**Verified:** 2026-03-25T14:30:00Z
**Status:** passed
**Re-verification:** Yes — after gap closure (Plan 04-04)

## Goal Achievement

### Observable Truths

| # | Truth | Status | Evidence |
|---|-------|--------|----------|
| 1 | Signal engine produces Buy/Hold/Sell with 0-100 confidence based on multi-factor analysis | ✓ VERIFIED | Composite scorer produces BUY/HOLD/SELL with 0-100 confidence. Gap (mode-weighted), spread (real dealer data), and trend (mode-weighted) factors all contribute. `calculate_dealer_spreads()` feeds real per-dealer spreads; `get_mode_weights()` applies mode-specific factor weights. |
| 2 | Each signal includes one-line reasoning with actual data values | ✓ VERIFIED | `reasoning.py` generates grounded strings using actual gap_pct and MA values. No prediction language. MA fallback chain (30d -> 7d). Unchanged from initial verification. |
| 3 | Saver/Trader modes produce different guidance and confidence weighting | ✓ VERIFIED | `get_mode_weights()` called in pipeline.py (line 10, 34). SAVER: gap=0.4, spread=0.1, trend=0.5. TRADER: gap=0.6, spread=0.3, trend=0.1. Same input data produces different raw_scores. Thresholds via `get_mode_thresholds()` imported in composite.py (line 3, 22). `THRESHOLDS` dict removed from composite.py. |
| 4 | Signals stored with full context for historical analysis | ✓ VERIFIED | `SignalRecord` model stores recommendation, confidence, gap_vnd, gap_pct, mode, reasoning, factor_data (JSON). Repository: save_signal(), get_latest_signal(), get_signals_since() all functional. API history endpoint wired. Unchanged from initial verification. |

**Score:** 4/4 truths verified

### Required Artifacts

| Artifact | Expected | Status | Details |
|----------|----------|--------|---------|
| `src/engine/types.py` | Signal, Recommendation, SignalMode, SignalFactor | ✓ VERIFIED | 67 lines. Enums + frozen dataclass with auto-clamping. |
| `src/engine/gap_signal.py` | Gap factor scoring with mode-adjustable weight | ✓ VERIFIED | 38 lines. Accepts `weight` param (default 0.5). Direction from gap_pct vs MA deviation. |
| `src/engine/spread_signal.py` | Spread factor scoring with mode-adjustable weight | ✓ VERIFIED | 34 lines. Accepts `weight` param (default 0.2). Step-function mapping from dealer spread percentages. |
| `src/engine/trend_signal.py` | Trend (MA-based) factor with mode-adjustable weight | ✓ VERIFIED | 52 lines. Accepts `weight` param (default 0.3). Half-split trend (70%) + MA crossover (30%). |
| `src/engine/composite.py` | Weighted composite scorer using modes.py thresholds | ✓ VERIFIED | 41 lines. Imports `get_mode_thresholds()` from modes.py. No duplicate `THRESHOLDS` dict. |
| `src/engine/reasoning.py` | One-line reasoning generation | ✓ VERIFIED | 94 lines. Deterministic f-strings, no LLM, observational language only. |
| `src/engine/modes.py` | Mode weights/thresholds | ✓ VERIFIED | 25 lines. `get_mode_weights()` and `get_mode_thresholds()` now fully wired. |
| `src/engine/pipeline.py` | End-to-end signal pipeline | ✓ VERIFIED | 53 lines. Imports `get_mode_weights` and `calculate_dealer_spreads`. Passes mode weights to factors, real dealer spreads to spread factor. |
| `src/analysis/gap.py` (calculate_dealer_spreads) | Per-dealer spread data query | ✓ VERIFIED | New function returns list[float] of spread percentages per dealer from price_history table. |
| `src/api/routes/signals.py` | Signal REST API | ✓ VERIFIED | GET /current and GET /history. Mode param, 503 on insufficient data. |
| `src/storage/models.py` (SignalRecord) | Signal persistence model | ✓ VERIFIED | SignalRecord with all fields including factor_data JSON column. |
| `src/storage/repository.py` (signal funcs) | Signal CRUD | ✓ VERIFIED | save_signal(), get_latest_signal(), get_signals_since() — all use async session pattern. |

### Key Link Verification

| From | To | Via | Status | Details |
|------|-----|-----|--------|---------|
| `types.py` | `gap_signal.py` | imports SignalFactor | ✓ WIRED | `from src.engine.types import SignalFactor` |
| `types.py` | `composite.py` | imports Signal, SignalFactor, Recommendation, SignalMode | ✓ WIRED | Line 4 |
| `pipeline.py` | `modes.py` | imports get_mode_weights | ✓ WIRED | Line 10, called line 34 |
| `pipeline.py` | `gap.py` | calls calculate_current_gap, calculate_historical_gaps, calculate_dealer_spreads | ✓ WIRED | Lines 3-7, 18, 32-33 |
| `pipeline.py` | `composite.py` | calls compute_composite_signal | ✓ WIRED | Lines 8, 46 |
| `pipeline.py` | `reasoning.py` | calls generate_reasoning | ✓ WIRED | Lines 11, 51 |
| `pipeline.py` | `spread_signal.py` | calls compute_spread_signal with real data | ✓ WIRED | Lines 12, 39 — passes `dealer_spreads`, not `[]` |
| `pipeline.py` | factor functions | passes mode-specific weights | ✓ WIRED | Lines 36-42 — `weight=mode_weights["gap/spread/trend"]` |
| `composite.py` | `modes.py` | imports get_mode_thresholds | ✓ WIRED | Line 3, used line 22 |
| `signals.py` | `pipeline.py` | calls compute_signal via asyncio.to_thread | ✓ WIRED | Lines 8, 32 |
| `signals.py` | `main.py` | include_router /api/signals | ✓ WIRED | main.py line 50 |

### Data-Flow Trace (Level 4)

| Artifact | Data Variable | Source | Produces Real Data | Status |
|----------|---------------|--------|-------------------|--------|
| `pipeline.py` | current_gap | calculate_current_gap() -> DuckDB query | ✓ Yes (real DB query) | ✓ FLOWING |
| `pipeline.py` | historical_gaps | calculate_historical_gaps() -> DuckDB query | ✓ Yes (real DB query) | ✓ FLOWING |
| `pipeline.py` | dealer_spreads | calculate_dealer_spreads() -> DuckDB query | ✓ Yes (real DB query) | ✓ FLOWING |
| `pipeline.py` | mode_weights | get_mode_weights(mode) | ✓ Yes (dict lookup) | ✓ FLOWING |
| `pipeline.py` | spread_factor | compute_spread_signal(dealer_spreads) | ✓ From real dealer data | ✓ FLOWING |
| `composite.py` | thresholds | get_mode_thresholds(mode) | ✓ From modes.py | ✓ FLOWING |
| `reasoning.py` | gap_pct, ma_value | From signal + current_gap dict | ✓ From real data | ✓ FLOWING |

### Behavioral Spot-Checks

| Behavior | Command | Result | Status |
|----------|---------|--------|--------|
| All Phase 4 tests pass | `uv run python -m pytest tests/test_*signal* tests/test_pipeline.py tests/test_modes.py tests/test_reasoning.py tests/test_signal_repository.py tests/test_signal_api.py` | 84 passed in 1.83s | ✓ PASS |
| Full suite no regressions | `uv run python -m pytest -x` | 199 passed in 3.23s | ✓ PASS |
| No LLM code in engine | `grep -rn "openai\|llm" src/engine/` | (none found) | ✓ PASS |
| No prediction language | `grep -rn "predict\|will \|forecast" src/engine/reasoning.py` | (none found) | ✓ PASS |
| Mode weights wired in pipeline | `grep "get_mode_weights" src/engine/pipeline.py` | Imported line 10, called line 34 | ✓ PASS |
| Spread data connected | `grep "calculate_dealer_spreads" src/engine/pipeline.py` | Imported line 5, called line 33 | ✓ PASS |
| No more empty spread call | `grep "compute_spread_signal(\[\])" src/engine/pipeline.py` | (none found) | ✓ PASS |
| No duplicate thresholds | `grep "THRESHOLDS" src/engine/composite.py` | Only "get_mode_thresholds" import (line 3) | ✓ PASS |

### Requirements Coverage

| Requirement | Source Plan | Description | Status | Evidence |
|-------------|------------|-------------|--------|----------|
| SIG-01 | 04-01, 04-03, 04-04 | Buy/Hold/Sell signal with confidence 0-100% | ✓ SATISFIED | Composite scorer with all 3 weighted factors + API endpoint /api/signals/current |
| SIG-02 | 04-02, 04-03 | One-line reasoning with actual data values | ✓ SATISFIED | reasoning.py generates grounded explanations; pipeline wires into signal; API returns reasoning field |
| SIG-06 | 04-01, 04-02, 04-03, 04-04 | Saver/Trader modes with different signals | ✓ SATISFIED | Mode-specific weights (SAVER: trend-heavy, TRADER: gap-heavy) applied via get_mode_weights(). Mode-specific thresholds via get_mode_thresholds(). Same data produces different composite scores per mode. |

### Anti-Patterns Found

| File | Line | Pattern | Severity | Impact |
|------|------|---------|----------|--------|
| (none) | - | - | - | No anti-patterns detected |

### Human Verification Required

None required. All checks are programmatic.

### Gaps Summary

Both gaps from the initial verification have been fully closed by Plan 04-04:

**Gap 1 (CLOSED): Mode-specific factor weights not wired.** `get_mode_weights()` is now imported and called in pipeline.py (line 34). Mode-specific weights are passed to each factor function: `compute_gap_signal(..., weight=mode_weights["gap"])`, `compute_spread_signal(..., weight=mode_weights["spread"])`, `compute_trend_signal(..., weight=mode_weights["trend"])`. composite.py now imports `get_mode_thresholds()` from modes.py instead of maintaining a duplicate `THRESHOLDS` dict. SAVER and TRADER modes produce genuinely different signals with different weight distributions AND different thresholds.

**Gap 2 (CLOSED): Spread factor disconnected from pipeline.** `calculate_dealer_spreads()` added to `src/analysis/gap.py` — queries DuckDB for latest per-dealer spread percentages from `price_history` table. Pipeline imports and calls it (line 33), passing real data to `compute_spread_signal()` (line 39). The spread factor now contributes non-zero signals when dealer spread data exists, with graceful degradation to zero when no data is available. The engine is now fully 3-factor.

---

_Verified: 2026-03-25T14:30:00Z_
_Verifier: Claude (gsd-verifier)_
