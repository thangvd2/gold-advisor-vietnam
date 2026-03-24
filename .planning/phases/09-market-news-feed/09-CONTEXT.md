# Phase 9: Market News Feed - Context

**Gathered:** 2026-03-25 (auto-generated)
**Status:** Ready for planning

<domain>
## Phase Boundary

Aggregated market news feed showing gold market news and State Bank policy announcements. Displayed on the dashboard alongside prices and signals.

</domain>

<decisions>
## Implementation Decisions

### Claude's Discretion
- News source(s) — RSS feeds, API, or scraping Vietnamese financial news sites
- How many articles to display
- Storage approach (database vs cache-only)
- Refresh frequency
- Whether to include news in signal reasoning (adds LLM dependency — per ARCHITECTURE anti-pattern, keep separate)

### Key Constraints
- NO LLM for news processing at this stage (deferred to v2)
- News is informational display only — doesn't affect signal computation
- Must include State Bank announcements prominently

</decisions>

<canonical_refs>
## Canonical References
- `.planning/research/ARCHITECTURE.md` — News feed as display layer, not signal input
- `.planning/REQUIREMENTS.md` — DEL-03

</canonical_refs>

<code_context>
## Existing Code Insights
- Full dashboard at templates/dashboard.html with Tailwind CSS
- API infrastructure ready for new endpoints
- Scheduler for periodic tasks

</code_context>

<specifics>
## Specific Ideas
- Start simple: scrape 1-2 RSS feeds for gold market news (VNExpress, Vietnam Investment Review, etc.)
- State Bank announcements: manual input via admin endpoint (same pattern as policy events in Phase 8)
- Display last 10-20 news items on dashboard
- Show source, headline, date, optional excerpt
- News section at bottom of dashboard page

</specifics>

<deferred>
## Deferred Ideas
None
</deferred>

---
*Phase: 09-market-news-feed*
*Context gathered: 2026-03-25 (auto)*
