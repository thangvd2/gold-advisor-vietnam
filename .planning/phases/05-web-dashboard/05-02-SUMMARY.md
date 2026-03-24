---
phase: 05-web-dashboard
plan: 02
subsystem: ui, frontend
tags: [jinja2, htmx, chart.js, tailwind, dashboard, javascript]

dependency-graph:
  requires:
    - phase: 05-01
      provides: "Dashboard data APIs, base template, static file serving"
  provides:
    - "Complete dashboard page at / with signal, prices, gap, charts"
    - "5 HTMX partial endpoints: signal, prices, gap, price-chart, gap-chart"
    - "Chart.js price chart with 3 datasets and timeframe selector"
    - "Chart.js gap chart with MA reference lines"
    - "HTMX auto-refresh every 30s for signal and prices"
    - "Saver/Trader mode toggle for signal display"
  affects: [05-web-dashboard-03]

tech-stack:
  added: []
  patterns:
    - "HTMX partial swap pattern: hx-get + hx-trigger=every 30s + hx-swap=innerHTML"
    - "Chart.js dark theme configuration with gold accent colors"
    - "Server-rendered partials via Jinja2Templates with graceful error fallback"
    - "Mode toggle via htmx.ajax() re-fetching partial with query param"

key-files:
  created:
    - templates/partials/signal_card.html
    - templates/partials/price_table.html
    - templates/partials/gap_display.html
    - templates/partials/price_chart.html
    - templates/partials/gap_chart.html
    - static/js/charts.js
    - static/js/dashboard.js
    - tests/test_dashboard_html.py
  modified:
    - templates/dashboard.html
    - src/api/routes/dashboard.py

key-decisions:
  - "HTMX loading spinners instead of blank space while partials load"
  - "Graceful error fallback in partial endpoints — always return 200 with empty state"
  - "Chart.js initialized via DOMContentLoaded + htmx:afterSettle for HTMX-loaded canvases"
  - "Mode toggle uses htmx.ajax() to re-fetch signal partial with mode query param"

patterns-established:
  - "HTMX partial endpoint pattern: GET /dashboard/partials/{section}"
  - "Timeframe selector pattern: data-range attribute + setActiveButton() JS helper"
  - "Chart color palette: SJC=#D4AF37, Ring=#F5D76E, Intl=#4A90D9"

requirements-completed: [DEL-01]

metrics:
  duration: 3min
  completed: 2026-03-25T19:55:38Z
---

# Phase 5 Plan 02: Dashboard UI Summary

**Complete dashboard with signal card (color-coded Buy/Hold/Sell), dealer price table (5 dealers, SJC bar + ring gold), gap tracker with trend arrows, Chart.js price/gap charts with timeframe selectors, and HTMX auto-refresh every 30s**

## Performance

- **Duration:** 3 min
- **Started:** 2026-03-24T19:52:16Z
- **Completed:** 2026-03-25T19:55:38Z
- **Tasks:** 2
- **Files modified:** 10

## Accomplishments
- Signal card with color-coded recommendation badges (green BUY, amber HOLD, red SELL), confidence progress bar, reasoning text, and Saver/Trader mode toggle
- Dealer price table showing all 5 Vietnamese dealers with SJC bar and ring gold buy/sell/spread, color-coded spreads
- Gap display with large VND value, percentage with trend arrow vs 7d MA, and reference MA values
- Chart.js price chart with 3 line datasets (SJC Bar, Ring Gold, Intl Gold) and 1D/1W/1M/1Y timeframe selector
- Chart.js gap chart showing gap percentage with 7d/30d MA reference lines and 1W/1M/3M/1Y timeframe selector
- HTMX partial endpoints with 30s auto-refresh for signal and prices, graceful error fallbacks

## Task Commits

Each task was committed atomically:

1. **Task 1: Dashboard HTML partials (TDD RED)** - `46bd329` (test)
2. **Task 1+2: Dashboard HTML sections + charts (TDD GREEN)** - `233924f` (feat)

_Note: Tasks 1 and 2 GREEN were combined since chart partials and JS were needed for tests to pass_

## Files Created/Modified
- `templates/dashboard.html` - Full dashboard layout with signal, gap, prices, charts sections and HTMX loading
- `templates/partials/signal_card.html` - Signal recommendation badge, confidence bar, mode toggle, gap info
- `templates/partials/price_table.html` - Responsive dealer price table with SJC bar and ring gold
- `templates/partials/gap_display.html` - Gap value, percentage, trend indicator, MA references
- `templates/partials/price_chart.html` - Price chart container with timeframe buttons and legend
- `templates/partials/gap_chart.html` - Gap chart container with timeframe buttons and legend
- `static/js/charts.js` - Chart.js configuration for price and gap charts with dark theme
- `static/js/dashboard.js` - Mode toggle handler and HTMX error handling
- `src/api/routes/dashboard.py` - Added 5 HTMX partial endpoints with Jinja2Templates rendering
- `tests/test_dashboard_html.py` - 17 tests for partials, chart rendering, and full page

## Decisions Made
- Used HTMX loading spinners (CSS animate-spin) in placeholder divs instead of blank space while partials load
- Partial endpoints always return 200 with empty-state HTML on error rather than 500 — prevents broken layout
- Chart.js initialized both on DOMContentLoaded and htmx:afterSettle event since canvases arrive via HTMX partials
- Mode toggle uses `htmx.ajax()` to re-fetch the signal partial with a `?mode=` query parameter

## Deviations from Plan

None - plan executed exactly as written.

## Issues Encountered
- Test fixture needed `Jinja2Templates` imported inside the `with` block to avoid shadowing — aliased as `AppTemplates` to avoid conflict with import inside `src.api.routes.dashboard`

## Known Stubs

None — all dashboard sections are fully wired with real data from existing APIs.

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness
- Complete dashboard page ready for visual verification at localhost:8000
- All partials render with live data from Phase 1-4 APIs
- Chart.js charts fetch from existing /api/prices/history and /api/gap/history endpoints
- Plan 05-03 can add any remaining polish or alert integration

---
*Phase: 05-web-dashboard*
*Completed: 2026-03-25*

## Self-Check: PASSED
