# Phase 5: Web Dashboard - Context

**Gathered:** 2026-03-25 (auto-generated)
**Status:** Ready for planning

<domain>
## Phase Boundary

Mobile-responsive web dashboard showing all current data: dealer prices, gap tracker, signal with confidence/reasoning, price charts, and macro snapshot. Server-rendered with Jinja2 + HTMX + Chart.js + Tailwind CSS (per STACK.md). This is the primary user interface.

</domain>

<decisions>
## Implementation Decisions

### Stack (from STACK.md, already decided)
- Jinja2 templates served by FastAPI — no SPA
- HTMX for partial page updates
- Chart.js for price/gap charts
- Tailwind CSS for styling
- Mobile-responsive layout

### Claude's Discretion
- Dashboard layout and information architecture
- Color scheme and visual design
- Specific Chart.js chart types (line, bar, etc.)
- HTMX polling interval for live price updates
- How to display Saver/Trader mode toggle
- Specific Tailwind component patterns

</decisions>

<canonical_refs>
## Canonical References

### Phase Outputs (data endpoints ready)
- `.planning/phases/01-project-foundation-international-data/01-03-SUMMARY.md` — Health endpoint, quality API
- `.planning/phases/02-vietnamese-gold-price-scraping/02-03-SUMMARY.md` — 5 dealer prices + spreads
- `.planning/phases/03-gap-analysis-price-charts/03-01-SUMMARY.md` — Gap API endpoints
- `.planning/phases/03-gap-analysis-price-charts/03-02-SUMMARY.md` — Price chart API endpoints
- `.planning/phases/04-signal-engine-core/04-03-SUMMARY.md` — Signal API endpoints

### Stack
- `.planning/research/STACK.md` — Jinja2 + HTMX + Chart.js + Tailwind CSS
- `.planning/REQUIREMENTS.md` — DEL-01 (mobile-responsive dashboard)

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- All API endpoints built: `/health`, `/api/prices/*`, `/api/gap/*`, `/api/signals/*`, `/api/quality/*`
- FastAPI app at `src/api/main.py` with router wiring
- SQLite + DuckDB infrastructure ready

### Integration Points
- Dashboard fetches data from existing JSON API endpoints via HTMX or JS
- Chart.js consumes `{x, y}` format already served by price/gap APIs

</code_context>

<specifics>
## Specific Ideas

- Single-page dashboard with sections: signal card, price table, gap chart, price chart
- Signal card at top (most important info) with mode toggle
- Price table showing all 5 dealers with SJC bar + ring gold prices
- Gap chart (line) showing historical SJC-international gap
- HTMX to refresh price table every 30-60s without full reload
- Charts load data via fetch() to JSON endpoints

</specifics>

<deferred>
## Deferred Ideas
None
</deferred>

---
*Phase: 05-web-dashboard*
*Context gathered: 2026-03-25 (auto)*
