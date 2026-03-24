# Gold Advisor Vietnam

## What This Is

An AI advisory agent that helps Vietnamese users time their physical gold purchases and sales. The agent tracks SJC gold bars and nhẫn trơn (plain gold rings), analyzes the gap between domestic and international gold prices alongside macro signals and seasonal patterns, and delivers buy/hold/sell recommendations via a web dashboard and messenger alerts. Advice only — no transactions.

## Core Value

Users buy lower and sell higher than they would with blind timing, and they understand *why*.

## Requirements

### Validated

- [x] International gold price (XAUUSD) displayed in both USD and VND — Validated in Phase 1
- [x] System validates prices across sources and flags stale, missing, or anomalous data — Validated in Phase 1
- [x] Live SJC bar buy/sell prices from 5+ dealers — Validated in Phase 2
- [x] Live nhẫn trơn (ring gold) buy/sell prices from dealers — Validated in Phase 2
- [x] Buy/sell spread for SJC bars and ring gold at each dealer — Validated in Phase 2
- [x] SJC-international price gap in VND and percentage with historical trend — Validated in Phase 3
- [x] Price charts for all gold products across 1D/1W/1M/1Y — Validated in Phase 3
- [x] Buy/Hold/Sell signal with confidence level — Validated in Phase 4
- [x] One-line reasoning explanation with each signal — Validated in Phase 4
- [x] Saver/Trader mode with adapted signals — Validated in Phase 4
- [x] Mobile-responsive web dashboard with prices, gap, signal, charts — Validated in Phase 5
- [x] Telegram push notifications on signals and price movements — Validated in Phase 6
- [x] Macro indicator dashboard (USD/VND, real rates, DXY, gold trend) — Validated in Phase 7
- [x] State Bank policy monitoring as signal override — Validated in Phase 8
- [x] Vietnamese seasonal demand patterns (Tet, wedding, Vu Lan) — Validated in Phase 8
- [x] Market news feed with gold news and State Bank announcements — Validated in Phase 9

### Active

All v1 requirements have been validated. No active requirements remain.

### Out of Scope

- Executing transactions — advice only, user decides where to buy/sell
- Dealer matching or price comparison between shops
- Paper gold, ETFs, futures, or digital gold
- Markets outside Vietnam
- Portfolio management beyond gold (no multi-asset allocation)

## Context

Vietnam's gold market has unique characteristics that make timing meaningful:

- **SJC dominance**: SJC gold bars are the state-sanctioned standard product, deeply embedded in Vietnamese culture for savings, weddings, Tet, and wealth preservation
- **Persistent gap**: A significant gap often exists between international spot gold price and domestic SJC price, driven by supply constraints, State Bank import controls, and local demand surges
- **Gap is exploitable**: When the gap narrows, it's a better time to buy. When it spikes (often during panic buying), it's a signal to sell or hold off
- **High premiums on physical**: Transaction costs are non-trivial, so getting timing right matters more than with paper gold
- **Seasonal demand is pronounced**: Pre-Tet buying pushes prices up, post-Tet and summer months see weaker demand
- **State Bank influence**: Import approvals, gold auctions, and policy interventions directly affect domestic supply and pricing
- **Nhẫn trơn (ring gold)**: A popular alternative to SJC bars, often with different pricing dynamics and smaller unit sizes accessible to regular savers

## Constraints

- **Data fragility**: Vietnamese gold price data comes from web sources that may change structure — scrapers need resilience and fallbacks
- **No real-time exchange feed**: Unlike paper gold, physical gold prices update intermittently from dealers, not from a continuous exchange
- **Regulatory sensitivity**: Gold market regulation in Vietnam can shift — State Bank policy changes can override all other signals
- **Advice liability**: Buy/sell recommendations need clear disclaimers and confidence thresholds to avoid misleading users

## Key Decisions

| Decision | Rationale | Outcome |
|----------|-----------|---------|
| Advice only, no transactions | Removes regulatory complexity and trust requirements | ✅ Enforced — no transaction features |
| Vietnam-only market | Vietnamese gold market has unique dynamics that general tools miss | ✅ All data sources are Vietnam-focused |
| SJC bars + nhẫn trơn | These are the two dominant physical gold products in Vietnam | ✅ Both tracked across all 5 dealers |
| Web dashboard + messenger alerts | Dashboard for analysis, messenger for timely action — matches how Vietnamese users consume info | ✅ Phase 5 dashboard + Phase 6 Telegram |
| Scrape Vietnamese sources + international APIs | No single API covers domestic Vietnamese gold prices — need both | yfinance + Vietcombank + 5 VN dealer scrapers |
| Market FX rate over SBV official | Gap calc accuracy requires real import cost rate | Vietcombank selling rate (D-02) |
| Deterministic signal engine, no LLM | LLM introduces hallucination risk in financial advice | ✅ All signal computation is pure Python |
| Observation language, not prediction | Avoids liability, sets correct expectations | ✅ Reasoning uses "tracks/analyzes/observed" |
| State Bank policy as override factor | SBV actions can invalidate all other signals | ✅ Policy events cap confidence |
| Seasonal patterns explain, not signal | Prevents misinterpreting expected demand as timing opportunity | ✅ Seasonal adjusts confidence only |

## Evolution

This document evolves at phase transitions and milestone boundaries.

**After each phase transition** (via `/gsd:transition`):
1. Requirements invalidated? → Move to Out of Scope with reason
2. Requirements validated? → Move to Validated with phase reference
3. New requirements emerged? → Add to Active
4. Decisions to log? → Add to Key Decisions
5. "What This Is" still accurate? → Update if drifted

**After each milestone** (via `/gsd:complete-milestone`):
1. Full review of all sections
2. Core Value check — still the right priority?
3. Audit Out of Scope — reasons still valid?
4. Update Context with current state

---
*Last updated: 2026-03-25 after v1.0 completion — all 9 phases delivered*
