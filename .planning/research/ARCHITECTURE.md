# Architecture Research

**Domain:** AI-powered financial advisory system (Vietnamese gold market)
**Researched:** 2026-03-25
**Confidence:** MEDIUM-HIGH

## Standard Architecture

### System Overview

```
┌─────────────────────────────────────────────────────────────────────┐
│                      PRESENTATION LAYER                             │
├──────────────────────┬──────────────────┬──────────────────────────┤
│  Web Dashboard       │  Telegram Bot    │  Zalo OA Bot (Phase 2)   │
│  (Next.js)           │  (python-tg-bot) │  (Zalo OA API)           │
└──────────┬───────────┴────────┬─────────┴────────────┬─────────────┘
           │                    │                       │
┌──────────┴────────────────────┴───────────────────────┴─────────────┐
│                         API LAYER                                   │
│                    (FastAPI / REST)                                  │
├─────────────────────────────────────────────────────────────────────┤
│  ┌──────────────┐ ┌──────────────┐ ┌──────────────┐                │
│  │ Price API    │ │ Signal API   │ │ Alert API    │                │
│  │ /prices      │ │ /signals     │ │ /alerts      │                │
│  │ /history     │ │ /analysis    │ │ /subscribe   │                │
│  └──────┬───────┘ └──────┬───────┘ └──────┬───────┘                │
└─────────┼────────────────┼────────────────┼────────────────────────┘
          │                │                │
┌─────────┴────────────────┴────────────────┴────────────────────────┐
│                      CORE ENGINE LAYER                              │
├──────────────────────┬──────────────────┬──────────────────────────┤
│  Signal Engine       │ LLM Advisory     │ Alert Dispatcher         │
│  - Gap calculator    │   Layer           │ - Threshold rules        │
│  - Spread tracker    │ - Prompt builder  │ - Template formatter      │
│  - Macro scorer      │ - Signal→narrative│ - Channel router         │
│  - Seasonal adjuster │ - Confidence eval │ - Rate limiter           │
│  - Composite scorer  │                   │                          │
└──────────┬───────────┴────────┬─────────┴────────────┬─────────────┘
           │                    │                       │
┌──────────┴────────────────────┴───────────────────────┴─────────────┐
│                   DATA INGESTION LAYER                              │
├──────────────────────┬──────────────────┬──────────────────────────┤
│  Scraper Workers     │  API Fetchers    │  Normalizer              │
│  - SJC scraper       │  - Kitco/XAU     │  - Standardize schema     │
│  - DOJI scraper      │  - USD/VND rate  │  - Validate ranges        │
│  - PNJ scraper       │  - Metals API    │  - Dedup                  │
│  - BTMC scraper      │  - (future APIs) │  - Timestamp normalize    │
│  - State Bank        │                  │                          │
└──────────┬───────────┴────────┬─────────┴────────────┬─────────────┘
           │                    │                       │
┌──────────┴────────────────────┴───────────────────────┴─────────────┐
│                      SCHEDULER                                      │
│                  (APScheduler)                                      │
│  - Every 5 min:  scrape domestic prices                            │
│  - Every 10 min: fetch international prices                        │
│  - Every 10 min: run signal engine                                 │
│  - On signal change: check alert thresholds → dispatch             │
└──────────┬──────────────────────────────────────────────────────────┘
           │
┌──────────┴──────────────────────────────────────────────────────────┐
│                    DATA LAYER                                       │
├──────────────────────┬──────────────────┬──────────────────────────┤
│  SQLite / PostgreSQL │  Redis (opt.)    │  File storage            │
│  - price_history     │  - Latest prices  │  - Chart images           │
│  - signal_history    │  - Alert cache    │  - Export CSV             │
│  - alert_log         │  - Rate limits    │                          │
│  - user_subscribers  │                  │                          │
└──────────────────────┴──────────────────┴──────────────────────────┘
```

### Component Responsibilities

| Component | Responsibility | Typical Implementation |
|-----------|----------------|------------------------|
| **Scraper Workers** | Fetch HTML from SJC, DOJI, PNJ, BTMC websites; parse buy/sell prices for SJC bars and nhẫn trơn | Python + requests/Playwright + BeautifulSoup; per-shop adapters |
| **API Fetchers** | Call external REST APIs for international gold (XAU/USD), USD/VND exchange rate | Python requests with retry/backoff; adapter pattern per API |
| **Normalizer** | Transform raw scraped/API data into a unified PriceRecord schema; validate ranges, dedup, normalize timestamps | Pure Python functions; pydantic models for validation |
| **Scheduler** | Trigger ingestion, signal computation, and alert dispatch at configured intervals | APScheduler (in-process) or Celery Beat (if distributed needed) |
| **Signal Engine** | Compute SJC-international gap, buy/sell spreads, macro scores, seasonal adjustments; produce composite signal with confidence | Pure Python; no LLM needed — deterministic computation |
| **LLM Advisory Layer** | Convert numeric signal data + context into human-readable Vietnamese-language buy/hold/sell narrative with reasoning | Single LLM call (OpenAI/Anthropic) with structured prompt; not multi-agent for MVP |
| **Alert Dispatcher** | Compare current signals against user thresholds; format alert messages; route to Telegram/Zalo | Rule-based threshold checker + message templates + channel adapters |
| **Web Dashboard** | Display current prices, gap tracker, signal status, macro snapshot, historical charts | Next.js or React frontend fetching from API layer |
| **Telegram Bot** | Receive commands (/start, /status, /subscribe); push alerts to subscribed users | python-telegram-bot library; webhook mode in production |
| **API Layer** | REST endpoints for dashboard consumption and bot integration | FastAPI with async support |
| **Database** | Persist price history, signal snapshots, alert logs, user subscriptions | SQLite for MVP, PostgreSQL for scale |

## Recommended Project Structure

```
gold_invester/
├── src/
│   ├── ingestion/              # Data collection from external sources
│   │   ├── scrapers/           # Web scrapers for VN gold shops
│   │   │   ├── base.py         # BaseScraper class (retry, parse, error handling)
│   │   │   ├── sjc.py          # SJC.com.vn scraper
│   │   │   ├── doji.py         # DOJI scraper
│   │   │   ├── pnj.py          # PNJ scraper
│   │   │   └── btmc.py         # Bao Tin Minh Chu scraper
│   │   ├── fetchers/           # API clients for international data
│   │   │   ├── base.py         # BaseFetcher class
│   │   │   ├── kitco.py        # International gold price (XAU/USD)
│   │   │   ├── fx_rate.py      # USD/VND exchange rate
│   │   │   └── metals_api.py   # Alternative metal price source
│   │   ├── normalizer.py       # Unified PriceRecord schema + validation
│   │   └── scheduler.py        # APScheduler job definitions
│   ├── engine/                 # Signal computation (deterministic, no LLM)
│   │   ├── gap.py              # SJC-international gap calculator
│   │   ├── spread.py           # Buy/sell spread tracker
│   │   ├── macro.py            # Macro indicator scorer (rates, FX, trend)
│   │   ├── seasonal.py         # Vietnamese seasonal demand patterns
│   │   ├── composite.py        # Multi-signal aggregation + confidence
│   │   └── types.py            # Signal, Confidence, Recommendation enums
│   ├── advisor/                # LLM-powered narrative generation
│   │   ├── prompt_builder.py   # Construct prompt from signal data
│   │   ├── llm_client.py       # LLM API wrapper (OpenAI/Anthropic)
│   │   └── renderer.py         # Parse LLM response → structured recommendation
│   ├── alerts/                 # Alert dispatch system
│   │   ├── dispatcher.py       # Check thresholds → trigger alerts
│   │   ├── templates.py        # Message templates (Telegram, Zalo)
│   │   └── channels/           # Channel-specific senders
│   │       ├── telegram.py     # Telegram Bot API integration
│   │       └── zalo.py         # Zalo OA API integration (Phase 2)
│   ├── api/                    # FastAPI application
│   │   ├── main.py             # FastAPI app factory
│   │   ├── routes/
│   │   │   ├── prices.py       # GET /prices, /prices/history
│   │   │   ├── signals.py      # GET /signals, /signals/latest
│   │   │   └── alerts.py       # POST /alerts/subscribe, GET /alerts/log
│   │   └── dependencies.py     # Shared dependencies (db, scheduler)
│   ├── storage/                # Database layer
│   │   ├── models.py           # SQLAlchemy/SQLModel table definitions
│   │   ├── repository.py       # CRUD operations
│   │   └── migrations/         # Alembic migrations
│   ├── dashboard/              # Web frontend (Next.js or React)
│   │   ├── pages/
│   │   ├── components/
│   │   └── lib/
│   └── config.py               # Centralized configuration
├── tests/
├── docs/
├── alembic.ini
├── pyproject.toml
└── README.md
```

### Structure Rationale

- **ingestion/:** Separates data collection from data processing. Each scraper is an independent adapter — if SJC changes their HTML, only `sjc.py` breaks. The base class provides retry, timeout, and error handling so each adapter focuses on parsing only.
- **engine/:** Pure deterministic computation, no external dependencies or LLM calls. This is the "brain" — it should be fast, testable, and reliable. Separating it from `advisor/` means signals work even if the LLM is down.
- **advisor/:** LLM layer is isolated. The prompt builder converts structured signal data into a prompt; the LLM client is swappable; the renderer parses the response. This separation means you can swap models (OpenAI → Claude → local) without touching the engine.
- **alerts/:** Dispatching is separate from generation. The dispatcher uses rules (not AI) to decide when to alert. Channel adapters handle Telegram/Zalo specifics.
- **api/:** Thin REST layer. No business logic — it delegates to engine, advisor, and storage.

## Architectural Patterns

### Pattern 1: Adapter Pattern for Data Sources

**What:** Each data source (SJC, DOJI, Kitco, etc.) implements a common `DataSource` interface. The scheduler calls `source.fetch()` without knowing implementation details.

**When to use:** Every data source has different HTML structure, API format, rate limits, and error modes. Adapters isolate this complexity.

**Trade-offs:** Slightly more upfront code (one file per source), but zero blast radius when a single source changes.HIGH confidence — this is standard practice in financial data systems.

**Example:**
```python
from abc import ABC, abstractmethod
from dataclasses import dataclass
from datetime import datetime

@dataclass
class PriceRecord:
    source: str          # "sjc", "doji", "kitco", etc.
    product_type: str    # "sjc_bar", "nhan_tron", "xau_usd"
    buy_price: float | None
    sell_price: float | None
    timestamp: datetime

class DataSource(ABC):
    @abstractmethod
    async def fetch(self) -> list[PriceRecord]:
        """Fetch latest prices. Return list of normalized records."""
        ...

class SJCScraper(DataSource):
    async def fetch(self) -> list[PriceRecord]:
        # Scrape sjc.com.vn, parse HTML, return PriceRecords
        ...
```

### Pattern 2: Pipeline Pattern for Signal Computation

**What:** Data flows through a sequence of deterministic computation stages: raw prices → gap calculation → spread analysis → macro scoring → seasonal adjustment → composite signal. Each stage takes structured input and produces structured output.

**When to use:** Signal computation is a linear data transformation pipeline. Each stage is independently testable. Stages can be added/removed/reordered without affecting others.

**Trade-offs:** Less flexible than a DAG (no branching), but gold signal computation is inherently sequential — gap depends on prices, composite depends on all sub-signals. HIGH confidence — the modular quant trading architecture literature (Chatterjee 2025, Algovantis 2026) consistently recommends layered pipelines.

**Example:**
```python
@dataclass
class SignalResult:
    recommendation: str    # "buy", "hold", "sell"
    confidence: float      # 0.0 - 1.0
    gap_signal: float      # SJC-international gap score
    spread_signal: float   # Buy/sell spread score
    macro_signal: float    # Macro indicator score
    seasonal_signal: float # Seasonal demand score
    narrative: str | None  # LLM-generated explanation
    timestamp: datetime

def compute_signal(
    domestic_prices: list[PriceRecord],
    intl_price: PriceRecord,
    fx_rate: float,
    historical_prices: list[PriceRecord],
) -> SignalResult:
    gap_score = calculate_gap(domestic_prices, intl_price, fx_rate)
    spread_score = calculate_spread(domestic_prices)
    macro_score = calculate_macro(fx_rate, intl_price)
    seasonal_score = calculate_seasonal(datetime.now())
    composite = aggregate_signals(gap_score, spread_score, macro_score, seasonal_score)
    return SignalResult(
        recommendation=composite.recommendation,
        confidence=composite.confidence,
        gap_signal=gap_score,
        spread_signal=spread_score,
        macro_signal=macro_score,
        seasonal_signal=seasonal_score,
    )
```

### Pattern 3: Single LLM Call for Advisory (Not Multi-Agent)

**What:** The signal engine produces structured numeric data. A single LLM call converts this data into a Vietnamese-language narrative explaining the recommendation. No multi-agent orchestration, no chain-of-thought loops, no agent debates.

**When to use:** The advisory problem here is narrative generation from structured data — not multi-source reasoning. Multi-agent architectures (FINCON, AlphaSwarm, AI NeuroSignal) are designed for systems that need to synthesize 10-47 independent data sources with conflicting signals. This system has ~5 well-defined numeric inputs.

**Trade-offs:** Less "intelligent" than multi-agent, but dramatically simpler, cheaper, faster, and more predictable. A single GPT-4-mini or Claude Haiku call costs <0.01 USD per analysis. Multi-agent systems cost 10-100x more and add failure modes (token exhaustion, agent coordination, inconsistent outputs).

**Why not multi-agent:** Research from Devarshi Vyas (2026) shows ReAct agents are "token-expensive by design" and recommends "only use LLMs where genuine reasoning is needed." Formatting a structured recommendation is not reasoning — it's templating with flair. Mehul Thakkar's 47-agent system (2026) is appropriate for institutional stock analysis across 47 data sources; it is massive overkill for 5 numeric signals about one commodity in one country.

**Confidence:** MEDIUM-HIGH — this recommendation is based on matching architecture complexity to problem complexity. Start simple; add multi-agent only if the single-call narrative is insufficient.

**Example:**
```python
def build_advisory_prompt(signal: SignalResult, prices: PriceSnapshot) -> str:
    return f"""You are a gold investment advisor for Vietnamese investors.

Based on the following analysis data, provide a concise buy/hold/sell recommendation 
for SJC gold bars and nhẫn trơn (plain gold rings). Write in Vietnamese.

## Current Data
- SJC bar price: {prices.sjc_bar_sell:,.0f} VND/lượng (buy: {prices.sjc_bar_buy:,.0f})
- Nhẫn trơn price: {prices.nhan_tron_sell:,.0f} VND/lượng (buy: {prices.nhan_tron_buy:,.0f})
- International gold: {prices.xau_usd:,.2f} USD/oz
- USD/VND rate: {prices.usd_vnd:,.0f}
- SJC-international gap: {signal.gap_signal:+.1%} (positive = SJC is expensive)
- Buy/sell spread: {signal.spread_signal:,.0f} VND/lượng
- Macro score: {signal.macro_signal:.2f}/10
- Seasonal factor: {signal.seasonal_signal} ({get_season_context()})

## Signal Engine Output
- Recommendation: {signal.recommendation.upper()}
- Confidence: {signal.confidence:.0%}

Provide a 3-4 sentence explanation in Vietnamese covering:
1. What the gap means for timing
2. Key risk factors
3. Actionable advice for savers vs active investors

End with a disclaimer that this is not financial advice."""

# Single LLM call — not a multi-agent pipeline
def generate_advisory(signal: SignalResult, prices: PriceSnapshot) -> str:
    prompt = build_advisory_prompt(signal, prices)
    return llm_client.complete(prompt, model="gpt-4o-mini", max_tokens=500)
```

### Pattern 4: Threshold-Based Alert Dispatch

**What:** The alert dispatcher compares current signals against configurable thresholds (gap crosses X%, recommendation changes from hold→buy, etc.). When triggered, it formats a message using templates and sends via the appropriate channel.

**When to use:** Alerts need to be timely and reliable. Rule-based dispatch is deterministic, testable, and doesn't depend on LLM availability. The LLM advisory narrative can be attached to the alert but is not required for the alert to fire.

**Trade-offs:** Less "smart" than AI-driven alerting, but far more predictable. Users want to know "the gap just crossed 15%" — they don't need an AI to decide whether that's interesting.

**Example:**
```python
@dataclass
class AlertRule:
    name: str
    condition: Callable[[SignalResult, SignalResult | None], bool]
    template: str
    channels: list[str]  # ["telegram", "zalo"]

# Example rules
ALERT_RULES = [
    AlertRule(
        name="gap_spike",
        condition=lambda curr, prev: curr.gap_signal > 0.15 and (prev is None or prev.gap_signal <= 0.15),
        template="⚠️ GAP TĂNG CAO: Chênh lệch SJC-QT đạt {gap_signal:.1%}. Xem xét giảm mua.",
        channels=["telegram"],
    ),
    AlertRule(
        name="recommendation_change",
        condition=lambda curr, prev: prev is not None and curr.recommendation != prev.recommendation,
        template="🔄 TÍN HIỆU ĐỔI: {recommendation.upper()} (từ {prev_recommendation}). Conf: {confidence:.0%}",
        channels=["telegram"],
    ),
]
```

## Data Flow

### Primary Data Flow: Price → Signal → Advisory → User

```
[Scheduler triggers every 5-10 min]
    ↓
[Scraper Workers] ──→ [Normalizer] ──→ [Database: price_history]
[API Fetchers]    ──↗                      ↓
                                          ↓
[Scheduler triggers signal computation]
    ↓
[Signal Engine] ← reads latest prices from DB
    ├── Gap Calculator (domestic vs international, FX-adjusted)
    ├── Spread Tracker (buy-sell spread at each shop)
    ├── Macro Scorer (USD/VND trend, global gold trend)
    ├── Seasonal Adjuster (Tet, wedding season, Vu Lan)
    └── Composite Aggregator (weighted combination → recommendation)
    ↓
[Database: signal_history]
    ↓
[LLM Advisory Layer] ← reads latest signal + price context
    ├── Build prompt from structured data
    ├── Single LLM call (Vietnamese narrative)
    └── Parse response → attach to SignalResult
    ↓
[Alert Dispatcher] ← reads current + previous signal
    ├── Check threshold rules
    ├── If triggered → format message template
    ├── Attach LLM narrative
    └── Send via Telegram Bot API / Zalo OA API
    ↓
[Web Dashboard] ← polls API every 30-60 seconds
    ├── GET /api/prices/latest → price cards
    ├── GET /api/signals/latest → signal status
    ├── GET /api/prices/history?days=30 → gap chart
    └── GET /api/signals/history?days=30 → signal trend chart
```

### State Management

```
[Database (source of truth)]
    ↑ writes          ↓ reads
[Ingestion]      [API Layer]
    ↑ writes          ↓ reads
[Signal Engine]  [Dashboard / Bots]
    ↑ reads
[Historical data for backtesting & charts]
```

No complex state management needed. The database is the source of truth. Redis is optional — useful for caching the latest price snapshot to avoid DB hits on every API request, but not required for MVP.

### Key Data Flows

1. **Price Collection:** Scheduler → scrapers/fetchers → normalizer → DB. Runs every 5-10 minutes during VN trading hours (8:00-17:00 ICT).
2. **Signal Computation:** Scheduler → engine (reads latest prices from DB) → DB (writes signal snapshot). Runs after each price collection cycle.
3. **Advisory Generation:** Signal engine → LLM client → DB (attaches narrative to signal). Runs only when recommendation changes or confidence crosses threshold (to control LLM costs).
4. **Alert Dispatch:** Dispatcher (compares current vs previous signal from DB) → channel adapters. Runs after each signal computation.
5. **Dashboard Updates:** Dashboard polls API layer → API reads from DB. Dashboard is a pure consumer; it never triggers computation.

## Scaling Considerations

| Scale | Architecture Adjustments |
|-------|--------------------------|
| 1-10 users | Monolith: all components in one process. SQLite. APScheduler in-process. Single Telegram bot. No Redis. |
| 10-1,000 users | Add Redis for caching. PostgreSQL instead of SQLite. Consider separating API server from worker process. |
| 1,000+ users | Separate ingestion workers (Celery). CDN for dashboard assets. Rate limiting on API. Consider Zalo OA integration. |

### Scaling Priorities

1. **First bottleneck:** Scraper reliability. Vietnamese gold shop websites change HTML structure unpredictably. Invest in robust error handling, fallback scrapers, and monitoring before scaling users.
2. **Second bottleneck:** LLM API costs and latency. At 1,000+ users with frequent alerts, LLM calls add up. Mitigate by only generating narrative on signal changes (not every cycle) and caching generated narratives.

### Why Monolith First

This system serves a single country's single commodity market. The data volume is tiny (~10 price records per cycle, 50-100 cycles per day). There is no real-time exchange feed — prices update intermittently. There is no portfolio management or multi-user trading. A monolith is the correct starting architecture. The multi-agent, microservice architectures seen in the research (47-agent systems, distributed Kafka pipelines) are designed for institutional multi-asset trading — they would be architectural overkill here by 2-3 orders of magnitude.

## Anti-Patterns

### Anti-Pattern 1: Multi-Agent Overkill

**What people do:** Inspired by AlphaSwarm, FINCON, or AI NeuroSignal articles, build a multi-agent system with separate agents for gap analysis, macro analysis, seasonal analysis, etc.

**Why it's wrong:** These systems coordinate 10-47 data sources with conflicting signals requiring debate and reconciliation. This system has 5 numeric inputs feeding a deterministic pipeline. Multi-agent adds: coordination overhead, token costs (10-100x), latency (sequential agent calls), failure modes (agent timeout, context overflow), and debugging complexity.

**Do this instead:** Single deterministic signal engine (pure Python, no LLM) + single LLM call for narrative. Add agents only if the advisory quality is demonstrably insufficient.

### Anti-Pattern 2: Scraping Without Normalization

**What people do:** Each scraper returns data in its own format. The signal engine has source-specific parsing logic mixed with computation logic.

**Why it's wrong:** When a source changes its format, you break both data collection AND computation. Hard to add new sources. Hard to test computation independently.

**Do this instead:** Adapter pattern — each scraper returns a normalized `PriceRecord`. The normalizer validates and enforces a single schema. The engine only ever sees `PriceRecord` objects.

### Anti-Pattern 3: LLM in the Hot Path

**What people do:** Call the LLM on every scheduler cycle (every 5-10 minutes) to generate advisory, regardless of whether the signal changed.

**Why it's wrong:** LLM API calls cost money, add latency (1-5 seconds), and introduce a failure dependency. If the signal hasn't changed, the advisory will be nearly identical — you're paying for no new information.

**Do this instead:** Only call the LLM when: (a) the recommendation changes (buy→hold, hold→sell), (b) confidence crosses a significant threshold (e.g., ±10%), or (c) a user explicitly requests fresh analysis. Cache the last generated narrative and reuse it.

### Anti-Pattern 4: Real-Time Architecture for Intermittent Data

**What people do:** Build WebSocket connections, streaming APIs, Kafka queues — as if this were a stock exchange feed.

**Why it's wrong:** Vietnamese gold prices update intermittently from dealer websites, not from a continuous exchange. SJC updates prices maybe 5-10 times per day. There is no millisecond-level data. Real-time infrastructure adds complexity with zero benefit.

**Do this instead:** Poll on a schedule (APScheduler), store in a database, serve via REST API. The dashboard polls every 30-60 seconds. Alerts fire on threshold crossings. Simple, reliable, sufficient.

## Integration Points

### External Services

| Service | Integration Pattern | Notes |
|---------|---------------------|-------|
| sjc.com.vn | HTTP GET + HTML parse (BeautifulSoup) | Historical data at `/giavang/textContent.php`; may require fallback to mobile site |
| doji.vn | HTTP GET + HTML parse | Check if they have a JSON API endpoint first |
| pnj.com.vn | HTTP GET + HTML parse | PNJ often has JavaScript-rendered content — may need Playwright |
| btmc.vn | REST API (`api.btmc.vn`) | Has official JSON API — preferred over scraping |
| Kitco / Metals API | REST API | International XAU/USD spot price; check free tier limits |
| USD/VND rate | REST API (Vietcombank, VCB) | Available via multiple sources; cache for 10+ minutes |
| Telegram Bot API | HTTPS webhook | Use webhook mode in production; long-polling for dev |
| Zalo OA API | HTTPS webhook | Requires Zalo Official Account registration; OA Access Token management |
| OpenAI / Anthropic | HTTPS REST | Single call per advisory generation; implement retry with backoff |

### Internal Boundaries

| Boundary | Communication | Notes |
|----------|---------------|-------|
| ingestion ↔ engine | Database (price_history table) | Decoupled — engine reads latest prices, never calls scrapers directly |
| engine ↔ advisor | Direct function call (in-process) | Advisor receives SignalResult object; no IPC needed in monolith |
| engine ↔ alerts | Database (signal_history table) | Dispatcher reads current + previous signal to detect changes |
| api ↔ all internals | Direct imports (in-process) | API layer is a thin REST wrapper; no microservice boundaries |
| dashboard ↔ api | HTTP REST (polling) | Dashboard is a separate process (Next.js dev server); polls every 30-60s |

## Suggested Build Order

Build order follows the dependency graph. Each phase produces a testable, deployable increment.

```
Phase 1: Data Foundation
  ├── 1a. Storage layer (DB schema, models, repository)
  ├── 1b. Scraper for SJC (primary source, simplest HTML)
  ├── 1c. International price fetcher (Kitco/XAU)
  └── 1d. Normalizer + scheduler (APScheduler, run every 10 min)
  → Outcome: System collects and stores prices. No signals yet.

Phase 2: Signal Engine
  ├── 2a. Gap calculator (domestic vs international, FX-adjusted)
  ├── 2b. Spread tracker (buy-sell spread per shop)
  ├── 2c. Composite scorer (weighted combination)
  └── 2d. API endpoints (GET /prices, GET /signals)
  → Outcome: System computes buy/hold/sell signals. Viewable via API.

Phase 3: Presentation + Alerts
  ├── 3a. FastAPI server (production deployment)
  ├── 3b. Telegram bot (/status command, alert subscription)
  ├── 3c. Alert dispatcher (threshold rules + message templates)
  └── 3d. Web dashboard (price cards, gap chart, signal display)
  → Outcome: Users see prices and receive alerts. Full MVP.

Phase 4: Intelligence + Enrichment
  ├── 4a. Macro scorer (USD/VND trend, global gold trend)
  ├── 4b. Seasonal adjuster (Vietnamese demand calendar)
  ├── 4c. LLM advisory layer (narrative generation)
  ├── 4d. Additional scrapers (DOJI, PNJ, BTMC, State Bank)
  └── 4e. Zalo OA integration
  → Outcome: Richer signals with AI narrative, multi-source data.

Phase 5: Historical Analysis
  ├── 5a. Historical signal accuracy tracking
  ├── 5b. Backtesting framework (would signals have been correct?)
  └── 5c. Dashboard enhancements (trend charts, heatmaps)
  → Outcome: System learns from its own track record.
```

### Build Order Rationale

- **Phase 1 must come first** because everything depends on having price data. No signals without prices.
- **Phase 2 before Phase 3** because alerts and dashboard need signal data to display.
- **Phase 3 is the MVP** — users get value (prices + alerts) even without LLM narrative.
- **Phase 4 is enrichment** — macro, seasonal, LLM, and additional sources improve quality but the system works without them.
- **Phase 5 is validation** — backtesting requires months of historical signal data, so it's inherently later.

### Critical Dependency: Scraper Stability Before Signal Engine

The signal engine is only as good as its input data. Before investing heavily in signal computation, ensure the scrapers are reliable: implement retry logic, fallback sources, price validation (reject prices that are >20% different from previous), and monitoring (alert if a scraper fails 3 consecutive cycles).

## Specific Vietnamese Market Considerations

### SJC.com.vn Scraping

Based on existing open-source projects (namtrhg/vn-gold-price-api, hieu-van gist), SJC provides price data at `https://sjc.com.vn/giavang/textContent.php` in a simple HTML table. This has been a stable endpoint for years, but should be monitored for changes.

**Fallback strategy:** If SJC endpoint changes, fall back to:
1. BTMC official API (`api.btmc.vn/api/BTMCAPI/getpricebtmc`) — always have this as backup
2. giavang.com.vn — aggregator site that scrapes multiple sources
3. Direct scraping of DOJI/PNJ websites

### USD/VND Exchange Rate

Multiple sources available: Vietcombank (most commonly referenced), SBI, VIB. The rate is needed to convert international gold price (USD/oz) to VND/lượng for gap calculation. Cache for at least 10 minutes — this rate changes slowly.

### Vietnamese Seasonal Calendar

Key demand events (affects domestic premium):
- **Tet (late Jan/early Feb):** Strong buying 1-2 months before; selling pressure in post-Tet weeks
- **Wedding season (Oct-Feb):** Elevated nhẫn trơn demand
- **Vu Lan (Aug/Jul lunar):** Moderate buying
- **State Bank interventions:** Unpredictable but impactful; monitor news sources

### Telegram vs Zalo Priority

**Telegram first** because:
- Bot API is open, well-documented, and free (no business verification needed)
- python-telegram-bot library is mature (311 code snippets on Context7, HIGH reputation)
- Webhook mode works reliably on a single VPS
- Vietnamese tech-savvy investors already use Telegram

**Zalo second** because:
- Zalo OA requires business registration and verification
- API documentation is less comprehensive
- Message format limitations (2000 char max, limited rich content)
- But Zalo has 74M+ users in Vietnam — essential for mainstream reach

## Sources

- Algovantis, "Building a Robust Algo Trading Signal-to-Execution Pipeline Architecture" (2026) — layered pipeline pattern
- HIYA ChATTERJEE, "A Modular Architecture for Systematic Quantitative Trading Systems" (2025) — separation of concerns, feedback loops
- Mehul Thakkar, "Designing a Multi Agent AI System for Institutional-Grade Stock Analysis" (2026) — 47-agent architecture (anti-pattern for this project's scale)
- Devarshi Vyas, "Building a Swing Trading Agent with LangGraph" (2026) — token cost optimization, "only use LLMs where genuine reasoning is needed"
- Ray Islam, PhD, "End-to-End AI-Enhanced Regime-Aware Hybrid Alpha Strategy Pipeline" (2026) — multi-signal workflow
- Azure Architecture Center, "AI Agent Orchestration Patterns" (2026) — sequential, concurrent, hierarchical patterns
- Microsoft, "AI Agent Orchestration Patterns" — when NOT to use multi-agent
- namtrhg/vn-gold-price-api — existing VN gold scraping patterns (JavaScript)
- Thanhtran-165/GoldSJC — Python SJC gold price tracker using vnstock
- APScheduler docs (Context7, /agronholm/apscheduler) — scheduling API
- Clawdbot/OpenClaw Zalo docs — Zalo Bot API integration patterns
- Nokasoft, "How to Integrate an AI Chatbot with Zalo OA" (2025) — Zalo OA integration steps

---
*Architecture research for: Vietnamese Gold Advisory Agent*
*Researched: 2026-03-25*
