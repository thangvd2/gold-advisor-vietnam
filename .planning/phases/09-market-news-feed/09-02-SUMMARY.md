---
phase: 9
plan: 2
subsystem: storage, api
tags: [news, database, rest-api, admin]
---

# Phase 9 Plan 2: News Storage + API Endpoints + Admin Manual Entry Summary

Persistent news storage with SQLAlchemy, REST API endpoints for querying, and admin endpoint for manually adding State Bank announcements.

## Tasks Completed

| # | Task | Commit | Files |
|---|------|--------|-------|
| 1 | NewsItem model + repository | 2dcfdf6 | src/storage/models.py, src/storage/repository.py |
| 2 | News API endpoints | 83b09f2 | src/api/routes/news.py, src/api/main.py |
| 3 | Admin manual news entry | ddf49ac | src/api/routes/admin.py |

## Key Files Created/Modified

- `src/storage/models.py` — Added NewsItem model (title, url unique, source, published_at, excerpt, category, is_manual)
- `src/storage/repository.py` — Added save_news_item() with ON CONFLICT DO NOTHING, get_recent_news() with limit+category
- `src/api/routes/news.py` — GET /api/news (list), GET /api/news/{id} (single)
- `src/api/routes/admin.py` — POST /api/admin/news (manual entry)
- `src/api/main.py` — Wired news router

## Tests Created

- `tests/test_news_repository.py` — 8 tests (model + CRUD)
- `tests/test_news_api.py` — 8 tests (list, filter, limit, sort, single, 404)
- `tests/test_news_admin.py` — 5 tests (create, optional fields, validation, feed visibility)

**Total: 21 tests, all passing**

## Decisions

- URL-based deduplication via SQLite ON CONFLICT DO NOTHING
- server_default for is_manual (0) and created_at (CURRENT_TIMESTAMP) for raw SQL compatibility
- Manual news defaults category to "state_bank"
- Auto-generated URL for manual entries without explicit URL

## Deviations from Plan

**[Rule 1 - Bug]** Fixed missing server_default on is_manual and created_at columns — caused raw SQL inserts to fail with NOT NULL constraint.

## Self-Check: PASSED
