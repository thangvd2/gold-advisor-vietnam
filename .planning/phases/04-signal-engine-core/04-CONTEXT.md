# Phase 4: Signal Engine Core - Context

**Gathered:** 2026-03-25 (auto-generated)
**Status:** Ready for planning

<domain>
## Phase Boundary

Generate Buy/Hold/Sell signals with confidence levels (0-100%), one-line reasoning explanations, and mode-appropriate interpretation for Savers vs Traders. This is the brain of the system — deterministic multi-factor analysis producing actionable signals from the data layers built in Phases 1-3.

</domain>

<decisions>
## Implementation Decisions

### Claude's Discretion
- Signal factor weights (gap signal, spread signal, trend signal)
- Confidence calculation methodology
- Threshold values for Buy/Hold/Sell classification
- Saver vs Trader mode signal interpretation differences
- Signal storage schema (what context to persist with each signal)
- Whether to include basic trend analysis as a signal factor

### Key Constraints (from PITFALLS.md)
- All numerical calculations and thresholds MUST be in deterministic code — NEVER use LLM for numerical signals
- Use directional accuracy, not price levels
- Include explicit "what the model CANNOT capture" in signal output
- Confidence ranges, not point estimates
- Never use "predict" language — use "tracks", "analyzes", "observes"

</decisions>

<canonical_refs>
## Canonical References

### Prior Phase Outputs
- `.planning/phases/03-gap-analysis-price-charts/03-01-SUMMARY.md` — Gap engine, DuckDB analytics
- `.planning/phases/02-vietnamese-gold-price-scraping/02-03-SUMMARY.md` — Spread calculation
- `.planning/phases/01-project-foundation-international-data/01-02-SUMMARY.md` — International gold fetcher

### Architecture & Pitfalls
- `.planning/research/ARCHITECTURE.md` §Pipeline Pattern — Signal computation as staged pipeline
- `.planning/research/ARCHITECTURE.md` §Anti-Pattern 1 — Why NOT multi-agent for this
- `.planning/research/PITFALLS.md` §Pitfall 1 — Gold prediction as solvable ML problem (CRITICAL)
- `.planning/research/PITFALLS.md` §Pitfall 5 — Overpromising accuracy / liability (CRITICAL for wording)
- `.planning/REQUIREMENTS.md` — SIG-01, SIG-02, SIG-06

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- `src/analysis/gap.py` — DuckDB gap calculation with historical averages
- `src/storage/repository.py` — Full price_history access
- `src/ingestion/models.py` — FetchedPrice, DataSource patterns
- DuckDB analytics infrastructure from Phase 3

### Established Patterns
- TDD, atomic commits, adapter pattern

</code_context>

<specifics>
## Specific Ideas

- Start with gap-based signal as the primary factor (this is the core timing metric)
- Spread can be a secondary factor (wider spread = less favorable to trade)
- Simple trend (price above/below N-day MA) as tertiary factor
- Weighted composite → confidence score → classification
- Saver mode: lower threshold for action, focus on "is gap favorable for accumulation?"
- Trader mode: higher threshold, focus on "is signal strong enough to act now?"

</specifics>

<deferred>
## Deferred Ideas
None
</deferred>

---
*Phase: 04-signal-engine-core*
*Context gathered: 2026-03-25 (auto)*
