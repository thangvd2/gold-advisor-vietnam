# Gold Advisor Vietnam

AI-powered gold price advisor for Vietnamese physical gold buyers and sellers.

## Overview

Gold Advisor Vietnam is an advisory agent that helps Vietnamese users time their physical gold purchases and sales. It tracks SJC gold bars and ring gold (nhẫn trơn) prices from multiple dealers, analyzes the gap between domestic and international gold prices alongside macro signals and seasonal patterns, and delivers buy/hold/sell recommendations through a web dashboard and Telegram alerts. This is an advice-only tool, no transactions are executed.

## Features

- Multi-source gold price tracking from SJC, PNJ, Doji, Phú Quý, BTMC, and YFinance (international)
- Deterministic signal engine analyzing SJC-international gold gap, USD/VND FX rate, XAU/USD trend, dealer spread, seasonal patterns, and State Bank policy
- AI-powered advisory via GLM-5-turbo (Z.ai) with the AgentScope framework
- Web dashboard with live price table, price history charts, gap tracking, and market news
- Telegram bot for price updates (`/update`) and price comparison (`/price`)
- Ring gold manual input from your local store (Tiệm vàng gần nhà)
- Vietnam timezone (UTC+7) throughout the UI and Telegram
- All data stored locally in SQLite, no cloud dependencies

## Architecture

```
Scrapers (SJC, PNJ, Doji, Phú Quý, BTMC)
    │
Fetchers (YFinance gold, DXY, Vietcombank FX)
    │
Normalizer → SQLite (price_history)
    │
Signal Engine (deterministic, multi-factor)
    │
    ├── Web Dashboard (FastAPI + Jinja2 + Chart.js)
    └── Telegram Bot (python-telegram-bot)
        │
    AI Advisor (AgentScope + GLM-5-turbo)
```

Price data flows from scrapers and fetchers into a normalizer, gets stored in SQLite, then feeds the deterministic signal engine. Results surface through the web dashboard and Telegram bot. The AI advisor layer generates natural-language recommendations on top of the signal data.

## Tech Stack

| Layer | Technologies |
|-------|-------------|
| **Backend** | Python 3.12+, FastAPI, SQLAlchemy 2.0, APScheduler 3.x |
| **Data** | SQLite, DuckDB (analytical queries), pandas |
| **Frontend** | Jinja2, HTMX, Chart.js, Tailwind CSS |
| **AI** | AgentScope, OpenAI SDK (GLM-5-turbo via Z.ai) |
| **Messaging** | python-telegram-bot |
| **Data Sources** | httpx + BeautifulSoup4, YFinance, Playwright (fallback) |

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
python main.py

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
| `FETCH_INTERVAL_MINUTES` | Price fetch interval | `5` |
| `FRESHNESS_THRESHOLD_MINUTES` | Max age before data is considered stale | `15` |
| `ANOMALY_THRESHOLD_PERCENT` | Price jump that triggers an anomaly alert | `10.0` |
| `TELEGRAM_BOT_TOKEN` | Telegram bot token from @BotFather | — |
| `OPENAI_API_KEY` | Z.ai API key (GLM-5-turbo) | — |
| `OPENAI_MODEL_NAME` | LLM model name | `glm-5-turbo` |
| `OPENAI_BASE_URL` | LLM API endpoint | `https://api.z.ai/api/coding/paas/v4` |
| `GOLDAPI_KEY` | GoldAPI key for supplementary data | — |

## Telegram Bot Commands

| Command | Description |
|---|---|
| `/update <buy> <sell> [date] [time]` | Update local ring gold prices (e.g. `/update 175000 176500`) |
| `/price` | Compare local prices with dealer ring gold prices |
| `/signal` | Get current buy/hold/sell signal analysis |

## Project Structure

```
src/
├── advisor/         # AI advisory agent (AgentScope + GLM-5-turbo)
├── alerts/          # Telegram bot
├── analysis/        # Price history, gap analysis, macro signals
├── api/             # FastAPI routes and main app
├── config.py        # App configuration (pydantic-settings)
├── engine/          # Deterministic signal engine
├── ingestion/       # Scrapers, fetchers, normalizer, scheduler
└── storage/         # SQLAlchemy models, database init
```

## License

MIT
