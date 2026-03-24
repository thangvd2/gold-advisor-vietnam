# Phase 7: Macro Indicators - Context

**Gathered:** 2026-03-25 (auto-generated)
**Status:** Ready for planning

<domain>
## Phase Boundary

Factor macroeconomic indicators (USD/VND exchange rate, real interest rates, DXY dollar strength, global gold trend) into signal confidence. Display macro context on dashboard. Macro factors influence signal confidence but don't override other signals.

</domain>

<decisions>
## Implementation Decisions
### Claude's Discretion
- Which macro indicators to prioritize (USD/VND trend is most relevant for Vietnam)
- Data sources for DXY, real interest rates (may need new API fetchers)
- How macro factors weight into existing 3-factor composite
- Dashboard display format for macro snapshot

### Key Constraints
- USD/VND fetcher already exists (Vietcombank from Phase 1) — reuse it
- Macro data updates less frequently than gold prices — cache appropriately
- Real interest rates may be hard to source for Vietnam specifically

</decisions>

<canonical_refs>
## Canonical References
- `.planning/research/ARCHITECTURE.md` §Macro Scorer component
- `.planning/REQUIREMENTS.md` — SIG-05
- `.planning/phases/04-signal-engine-core/04-01-SUMMARY.md` — Signal types, factor weights

</canonical_refs>

<code_context>
## Existing Code Insights
- `src/ingestion/fetchers/fx_rate.py` — Vietcombank USD/VND fetcher (already running)
- `src/engine/types.py` — SignalFactor interface, CompositeScorer
- `src/engine/pipeline.py` — Signal pipeline with 3 factors (gap, spread, trend)
- Factor weight system already supports adding new factors

</code_context>

<specifics>
## Specific Ideas
- USD/VND trend: already fetched, just need trend calculation (price above/below N-day MA)
- Global gold trend: reuse international gold price data, compute trend
- DXY: need new fetcher (free forex API)
- Real interest rates: may need to approximate or defer to a simple indicator
- Add macro as 4th/5th factor in composite scorer
- Dashboard: add macro section showing current values and trends

</specifics>

<deferred>
## Deferred Ideas
None
</deferred>

---
*Phase: 07-macro-indicators*
*Context gathered: 2026-03-25 (auto)*
