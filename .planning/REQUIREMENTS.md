# Requirements: Gold Advisor Vietnam

**Defined:** 2026-03-25
**Core Value:** Users buy lower and sell higher than they would with blind timing, and they understand *why*.

## v1 Requirements

Requirements for initial release. Each maps to roadmap phases.

### Data & Pricing

- [x] **DATA-01**: User can see live SJC bar buy/sell prices from 5+ dealers (SJC, Doji, PNJ, BTMC, Phú Quý, Mi Hồng), updated every 1-5 minutes
- [x] **DATA-02**: User can see live nhẫn trơn (ring gold) buy/sell prices from dealers
- [x] **DATA-03**: User can see international gold price (XAUUSD) displayed in both USD and VND
- [x] **DATA-04**: User can see SJC-international price gap displayed in VND and as percentage, with historical trend (1W/1M/3M/1Y)
- [x] **DATA-05**: User can see buy/sell spread for SJC bars and ring gold at each dealer
- [x] **DATA-06**: System validates prices across sources and flags stale, missing, or anomalous data
- [x] **DATA-07**: User can view price charts for SJC bars, ring gold, and international gold across 1D/1W/1M/1Y timeframes

### Signal Engine

- [x] **SIG-01**: User receives a Buy/Hold/Sell signal with a confidence level (0-100%) based on multi-factor analysis
- [x] **SIG-02**: User sees a one-line reasoning explanation with each signal (e.g., "Gap narrowed to 2.8% vs 30-day avg 4.5% — favorable buy conditions")
- [x] **SIG-03**: Signal engine factors in State Bank policy events (import approvals, gold auctions, interventions) as an override factor
- [x] **SIG-04**: Signal engine factors in Vietnamese seasonal demand patterns (pre-Tet spike, post-Tet weakness, wedding season, Vu Lan, ghost month)
- [x] **SIG-05**: User can view macro indicator dashboard showing USD/VND exchange rate, real interest rates, DXY dollar strength, and global gold trend
- [x] **SIG-06**: User can select Saver mode (accumulation guidance, long-term trend interpretation) or Trader mode (timing precision, signal confidence focus), and signals adapt accordingly

### Delivery & Interface

- [x] **DEL-01**: User can access a mobile-responsive web dashboard showing current prices, gap, signal, confidence, reasoning, charts, and macro indicators
- [x] **DEL-02**: User receives Telegram push notifications on signal changes and significant price movements
- [ ] **DEL-03**: User can read aggregated market news feed including gold market news and State Bank policy announcements

## v2 Requirements

Deferred to future release. Tracked but not in current roadmap.

### Alerts & Reach

- **ZALO-01**: User receives Zalo notifications (ZNS) on signal changes and price movements
- **ZALO-02**: User can interact with Zalo chatbot for basic queries (current price, signal, gap)

### Tracking & Trust

- **TRCK-01**: User can record their gold holdings (SJC bars, ring gold) with purchase price and date, and see current portfolio value (Sổ vàng)
- **TRCK-02**: User can view signal accuracy tracking — historical signals compared with actual price outcomes, running win rate and average gain/loss statistics
- **TRCK-03**: User can compare buy/sell spreads across dealers to find the best current spread

### Intelligence

- **ADV-01**: System provides advanced backtesting — user can simulate "what if I followed signals for the past year"
- **ADV-02**: Signal engine uses ML-based seasonal demand prediction using multi-year historical data

## Out of Scope

Explicitly excluded. Documented to prevent scope creep.

| Feature | Reason |
|---------|--------|
| Automatic trade execution | Regulatory requirement (no gold trading license), liability risk, contradicts "advice only" positioning |
| Real-time streaming prices | Vietnamese physical gold prices update intermittently from dealers, not from continuous exchange feed; 1-5 min polling is appropriate |
| Paper gold / ETF / futures signals | Different market dynamics, requires licensing, dilutes Vietnam physical gold focus |
| Multi-asset portfolio allocation | Out of scope, requires investment advisor license; gold-only focus is clearer value prop |
| Dealer price comparison / marketplace | Turns advisory into lead-gen, creates bias perception, conflicts with "advice only" |
| AI chatbot for Q&A | LLM hallucination on financial advice is dangerous, users may treat responses as personalized advice |
| Price prediction / forecasting | No model reliably predicts gold prices; false precision destroys trust when wrong |
| Social / community features | Creates herd behavior, moderation burden, liability if group consensus leads to losses |
| Markets outside Vietnam | Vietnam physical gold market has unique dynamics; generalizing dilutes value prop |
| Native mobile app | Web-first approach; native app only if web usage validates demand |

## Traceability

Which phases cover which requirements. Updated during roadmap creation.

| Requirement | Phase | Status |
|-------------|-------|--------|
| DATA-01 | Phase 2 | Complete |
| DATA-02 | Phase 2 | Complete |
| DATA-03 | Phase 1 | Complete |
| DATA-04 | Phase 3 | Complete |
| DATA-05 | Phase 2 | Complete |
| DATA-06 | Phase 1 | Complete |
| DATA-07 | Phase 3 | Complete |
| SIG-01 | Phase 4 | Complete |
| SIG-02 | Phase 4 | Complete |
| SIG-03 | Phase 8 | Complete |
| SIG-04 | Phase 8 | Complete |
| SIG-05 | Phase 7 | Complete |
| SIG-06 | Phase 4 | Complete |
| DEL-01 | Phase 5 | Complete |
| DEL-02 | Phase 6 | Pending |
| DEL-03 | Phase 9 | Pending |

**Coverage:**
- v1 requirements: 16 total
- Mapped to phases: 16
- Unmapped: 0 ✓

---
*Requirements defined: 2026-03-25*
*Last updated: 2026-03-25 after roadmap creation*
