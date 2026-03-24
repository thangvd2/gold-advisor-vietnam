---
phase: 02-vietnamese-gold-price-scraping
plan: 02
subsystem: data-ingestion
tags: [httpx, json-api, scraping, sjc, pnj, playwright-avoided]

dependency-graph:
  requires:
    - phase: 02-01
      provides: "DOJI/PhuQuy static scrapers, DataSource base class, retry decorator"
  provides:
    - "SJC scraper via JSON API (sjc.com.vn PriceService.ashx)"
    - "PNJ scraper via JSON API (edge-api.pnj.io)"
    - "4 of 5 required Vietnamese gold dealers operational"
  affects: [03-signal-engine, 02-03, dashboard, alerting]

tech-stack:
  added: []
  patterns:
    - "JSON API scraping preferred over HTML/Playwright when API endpoint exists"
    - "API discovery: inspect page JS source (goldprice.js, Next.js chunks) to find endpoints"

key-files:
  created:
    - src/ingestion/scrapers/sjc.py
    - src/ingestion/scrapers/pnj.py
    - tests/test_scrapers_sjc.py
    - tests/test_scrapers_pnj.py
  modified:
    - src/api/main.py

key-decisions:
  - "SJC: use JSON API at /GoldPrice/Services/PriceService.ashx instead of Playwright — values already in VND/lượng"
  - "PNJ: use REST API at edge-api.pnj.io instead of Playwright — values in 1,000 VND/chỉ, multiply by 10,000"
  - "Playwright not needed for any Vietnamese gold dealer so far — all 4 dealers use httpx"
  - "SJC uses first-branch dedup to avoid duplicate products across multiple branches"

patterns-established:
  - "JSON API scraping: httpx POST/GET → response.json() → parse fields → FetchedPrice[]"
  - "API discovery workflow: probe site → check JS source → find AJAX/fetch endpoints → test directly"

requirements-completed: [DATA-01, DATA-02]

metrics:
  duration: 4min
  completed: 2026-03-25
---

# Phase 02 Plan 02: SJC & PNJ Scrapers Summary

**SJC and PNJ gold price scrapers using discovered JSON APIs via httpx — no Playwright needed for any dealer**

## Performance

- **Duration:** 4 min
- **Started:** 2026-03-24T18:39:12Z
- **Completed:** 2026-03-24T18:43:12Z
- **Tasks:** 2
- **Files modified:** 5

## Accomplishments
- SJC scraper extracts SJC bar and ring gold prices from discovered JSON API
- PNJ scraper extracts SJC bar and ring gold prices from discovered REST API
- Both handle network errors, JSON parse errors, and empty responses gracefully
- Both wired into scheduler pipeline — 4 of 5 required dealers now operational
- Playwright completely avoided — all 4 Vietnamese dealers scrape via httpx

## Task Commits

Each task was committed atomically (TDD: RED → GREEN → wiring):

1. **Task 1: SJC Scraper** - `c2b2b6e` (test), `46060fe` (feat)
2. **Task 2: PNJ Scraper + Wiring** - `90f2f72` (test), `43a7983` (feat), `82cf37c` (feat/wiring)

## Files Created/Modified
- `src/ingestion/scrapers/sjc.py` — SJC gold price scraper via PriceService.ashx JSON API
- `src/ingestion/scrapers/pnj.py` — PNJ gold price scraper via edge-api.pnj.io REST API
- `tests/test_scrapers_sjc.py` — 8 test cases for SJC scraper
- `tests/test_scrapers_pnj.py` — 4 test cases for PNJ scraper
- `src/api/main.py` — Added SJCScraper and PNJScraper to scheduler pipeline

## Decisions Made
- **SJC JSON API over Playwright:** Discovered SJC exposes `/GoldPrice/Services/PriceService.ashx` (POST) returning structured JSON with `BuyValue`/`SellValue` already in VND/lượng. Much simpler and more reliable than browser automation.
- **PNJ REST API over Playwright:** Found `edge-api.pnj.io/ecom-frontend/v1/get-gold-price` by inspecting Next.js JS chunks. Returns flat JSON with `giamua`/`giaban` in 1,000 VND/chỉ units.
- **No Playwright dependency added:** All 4 Vietnamese gold dealers (DOJI, Phú Quý, SJC, PNJ) now scrape via httpx. Playwright remains available for Plan 03 if the 5th dealer requires it.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] Fixed PNJ API response structure mismatch**
- **Found during:** Task 2 (PNJ GREEN phase — live API verification)
- **Issue:** Test mock assumed nested `{"data": {"data": [...], "updateDate": "..."}}` but actual API returns flat `{"data": [...], "updateDate": "...", "chinhanh": "..."}`
- **Fix:** Updated scraper to use `body.get("data", [])` and `body.get("updateDate", "")` instead of nested access. Updated test mock to match actual structure.
- **Files modified:** src/ingestion/scrapers/pnj.py, tests/test_scrapers_pnj.py
- **Committed in:** `43a7983`

### Major Deviation (Documented)

**2. [Architectural] Used httpx JSON APIs instead of Playwright for both SJC and PNJ**
- **Found during:** Task 1 (pre-implementation probe)
- **Issue:** Plan specified Playwright for SJC (JS-rendered) and PNJ (React SPA). Investigation revealed both sites have hidden JSON APIs accessible via httpx.
- **Resolution:** Used httpx for both scrapers, following the established pattern from DOJI/PhuQuy. This is strictly better: simpler code, no browser binary dependency, faster execution, more reliable.
- **Impact:** pyproject.toml unchanged (no playwright dependency added). All 4 dealers use identical httpx pattern.

---

**Total deviations:** 1 auto-fixed (1 bug), 1 architectural (both scrapers use httpx instead of Playwright — improvement over plan)
**Impact on plan:** All deviations improved code quality. No scope creep.

## Issues Encountered
- SJC's old URL (`sjc.com.vn/giavang/textContent.php`) returns 404 — site restructured. Discovered new JSON API by reading the `goldprice.js` source on the main page.
- PNJ's giavang.pnj.com.vn is a React SPA behind Cloudflare — httpx gets empty `<div id="root"></div>`. Found REST API by reading the Next.js page chunk JS source.

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness
- 4 of 5 required dealers operational (DOJI, Phú Quý, SJC, PNJ)
- Plan 03 can add the 5th dealer — Playwright infrastructure may still be needed depending on target
- All scrapers follow uniform DataSource pattern with @retry decorator
- 78 tests passing, zero regressions

## Known Stubs

None — both scrapers are fully functional against live APIs.

## Self-Check: PASSED

---
*Phase: 02-vietnamese-gold-price-scraping*
*Completed: 2026-03-25*
