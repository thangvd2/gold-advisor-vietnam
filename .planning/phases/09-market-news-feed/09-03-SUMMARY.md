---
phase: 9
plan: 3
subsystem: dashboard, scheduler
tags: [news, dashboard, scheduler, htmx]
---

# Phase 9 Plan 3: Dashboard News Section + Scheduler Integration Summary

News feed card added to the dashboard with HTMX auto-refresh, and periodic RSS fetching integrated into the APScheduler pipeline.

## Tasks Completed

| # | Task | Commit | Files |
|---|------|--------|-------|
| 1 | News dashboard partial + API | d4ac575 | templates/partials/news_card.html, src/api/routes/dashboard.py, templates/dashboard.html |
| 2 | Scheduler integration | 82d4f1e | src/ingestion/news/store.py, src/ingestion/scheduler.py, src/config.py |

## Key Files Created/Modified

- `templates/partials/news_card.html` — News feed card with headline links, source, date, SBV gold badge
- `templates/dashboard.html` — Added news section with HTMX auto-refresh (every 30s)
- `src/api/routes/dashboard.py` — Added /dashboard/news (JSON) and /dashboard/partials/news (HTML)
- `src/ingestion/news/store.py` — fetch_and_store_news() orchestrator
- `src/ingestion/scheduler.py` — Added news_fetch APScheduler job (30 min default)
- `src/config.py` — Added news_fetch_interval_minutes setting (default 30)

## Tests Created

- `tests/test_news_template.py` — 8 tests (JSON endpoint, HTML partial, empty state, headlines, SBV badge)
- `tests/test_news_scheduler.py` — 3 tests (store new, skip duplicates, empty feed)
- `tests/test_alert_pipeline.py` — 1 test fix (added missing mock attribute)

**Total: 12 new/modified tests, all passing**

## Decisions

- News card placed between charts and footer on dashboard
- 30-minute fetch interval (separate from 5-minute price fetch)
- Default RSS feeds: VNExpress Economy, Kitco News Gold
- News section uses same HTMX pattern as other dashboard cards (load + every 30s)

## Deviations from Plan

**[Rule 1 - Bug]** Fixed pre-existing test_alert_pipeline.py missing `news_fetch_interval_minutes` mock attribute.

## Self-Check: PASSED
