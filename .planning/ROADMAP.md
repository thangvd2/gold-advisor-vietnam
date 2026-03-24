# Roadmap: Gold Advisor Vietnam

## Overview

From zero to a working gold timing advisor for Vietnamese users. The journey starts with reliable data ingestion (international gold prices + Vietnamese dealer scraping), builds analytical layers on top (gap tracking, signal engine), delivers value through a web dashboard and Telegram alerts, then enriches intelligence with macro indicators, State Bank policy awareness, and seasonal demand modeling. The highest-risk phase is first — scraping unpredictable Vietnamese gold sites and designing signal logic that handles regime changes from day one.

## Phases

**Phase Numbering:**
- Integer phases (1, 2, 3): Planned milestone work
- Decimal phases (2.1, 2.2): Urgent insertions (marked with INSERTED)

Decimal phases appear between their surrounding integers in numeric order.

- [x] **Phase 1: Project Foundation & International Data** - Ingest international gold prices with data quality monitoring (completed 2026-03-24)
- [x] **Phase 2: Vietnamese Gold Price Scraping** - Scrape SJC bars, ring gold, and spreads from 5+ dealers (completed 2026-03-24)
- [x] **Phase 3: Gap Analysis & Price Charts** - Compute and visualize the SJC-international price gap (completed 2026-03-24)
- [x] **Phase 4: Signal Engine Core** - Generate Buy/Hold/Sell signals with confidence and reasoning (completed 2026-03-24)
- [x] **Phase 5: Web Dashboard** - Mobile-responsive dashboard showing prices, gap, signal, and charts (completed 2026-03-24)
- [x] **Phase 6: Telegram Alerts** - Push notifications on signal changes and price movements (completed 2026-03-24)
- [x] **Phase 7: Macro Indicators** - Factor USD/VND, interest rates, DXY, and global gold trend into signals (completed 2026-03-25)
- [x] **Phase 8: State Bank Policy & Seasonal Factors** - Incorporate regulatory events and Vietnamese seasonal demand patterns (completed 2026-03-25)
- [x] **Phase 9: Market News Feed** - Aggregated gold market news and State Bank policy announcements (completed 2026-03-25)

## Phase Details

### Phase 1: Project Foundation & International Data
**Goal**: System reliably ingests and stores international gold price data (XAUUSD) in both USD and VND, with data quality monitoring that flags stale or anomalous data
**Depends on**: Nothing (first phase)
**Requirements**: DATA-03, DATA-06
**Success Criteria** (what must be TRUE):
  1. System starts up, serves a health check endpoint, and runs scheduled tasks via APScheduler
  2. International gold price (XAUUSD) is fetched every 5 minutes, converted to VND, and stored with timestamps and source metadata
  3. Data quality checks run after each fetch — stale data (>15 min old), missing values, and anomalous price jumps are flagged in logs and surfaced via an API endpoint
  4. Database schema supports storing time-series price records with source tracking and validation status
**Plans:** 3/3 plans complete

Plans:
- [x] 01-01-PLAN.md — FastAPI app scaffold, SQLite database models, config, health endpoint
- [x] 01-02-PLAN.md — Gold price fetcher (yfinance), USD/VND FX fetcher (Vietcombank), repository layer
- [x] 01-03-PLAN.md — Data quality checks, APScheduler integration, quality API, end-to-end pipeline

### Phase 2: Vietnamese Gold Price Scraping
**Goal**: System reliably scrapes buy/sell prices from 5+ Vietnamese gold dealers for SJC bars, ring gold (nhẫn trơn), and dealer buy/sell spreads, on a 1-5 minute schedule
**Depends on**: Phase 1
**Requirements**: DATA-01, DATA-02, DATA-05
**Success Criteria** (what must be TRUE):
  1. Buy/sell prices are scraped from 5+ dealers (SJC, Doji, PNJ, BTMC, Phú Quý, Mi Hồng) and stored in the database
  2. Ring gold (nhẫn trơn) prices are scraped alongside SJC bar prices from the same dealers
  3. Buy/sell spreads are calculated and stored for each dealer and product type
  4. Individual scraper failures don't crash the system or block other scrapers — failures are logged and surfaced in data quality checks
**Plans:** 3/3 plans complete

Plans:
- [x] 02-01-PLAN.md — Static HTML scrapers for DOJI & Phu Quý (httpx + BeautifulSoup)
- [x] 02-02-PLAN.md — Playwright scrapers for SJC & PNJ (JS-rendered sites)
- [x] 02-03-PLAN.md — BTMC API scraper, spread storage, full pipeline verification

### Phase 3: Gap Analysis & Price Charts
**Goal**: Users can see the SJC-international price gap with historical context (1W/1M/3M/1Y) and visual price charts for all gold products
**Depends on**: Phase 2
**Requirements**: DATA-04, DATA-07
**Success Criteria** (what must be TRUE):
  1. SJC-international price gap is calculated and available in both VND absolute and percentage terms
  2. Historical gap trend is queryable for 1W, 1M, 3M, and 1Y windows
  3. Price charts display SJC bars, ring gold, and international gold for 1D, 1W, 1M, and 1Y timeframes
**Plans:** 2/2 plans complete

Plans:
- [x] 03-01-PLAN.md — DuckDB analytics foundation + gap calculation engine (DATA-04)
- [x] 03-02-PLAN.md — Price chart data API for all gold products (DATA-07)

### Phase 4: Signal Engine Core
**Goal**: Users receive Buy/Hold/Sell signals with confidence levels (0-100%), one-line reasoning explanations, and mode-appropriate interpretation for Savers vs Traders
**Depends on**: Phase 3
**Requirements**: SIG-01, SIG-02, SIG-06
**Success Criteria** (what must be TRUE):
  1. Signal engine produces a Buy/Hold/Sell recommendation with a 0-100% confidence score based on multi-factor analysis
  2. Each signal includes a one-line reasoning explanation (e.g., "Gap narrowed to 2.8% vs 30-day avg 4.5% — favorable buy conditions")
  3. Selecting Saver mode produces accumulation-oriented guidance; selecting Trader mode produces timing-precision-focused signals with different confidence weighting
  4. Signals are stored with full context (inputs, confidence breakdown, mode) for historical analysis
**Plans:** 4/4 plans complete

Plans:
- [x] 04-01-PLAN.md — Signal types + gap/spread/trend factors + composite scorer (SIG-01)
- [x] 04-02-PLAN.md — Reasoning generator + Saver/Trader modes + signal persistence (SIG-02, SIG-06)
- [x] 04-03-PLAN.md — Signal pipeline orchestrator + API endpoints + FastAPI wiring (SIG-01, SIG-02, SIG-06)
- [x] 04-04-PLAN.md — Gap closure: wire mode weights + connect spread data to pipeline (SIG-01, SIG-06)

### Phase 5: Web Dashboard
**Goal**: Users can view all current data (dealer prices, gap tracker, signal with confidence and reasoning, price charts) on a mobile-responsive web dashboard
**Depends on**: Phase 4
**Requirements**: DEL-01
**Success Criteria** (what must be TRUE):
  1. Dashboard loads and displays current SJC bar and ring gold buy/sell prices from all dealers
  2. Dashboard shows current signal (Buy/Hold/Sell), confidence level, and one-line reasoning
  3. Dashboard displays SJC-international gap with historical trend
  4. Dashboard includes price charts for SJC bars, ring gold, and international gold across selectable timeframes
  5. Dashboard is usable on mobile devices (responsive layout, readable without horizontal scrolling)
**Plans:** 3/3 plans complete

Plans:
- [x] 05-01-PLAN.md — Dashboard data API + template/static infrastructure (Tailwind, Chart.js, HTMX)
- [x] 05-02-PLAN.md — Full dashboard: signal card, price table, gap display, charts, HTMX live refresh
- [x] 05-03-PLAN.md — Human verification checkpoint

### Phase 6: Telegram Alerts
**Goal**: Users receive timely Telegram notifications when signals change or prices move significantly, with signal context and disclaimers
**Depends on**: Phase 4
**Requirements**: DEL-02
**Success Criteria** (what must be TRUE):
  1. User can start a Telegram bot conversation and subscribe to alerts
  2. User receives a Telegram message when the signal changes (e.g., Hold → Buy)
  3. User receives a Telegram message on significant price movements (threshold-based)
  4. Alert messages include the signal/reasoning and a "not financial advice" disclaimer
**Plans**: 0/3 plans complete

Plans:
- [x] 06-01-PLAN.md — Telegram bot setup with /start and /status commands
- [x] 06-02-PLAN.md — Alert dispatcher with signal change detection and message templates
- [x] 06-03-PLAN.md — Wire alerts into scheduler pipeline and end-to-end verification

### Phase 7: Macro Indicators
**Goal**: Users can see macroeconomic context (USD/VND exchange rate, real interest rates, DXY dollar strength, global gold trend) on the dashboard and macro factors influence signal confidence
**Depends on**: Phase 5
**Requirements**: SIG-05
**Success Criteria** (what must be TRUE):
  1. Dashboard displays USD/VND exchange rate with trend indicator
  2. Dashboard displays real interest rate level and direction
  3. Dashboard displays DXY dollar strength index
  4. Dashboard displays global gold trend direction
  5. Macro indicators contribute to signal confidence calculation
**Plans**: 3/3 plans complete

Plans:
- [x] 07-01-PLAN.md — DXY fetcher + FX trend + gold trend calculators
- [x] 07-02-PLAN.md — Macro signal factors + composite scorer integration
- [x] 07-03-PLAN.md — Macro dashboard section + API endpoints
**UI hint**: yes

### Phase 8: State Bank Policy & Seasonal Factors
**Goal**: Signal engine incorporates State Bank policy events (import approvals, auctions, interventions) as an override factor and Vietnamese seasonal demand patterns (Tet, wedding season, Vu Lan, ghost month) into signal calculation
**Depends on**: Phase 4
**Requirements**: SIG-03, SIG-04
**Success Criteria** (what must be TRUE):
  1. State Bank policy events are tracked — when detected, they are flagged and affect signal confidence (override or reduce confidence)
  2. Vietnamese seasonal calendar (Tet, wedding season, Vu Lan, ghost month) is built into the signal engine
  3. Seasonal demand patterns influence signal direction and/or confidence (e.g., pre-Tet premium awareness reduces buy confidence)
  4. State Bank policy events are surfaced in the dashboard signal display
**Plans:** 3/3 plans complete

Plans:
- [x] 08-01-PLAN.md — Vietnamese seasonal demand calendar + confidence modifier
- [x] 08-02-PLAN.md — State Bank policy event tracking + admin API
- [x] 08-03-PLAN.md — Integration into composite scorer + pipeline + dashboard display
**UI hint:** yes

### Phase 9: Market News Feed
**Goal**: Users can read an aggregated feed of gold market news and State Bank policy announcements on the dashboard
**Depends on**: Phase 5
**Requirements**: DEL-03
**Success Criteria** (what must be TRUE):
  1. Dashboard displays a news feed of gold market news articles
  2. News feed includes State Bank policy announcements
  3. News items are sorted by recency and relevance to gold pricing
**Plans:** 3/3 plans complete

Plans:
- [x] 09-01-PLAN.md — News fetcher (RSS feed reader for gold market news)
- [x] 09-02-PLAN.md — News storage + API endpoints + admin endpoint for manual entries
- [x] 09-03-PLAN.md — Dashboard news section + scheduler integration
**UI hint:** yes

## Progress

**Execution Order:**
Phases execute in numeric order. With parallelization enabled:
- Phase 5 and Phase 6 can execute in parallel (both depend on Phase 4)
- Phase 7, Phase 8, and Phase 9 can execute in parallel (depend on Phase 4/5)

| Phase | Plans Complete | Status | Completed |
|-------|----------------|--------|-----------|
| 1. Project Foundation & International Data | 0/3 | Complete    | 2026-03-24 |
| 2. Vietnamese Gold Price Scraping | 0/3 | Complete    | 2026-03-24 |
| 3. Gap Analysis & Price Charts | 0/2 | Complete    | 2026-03-24 |
| 4. Signal Engine Core | 3/4 | Complete    | 2026-03-24 |
| 5. Web Dashboard | 0/3 | Complete    | 2026-03-24 |
| 6. Telegram Alerts | 3/3 | Complete    | 2026-03-24 |
| 7. Macro Indicators | 3/3 | Complete    | 2026-03-24 |
| 8. State Bank Policy & Seasonal Factors | 3/3 | Complete    | 2026-03-24 |
| 9. Market News Feed | 3/3 | Complete    | 2026-03-25 |

---
*Roadmap created: 2026-03-25*
