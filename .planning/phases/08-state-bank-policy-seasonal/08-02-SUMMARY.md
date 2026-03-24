---
phase: 08-state-bank-policy-seasonal
plan: 02
subsystem: signal-engine,admin-api
tags: [state-bank, policy, override, admin, crud]
requirements: [SIG-03]

dependency_graph:
  requires: []
  provides: [08-state-bank-policy-seasonal-03]
  affects: [src/storage/models.py, src/api/main.py]

tech_stack:
  added: []
  patterns: [admin-crud-api, policy-override, confidence-capping]

key_files:
  created:
    - src/engine/policy.py
    - src/api/routes/admin.py
    - tests/test_policy_signal.py
  modified:
    - src/storage/models.py
    - src/api/main.py

decisions:
  - key: "No Alembic — project uses Base.metadata.create_all()"
    rationale: "No Alembic setup exists in the project; new PolicyEvent table is created automatically"
  - key: "Admin API uses Pydantic model with regex validation for enums"
    rationale: "FastAPI's Pydantic integration provides automatic validation; no need for custom validators"
  - key: "Policy override caps confidence rather than changing direction"
    rationale: "Per PITFALLS.md: State Bank actions override all other signals via confidence reduction, not directional flip"

metrics:
  duration: 5min
  completed: 2026-03-25
  tasks: 3
  files: 5
  tests_added: 17
  tests_passing: 356
---

# Phase 8 Plan 02: State Bank Policy Model Summary

State Bank policy event tracking system with manual admin API for recording policy events. Policy events override all other signals by capping confidence.

## What Was Built

- **PolicyEvent model**: SQLAlchemy model tracking SBV policy events with event_type, impact, severity, effective_date, expiry, and active flag
- **Policy signal calculator**: `compute_policy_signal()` identifies active events, computes confidence caps (high=0.3, medium=0.6, low=1.0)
- **Admin API**: CRUD endpoints for managing policy events via REST API

## Deviations from Plan

- **Rule 3 - Blocking issue**: No Alembic migration system exists in the project. Instead of adding Alembic, the PolicyEvent table is automatically created via `Base.metadata.create_all()` in `init_db()` (same pattern as all other models). This is simpler and consistent with existing codebase.

## Key Design Decisions

1. **Confidence caps, not directional overrides**: High-severity events cap confidence at 30% rather than flipping the signal. This preserves the informational nature of signals while communicating uncertainty.
2. **Soft-delete pattern**: DELETE endpoint sets `is_active=False` rather than removing records, preserving audit trail.
3. **Expired events auto-excluded**: Events with `expires_at < now` are automatically excluded from active events, even if `is_active=True`.

## Known Stubs

None. The policy model and admin API are fully functional.
