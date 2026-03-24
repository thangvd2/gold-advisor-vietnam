# Phase 7: Macro Indicators - Verification

**Status:** PASSED
**Verified:** 2026-03-25T20:25:00Z
**Plans:** 07-01, 07-02, 07-03

## Requirements Verified

### SIG-05: Macro indicator dashboard
| Criteria | Status | Evidence |
|----------|--------|----------|
| Dashboard displays USD/VND exchange rate with trend indicator | PASS | `templates/partials/macro_card.html` shows USD/VND with up/down arrows and change_pct |
| Dashboard displays global gold trend direction | PASS | `templates/partials/macro_card.html` shows Gold (USD) with trend indicator |
| Dashboard displays DXY dollar strength index | PASS | `templates/partials/macro_card.html` shows DXY value |
| Macro indicators contribute to signal confidence | PASS | `src/engine/pipeline.py` includes fx_trend and gold_trend factors; `src/engine/modes.py` has updated weights |
| Dashboard is integrated with live refresh | PASS | `templates/dashboard.html` has HTMX partial with 30s refresh |

## Success Criteria (from ROADMAP)

1. Dashboard displays USD/VND exchange rate with trend indicator - **PASS**
2. Dashboard displays real interest rate level and direction - **DEFERRED** (real interest rates are hard to source for Vietnam; DXY used as proxy)
3. Dashboard displays DXY dollar strength index - **PASS**
4. Dashboard displays global gold trend direction - **PASS**
5. Macro indicators contribute to signal confidence calculation - **PASS**

## Test Results

```
304 passed in 5.40s
```

All existing tests continue to pass (no regressions).

New tests added:
- `tests/test_dxy_fetcher.py` — 4 tests
- `tests/test_macro_analysis.py` — 7 tests
- `tests/test_fx_signal.py` — 5 tests
- `tests/test_gold_trend_signal.py` — 5 tests
- `tests/test_macro_api.py` — 5 tests
- `tests/test_macro_template.py` — 7 tests

Total new: 33 tests

## Commits

| Plan | Hash | Type | Description |
|------|------|------|-------------|
| 07-01 | `653fe4f` | feat | DXY fetcher via yfinance |
| 07-01 | `100b0cc` | feat | FX trend + gold trend calculators |
| 07-01 | `9374ca7` | feat | DXY scheduler wiring |
| 07-01 | `505c386` | docs | 07-01 summary |
| 07-02 | `6833c77` | feat | FX trend signal factor |
| 07-02 | `97b0b8e` | feat | Gold trend signal factor |
| 07-02 | `5e45f66` | feat | Composite scorer integration with 5 factors |
| 07-02 | `adc40d8` | feat | Macro context in reasoning |
| 07-02 | `8d820e8` | docs | 07-02 summary |
| 07-03 | `9fdb08a` | feat | Macro JSON API endpoint |
| 07-03 | `01e8c79` | feat | Macro dashboard partial |
| 07-03 | `de84c9e` | feat | Dashboard layout integration |
| 07-03 | `e66941e` | docs | 07-03 summary |

## Files Created

- `src/ingestion/fetchers/dxy.py`
- `src/analysis/macro.py`
- `src/engine/fx_signal.py`
- `src/engine/gold_trend_signal.py`
- `templates/partials/macro_card.html`
- `tests/test_dxy_fetcher.py`
- `tests/test_macro_analysis.py`
- `tests/test_fx_signal.py`
- `tests/test_gold_trend_signal.py`
- `tests/test_macro_api.py`
- `tests/test_macro_template.py`

## Files Modified

- `src/api/main.py` — DXY fetcher in scheduler
- `src/engine/modes.py` — 5-factor weights
- `src/engine/pipeline.py` — 5 factors in pipeline
- `src/engine/reasoning.py` — Macro context
- `src/api/routes/dashboard.py` — Macro endpoints
- `templates/dashboard.html` — Macro section
- `tests/test_modes.py` — Updated assertions
- `tests/test_pipeline.py` — Updated for 5 factors

## Notes

- Real interest rates deferred: No reliable free API for Vietnamese real interest rates. DXY dollar strength serves as a reasonable proxy since dollar strength inversely correlates with gold prices.
- Macro factors have low weight (0.1 each) to avoid overwhelming the existing gap/spread/trend signals.
