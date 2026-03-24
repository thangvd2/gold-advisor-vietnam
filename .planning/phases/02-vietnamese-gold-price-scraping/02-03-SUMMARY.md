---
phase: 02-vietnamese-gold-price-scraping
plan: 03
subsystem: ingestion, storage
tags: [btmc, scraper, html-parsing, spread, json-api, beautifulsoup, httpx]

# Dependency graph
requires:
  - phase: 02-02
    provides: "4 dealer scrapers (DOJI, Phú Quý, SJC, PNJ), DataSource adapter, retry decorator"
provides:
  - "BTMC scraper with JSON API + HTML fallback"
  - "spread column on PriceRecord model"
  - "Automatic spread calculation in save_price()"
  - "Complete 5-dealer Vietnamese gold price pipeline"
affects: [03-international-gold-price-differential, 04-signal-engine, 05-dashboard]

# Tech tracking
tech-stack:
  added: [beautifulsoup4, lxml]
  patterns: ["HTML table fallback for VN-only APIs", "spread = sell - buy computed on save"]

key-files:
  created:
    - src/ingestion/scrapers/btmc.py
    - tests/test_scrapers_btmc.py
    - tests/test_spread.py
  modified:
    - src/storage/models.py
    - src/storage/repository.py
    - src/api/main.py

key-decisions:
  - "BTMC JSON API unreachable from outside VN — implemented HTML table fallback at /Home/BGiaVang"
  - "HTML prices in thousands VND/chỉ — multiply by 10,000 for VND/lượng (same convention as PNJ)"
  - "Both VRTL bar and SJC bar mapped to product_type='sjc_bar'"
  - "Spread computed as sell - buy, None when either price is missing"
  - "Deleted dev SQLite DB to recreate with spread column (no production data)"

patterns-established:
  - "HTML fallback pattern: try JSON API first, fall back to HTML table parsing via BS4"
  - "Spread as derived column: always computed from buy/sell, never stored independently"

requirements-completed: [DATA-01, DATA-05]

# Metrics
duration: 8min
completed: 2026-03-25
---

# Phase 2 Plan 3: BTMC Scraper + Spread Storage Summary

**BTMC JSON API scraper with HTML fallback, automatic buy/sell spread calculation on every price save, completing the 5-dealer Vietnamese gold pipeline**

## Performance

- **Duration:** 8 min
- **Started:** 2026-03-24T18:45:04Z
- **Completed:** 2026-03-24T18:53:00Z
- **Tasks:** 2
- **Files modified:** 6

## Accomplishments
- BTMC scraper with JSON API + HTML table fallback (confirmed VN-only API restriction)
- `spread` column added to PriceRecord; automatically calculated in `save_price()`
- All 5 Vietnamese gold dealers now in the scraping pipeline: DOJI, Phú Quý, SJC, PNJ, BTMC
- 91 tests pass (13 new: 8 BTMC scraper + 5 spread calculation)

## Task Commits

Each task was committed atomically:

1. **Task 1: BTMC API Scraper + Spread Column** - `f9fdaeb` (test), `ccba719` (feat)
2. **Task 2: Full Pipeline Wiring + End-to-End Verification** - `e9bffb1` (feat)

_Note: TDD tasks have multiple commits (test → feat). No refactor commit needed — lint was clean for modified files._

## Files Created/Modified
- `src/ingestion/scrapers/btmc.py` - BTMC scraper: JSON API with HTML fallback at /Home/BGiaVang
- `src/storage/models.py` - Added `spread: Mapped[float | None]` column to PriceRecord
- `src/storage/repository.py` - `save_price()` computes `spread = sell - buy` when both present
- `src/api/main.py` - BTMCScraper added to vn_scrapers list (5 dealers total)
- `tests/test_scrapers_btmc.py` - 8 tests: JSON parsing, HTML fallback, error handling
- `tests/test_spread.py` - 5 tests: spread calculation with various price combinations

## Decisions Made
- **BTMC API unreachable**: Confirmed via direct probe — `api.btmc.vn` returns connection reset from outside Vietnam. HTML fallback at `btmc.vn/Home/BGiaVang` works and provides same data.
- **Unit convention**: BTMC HTML table prices are in thousands VND/chỉ (16,770 = 167,700,000 VND/lượng). Same as PNJ convention. Both VRTL and SJC bars mapped to `sjc_bar`.
- **Spread as derived value**: Computed in `save_price()`, not stored independently. `None` when either buy or sell is missing.
- **DB recreation**: Deleted dev SQLite file to recreate with new spread column. Acceptable since no production data exists.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] Test 4 mock returned MagicMock for HTML fallback .text**
- **Found during:** Task 1 (TDD RED → GREEN iteration)
- **Issue:** Test 4 mocked JSON API with bad data, but the HTML fallback also used the same mock client. `.text` returned a MagicMock object, causing BeautifulSoup to crash with TypeError.
- **Fix:** Updated test to provide both a JSON mock response and an HTML mock response, routing them by call order.
- **Files modified:** tests/test_scrapers_btmc.py
- **Verification:** All 8 BTMC scraper tests pass

**2. [Rule 1 - Bug] Test variable `vrtl` removed during comment cleanup**
- **Found during:** Task 1 (REFACTOR phase)
- **Issue:** When removing an inline comment above `vrtl = [...]`, the variable assignment line was accidentally included.
- **Fix:** Restored the `vrtl` variable assignment.
- **Files modified:** tests/test_scrapers_btmc.py
- **Verification:** test_html_prices_in_correct_unit passes

---

**Total deviations:** 2 auto-fixed (2 bugs, both in test code)
**Impact on plan:** Minor test fixes. No production code deviations. Plan scope unchanged.

## Issues Encountered
- **BTMC API geo-restriction**: The JSON API at `api.btmc.vn/api/BTMCAPI/getpricebtmc` is unreachable from outside Vietnam (connection reset). Implemented HTML fallback as planned in the DISCOVERY.md risk assessment.

## Known Stubs
None. All implemented features are wired end-to-end.

## Next Phase Readiness
- All 5 Vietnamese gold dealers producing price data → DATA-01 satisfied
- Ring gold available from all dealers that provide it → DATA-02 satisfied
- Spread calculated on every save → DATA-05 satisfied
- Phase 2 complete — ready for Phase 3 (International Gold Price Differential)

---
*Phase: 02-vietnamese-gold-price-scraping*
*Completed: 2026-03-25*
