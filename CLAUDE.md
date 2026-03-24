<!-- GSD:project-start source:PROJECT.md -->
## Project

**Gold Advisor Vietnam**

An AI advisory agent that helps Vietnamese users time their physical gold purchases and sales. The agent tracks SJC gold bars and nhẫn trơn (plain gold rings), analyzes the gap between domestic and international gold prices alongside macro signals and seasonal patterns, and delivers buy/hold/sell recommendations via a web dashboard and messenger alerts. Advice only — no transactions.

**Core Value:** Users buy lower and sell higher than they would with blind timing, and they understand *why*.

### Constraints

- **Data fragility**: Vietnamese gold price data comes from web sources that may change structure — scrapers need resilience and fallbacks
- **No real-time exchange feed**: Unlike paper gold, physical gold prices update intermittently from dealers, not from a continuous exchange
- **Regulatory sensitivity**: Gold market regulation in Vietnam can shift — State Bank policy changes can override all other signals
- **Advice liability**: Buy/sell recommendations need clear disclaimers and confidence thresholds to avoid misleading users
<!-- GSD:project-end -->

<!-- GSD:stack-start source:research/STACK.md -->
## Technology Stack

## Recommended Stack
### Core Technologies
| Technology | Version | Purpose | Why Recommended |
|------------|---------|---------|-----------------|
| **Python** | 3.12+ | Runtime language | Best ecosystem for data analysis, web scraping, AI/LLM integration. Type hints are mature, async is first-class, and every domain library we need is Python-native. |
| **FastAPI** | 0.115+ | Web framework / API server | Async-native, automatic OpenAPI docs, Pydantic validation (critical for financial data integrity), BackgroundTasks for async alert dispatch. De facto standard for Python APIs in 2025. Verified via Context7: has built-in CORS, lifespan events, middleware, static file serving. |
| **SQLAlchemy** | 2.0+ | ORM / database access | Industry-standard async ORM. SQLAlchemy 2.0's new Mapped syntax is clean, async engine support is mature. Works with SQLite (dev) and PostgreSQL (prod). Verified via Context7. |
| **Alembic** | 1.14+ | Database migrations | Paired with SQLAlchemy. Handles schema evolution cleanly. Essential for iterating on data models as you discover what gold price data shape you actually need. |
| **APScheduler** | 3.11.2 | Task scheduling | **Stable release.** APScheduler 4.0.0a6 is still in alpha with "DO NOT use in production" warning (last alpha: April 2025). Use 3.11.2 with `BackgroundScheduler` or `AsyncIOScheduler` for cron-style scraping jobs (every 5-15 min) and periodic signal analysis. No Redis/RabbitMQ required. Verified via PyPI. |
| **SQLite** | 3.x | Persistent storage (dev/default) | Zero-config, single-file database. Perfect for this project's data volume (thousands of price points per day, not millions). Works great with SQLAlchemy async via `aiosqlite`. Can migrate to PostgreSQL later if needed with zero code changes (SQLAlchemy abstracts this). |
| **DuckDB** | 1.1+ | Analytical queries | In-process OLAP database. Blazing fast for time-series aggregations, window functions (moving averages, gap calculations). Complements SQLite: use SQLite for writes/CRUD, DuckDB for reads/analysis. Verified via Context7: supports RANGE BETWEEN INTERVAL framing, named WINDOW clauses. |
### Supporting Libraries
| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| **httpx** | 0.28+ | Async HTTP client | Primary HTTP client for international gold price APIs (Kitco, etc.), State Bank data fetches, and Zalo API calls. Built-in retry support via `HTTPTransport(retries=N)`. Async-native. Verified via Context7. |
| **beautifulsoup4** | 4.12+ | HTML parsing | Parse static HTML from Vietnamese gold shop sites (SJC, Doji, PNJ). Lightweight, battle-tested. Use with httpx (not requests - httpx is async). Pair with `lxml` parser for speed. |
| **playwright** | 1.49+ | Browser automation (fallback) | For gold shop sites that require JavaScript rendering (React/Vue SPAs). Don't start here - start with httpx+BS4. Only reach for Playwright when static fetching fails. Use async API (`async_playwright`). Verified via Context7. |
| **pandas** | 2.2+ | Data analysis & manipulation | Time-series resampling, rolling windows, gap calculations between domestic/international prices. Core analysis engine. Verified via Context7: `resample()` with time-based indexing, groupby aggregation. |
| **openai** | 1.68+ | LLM integration | Generate natural-language buy/sell advice in Vietnamese from signal data. `chat.completions.parse()` with Pydantic models for structured output. Verified via Context7: supports structured output, streaming, function calling. |
| **python-telegram-bot** | 22.x | Telegram bot alerts | Production-grade Telegram bot library. Async-native, handles webhook/polling, message formatting, inline keyboards for user interaction. Verified via Context7. |
| **pydantic** | 2.10+ | Data validation | Used throughout: API request/response models, gold price data schemas, signal output models, LLM structured output. FastAPI depends on it already. |
| **jinja2** | 3.1+ | HTML templating | Dashboard templates served by FastAPI. Keep it simple - server-rendered HTML is sufficient for a price dashboard. No need for a separate SPA framework at this scale. |
### Development Tools
| Tool | Purpose | Notes |
|------|---------|-------|
| **uv** | Package manager & Python version manager | Replaces pip + venv + pyenv. 10-100x faster than pip. `uv init`, `uv add`, `uv sync`. The standard in 2025 Python tooling. |
| **ruff** | Linter + formatter | Replaces flake8 + black + isort. Extremely fast (Rust-based). Single config in `pyproject.toml`. |
| **pytest** | Testing | Async testing via `pytest-asyncio`. Test scrapers with mocked HTTP responses, test signal logic with sample price data. |
| **pytest-asyncio** | Async test support | Required for testing FastAPI endpoints, async scrapers, APScheduler jobs. |
| **pre-commit** | Git hooks | Run ruff, pytest on commit. Prevents broken code from landing. |
### Dashboard Frontend (Server-Rendered)
| Technology | Purpose | Notes |
|------------|---------|-------|
| **Jinja2 templates** | HTML server-rendering | FastAPI serves HTML directly. No separate frontend build step. Sufficient for a dashboard with charts. |
| **HTMX** | Dynamic updates | Minimal JS for partial page updates (refresh price table without full reload). Progressive enhancement. |
| **Chart.js** or **Plotly.js** | Price charts | Client-side charting for gold price history, gap tracker, moving averages. Chart.js is lighter; Plotly.js has more chart types. |
| **Tailwind CSS** | Styling | Utility-first CSS. Rapid styling without writing custom CSS. Works great with Jinja2 templates. |
### Messenger Alert Framework
| Platform | Library | Status | Notes |
|----------|---------|--------|-------|
| **Telegram** | python-telegram-bot 22.x | PRIMARY - build first | Best documented, easiest setup, async-native, large Vietnamese user base. Start here. |
| **Zalo** | Direct httpx calls to Zalo OA API | SECONDARY - add later | Zalo is the dominant Vietnamese messenger. Use Official Account (OA) API via httpx directly. No mature Python SDK exists (python-zalo-bot v0.1.9 is unofficial and low-maturity). The OA API is straightforward REST calls. |
## Installation
# Core application
# FastAPI + server
# Database
# Scheduling
# Data fetching & scraping
# Analysis
# LLM
# Telegram alerts
# Configuration
# Dev dependencies
## Alternatives Considered
| Recommended | Alternative | When to Use Alternative |
|-------------|-------------|-------------------------|
| **FastAPI** | Flask | Only if you need Flask-specific extensions. FastAPI is strictly better for this use case (async, auto-docs, Pydantic integration). |
| **APScheduler 3.x** | Celery + Redis | Celery is overkill for this project. APScheduler runs in-process, no Redis/RabbitMQ needed. If you later need distributed task processing across multiple machines, migrate to Celery. |
| **SQLite + DuckDB** | PostgreSQL + TimescaleDB | PostgreSQL is better if you expect >1M daily rows or need concurrent writes. For a single-user advisory app with thousands of data points per day, SQLite is simpler and faster. Migrate path exists via SQLAlchemy. |
| **httpx + BeautifulSoup** | Scrapy | Scrapy is a full crawling framework with Twisted (not asyncio). Overkill for scraping 5-10 gold shop sites. Use httpx+BS4 first, add Playwright only for JS-heavy sites. |
| **python-telegram-bot** | aiogram | aiogram is faster and more Pythonic for Telegram, but python-telegram-bot has better documentation and a gentler learning curve. Either works; python-telegram-bot is the safer choice. |
| **Server-rendered (Jinja2+HTMX)** | React/Vue SPA | A separate SPA adds build tooling, state management, and deployment complexity. Server-rendered HTML is sufficient for a dashboard. Add a SPA later only if you need complex interactivity. |
| **OpenAI SDK** | LiteLLM / direct API | OpenAI SDK is the most mature Python LLM client. LiteLLM adds multi-provider support (Claude, Gemini) if you want provider flexibility. Start with OpenAI SDK directly. |
| **Chart.js** | Plotly.js | Chart.js is lighter (70KB vs 3MB). Plotly.js has more interactive chart types. Start with Chart.js; switch to Plotly.js if you need candlestick charts or complex financial visualizations. |
## What NOT to Use
| Avoid | Why | Use Instead |
|-------|-----|-------------|
| **requests** | Synchronous-only. Blocks the event loop in FastAPI. Can't do concurrent API calls to multiple gold shops. | **httpx** - async-first, supports HTTP/2, built-in retries, compatible API |
| **Selenium** | Legacy. Slow, heavy, poor async support. Playwright has superseded it for all new projects. | **Playwright** - 3-10x faster, async-native, auto-waiting, better API |
| **Celery** | Requires Redis or RabbitMQ broker. Three separate processes (worker, beat, broker). Massive operational overhead for periodic scraping of 5-10 sites. | **APScheduler 3.x** - in-process, zero external dependencies, dynamic job management |
| **Scrapy** | Built on Twisted (not asyncio), steep learning curve, designed for millions of pages. You're scraping 5-10 Vietnamese gold shop sites. | **httpx + BeautifulSoup** for static pages, **Playwright** for JS-heavy pages |
| **Streamlit** | Great for prototyping but forces a specific architecture. Hard to customize, can't control HTTP endpoints, poor for production dashboards. Not designed for APIs. | **FastAPI + Jinja2 templates** - full control, production-ready, serves both API and HTML |
| **Next.js / React** | Adds TypeScript/Node.js to a Python project. Build step, state management, API layer duplication. Overkill for a financial dashboard. | **Jinja2 + HTMX + Chart.js** - stays in Python, minimal JS, progressive enhancement |
| **APScheduler 4.x** | Still in alpha (4.0.0a6, April 2025). Official warning: "DO NOT use in production." Breaking changes between alpha releases. | **APScheduler 3.11.2** - stable, well-documented, proven in production |
| **Flask** | Synchronous by default. No built-in async support (without significant workarounds). No automatic API docs. | **FastAPI** - async-native, auto-docs, Pydantic integration, same learning curve |
| **MongoDB** | Schema-less is a liability for financial time-series data where structure matters. Weak aggregation compared to SQL for gap calculations, moving averages. | **SQLite + DuckDB** - structured schemas, SQL window functions, zero config |
## Stack Patterns by Variant
- Use httpx + BeautifulSoup + lxml parser
- Add `selectolax` if parsing performance becomes a bottleneck (30x faster than BS4)
- This covers SJC.com.vn, PNJ.com.vn, State Bank pages
- Use Playwright async API with Chromium
- Run headless, add retry logic for flaky pages
- Cache pages locally before parsing (resilience against structure changes)
- This likely covers Doji and some dealer sites
- Add random delays between requests (1-3 seconds)
- Rotate User-Agent headers
- Use `curl_cffi` (TLS fingerprint spoofing) if basic header rotation fails
- Last resort: use a scraping proxy service (ScrapingBee, Bright Data)
- Replace direct OpenAI SDK with **LiteLLM** (unified interface for OpenAI, Anthropic, Gemini, local models)
- LiteLLM translates provider differences into a single OpenAI-compatible API
- Migrate to PostgreSQL using `sqlalchemy` - zero code changes to queries
- Add `timescaledb` extension for time-series specific optimizations
- Keep DuckDB for analytical queries (it can query PostgreSQL directly)
## Version Compatibility
| Package A | Compatible With | Notes |
|-----------|-----------------|-------|
| FastAPI 0.115+ | Python 3.12+, Pydantic 2.10+, Starlette 0.40+ | FastAPI pins its Pydantic dependency; don't override |
| SQLAlchemy 2.0+ | Python 3.10+, Alembic 1.13+ | Use 2.0-style Mapped declarations, not legacy |
| APScheduler 3.11.2 | Python 3.9+, SQLAlchemy 1.4+ (for job stores) | Stay on 3.x branch; 4.x is alpha |
| python-telegram-bot 22.x | Python 3.9+, httpx 0.27+ | Uses httpx internally for API calls |
| openai 1.68+ | Python 3.8+, httpx 0.25+, Pydantic 2.0+ | SDK v1.x uses httpx for transport |
| Playwright 1.49+ | Python 3.8+ | Install browser binaries separately: `playwright install` |
| httpx 0.28+ | Python 3.8+, httpcore 1.0+ | Used by multiple libraries above; pin a compatible version |
| pandas 2.2+ | Python 3.10+, numpy 1.22+ | 2.x required for modern time-series features |
## Architecture Overview
### Data Flow
## Deployment Notes
| Concern | Approach | Notes |
|---------|----------|-------|
| **Development** | `uvicorn app:app --reload` | Hot reload, single process |
| **Production** | `uvicorn app:app --workers 2` with systemd or Docker | 2 workers sufficient for this scale |
| **Process Manager** | systemd unit file (Linux VPS) | Simplest option for a single-server deploy. Docker Compose if you prefer containerization. |
| **Reverse Proxy** | Caddy or nginx | Caddy auto-handles HTTPS (Let's Encrypt). |
| **Environment** | `.env` file + pydantic-settings | API keys, DB paths, Telegram tokens. Never commit `.env`. |
| **Database Backup** | SQLite file copy + cron | `cp gold_advisor.db gold_advisor_$(date +%Y%m%d).db` |
| **Monitoring** | Simple health endpoint + log file | `/health` returns 200 if scheduler is running and last scrape < 30 min ago |
## Sources
- Context7: `/websites/fastapi_tiangolo` — FastAPI background tasks, middleware, lifespan events, CORS
- Context7: `/websites/playwright_dev_python` — Playwright async API, browser context, page interaction
- Context7: `/websites/pandas_pydata` — Time-series resampling, rolling windows, aggregation
- Context7: `/agronholm/apscheduler` — APScheduler 3.x + 4.x alpha, FastAPI integration, cron triggers
- Context7: `/openai/openai-python` — OpenAI SDK structured output, streaming, Pydantic parsing
- Context7: `/encode/httpx` — HTTPX async client, retries, timeout handling, error hierarchy
- Context7: `/websites/duckdb_stable` — DuckDB window functions, moving averages, time-series SQL
- Context7: `/python-telegram-bot/python-telegram-bot` — Telegram bot v22.x API
- PyPI: `APScheduler` — Version 3.11.2 stable, 4.0.0a6 alpha warning verified
- PyPI: `python-zalo-bot` — Zalo bot SDK v0.1.9 (unofficial)
- WebSearch: "Best Python Web Scraping Libraries 2026" — httpx+BS4 recommended for static, Playwright for dynamic (multiple sources agree)
- WebSearch: "APScheduler vs Celery Beat 2025" — APScheduler recommended for single-process scheduling (multiple sources agree)
- WebSearch: "Zalo OA API Python wrapper" — Direct httpx to Zalo OA REST API is the most reliable approach
- MEDIUM confidence: Vietnamese gold shop website structure (assumed mix of static/dynamic based on typical Vietnamese e-commerce patterns — validate during Phase 1)
- LOW confidence: Zalo OA API rate limits and approval process (unofficial documentation only — validate during Phase 2)
<!-- GSD:stack-end -->

<!-- GSD:conventions-start source:CONVENTIONS.md -->
## Conventions

Conventions not yet established. Will populate as patterns emerge during development.
<!-- GSD:conventions-end -->

<!-- GSD:architecture-start source:ARCHITECTURE.md -->
## Architecture

Architecture not yet mapped. Follow existing patterns found in the codebase.
<!-- GSD:architecture-end -->

<!-- GSD:workflow-start source:GSD defaults -->
## GSD Workflow Enforcement

Before using Edit, Write, or other file-changing tools, start work through a GSD command so planning artifacts and execution context stay in sync.

Use these entry points:
- `/gsd:quick` for small fixes, doc updates, and ad-hoc tasks
- `/gsd:debug` for investigation and bug fixing
- `/gsd:execute-phase` for planned phase work

Do not make direct repo edits outside a GSD workflow unless the user explicitly asks to bypass it.
<!-- GSD:workflow-end -->



<!-- GSD:profile-start -->
## Developer Profile

> Profile not yet configured. Run `/gsd:profile-user` to generate your developer profile.
> This section is managed by `generate-claude-profile` -- do not edit manually.
<!-- GSD:profile-end -->
