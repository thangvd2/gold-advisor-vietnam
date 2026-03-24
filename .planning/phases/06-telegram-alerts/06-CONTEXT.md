# Phase 6: Telegram Alerts - Context

**Gathered:** 2026-03-25 (auto-generated)
**Status:** Ready for planning

<domain>
## Phase Boundary

Telegram bot that sends push notifications on signal changes and significant price movements. Includes signal context and disclaimers. Uses python-telegram-bot 22.x library.

</domain>

<decisions>
## Implementation Decisions

### Claude's Discretion
- Bot commands and interaction design
- Alert message format and content
- Thresholds for "significant price movements"
- How to handle bot setup (token from env var)
- Subscription mechanism (simple for now — no multi-user auth)

### Key Constraints
- Alerts must include disclaimers (PITFALLS §Pitfall 5)
- Alert fatigue prevention — don't spam (PITFALLS §UX Pitfalls)
- Include context in alerts, not just "BUY" (PITFALLS §UX Pitfalls)

</decisions>

<canonical_refs>
## Canonical References
- `.planning/research/STACK.md` — python-telegram-bot 22.x
- `.planning/research/ARCHITECTURE.md` §Threshold-Based Alert Dispatch
- `.planning/research/PITFALLS.md` §Pitfall 5 — Liability/disclaimers
- `.planning/REQUIREMENTS.md` — DEL-02

</canonical_refs>

<code_context>
## Existing Code Insights
- Signal pipeline at `src/engine/pipeline.py` — `compute_signal()`
- Signal repository with history
- Scheduler infrastructure for periodic tasks
- Config system via pydantic-settings

</code_context>

<specifics>
## Specific Ideas
- /start command to get chat_id, /status for current signal
- Alert on signal change (buy→hold, hold→sell) and confidence crossing ±20%
- Alert template: signal badge, confidence, reasoning, key data points, disclaimer
- Run bot polling in background thread alongside scheduler

</specifics>

<deferred>
## Deferred Ideas
None
</deferred>

---
*Phase: 06-telegram-alerts*
*Context gathered: 2026-03-25 (auto)*
