# Phase 8: State Bank Policy & Seasonal Factors - Context

**Gathered:** 2026-03-25 (auto-generated)
**Status:** Ready for planning

<domain>
## Phase Boundary

Incorporate State Bank of Vietnam policy events (import approvals, gold auctions, interventions) as a signal override factor, and factor in Vietnamese seasonal demand patterns (pre-Tet spike, post-Tet weakness, wedding season, Vu Lan, ghost month) into the signal engine.

</domain>

<decisions>
## Implementation Decisions

### Claude's Discretion
- How to model State Bank policy as a signal factor (override vs weighted factor)
- Seasonal demand calendar implementation (hardcoded dates per year or lunar calendar)
- Data source for State Bank policy events (manual curation initially per PITFALLS)
- How much weight seasonal factors get in composite scorer
- Whether to reduce confidence during known high-volatility periods

### Key Constraints (from PITFALLS.md)
- State Bank actions override all other signals — must be first-class
- Track market regime explicitly (post-Decree-232 era)
- Seasonal patterns should EXPLAIN gap widening, not be signals themselves
- "A VND 5M gap during Tet is normal (structural demand). A VND 5M gap during quiet August is unusual."
- Weight recent data more heavily (6-12 month rolling window)

</decisions>

<canonical_refs>
## Canonical References
- `.planning/research/PITFALLS.md` §Pitfall 4 — State Bank policy invalidating signals (CRITICAL)
- `.planning/research/PITFALLS.md` §Pitfall 6 — Vietnamese cultural complexity
- `.planning/research/ARCHITECTURE.md` §Vietnamese Seasonal Calendar
- `.planning/REQUIREMENTS.md` — SIG-03, SIG-04

</canonical_refs>

<code_context>
## Existing Code Insights
- 5-factor composite scorer at `src/engine/composite.py` with mode-specific weights
- Signal pipeline at `src/engine/pipeline.py`
- Reasoning generator at `src/engine/reasoning.py`
- Factor weight system supports adding new factors
- Dashboard at `templates/dashboard.html`

</code_context>

<specifics>
## Specific Ideas
- Seasonal model: simple lookup table mapping month → demand level (low/medium/high/very_high)
  - January-February: very high (Tet buying)
  - March-April: medium (post-Tet selling, wedding season start)
  - May-July: low (summer doldrums)
  - August: medium (Vu Lan)
  - September-October: low-medium
  - November-December: high (pre-Tet accumulation, wedding season)
- State Bank policy: start with manual override (admin endpoint to flag events), auto-detection deferred
- Seasonal factor: doesn't change direction, only adjusts confidence (reduce confidence during high-demand periods when gap widening is expected)
- SBV policy factor: overrides — if SBV intervention detected, set confidence to capped level

</specifics>

<deferred>
## Deferred Ideas
None
</deferred>

---
*Phase: 08-state-bank-policy-seasonal*
*Context gathered: 2026-03-25 (auto)*
