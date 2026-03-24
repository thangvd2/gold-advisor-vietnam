# Project Research Summary

**Project:** Gold Advisor Vietnam
**Domain:** AI-powered financial advisory web app (Vietnamese gold market — SJC bars + nhẫn trơn timing signals)
**Researched:** 2026-03-25
**Confidence:** MEDIUM-HIGH

## Executive Summary

Gold Advisor Vietnam is a single-commodity, single-country financial advisory tool that helps Vietnamese users time physical gold purchases by analyzing the SJC-international price gap, macro indicators, seasonal demand patterns, and State Bank policy. The Vietnamese gold app market is entirely focused on price display and news — no existing product provides analytical signals, gap-based timing advice, or messenger alerts. This is a blue-ocean opportunity in a space where millions of Vietnamese check gold prices daily.

The recommended approach is a Python monolith (FastAPI + APScheduler + SQLAlchemy/SQLite + DuckDB) with server-rendered HTML (Jinja2 + HTMX + Tailwind), scraping ~5-8 gold shop websites and international APIs on a 5-15 minute schedule. The signal engine should be **deterministic** (pure Python, no LLM) with a **single LLM call** used only to convert structured signal data into Vietnamese-language narrative. Multi-agent architectures and real-time streaming infrastructure are explicitly anti-patterns for this scale. Alerts deliver via Telegram (primary) and Zalo OA (secondary). The architecture follows a clear pipeline: ingest → normalize → compute signal → generate narrative → dispatch alert → serve dashboard.

The six critical pitfalls are: (1) treating gold prediction as solvable ML (frame signals as informational, not predictive), (2) LLM hallucinating financial advice (strict data-grounding architecture), (3) scraped data going silently stale (multi-source cross-validation + freshness monitoring), (4) State Bank policy changes invalidating signal logic (regime-aware model + policy monitoring), (5) overpromising accuracy and facing liability (prominent disclaimers, never use "predict"), and (6) oversimplifying Vietnamese cultural complexity (separate SJC bar vs nhẫn trơn models, build seasonal calendar). All six must be addressed in Phase 1 design decisions — retrofitting is extremely painful.

## Key Findings

### Recommended Stack

Python monolith optimized for simplicity, async performance, and financial data workloads. No JavaScript runtime needed for the core product.

**Core technologies:**
- **Python 3.12+** — runtime; best ecosystem for data analysis, scraping, AI/LLM integration, async
- **FastAPI 0.115+** — web framework/API server; async-native, auto OpenAPI docs, Pydantic validation
- **APScheduler 3.11.2** — task scheduling; stay on 3.x (4.x is alpha with "DO NOT use in production"), in-process, no Redis needed
- **SQLAlchemy 2.0+ / SQLite** — database; zero-config for MVP, migrate to PostgreSQL via SQLAlchemy when scale demands it
- **DuckDB 1.1+** — analytical queries; in-process OLAP for time-series aggregations, window functions, gap analysis
- **httpx + BeautifulSoup** — scraping; async-first HTTP + HTML parsing for static Vietnamese gold shop sites
- **Playwright** — fallback scraping for JS-heavy sites (PNJ, some dealers)
- **pandas 2.2+** — time-series analysis; resampling, rolling windows, gap calculations
- **openai 1.68+** — LLM integration; structured output with Pydantic models for Vietnamese narrative
- **python-telegram-bot 22.x** — Telegram alerts; async-native, best-documented, primary messenger channel
- **Jinja2 + HTMX + Tailwind CSS** — dashboard; server-rendered, no SPA build step needed
- **uv** — package manager; replaces pip+venv+pyenv, 10-100x faster

**Explicitly avoid:** requests (sync), Selenium (legacy), Celery (overkill), Scrapy (overkill), Streamlit (not production-ready), React/Next.js (adds Node.js complexity), APScheduler 4.x (alpha), Flask (no async), MongoDB (schema-less liability).

### Expected Features

**Must have (table stakes) — MVP v1:**
- SJC price data pipeline — scrape SJC, Doji, PNJ, BTMC prices every 2-5 min with fallbacks
- International gold price (XAUUSD) — source from free API, convert to VND
- SJC-international gap tracker — core differentiator; no Vietnamese app does this analytically
- Basic signal engine — Buy/Hold/Sell based on gap thresholds + confidence level
- Web dashboard — mobile-responsive, current prices, gap, signal, chart
- Telegram alerts — push notifications on signal changes and price movements
- Signal reasoning — one-line explanation with each signal ("gap at 2.8% vs 30-day avg 4.5%")
- Nhẫn trơn tracking — ring gold alongside SJC bars (different dynamics)
- Disclaimers — "not financial advice" on every output

**Should have (competitive) — v1.x after validation:**
- Zalo OA integration — 95% smartphone penetration in Vietnam, 74M+ users
- State Bank policy monitoring — unique competitive moat, no one does this programmatically
- Seasonal demand modeling — Tet, wedding season, Vu Lan create predictable cycles
- Macro indicator dashboard — USD/VND, Fed rates, global gold trend
- Signal accuracy tracking — published win/loss record builds trust
- Buy/sell spread comparison across dealers
- Gold portfolio tracker (Sổ vàng) — sticky feature
- Dual user mode (Saver vs Trader) — different interpretations of same signal

**Defer (v2+):**
- Automatic trade execution (regulatory nightmare, out of scope)
- Real-time streaming (no real-time feed exists for Vietnamese physical gold)
- Paper gold / ETF / futures (different market dynamics, dilutes value prop)
- Multi-asset portfolio allocation (requires license, out of scope)
- AI chatbot for Q&A (hallucination risk, liability)
- Price prediction / forecasting (no one can predict gold)
- Native mobile app (validate web usage first)

### Architecture Approach

Monolith-first architecture with clear separation between deterministic computation and LLM narrative generation. The system follows a linear pipeline: data ingestion → normalization → signal computation → advisory generation → alert dispatch → dashboard serving.

**Major components:**
1. **Data Ingestion Layer** — scraper workers (per-shop adapters: SJC, DOJI, PNJ, BTMC) + API fetchers (Kitco/XAUUSD, USD/VND) + normalizer (unified PriceRecord schema with Pydantic validation)
2. **Core Engine Layer** — signal computation (gap calculator, spread tracker, macro scorer, seasonal adjuster, composite aggregator) — pure deterministic Python, no LLM dependency
3. **LLM Advisory Layer** — single LLM call to convert structured SignalResult into Vietnamese-language narrative; prompt builder + renderer pattern; NOT multi-agent
4. **Alert Dispatcher** — threshold-based rule checker (not AI-driven) + message templates + channel adapters (Telegram + Zalo OA)
5. **API Layer** — thin FastAPI REST wrapper, no business logic
6. **Scheduler** — APScheduler 3.x in-process: every 5 min scrape domestic, every 10 min fetch international, every 10 min run signal engine
7. **Data Layer** — SQLite for writes/CRUD, DuckDB for analytical reads, optional Redis for caching

**Key architectural decisions:**
- Adapter pattern per data source (isolates HTML changes to one file)
- Pipeline pattern for signal computation (each stage independently testable)
- Single LLM call for advisory, not multi-agent (5 numeric inputs don't warrant 47-agent orchestration)
- LLM only called when recommendation changes or confidence crosses threshold (cost/latency optimization)
- Database as source of truth, no complex state management
- Monolith scales to 1000+ users before any separation needed

### Critical Pitfalls

1. **Treating gold prediction as solvable ML** — Gold price variance explained by traditional models is <40% (lowest since 2011). Frame signals as informational, use naive baselines, present confidence ranges. Never claim prediction capability.
2. **LLM hallucinating financial advice** — Implement strict data-grounding: LLM may only reference structured data from the database, never fabricate statistics or policy references. Log all outputs for audit. Mandatory disclaimers on every output.
3. **Scraped data going silently stale** — Multi-source cross-validation, explicit freshness timestamps, schema validation on every record, canary checks against known prices, health reports per scraper run. "Data may be stale" warning when SLA breached.
4. **State Bank policy invalidating signals** — Track regulatory regimes explicitly, weight recent data (6-12 month windows), include SBV action as first-class signal, default to "reduced confidence" mode after policy changes.
5. **Overpromising accuracy / liability exposure** — Never use "predict," "forecast," or "guarantee." Show data behind conclusions. Publish transparent accuracy tracking. Include "what could go wrong" with every signal. Betterment ($9M) and Schwab ($187M) settlements are cautionary precedents.
6. **Oversimplifying Vietnamese cultural complexity** — Model SJC bars and nhẫn trơn as separate products. Build seasonal calendar (Tet, wedding season, Vu Lan). Distinguish structural premium (expected) from timing opportunity (actionable). Factor buy/sell spreads into signal evaluation.

## Implications for Roadmap

Based on combined research, the project decomposes into 4-5 phases following the dependency graph. Data quality and signal design decisions made in Phase 1 are irreversible — they determine whether the entire product works.

### Phase 1: Data Foundation + Signal Core
**Rationale:** Everything depends on reliable price data and a well-designed signal model. This is the highest-risk phase because it involves scraping unpredictable Vietnamese websites and designing signal logic that must handle regime changes, cultural complexity, and prediction limitations from day one.
**Delivers:** Price ingestion pipeline (SJC + 1 international source + USD/VND), normalized database, gap calculator, basic composite signal (Buy/Hold/Sell + confidence), data quality monitoring (freshness checks, cross-validation), walk-forward backtest framework
**Addresses:** SJC price data pipeline, international gold price, gap tracker, basic signal engine, signal reasoning, nhẫn trơn tracking, disclaimers
**Avoids:** Pitfalls 1 (predictive framing), 3 (stale data), 4 (regime-blind signals), 5 (overpromising language), 6 (cultural oversimplification)
**Key decision:** Signal model design (gap thresholds, confidence calculation, regime awareness) — this decision is hard to change later

### Phase 2: Presentation + Telegram Alerts
**Rationale:** Users need to see prices and receive alerts for the product to provide value. This phase delivers the full MVP. Telegram is prioritized over Zalo because it has a well-documented free API, no business verification needed, and reaches the tech-savvy investor segment first.
**Delivers:** FastAPI production server, web dashboard (Jinja2 + HTMX + Chart.js/Tailwind), mobile-responsive layout, Telegram bot (/status, /subscribe commands), alert dispatcher with threshold rules, formatted alerts with signal + reasoning + disclaimer
**Addresses:** Web dashboard, Telegram alerts, signal reasoning display, mobile-responsive web, price charts/history, buy/sell spread display
**Avoids:** Pitfall 2 (LLM hallucination — advisory layer deferred), Pitfall 5 (overpromising — UX language reviewed here)
**Uses:** FastAPI, Jinja2, HTMX, Tailwind CSS, Chart.js, python-telegram-bot, APScheduler

### Phase 3: Intelligence Enrichment
**Rationale:** Now that the core pipeline is running and users are receiving basic signals, enrich the signal quality with additional data sources and LLM narrative. This is the right time to add the LLM advisory layer because the signal engine provides structured, validated data for grounding.
**Delivers:** LLM advisory layer (Vietnamese narrative generation with data-grounding), macro scorer (USD/VND trend, global gold trend), seasonal demand model (Vietnamese cultural calendar), additional scrapers (DOJI, PNJ, BTMC, State Bank), expanded composite signal with macro + seasonal factors
**Addresses:** Signal reasoning (enhanced with LLM), State Bank policy monitoring, seasonal demand model, macro indicator dashboard, market news feed
**Avoids:** Pitfall 2 (data-grounding architecture built into LLM layer), Pitfall 4 (policy monitoring as first-class signal)
**Implements:** LLM Advisory Layer from architecture, Macro Scorer, Seasonal Adjuster

### Phase 4: Zalo + Retention Features
**Rationale:** With the core product validated and enriched, expand reach to mainstream Vietnamese users via Zalo OA and add retention features (portfolio tracking, accuracy tracking) that increase stickiness.
**Delivers:** Zalo OA integration (chatbot + ZNS push notifications), signal accuracy tracking (published track record), gold portfolio tracker (Sổ vàng), buy/sell spread comparison across dealers, user profiles (Saver vs Trader modes)
**Addresses:** Zalo OA integration, signal accuracy tracking, gold portfolio tracker, buy/sell spread comparison, user profiles
**Research flag:** Zalo OA API has LOW confidence documentation — approval process, rate limits, and message format constraints need validation during planning

### Phase 5: Validation + Growth (Future)
**Rationale:** Only after months of signal history can the system meaningfully backtest and validate its own performance. Premium features come after product-market fit is established.
**Delivers:** Advanced backtesting framework, multi-dealer spread alerts, community features (curated analysis), advanced seasonal modeling, mobile app (if web usage validates demand), premium subscription tier

### Phase Ordering Rationale

- **Phase 1 is foundational and highest risk:** Scraping Vietnamese gold sites is unpredictable, signal design is irreversible, and all 6 critical pitfalls must be addressed in Phase 1 architecture decisions. Get this wrong and nothing downstream fixes it.
- **Phase 2 delivers the MVP:** Users get value (prices + gap + signals + alerts) even without LLM narrative. This is the minimum to validate the core value proposition.
- **Phase 3 is enrichment, not essential:** The signal engine works without LLM, macro data, or seasonal modeling. These improve quality but aren't required for launch.
- **Phase 4 expands reach and retention:** Zalo reaches the mainstream Vietnamese market. Retention features keep users engaged.
- **Phase 5 is post-PMF:** Backtesting needs months of history. Premium tier needs established trust.

### Research Flags

**Phases likely needing deeper research during planning:**
- **Phase 1:** Vietnamese gold shop website structure — assumed mix of static/dynamic based on typical patterns but must validate each target site (sjc.com.vn, doji.vn, pnj.com.vn, btmc.vn). Scrape targets may have changed since research. Use `/gsd:research-phase`.
- **Phase 1:** Signal threshold calibration — gap thresholds for buy/sell signals need historical data analysis. No research could determine optimal thresholds. Need to analyze historical gap data during implementation.
- **Phase 4:** Zalo OA API — LOW confidence on rate limits, approval process, and ZNS capabilities. Unofficial documentation only. Needs `/gsd:research-phase` or direct Zalo developer documentation review.

**Phases with standard patterns (skip research-phase):**
- **Phase 2:** FastAPI dashboard, Telegram bot, alert dispatch — all well-documented with established patterns, high-quality Context7 documentation available
- **Phase 3:** LLM integration (OpenAI structured output) — well-documented, mature SDK
- **Phase 5:** Backtesting, premium tiers — standard patterns from signal service industry

## Confidence Assessment

| Area | Confidence | Notes |
|------|------------|-------|
| Stack | HIGH | All core technologies verified via Context7 official docs, PyPI, and multiple community sources. APScheduler 3.x vs 4.x alpha verified on PyPI. Vietnamese gold scraping stack (httpx+BS4+Playwright) confirmed by multiple web scraping guides. |
| Features | MEDIUM | Vietnamese app features verified via app store listings (HIGH). Signal service patterns from international sources (MEDIUM). Zalo OA capabilities from unofficial docs only (MEDIUM-LOW). The core differentiator (gap-based timing) is validated as unique — no Vietnamese app does this. |
| Architecture | MEDIUM-HIGH | Pipeline and adapter patterns are industry-standard (HIGH). Single-LLM-call recommendation based on strong reasoning about problem scale (MEDIUM-HIGH). Monolith-first approach strongly supported by data volume analysis. Project structure follows established Python conventions. |
| Pitfalls | MEDIUM-HIGH | Gold prediction limitations backed by AhaSignals research + LBMA consensus data + academic papers (HIGH). LLM hallucination risk backed by FINRA 2026 report + legal precedents (HIGH). Scraping staleness backed by industry consensus (MEDIUM-HIGH). Vietnamese market dynamics backed by SBV reports + World Gold Council + Decree 24/232 (HIGH). Liability precedents from SEC settlements (HIGH). |

**Overall confidence:** MEDIUM-HIGH

### Gaps to Address

- **Vietnamese gold shop website structure:** Research assumed mix of static/dynamic based on typical patterns. Must validate each target site (sjc.com.vn, doji.vn, pnj.com.vn, btmc.vn) during Phase 1 implementation. Open-source projects (namtrhg/vn-gold-price-api) provide SJC patterns but other sites are unverified.
- **Optimal signal thresholds:** Research could not determine specific gap thresholds (e.g., "buy when gap < 3%") because this requires historical data analysis. Must be calibrated during Phase 1 using walk-forward validation on actual data.
- **Zalo OA API details:** Rate limits, approval timeline, message format constraints, and ZNS capabilities are documented only in unofficial guides. Needs direct validation during Phase 4 planning.
- **International gold price API selection:** Multiple options exist (Kitco, MetalPriceAPI, free tiers). Must evaluate free tier limits, reliability, and data quality during Phase 1.
- **State Bank data source:** How to reliably detect and parse SBV policy announcements is unclear. Hybrid approach (automated monitoring + manual curation) recommended but needs operational planning.

## Sources

### Primary (HIGH confidence)
- Context7: `/websites/fastapi_tiangolo` — FastAPI background tasks, middleware, lifespan events, CORS
- Context7: `/websites/playwright_dev_python` — Playwright async API, browser context
- Context7: `/websites/pandas_pydata` — Time-series resampling, rolling windows, aggregation
- Context7: `/agronholm/apscheduler` — APScheduler 3.x + 4.x alpha status, FastAPI integration
- Context7: `/openai/openai-python` — OpenAI SDK structured output, Pydantic parsing
- Context7: `/encode/httpx` — HTTPX async client, retries, timeout handling
- Context7: `/websites/duckdb_stable` — DuckDB window functions, time-series SQL
- Context7: `/python-telegram-bot/python-telegram-bot` — Telegram bot v22.x API
- FINRA 2026 Annual Regulatory Oversight Report — AI hallucination compliance risk
- SEC speech on AI and investment management (Feb 2026)
- World Gold Council reporting on Vietnam gold price gap (2024-2025)
- State Bank of Vietnam reports to National Assembly on gold market (2025)
- Decree 24 / Decree 232 on gold trading management
- AhaSignals research on gold forecast consensus gap (March 2026)
- PyPI: APScheduler 3.11.2 stable / 4.0.0a6 alpha verified

### Secondary (MEDIUM confidence)
- Vietnamese gold apps analyzed: Vàng Mi Hồng, Giá Vàng VN, iGold, Gold VN, Báo Giá Vàng (feature comparison)
- Algovantis "Robust Algo Trading Pipeline Architecture" (2026) — pipeline pattern
- Chatterjee "Modular Architecture for Quantitative Trading Systems" (2025) — separation of concerns
- Devarshi Vyas "Swing Trading Agent with LangGraph" (2026) — token cost optimization
- Web scraping pitfall articles (Firecrawl, AIMultiple, ScrapeGraphAI 2025-2026)
- Zalo ecosystem research: Prodima Vietnam, Nokasoft Zalo OA integration guide
- Academic papers on gold price forecasting (Springer, ResearchGate 2025-2026)
- namtrhg/vn-gold-price-api — existing VN gold scraping patterns

### Tertiary (LOW confidence)
- python-zalo-bot v0.1.9 (unofficial, low-maturity) — use direct httpx instead
- Mehul Thakkar 47-agent system (2026) — referenced as anti-pattern, not pattern to follow
- Vietnamese gold shop website structure — assumed from typical patterns, not verified per-site
- Zalo OA API rate limits and approval process — unofficial documentation only

---
*Research completed: 2026-03-25*
*Ready for roadmap: yes*
