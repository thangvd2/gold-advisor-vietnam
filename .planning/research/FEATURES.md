# Feature Research

**Domain:** Gold Investment Advisory / Financial Signal Product (Vietnam-specific)
**Researched:** 2026-03-25
**Confidence:** MEDIUM

## Feature Landscape

### Table Stakes (Users Expect These)

Features users assume exist. Missing these = product feels incomplete.

| Feature | Why Expected | Complexity | Notes |
|---------|--------------|------------|-------|
| **Live SJC price display** | Every Vietnamese gold app shows this; users check gold prices daily like checking weather | LOW | Must cover SJC bars + nhẫn trơn from multiple dealers (SJC, Doji, PNJ, Bảo Tín Minh Châu, Phú Quý, Mi Hồng). Update every 1-5 min. Vàng Mi Hồng (74K+ downloads), Giá Vàng VN (17K+), iGold, Gold VN all offer this. |
| **International gold price** (XAUUSD) | Users need to compare domestic vs world price to understand the gap | LOW | Source from Kitco, Goldprice.org, or free API. Display in USD and converted VND. |
| **SJC-international gap tracker** | The gap is THE primary timing signal for Vietnamese gold investors | LOW | Show current gap, gap as % of international price, gap history over time. This is the core insight users come for. |
| **Buy/sell spread display** | Physical gold has significant buy-sell spreads at shops; this is real transaction cost | LOW | Show bid/ask for SJC bars and ring gold at each dealer. Critical for timing accuracy — a narrow gap with wide spreads still means poor timing. |
| **Price chart / history** | Every gold app offers 1D/1W/1M/1Y charts; users feel lost without visual context | LOW | Standard line/candlestick charts. Historical price data essential for seasonal pattern recognition. |
| **Buy/Hold/Sell signal with confidence** | The core product promise — users subscribe for this specifically | HIGH | Must have clear signal (BUY/HOLD/SELL) with confidence level (e.g., 70%) and reasoning. Industry standard across all signal services. |
| **Price alert notifications** | Push/Telegram notification when gold hits a target price | LOW | Standard feature in every gold app. Set alerts on SJC price or gap %. Critical for timely action without watching screen. |
| **Market news feed** | Gold price moves on news; users expect context for why price changed | MEDIUM | Gold market news, State Bank policy announcements, macro events. Can aggregate from RSS sources. Vàng Mi Hồng and iGold both offer this. |
| **Signal reasoning / "why"** | Users need to trust the signal; blind "BUY NOW" creates skepticism and liability | MEDIUM | Brief explanation: "Gap narrowed to 3% (below 30-day avg 5%) — favorable buy window" or "Pre-Tet demand surge pushing premiums — HOLD." This is the "understand why" promise from PROJECT.md. |
| **Disclaimers and risk notices** | Regulatory requirement for any financial advice product | LOW | Clear "not financial advice, for informational purposes only" language. Required for liability protection in Vietnam and internationally. |
| **Mobile-responsive web** | Most Vietnamese users access via phone; dashboard must work on mobile browsers | LOW | No native app needed initially (MVP), but web dashboard must be mobile-first. Vietnamese diaspora users especially rely on mobile. |

### Differentiators (Competitive Advantage)

Features that set the product apart. Not required, but valuable.

| Feature | Value Proposition | Complexity | Notes |
|---------|-------------------|------------|-------|
| **SJC-international gap as primary signal** | No existing Vietnamese app uses the gap analytically — they just display prices | MEDIUM | Current apps (Vàng Mi Hồng, Gold VN, iGold, Giá Vàng VN) only show prices and news. None generate timing signals based on the gap. This IS the product. |
| **State Bank policy monitoring** | Import approvals, gold auctions, Saigon Jewelry Company interventions — these override all other signals | HIGH | Requires monitoring State Bank website, news sources, and interpreting policy implications. Unique to Vietnam market. Huge competitive moat — no one does this programmatically. |
| **Vietnamese seasonal demand modeling** | Tet, wedding season, Vu Lan, ghost month create predictable demand cycles | MEDIUM | Pre-Tet (Jan-Feb) buying pushes premiums up 5-15%. Post-Tet and summer (May-Jul) see weaker demand. Wedding season (Oct-Dec) creates moderate demand. Quantifiable and exploitable. |
| **Macro indicator dashboard** | USD/VND exchange rate, Fed rate decisions, global gold trend — these drive the gap | MEDIUM | Real rates (10Y Treasury yield - CPI), USD strength (DXY), gold ETF flows. Gives institutional-grade context to retail Vietnamese investors. |
| **Dual user mode (Saver vs Trader)** | Savers want "accumulate more" guidance; traders want timing precision | MEDIUM | Savers: DCA recommendations, long-term trend, seasonal buying windows. Traders: Gap analysis, signal confidence, spread optimization. Different default views and signal interpretations. |
| **Buy/sell spread optimization** | Which dealer has the best spread right now? Saves real money on every transaction | MEDIUM | Compare spreads across SJC, Doji, PNJ, Bảo Tín Minh Châu, etc. Alert when a particular shop offers unusually good buy/sell prices. No existing app does signal-aware spread comparison. |
| **Signal accuracy tracking** | Published win/loss record builds trust; no Vietnamese gold signal service does this | MEDIUM | Track historical signals vs actual outcomes. Show running accuracy %, average gain when following signals. Critical trust builder — signal services live and die by their track record. |
| **Zalo integration** | 95% smartphone penetration in Vietnam; Zalo > Telegram for mainstream users | HIGH | Zalo OA (Official Account) with chatbot and ZNS (Zalo Notification Service) for alerts. Zalo is the #2 social platform in Vietnam after Facebook, 70M+ Zalo Pay users. Higher reach than Telegram for Vietnamese market. |
| **Nhẫn trơn (ring gold) tracking** | More accessible than SJC bars (smaller units), different pricing dynamics | LOW | Most apps track SJC but ring gold is equally important for regular savers. Ring gold premium vs melt value varies differently from SJC bar premium. |
| **Gold portfolio tracking** ("Sổ vàng") | Users want to record their gold holdings and see P&L | LOW | Báo Giá Vàng and SJC Gold & FX Price Tracker both offer "Sổ vàng" (gold ledger). Enter quantity, purchase date, see current value. Simple but sticky feature. |

### Anti-Features (Commonly Requested, Often Problematic)

Features that seem good but create problems.

| Feature | Why Requested | Why Problematic | Alternative |
|---------|---------------|-----------------|-------------|
| **Automatic trade execution** | "Just do it for me" — users want hands-free | OUT OF SCOPE per PROJECT.md. Regulatory nightmare in Vietnam (no gold trading license). Liability if automated trades lose money. Removes "advice only" simplicity. | Clear buy/hold/sell signals with manual execution. Link to shop locations or dealer websites. |
| **Real-time streaming prices** | "I want second-by-second updates" | Vietnamese physical gold prices update from dealers, not exchanges. No real-time feed exists. Simulating it would be misleading. Scraping every 30 seconds gets IP-banned. | 1-5 minute polling with clear "last updated" timestamp. Push alerts only on significant changes. |
| **Paper gold / ETF / futures signals** | "Can you also do digital gold?" | Completely different market dynamics. Requires licensing. Dilutes Vietnam-focused value prop. | Stay ruthlessly focused on physical SJC + ring gold in Vietnam. |
| **Multi-asset portfolio allocation** | "What % gold vs stocks vs bonds?" | Out of scope per PROJECT.md. Requires investment advisor license. Gold-only focus is clearer value prop for a niche product. | Pure gold advisory. Point users to licensed financial advisors for broader allocation. |
| **Dealer price comparison / marketplace** | "Where should I buy right now?" | Turns advisory into lead-gen for dealers. Conflicts with "advice only" positioning. Dealer relationships create bias perceptions. | Show spread data (transparent). Let users decide where to buy. No referrals. |
| **AI chatbot for Q&A** | "I want to ask the AI questions" | LLM hallucination on financial advice is dangerous. Users may treat chatbot responses as personalized advice. Liability risk. | Pre-written analysis and signal reasoning. FAQ section. No generative AI for financial Q&A. |
| **Price prediction / forecasting** | "What will gold be next month?" | No one can predict gold prices. False precision destroys trust when wrong. Backtested gold momentum strategies show ~6% annual returns vs 10.5% buy-and-hold — worse than doing nothing. | Probabilistic signals with confidence levels. "Conditions favor buying" not "Gold will be X next week." |
| **Social / community features** | "I want to see what others are doing" | Creates herd behavior. Groupthink leads to panic buying/selling. Moderation burden. Liability if group consensus leads to losses. | Focus on individual signals. Optional: curated analysis, not user-generated content. |

## Feature Dependencies

```
[Data Ingestion: SJC/international prices]
    ├──requires──> [Price Display & Charts]
    │                  └──requires──> [Gap Tracker]
    │                                      └──requires──> [Buy/Hold/Sell Signal Engine]
    │                                                          └──requires──> [Signal Reasoning]
    │                                                                              └──enhances──> [Alerts/Notifications]
    ├──requires──> [Buy/Sell Spread Tracker]
    └──enhances──> [Gold Portfolio Tracker ("Sổ vàng")]

[State Bank Policy Monitoring] ──enhances──> [Signal Engine]
[Seasonal Demand Model] ──enhances──> [Signal Engine]
[Macro Indicators (USD/VND, rates)] ──enhances──> [Signal Engine]

[Signal Engine] ──requires──> [Signal Accuracy Tracking]
[Telegram Bot] ──requires──> [Signal Engine]
[Zalo OA Bot] ──requires──> [Signal Engine]
[Market News Feed] ──enhances──> [Dashboard Context]

[User Profiles (Saver vs Trader)] ──enhances──> [Signal Display & Dashboard]
[User Profiles] ──requires──> [Authentication System]
```

### Dependency Notes

- **Signal Engine requires Gap Tracker + Data Ingestion:** The core signal is derived from the gap between domestic and international prices. Without reliable, frequently-updated data from both sources, no signal can be generated. Data quality is the foundation — garbage in, garbage out.
- **Signal Reasoning enhances Alerts:** An alert that says "BUY" is useless. An alert that says "BUY — gap narrowed to 2.8%, below 30-day average of 4.5%, seasonal post-Tet weakness expected" is actionable. Always pair signal with reasoning.
- **State Bank Policy + Seasonal + Macro all enhance Signal Engine:** These are secondary signals layered on top of the primary gap signal. The gap is necessary but not sufficient — policy changes can override gap analysis entirely (e.g., sudden import ban = gap spikes regardless of international trends).
- **User Profiles enhances Signal Display:** Same raw signal, different interpretation. A "HOLD" for a trader (wait for better entry) might be "BUY small amount" for a saver (DCA is always good).
- **Zalo OA is separate from Telegram:** Different APIs, different message format constraints, different user base. Build signal engine first, then connect to both channels independently. Zalo reaches mainstream Vietnamese users; Telegram reaches more tech-savvy/crypto-experienced users.
- **Signal Accuracy Tracking requires Signal Engine history:** Can't track accuracy without recording signals and their outcomes over time. This is a post-launch feature that needs several weeks/months of signal history.

## MVP Definition

### Launch With (v1)

Minimum viable product — what's needed to validate the concept.

- [ ] **SJC price data pipeline** — Scrape SJC, Doji, PNJ prices every 2-5 min. Fallback sources. This is the foundation everything else depends on.
- [ ] **International gold price** — XAUUSD from API (Kitco, MetalPriceAPI, or similar). Convert to VND.
- [ ] **Gap tracker** — Calculate and display SJC-international gap in VND and %. Show gap trend (1W, 1M).
- [ ] **Basic signal engine** — Buy/Hold/Sell based on gap thresholds + confidence level. Start simple: gap below historical average → BUY, gap above → SELL/HOLD.
- [ ] **Web dashboard** — Current prices, gap, signal, confidence, basic chart. Mobile-responsive.
- [ ] **Telegram alerts** — Push notifications on signal changes and significant price movements. Telegram Bot API is simpler to implement first than Zalo.
- [ ] **Signal reasoning** — One-line explanation with each signal. "Gap at 2.8% vs 30-day avg 4.5% — favorable buy conditions."
- [ ] **Nhẫn trơn tracking** — At least SJC ring gold prices alongside bars. Important for saver persona.

### Add After Validation (v1.x)

Features to add once core is working and users are engaged.

- [ ] **Zalo OA integration** — Reach the mainstream Vietnamese market (95% penetration). ZNS for push notifications. Chatbot for basic queries.
- [ ] **State Bank policy monitoring** — Scrape State Bank website for gold auction announcements, import approvals. Integrate into signal as override factor.
- [ ] **Seasonal demand model** — Quantify Tet, wedding season, Vu Lan effects. Show "seasonal outlook" on dashboard.
- [ ] **Macro indicator dashboard** — USD/VND, US real rates, global gold trend. Simple display, no complex modeling.
- [ ] **Gold portfolio tracker (Sổ vàng)** — Users record holdings, see P&L. Simple CRUD. Increases stickiness.
- [ ] **Signal accuracy tracking** — Record signals, compare with outcomes after 1/7/30 days. Show running stats.
- [ ] **Buy/sell spread comparison** — Which dealer has best spread right now for the product you want.
- [ ] **User profiles (Saver vs Trader)** — Different dashboard views and signal interpretations based on user type.

### Future Consideration (v2+)

Features to defer until product-market fit is established.

- [ ] **Advanced backtesting** — Let users simulate "what if I followed signals for the past year." Requires substantial historical data and statistical rigor.
- [ ] **Multi-dealer spread alerts** — "PNJ just narrowed their buy-sell spread to 1.5%, best in 30 days."
- [ ] **Community features** — Curated analysis sharing, weekly market recap newsletter.
- [ ] **Advanced seasonal modeling** — ML-based demand prediction using multi-year data.
- [ ] **Mobile app (native)** — Only if web usage validates demand. React Native or Flutter.
- [ ] **Premium tier** — Subscription for higher-frequency signals, deeper analysis, early alerts.

## Feature Prioritization Matrix

| Feature | User Value | Implementation Cost | Priority |
|---------|------------|---------------------|----------|
| SJC price data pipeline | HIGH | MEDIUM | P1 |
| International gold price | HIGH | LOW | P1 |
| Gap tracker | HIGH | LOW | P1 |
| Basic signal engine | HIGH | HIGH | P1 |
| Web dashboard | HIGH | MEDIUM | P1 |
| Telegram alerts | HIGH | MEDIUM | P1 |
| Signal reasoning | HIGH | MEDIUM | P1 |
| Nhẫn trơn tracking | MEDIUM | LOW | P1 |
| Zalo OA integration | HIGH | HIGH | P2 |
| State Bank policy monitor | HIGH | HIGH | P2 |
| Seasonal demand model | MEDIUM | MEDIUM | P2 |
| Macro indicator dashboard | MEDIUM | MEDIUM | P2 |
| Gold portfolio tracker | MEDIUM | MEDIUM | P2 |
| Signal accuracy tracking | MEDIUM | MEDIUM | P2 |
| Buy/sell spread comparison | MEDIUM | MEDIUM | P2 |
| User profiles (Saver/Trader) | MEDIUM | MEDIUM | P2 |
| Advanced backtesting | LOW | HIGH | P3 |
| Community features | LOW | HIGH | P3 |
| Mobile app (native) | MEDIUM | HIGH | P3 |
| Premium tier | LOW | MEDIUM | P3 |

**Priority key:**
- P1: Must have for launch — validates core value prop
- P2: Should have — strengthens retention and competitive position
- P3: Nice to have — future consideration after PMF

## Competitor Feature Analysis

| Feature | Vàng Mi Hồng | Giá Vàng VN | iGold | Gold VN | Báo Giá Vàng | **Our Approach** |
|---------|-------------|-------------|-------|---------|--------------|-----------------|
| SJC live prices | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ Standard |
| Multiple dealers | ✅ (Mi Hồng only) | ✅ (15+ shops) | ✅ (SJC, PNJ, DOJI) | ✅ (SJC, DOJI, PNJ, rings) | ✅ (15+ shops) | ✅ Aggregate from 5+ dealers |
| International gold | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ Standard |
| Gap tracker | ❌ (no analytical gap) | ❌ (price comparison only) | ❌ | ❌ | ❌ | ✅ **PRIMARY SIGNAL** — our differentiator |
| Buy/sell signals | ❌ | ❌ | ❌ | ❌ | ❌ | ✅ **Core product** |
| Price alerts | ✅ (push notifications) | ❌ | ✅ | Coming Soon | ✅ | ✅ Signal + price alerts |
| Portfolio tracker | ❌ | ❌ | ❌ | ❌ | ✅ (Sổ vàng) | ✅ v1.x |
| News feed | ✅ (articles + video) | ✅ (24/7 market news) | ✅ | ❌ | ✅ | ✅ Aggregated |
| Pawn value calculator | ✅ | ❌ | ❌ | ❌ | ❌ | ❌ Out of scope |
| Telegram/Zalo alerts | ❌ | ❌ | ❌ | ❌ | ❌ | ✅ **Messenger-first delivery** |
| State Bank monitoring | ❌ | ❌ | ❌ | ❌ | ❌ | ✅ **Unique** |
| Seasonal analysis | ❌ | ❌ | ❌ | ❌ | ❌ | ✅ **Unique** |
| Signal reasoning | ❌ | ❌ | ❌ | ❌ | ❌ | ✅ **Core value** ("understand why") |
| Offline mode | ❌ | ❌ | ❌ | ❌ | ✅ | ❌ Web-only, no need |

**Key insight:** The Vietnamese gold app market is entirely focused on price display and news. NO existing product provides analytical signals, gap-based timing advice, or messenger alerts. The market is a price-reading tool, not an advisory tool. This is a blue-ocean opportunity in a space with established user habits (checking gold prices is daily behavior for millions of Vietnamese).

### International Signal Service Comparison (Pattern Reference)

| Feature | CryptoNinjas | WolfX Signals | Gold Signals H1 | TradingView Alerts | **Our Approach** |
|---------|-------------|---------------|-----------------|-------------------|-----------------|
| Signal delivery | Telegram | Telegram | App notifications | App/web | Telegram + Zalo |
| Entry/SL/TP levels | ✅ | ✅ | ✅ | User-defined | ❌ (advice-only, no trade levels) |
| Win rate tracking | ✅ (claimed 90%+) | ✅ (89%) | ❌ | ❌ | ✅ (honest, transparent) |
| Market analysis | ✅ | ✅ | ✅ | ❌ | ✅ Gap + macro + seasonal |
| Subscription tiers | Free + VIP | Free + VIP | Paid only | Free + paid | Start free, add paid later |
| Automated trading | ✅ (Cornix bot) | ✅ (bot support) | ❌ | ✅ | ❌ (advice only) |
| Multi-market | Crypto + forex | Crypto + forex + gold | Gold only | Everything | Vietnam physical gold only |

## Sources

- **Vietnamese gold apps analyzed:** Vàng Mi Hồng (74K+ downloads, App Store/Google Play listings), Giá Vàng VN (17K+ downloads), iGold, Gold VN, Báo Giá Vàng & Tỷ Giá Ngoại Tệ, SJC Gold & FX Price Tracker
- **International signal services reviewed:** CryptoNinjas, WolfX Signals, Gold Signals H1, XAUUSD XAGUSD Signal Notification, Gold Signal Alert (Google Play), various Telegram signal groups (Smart Options comparison)
- **Telegram signal bot patterns:** AstroSentinel V2 (GitHub open-source), TGBotsLab commercial bot, Ben Gold Trader EA — all follow same pattern: signal → entry/SL/TP → confidence → notification
- **Backtesting tools examined:** BacktestAI, Forex Tester, QuantifiedStrategies gold momentum analysis — standard metrics are win rate, max drawdown, Sharpe ratio, profit factor
- **Zalo ecosystem research:** Prodima Vietnam 2026 guide, Nokasoft Zalo OA integration guide, Infobip ZNS partnership — Zalo has 95% smartphone penetration in Vietnam, ZNS enables push notifications via Zalo OA
- **Risk management literature:** WallStreetZen portfolio risk guide, Flexible Plan Investments gold allocation research (2025 white paper), State Street SPDR gold portfolio analysis (2005-2025 data)
- **Confidence levels:** Vietnamese app features = HIGH (verified via app store listings), international signal patterns = MEDIUM (multiple sources), Zalo technical capabilities = MEDIUM (official docs + guides), Vietnamese market dynamics from PROJECT.md = HIGH (validated by project owner)

---
*Feature research for: Gold Advisory Agent (Vietnam)*
*Researched: 2026-03-25*
