---
phase: 08-state-bank-policy-seasonal
plan: 03
subsystem: signal-engine,dashboard
tags: [integration, composite-scorer, pipeline, reasoning, dashboard, seasonal, policy]
requirements: [SIG-03, SIG-04]

dependency_graph:
  requires: [08-state-bank-policy-seasonal-01, 08-state-bank-policy-seasonal-02]
  provides: []
  affects: [src/engine/composite.py, src/engine/pipeline.py, src/engine/reasoning.py, templates/partials/signal_card.html, src/api/routes/dashboard.py]

tech_stack:
  added: []
  patterns: [confidence-capping, multiplicative-modifier, contextual-badges, override-priority]

key_files:
  created:
    - tests/test_composite_override.py
    - tests/test_pipeline_seasonal_policy.py
    - tests/test_reasoning_seasonal_policy.py
  modified:
    - src/engine/composite.py
    - src/engine/pipeline.py
    - src/engine/reasoning.py
    - templates/partials/signal_card.html
    - src/api/routes/dashboard.py

decisions:
  - key: "Policy cap applied after seasonal modifier (policy takes priority)"
    rationale: "State Bank policy overrides everything — cap is applied last to ensure it's never exceeded"
  - key: "Seasonal badge only shown for high/very_high demand months"
    rationale: "Showing a badge during low/medium demand adds no information value to the user"
  - key: "Policy alert banner only shown when has_override=True"
    rationale: "Low-severity policy events (inspections) don't warrant a prominent alert"

metrics:
  duration: 5min
  completed: 2026-03-25
  tasks: 5
  files: 8
  tests_added: 23
  tests_passing: 379
---

# Phase 8 Plan 03: Integration Summary

Wired seasonal demand modifier and State Bank policy override into the signal pipeline, composite scorer, reasoning generator, and dashboard display.

## What Was Built

- **Composite scorer**: Accepts `policy_override` (confidence cap) and `seasonal_modifier` (multiplicative) parameters. Policy cap applied after seasonal modifier.
- **Pipeline**: Computes seasonal signal from current month, queries policy events, passes both to composite scorer and reasoning.
- **Reasoning**: Appends seasonal demand context ("High demand season (January) — gap widening is expected") and policy alerts ("State Bank policy alert: SBV gold auction").
- **Dashboard**: Seasonal demand badge (amber) and State Bank policy alert banner (red) shown on signal card.
- **API**: Signal JSON response includes `seasonal_demand_level` and `active_policy_events` fields.

## Deviations from Plan

None - plan executed as written.

## Key Design Decisions

1. **Policy override always wins**: Even if seasonal modifier reduces confidence, the policy cap is applied last and takes priority.
2. **Seasonal factor included in factors list**: The pipeline adds seasonal as a 6th factor (with zero direction/weight) for transparency and auditability.
3. **Graceful degradation**: Policy signal computation wrapped in try/except in dashboard routes — if policy events table doesn't exist yet, dashboard still works.

## Known Stubs

None. All features are fully functional and wired end-to-end.
