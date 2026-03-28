# Gold Advisor Vietnam

AI-powered gold price advisor for Vietnamese physical gold buyers and sellers.

## Overview

Gold Advisor Vietnam is an advisory agent that helps Vietnamese users time their physical gold purchases and sales. It tracks SJC gold bars and ring gold (nhẫn trơn) prices from multiple dealers, analyzes the gap between domestic and international gold prices alongside macro signals and seasonal patterns, and delivers buy/hold/sell recommendations through a web dashboard and Telegram alerts. This is an advice-only tool, no transactions are executed.

## Features

- Multi-source gold price tracking from 6 dealers: SJC, PNJ, Doji, Phú Quý, BTMC, Kim Phát
- International gold (XAU/USD), DXY index, USD/VND FX rate via YFinance + Vietcombank
- CME FedWatch — market-implied Fed rate from ZQ futures
- Polymarket prediction market monitoring — Gold & Macro events on dashboard, full Market Movers on dedicated page
- Kim Phát auto-scraper for ring gold (nhẫn trơn 99.99%) prices, stored as local store data
- Deterministic signal engine with 8 factors: SJC-international gold gap, USD/VND FX rate, XAU/USD trend, dealer buy-sell spread, local store spread, gap trend, seasonal patterns, and State Bank policy
- GLM-5-turbo powered bilingual (EN+VN) signal explanations — compact reasoning on the signal card and detailed per-section analysis in the full report
- Detailed signal report page with analysis for all 8 factors plus final recommendation
- EN/VN language toggle across all dashboard pages
- Web dashboard with live price table, price history charts, gap tracking, and market news
- Telegram bot for price updates (`/update`) and price comparison (`/price`)
- Ring gold manual input from your local store (Tiệm vàng gần nhà) via Telegram `/update` command
- Manual `/update` overrides auto-scrape for 20 minutes (backdated updates don't block auto-scrape)
- Vietnam timezone (UTC+7) throughout the UI and Telegram
- All data stored locally in SQLite, no cloud dependencies

## Architecture

```
Scrapers (SJC, PNJ, Doji, Phú Quý, BTMC, Kim Phát)
    │
Fetchers (YFinance gold/DXY/FedWatch, Vietcombank FX, Polymarket)
    │
Normalizer → SQLite (price_history)
    │
Signal Engine (deterministic, 8-factor)
    │
    ├── Web Dashboard (FastAPI + Jinja2 + HTMX + Chart.js)
    │       ├── Signal card (compact LLM reasoning, EN+VN)
    │       ├── FedWatch card (market-implied Fed rate)
    │       ├── Polymarket card (Gold & Macro events)
    │       └── Report page (detailed LLM analysis, EN+VN)
    ├── Polymarket Page (Market Movers + future smart money detection)
    └── Telegram Bot (python-telegram-bot)
            │
        AI Advisor (AgentScope + GLM-5-turbo)
```

Price data flows from scrapers and fetchers into a normalizer, gets stored in SQLite, then feeds the deterministic signal engine (8 factors). The signal is enriched with GLM-5-turbo generated bilingual explanations for both the compact signal card and the full detailed report. Results surface through the web dashboard and Telegram bot. The AI advisor layer generates natural-language recommendations on top of the signal data.

## Data Sources

### Gold Price Scrapers (every 5 min)

| Dealer | URL | Method | Products |
|--------|-----|--------|----------|
| SJC | `sjc.com.vn` | JSON API | SJC bar, ring gold |
| PNJ | `pnj.com.vn` | REST API + HTML fallback | SJC bar, ring gold |
| Doji | `giavang.doji.vn` | HTML scrape | SJC bar, ring gold |
| Phú Quý | `phuquygroup.vn` | HTML scrape | SJC bar, ring gold |
| BTMC | `btmc.vn/Home/BGiaVang` | HTML scrape | SJC bar, ring gold |
| Kim Phát | `kimphat.evosoft.vn` | HTML scrape | Ring gold (→ stored as local) |

### International Price & FX (every 5 min)

| Source | Ticker / URL | Method |
|--------|-------------|--------|
| XAU/USD (international gold) | YFinance `GC=F` | yfinance |
| DXY (USD index) | YFinance `^DXY` | yfinance |
| USD/VND FX rate | `vietcombank.com.vn/api/exrates/usd` + YFinance `USDVND=X` fallback | REST API + yfinance |

### Macro Monitoring (every 30 min)

| Source | Ticker / URL | Method |
|--------|-------------|--------|
| CME FedWatch | YFinance `ZQ=F` (front-month futures) | yfinance |
| Polymarket | `gamma-api.polymarket.com/events` | REST API |

### News Feeds (every 30 min)

| Source | URL |
|--------|-----|
| Tuổi Trẻ | `tuoitre.vn/rss/kinh-doanh.rss` |
| VNExpress | `vnexpress.net/rss/kinh-doanh.rss` |
| NYT Business | `rss.nytimes.com/services/xml/rss/nyt/Business.xml` |

## Signal Factors

| Factor | Weight | What It Measures |
|--------|--------|------------------|
| **Domestic-International Gap** | 0.20 | SJC sell price vs international gold price in VND |
| **USD/VND FX Rate** | 0.10 | Vietnamese dong strength vs US dollar |
| **Gold Trend (XAU/USD)** | 0.10 | Global gold price momentum |
| **Dealer Buy-Sell Spread** | 0.10 | Wholesale market liquidity indicator |
| **Local Store Spread** | 0.20 | Your store's buy-sell spread vs dealer spread |
| **Gap Trend** | 0.10 | 7-day vs 30-day gap direction (widening/narrowing) |
| **Seasonal Pattern** | 0.00 | Historical monthly demand (adjusts confidence only) |
| **State Bank Policy** | Override | Regulatory interventions override all other signals |

Signal modes: **Saver** (conservative, favors HOLD) and **Trader** (responsive, favors BUY/SELL).

## Quick Start

```bash
# Prerequisites: Python 3.12+, uv package manager
git clone https://github.com/thangvd2/gold-advisor-vietnam.git
cd gold-advisor-vietnam

# Install dependencies
uv sync

# Configure environment
cp .env.example .env
# Edit .env: set OPENAI_API_KEY (Z.ai/GLM key), TELEGRAM_BOT_TOKEN

# Start the server
uv run uvicorn src.api.main:app --reload
```

Open http://localhost:8000 to view the dashboard.

## Environment Variables

| Variable | Description | Default |
|---|---|---|
| `APP_NAME` | Application name | `gold_advisor` |
| `DATABASE_URL` | SQLite database path | `sqlite+aiosqlite:///./gold_advisor.db` |
| `LOG_LEVEL` | Logging level | `INFO` |
| `FETCH_INTERVAL_MINUTES` | Price fetch/scrape interval | `5` |
| `NEWS_FETCH_INTERVAL_MINUTES` | News feed fetch interval | `30` |
| `FEDWATCH_FETCH_INTERVAL_MINUTES` | FedWatch fetch interval | `30` |
| `POLYMARKET_FETCH_INTERVAL_MINUTES` | Polymarket fetch interval | `30` |
| `FRESHNESS_THRESHOLD_MINUTES` | Max age before data is considered stale | `15` |
| `ANOMALY_THRESHOLD_PERCENT` | Price jump that triggers an anomaly alert | `10.0` |
| `TELEGRAM_BOT_TOKEN` | Telegram bot token from @BotFather | — |
| `OPENAI_API_KEY` | Z.ai API key (GLM-5-turbo) | — |
| `OPENAI_MODEL_NAME` | LLM model name | `glm-5-turbo` |
| `OPENAI_BASE_URL` | LLM API endpoint | `https://api.z.ai/api/coding/paas/v4` |

## Telegram Bot Commands

| Command | Description |
|---|---|
| `/update <buy> <sell> [date] [time]` | Update local ring gold prices (e.g. `/update 175000 176500`) |
| `/update <buy> <sell> <YYYY-MM-DD> <HH:MM>` | Update with specific date/time |
| `/price` | Compare local prices with dealer ring gold prices |
| `/signal` | Get current buy/hold/sell signal analysis |
| `/history` | View ring gold price history grouped by price change |

## Dashboard Pages

| Page | URL | Description |
|------|-----|-------------|
| **Main Dashboard** | `/` | Price table, signal card, charts, news, FedWatch, Polymarket Gold & Macro |
| **Signal Report** | `/dashboard/report?mode=saver` | Detailed LLM-powered analysis of all 8 factors |
| **Prices** | `/dashboard/prices` | Live dealer price comparison |
| **Macro** | `/dashboard/macro` | FX rate and gold trend data |
| **News** | `/dashboard/news` | Market news from Tuổi Trẻ, VNExpress, NYT |
| **Prediction Markets** | `/dashboard/polymarket` | Polymarket Market Movers + future smart money detection |

## Project Structure

```
src/
├── advisor/              # AI advisory agent (AgentScope + GLM-5-turbo)
├── alerts/               # Telegram bot
├── analysis/             # Price history, gap analysis, macro signals
├── api/                  # FastAPI routes and main app
├── config.py             # App configuration (pydantic-settings)
├── engine/               # Signal engine
│   ├── composite.py      # Composite signal computation
│   ├── gap_signal.py     # Domestic-international gap factor
│   ├── fx_signal.py      # USD/VND FX factor
│   ├── gold_signal.py    # XAU/USD trend factor
│   ├── dealer_spread.py  # Dealer spread factor
│   ├── local_spread_signal.py  # Local store spread factor
│   ├── local_trend_signal.py   # Local store trend factor
│   ├── gap_trend_signal.py     # Gap trend factor
│   ├── seasonal_signal.py      # Seasonal pattern factor
│   ├── policy_signal.py        # State Bank policy override
│   ├── pipeline.py      # Signal computation pipeline
│   ├── reasoning.py     # Deterministic bilingual reasoning (fallback)
│   ├── llm_reasoning.py # GLM-5-turbo bilingual report generation
│   ├── modes.py         # Saver/Trader mode configuration
│   └── types.py         # Signal, SignalFactor, SignalMode types
├── ingestion/            # Scrapers, fetchers, normalizer, scheduler
│   ├── scrapers/         # SJC, PNJ, Doji, Phú Quý, BTMC, Kim Phát
│   ├── fetchers/         # YFinance gold/DXY/FedWatch, Vietcombank FX, Polymarket
│   ├── polymarket/       # Polymarket significant move monitor
│   └── news/             # RSS news parser (Tuổi Trẻ, VNExpress, NYT)
└── storage/              # SQLAlchemy models, database init
templates/
├── base.html             # Base layout with nav bar and EN/VN toggle
├── report.html           # Detailed signal report page
├── polymarket.html       # Polymarket dedicated page (Market Movers)
└── partials/             # HTMX partials for dashboard sections
```

## License

MIT
