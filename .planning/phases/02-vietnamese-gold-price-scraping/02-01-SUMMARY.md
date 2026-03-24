---
phase: 02-vietnamese-gold-price-scraping
plan: 01
subsystem: ingestion
tags: [beautifulsoup4, lxml, httpx, scraping, vietnamese-gold, doji, phuquy]

requires:
  - phase: 01-international-gold-price
    provides: "DataSource base class, FetchedPrice model, fetch_and_store pipeline, scheduler"

provides:
  - "DOJI scraper (SJC bar + ring gold) from giavang.doji.vn"
  - "Phú Quý scraper (SJC bar + ring gold) from phuquygroup.vn"
  - "source_name property on DataSource for uniform name extraction"
  - "Scrapers wired into scheduler alongside existing YFinance fetcher"

affects: [02-02, 02-03, 04-signal-engine]

tech-stack:
  added: [beautifulsoup4>=4.12, lxml>=6.0]
  patterns:
    - "Static HTML scraper pattern: httpx async GET → BeautifulSoup parse → extract rows → convert units → return list[FetchedPrice]"
    - "source_name property on DataSource for uniform name extraction across Fetcher/Scraper variants"
    - "Unit conversion: raw page units → standard VND/lượng"

key-files:
  created:
    - src/ingestion/scrapers/__init__.py
    - src/ingestion/scrapers/doji.py
    - src/ingestion/scrapers/phuquy.py
    - tests/test_scrapers_doji.py
    - tests/test_scrapers_phuquy.py
  modified:
    - src/ingestion/fetchers/base.py
    - src/api/main.py
    - src/ingestion/normalizer.py
    - tests/test_quality.py
    - pyproject.toml

key-decisions:
  - "Scrapers use @retry decorator with max_retries=2, backoff_factor=1.0 for resilience"
  - "DOJI HTML uses class-based selectors (.goldprice-td-0, .goldprice-td-1) while Phú Quý uses semantic classes (.buy-price, .sell-price)"
  - "HTML entity decoding (html.unescape) needed for Phú Quý timestamp regex matching"
  - "Normalizer changed from string-based name extraction to source_name property for Scraper/Fetcher uniformity"

patterns-established:
  - "Scraper pattern: extend DataSource, override source_name, @retry on fetch(), return [] on errors"
  - "Test pattern: _make_mock_response() helper for httpx response mocking without AsyncMock warnings"

requirements-completed: [DATA-01, DATA-02]

duration: 5min
completed: 2026-03-25
---

# Phase 02 Plan 01: DOJI & Phú Quý Scrapers Summary

**DOJI and Phú Quý gold price scrapers via httpx + BeautifulSoup, both returning SJC bar and ring gold prices in VND/lượng**

## Performance

- **Duration:** 5 min
- **Started:** 2026-03-24T18:32:14Z
- **Completed:** 2026-03-24T18:37:30Z
- **Tasks:** 2 (TDD: RED → GREEN → REFACTOR per task)
- **Files modified:** 10

## Accomplishments
- DOJI scraper parses SJC bar + ring gold from giavang.doji.vn static HTML, converts nghìn/chỉ → VND/lượng (×10,000)
- Phú Quý scraper parses SJC bar + ring gold from phuquygroup.vn static HTML, converts VNĐ/Chỉ → VND/lượng (×10)
- Both scrapers wired into the existing scheduler pipeline alongside YFinance fetcher
- source_name property on DataSource enables uniform name extraction for both Fetcher and Scraper subclasses
- 15 new scraper tests (8 DOJI + 7 Phú Quý), all 66 project tests pass

## Task Commits

1. **Task 1 RED: DOJI scraper tests** - `8b446d5` (test)
2. **Task 1 GREEN: DOJI scraper implementation** - `5256212` (feat)
3. **Task 2 RED: Phú Quý scraper tests** - `4eb9cad` (test)
4. **Task 2 GREEN: Phú Quý scraper implementation** - `cb1e403` (feat)
5. **Task 2 WIRING: Scheduler integration** - `7b221db` (feat)
6. **Lint cleanup** - `1b32ed9` (refactor)

## Files Created/Modified
- `src/ingestion/scrapers/doji.py` - DOJI gold price scraper with SJC bar + ring gold extraction
- `src/ingestion/scrapers/phuquy.py` - Phú Quý gold price scraper with SJC bar + ring gold extraction
- `src/ingestion/scrapers/__init__.py` - Scrapers package init
- `src/ingestion/fetchers/base.py` - Added source_name property to DataSource
- `src/api/main.py` - Wired DOJI + Phú Quý scrapers into scheduler sources
- `src/ingestion/normalizer.py` - Use source_name property instead of string manipulation
- `tests/test_scrapers_doji.py` - 8 DOJI scraper tests (SJC, ring gold, conversion, errors, timestamp)
- `tests/test_scrapers_phuquy.py` - 7 Phú Quý scraper tests (SJC, ring gold, conversion, errors, timestamp)
- `tests/test_quality.py` - Updated mock fetchers with source_name for normalizer compatibility

## Decisions Made
- Scrapers return empty list on errors (logged but don't crash system) — aligns with existing Fetcher pattern
- DOJI row identification via regex: `\bSJC\b` for bars, `NHẪN\s+TRÒN\s+9999` for ring gold
- Phú Quý row identification: exact match "Vàng miếng SJC" and "Nhẫn tròn Phú Quý 999.9"
- Used MagicMock for httpx response mock (not AsyncMock) to avoid RuntimeWarning on non-async raise_for_status()

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] HTML entity decoding for Phú Quý timestamp**
- **Found during:** Task 2 GREEN (PhuQuyScraper implementation)
- **Issue:** Regex pattern `lúc` didn't match HTML-encoded `l&#250;c` in raw response, causing _parse_timestamp to return None and fall back to datetime.now()
- **Fix:** Added `html.unescape()` call before regex matching in _parse_timestamp
- **Files modified:** src/ingestion/scrapers/phuquy.py
- **Verification:** test_parses_update_timestamp passes with correct hour/minute

**2. [Rule 1 - Bug] Normalizer change broke existing quality test**
- **Found during:** Task 2 WIRING (all-test regression check)
- **Issue:** Changing normalizer from string-based name extraction to `source_name` property caused `test_handles_empty_fetch_gracefully` to fail — AsyncMock doesn't have a source_name property
- **Fix:** Added `_mock_gold_fetcher()` helper method with `source_name = "yfinance"` to TestFetchAndStore class, updated all 4 mock fetcher instances
- **Files modified:** tests/test_quality.py
- **Verification:** All 66 tests pass

---

**Total deviations:** 2 auto-fixed (2 bugs)
**Impact on plan:** Both fixes were necessary for correctness. No scope creep.

## Issues Encountered
- AsyncMock used for httpx response objects caused RuntimeWarning about unawaited coroutine on `raise_for_status()` — resolved by using MagicMock for responses instead

## Known Stubs
None — all scrapers are fully wired and functional.

## User Setup Required
None - no external service configuration required.

## Next Phase Readiness
- DOJI + Phú Quý scraper pattern established, ready for Plans 02-02 (BTMC/SJC) and 02-03 (PNJ)
- For Plans 02-02/03: will need Playwright for JS-rendered sites (SJC, PNJ) — pattern to extend from static scraper base
- Signal engine (Phase 4) will consume VND prices from these scrapers for gap calculations

## Self-Check: PASSED
- All 6 created files verified: doji.py, phuquy.py, __init__.py, test_scrapers_doji.py, test_scrapers_phuquy.py, 02-01-SUMMARY.md
- All 7 commits verified in git log
- All 66 tests pass

---
*Phase: 02-vietnamese-gold-price-scraping*
*Completed: 2026-03-25*
