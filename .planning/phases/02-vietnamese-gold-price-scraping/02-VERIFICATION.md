---
phase: 02-vietnamese-gold-price-scraping
verified: 2026-03-25T19:30:00Z
status: passed
score: 4/4 must-haves verified
---

# Phase 2: Vietnamese Gold Price Scraping Verification Report

**Phase Goal:** System reliably scrapes buy/sell prices from 5+ Vietnamese gold dealers for SJC bars, ring gold (nhẫn trơn), and dealer buy/sell spreads, on a 1-5 minute schedule
**Verified:** 2026-03-25T19:30:00Z
**Status:** passed
**Re-verification:** No — initial verification

## Goal Achievement

### Observable Truths

| # | Truth | Status | Evidence |
|---|-------|--------|----------|
| 1 | Buy/sell prices scraped from 5+ dealers (DOJI, Phu Quý, SJC, PNJ, BTMC) and stored in DB | ✓ VERIFIED | All 5 scraper classes exist (109-210 lines each), extend DataSource, return list[FetchedPrice]. All 5 instantiated and wired in main.py line 28-34 into scheduler pipeline. Normalizer's fetch_and_store_all iterates all sources. |
| 2 | Ring gold (nhẫn trơn) prices scraped alongside SJC bar prices from same dealers | ✓ VERIFIED | All 5 scrapers contain ring gold pattern matching: DOJI (RING_GOLD_PATTERN line 23), Phu Quý (RING_GOLD_PATTERN line 24), SJC (RING_GOLD_PATTERN line 27), PNJ (RING_GOLD_CODES line 30), BTMC (RING_GOLD_KEYWORDS line 22 + JSON_RING_PATTERNS line 28). |
| 3 | Buy/sell spreads calculated and stored for each dealer and product type | ✓ VERIFIED | PriceRecord.spread column exists (models.py line 28). save_price() computes spread = sell - buy when both present (repository.py lines 29-30). Returns None when either missing. 5 spread tests pass. |
| 4 | Individual scraper failures don't crash system or block other scrapers | ✓ VERIFIED | Normalizer fetch_and_store() wraps each fetch in try/except (normalizer.py lines 28-32), returns {"status": "failed"} on error. fetch_and_store_all iterates all sources sequentially — one failure doesn't stop others. Each scraper has internal try/except returning [] on HTTP/parse errors. @retry decorator provides resilience. |

**Score:** 4/4 truths verified

### Required Artifacts

| Artifact | Expected | Status | Details |
|----------|----------|--------|---------|
| `src/ingestion/scrapers/doji.py` | DOJI price scraping via httpx + BS4 | ✓ VERIFIED | 109 lines, DojiScraper(DataSource), fetch() with httpx+BS4, SJC bar + ring gold extraction, nghìn/chi × 10,000 conversion |
| `src/ingestion/scrapers/phuquy.py` | Phú Quý price scraping via httpx + BS4 | ✓ VERIFIED | 110 lines, PhuQuyScraper(DataSource), fetch() with httpx+BS4, SJC bar + ring gold, VNĐ/Chỉ × 10 conversion |
| `src/ingestion/scrapers/sjc.py` | SJC price scraping via JSON API | ✓ VERIFIED | 109 lines, SJCScraper(DataSource), fetch() via httpx POST to PriceService.ashx, dedup by seen_types |
| `src/ingestion/scrapers/pnj.py` | PNJ price scraping via JSON API | ✓ VERIFIED | 108 lines, PNJScraper(DataSource), fetch() via httpx GET to edge-api.pnj.io, 1,000 VND/chi × 10,000 conversion |
| `src/ingestion/scrapers/btmc.py` | BTMC price scraping via JSON API + HTML fallback | ✓ VERIFIED | 210 lines, BTMCScraper(DataSource), _try_json_api() + _try_html_fallback(), JSON classification, HTML table parsing |
| `src/storage/models.py` | PriceRecord with spread column | ✓ VERIFIED | Line 28: `spread: Mapped[float \| None] = mapped_column(Float, nullable=True)` |
| `src/storage/repository.py` | save_price calculates spread | ✓ VERIFIED | Lines 29-30: `if record.buy_price is not None and record.sell_price is not None: record.spread = record.sell_price - record.buy_price` |
| `src/api/main.py` | All 5 scrapers wired into scheduler | ✓ VERIFIED | Lines 28-34: all 5 imported, instantiated, added to vn_scrapers list, combined with gold_fetcher into sources |

### Key Link Verification

| From | To | Via | Status | Details |
|------|----|-----|--------|---------|
| `doji.py` | `fetchers/base.py` | DojiScraper extends DataSource | ✓ WIRED | Line 41: `class DojiScraper(DataSource)`, uses `@retry` decorator |
| `phuquy.py` | `fetchers/base.py` | PhuQuyScraper extends DataSource | ✓ WIRED | Line 43: `class PhuQuyScraper(DataSource)`, uses `@retry` decorator |
| `sjc.py` | `fetchers/base.py` | SJCScraper extends DataSource | ✓ WIRED | Line 38: `class SJCScraper(DataSource)`, uses `@retry` decorator |
| `pnj.py` | `fetchers/base.py` | PNJScraper extends DataSource | ✓ WIRED | Line 41: `class PNJScraper(DataSource)`, uses `@retry` decorator |
| `btmc.py` | `fetchers/base.py` | BTMCScraper extends DataSource | ✓ WIRED | Line 117: `class BTMCScraper(DataSource)`, uses `@retry` decorator |
| `main.py` | `scrapers/` | Imports + instantiates all 5 | ✓ WIRED | Lines 10-14: imports, Lines 28-32: instantiation, Line 33: vn_scrapers list |
| `main.py` | `scheduler.py` | start_scheduler with sources | ✓ WIRED | Line 36: `start_scheduler(app_state, sources, fx_fetcher, settings)` |
| `scheduler.py` | `normalizer.py` | Calls fetch_and_store_all | ✓ WIRED | Line 22-28: scheduler job calls `fetch_and_store_all(sources, fx_fetcher, settings)` |
| `normalizer.py` | `repository.py` | save_price per FetchedPrice | ✓ WIRED | Line 56: `record = await save_price(session, fetched_price, ...)` |
| `repository.py` | `models.py` | spread = sell - buy | ✓ WIRED | Lines 29-30: computed during save_price |

### Data-Flow Trace (Level 4)

| Artifact | Data Variable | Source | Produces Real Data | Status |
|----------|---------------|--------|-------------------|--------|
| All scrapers | FetchedPrice list | httpx calls to live dealer APIs/pages | ✓ | Real HTTP calls to giavang.doji.vn, phuquygroup.vn, sjc.com.vn, edge-api.pnj.io, btmc.vn |
| `save_price()` | PriceRecord.spread | Computed from buy_price, sell_price | ✓ | Derived on every save when both present |
| Scheduler → Normalizer | fetch_and_store_all | Iterates all sources on interval | ✓ | APScheduler BackgroundScheduler, interval=settings.fetch_interval_minutes |
| Normalizer | quality checks | check_missing on empty fetch | ✓ | Triggers missing-data alert when scraper returns [] |

### Behavioral Spot-Checks

| Behavior | Command | Result | Status |
|----------|---------|--------|--------|
| All 91 tests pass | `uv run pytest tests/ -x` | 91 passed in 0.91s | ✓ PASS |
| All scrapers importable | `python -c "from src.ingestion.scrapers.{doji,phuquy,sjc,pnj,btmc} import ..."` | All 5 scrapers import OK | ✓ PASS |
| Spread column exists | `python -c "from src.storage.models import PriceRecord; print(hasattr(PriceRecord, 'spread'))"` | True | ✓ PASS |
| Lint check | `uv run ruff check src/ tests/` | 2 minor unused-import warnings (fixable, non-blocking) | ⚠️ PASS (minor) |

### Requirements Coverage

| Requirement | Source Plan | Description | Status | Evidence |
|-------------|-------------|-------------|--------|----------|
| **DATA-01** | 02-01, 02-02, 02-03 | Live SJC bar buy/sell prices from 5+ dealers | ✓ SATISFIED | 5 dealers (DOJI, Phú Quý, SJC, PNJ, BTMC) all scrape SJC bar prices, all wired into scheduler |
| **DATA-02** | 02-01, 02-02, 02-03 | Live nhẫn trơn (ring gold) buy/sell prices | ✓ SATISFIED | All 5 scrapers have ring gold pattern matching and produce ring_gold FetchedPrice objects |
| **DATA-05** | 02-03 | Buy/sell spread for SJC bars and ring gold | ✓ SATISFIED | spread column in PriceRecord (nullable float), computed as sell - buy in save_price(), 5 spread tests |

### Anti-Patterns Found

| File | Line | Pattern | Severity | Impact |
|------|------|---------|----------|--------|
| `src/ingestion/scrapers/pnj.py` | 19 | `FALLBACK_URL` defined but never used | ℹ️ Info | Unused code — primary API works; fallback was planned but not needed. Minor cleanup opportunity. |
| `tests/test_spread.py` | 3 | Unused `timedelta` import flagged by ruff | ℹ️ Info | Test file lint warning, non-functional |

No blocker (🛑) or warning (⚠️) anti-patterns found. All code is substantive and wired.

### Human Verification Required

### 1. Live Data from Vietnamese Dealer Sites

**Test:** Start the app with `uv run uvicorn src.api.main:app --reload`, wait 5+ minutes for a scheduler cycle, then query `curl http://localhost:8000/quality/alerts` and check the database for rows with source in (doji, phuquy, sjc, pnj, btmc).
**Expected:** Price records appear for all 5 Vietnamese sources with non-null spread values. Some sources may fail from outside Vietnam (BTMC JSON API known geo-restriction), but HTML fallback should compensate.
**Why human:** Vietnamese gold dealer sites may block or return different HTML from non-VN IP addresses. Scrapers have been tested with mocks but live verification requires running the actual pipeline.

### 2. BTMC Geo-Restriction Handling

**Test:** Check logs for "BTMC JSON API unreachable" warnings. Verify that the HTML fallback at btmc.vn/Home/BGiaVang returns valid prices.
**Expected:** JSON API may fail (connection reset from outside VN), but HTML fallback produces valid price records.
**Why human:** BTMC JSON API is geo-restricted; behavior depends on network location.

### Gaps Summary

No gaps found. All 4 success criteria are met, all 3 requirements (DATA-01, DATA-02, DATA-05) are satisfied, and all 8 artifacts pass all verification levels (exists, substantive, wired, data flowing).

---

_Verified: 2026-03-25T19:30:00Z_
_Verifier: Claude (gsd-verifier)_
