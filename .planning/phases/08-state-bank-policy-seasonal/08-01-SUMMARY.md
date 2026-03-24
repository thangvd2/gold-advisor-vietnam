---
phase: 08-state-bank-policy-seasonal
plan: 01
subsystem: signal-engine
tags: [seasonal, demand, vietnamese-calendar, signal-factor]
requirements: [SIG-04]

dependency_graph:
  requires: []
  provides: [08-state-bank-policy-seasonal-03]
  affects: []

tech_stack:
  added: []
  patterns: [lookup-table-calendar, confidence-modifier]

key_files:
  created:
    - src/engine/seasonal.py
    - tests/test_seasonal.py
  modified: []

decisions:
  - key: "Seasonal factor has zero direction and weight — only modifies confidence"
    rationale: "Per PITFALLS.md, seasonal patterns EXPLAIN gap widening, they don't generate buy/sell signals"
  - key: "Tet (Jan-Feb) = 0.7 modifier, high-demand (Nov-Dec) = 0.85 modifier"
    rationale: "During Tet, gap widening of 5M VND is expected/normal; during quiet months, same gap is anomalous"
  - key: "Medium and low demand months have modifier 1.0 (no adjustment)"
    rationale: "Gaps during quiet periods are meaningful signals; no reduction needed"

metrics:
  duration: 3min
  completed: 2026-03-25
  tasks: 3
  files: 2
  tests_added: 35
  tests_passing: 339
---

# Phase 8 Plan 01: Seasonal Demand Model Summary

Vietnamese seasonal demand calendar that maps months to demand levels and produces confidence modifiers for the signal engine. Seasonal patterns explain gap widening — they don't generate buy/sell signals themselves.

## What Was Built

- **Vietnamese seasonal calendar**: Maps each month (1-12) to a demand level based on cultural events (Tet, Vu Lan, wedding season)
- **Seasonal confidence modifier**: Reduces signal confidence during high-demand periods when gap widening is expected and not anomalous
- **Seasonal signal factor**: `SignalFactor` with zero direction/weight that stores the modifier for the composite scorer

## Deviations from Plan

None - plan executed exactly as written.

## Key Design Decisions

1. **Seasonal factor has direction=0.0 and weight=0.0**: Per PITFALLS.md, seasonal patterns explain gap widening but don't generate buy/sell signals. The composite scorer uses this differently from other factors.
2. **Modifier stored in confidence field**: Reuses existing `SignalFactor.confidence` to carry the modifier value (0.7-1.0) rather than adding a new field.

## Known Stubs

None. The seasonal model is fully functional and self-contained.
