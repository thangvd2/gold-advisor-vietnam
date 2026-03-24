# Pitfalls Research

**Domain:** Vietnamese Gold Advisory Agent (AI-powered financial timing signals for SJC gold and nhẫn trơn)
**Researched:** 2026-03-25
**Confidence:** MEDIUM-HIGH

---

## Critical Pitfalls

### Pitfall 1: Treating Gold Price Prediction as a Solvable ML Problem

**What goes wrong:**
You build a model that achieves 95%+ accuracy on backtested data, ship it, and it produces buy/sell signals that lose users real money. The model appears to work because it learned spurious correlations in historical data that don't hold forward. Gold is not a normal time series — it's a monetary asset driven by geopolitics, central bank behavior, and irrational sentiment that no amount of feature engineering can fully capture.

**Why it happens:**
- Gold prices are driven by factors *outside* traditional pricing models. As of 2026, traditional gold pricing variables (real rates, dollar correlation, inflation expectations) explain **less than 40% of price variance** — the lowest explanatory power since the 2011 peak (AhaSignals research, March 2026)
- Central banks — the dominant marginal buyers since 2022 — operate outside market-based pricing logic. They don't respond to real rates or dollar strength the way private investors do
- Professional forecasters at LBMA, Goldman Sachs, and J.P. Morgan produce wildly divergent targets (2026 range: $4,450–$6,300/oz) — the widest dispersion in survey history — and the consensus average still underestimates spot by 8–9%
- Gold hit $5,602/oz on Jan 28, 2026, then crashed nearly 20% in weeks. No model predicted this
- The most common methodological error: randomly shuffling time-series data for train/test splits, creating look-ahead bias. A model with 97% accuracy on a random-split test set is worthless for actual trading

**How to avoid:**
- **Frame signals as "informational" not "predictive."** The agent should present the SJC-international gap, macro context, and seasonal patterns as *inputs to a human decision*, not as automated buy/sell commands
- **Use naive baselines religiously.** If your model doesn't beat "price was X yesterday, so it'll be X today" (price persistence), your model has no signal
- **Focus on directional accuracy, not price levels.** Getting the direction right (up/down) matters more than exact price targets
- **Explicitly state what the model CANNOT capture** — State Bank interventions, geopolitical shocks, panic buying events
- **Use confidence ranges, not point estimates.** Always present signals with uncertainty bands
- **Beware of backtest overfitting.** Use walk-forward validation only. Never random-train-test-split a time series

**Warning signs:**
- Backtested accuracy above 70% on directional calls (suspiciously high for gold)
- Model performance degrades sharply after deployment (classic overfitting signal)
- Model gives the same signal as just extrapolating the recent trend
- Feature importance is dominated by lagged price variables only (no independent signal)

**Phase to address:**
Phase 1 (Core signal logic). If the signal approach is wrong from day one, nothing downstream fixes it.

---

### Pitfall 2: LLM Hallucinating Financial Advice That Reaches Users

**What goes wrong:**
The AI agent generates a convincing-sounding buy recommendation citing a "recent State Bank policy" that doesn't exist, or fabricates a historical pattern ("every time the gap exceeds VND 15M/tael, prices drop within 2 weeks"). A user acts on this and loses money. The fabricated advice reaches the user before anyone notices. FINRA's 2026 Annual Regulatory Oversight Report explicitly flags AI hallucinations as a compliance risk — models "generating information that is inaccurate or misleading, yet presented as factual information."

**Why it happens:**
- LLMs are pattern-matchers, not databases. They generate plausible-sounding text that may not correspond to reality
- Financial data requires precision — a hallucinated "VND 15M gap threshold" that never existed can drive real decisions
- The agent combines multiple data streams (scraped prices, macro indicators, policy news). Hallucinations are more likely when the model tries to synthesize across heterogeneous sources
- Air Canada was ordered to compensate a passenger after its chatbot provided false refund information. The legal precedent for AI-generated misinformation causing financial harm is being established now
- FINRA 2026: "A model that misinterprets a regulatory requirement or misstates client information could lead to flawed downstream decisions"

**How to avoid:**
- **Never let the LLM make assertions about specific data points.** The agent should only *reference* data that exists in the structured database — prices, gaps, macro indicators — and format it into natural language
- **Implement a data-grounding architecture.** The LLM should have access to a structured fact store (current prices, gap values, historical patterns) and be instructed: "Only discuss data from the provided context. Never fabricate statistics, thresholds, or policy references."
- **Add a verification layer.** Any claim the LLM makes about historical patterns or policy should be checked against the database before being shown to users
- **Include mandatory disclaimers in every output.** "This is informational analysis, not financial advice. Data may be delayed or inaccurate."
- **Log all outputs for audit.** If hallucinated advice reaches a user, you need to know exactly what was said, when, and based on what inputs

**Warning signs:**
- The LLM cites specific statistics, percentages, or policy numbers that you can't verify in your data store
- Users report "interesting facts" from the agent that weren't in the original data
- The agent's explanation changes even when the underlying data hasn't changed
- Tone shifts to overconfidence ("This is clearly a buying opportunity")

**Phase to address:**
Phase 1 (Agent architecture). The data-grounding pattern must be built into the agent's core design. Retrofitting it later is extremely painful.

---

### Pitfall 3: Scraped Vietnamese Gold Data Going Stale or Wrong Without Detection

**What goes wrong:**
The scraper for SJC.com.vn, Doji, or PNJ silently breaks after a website redesign. The dashboard continues showing "current" prices that are actually days or weeks old. Users make decisions based on stale data. The scraper returns partial data that *looks* right — a price appears, but it's from a different product (ring gold price displayed as SJC bar price), or the buy/sell spread is inverted. This is the most dangerous failure mode: **silent data corruption** where the pipeline appears healthy but the signal is wrong.

**Why it happens:**
- Vietnamese gold shop websites are not designed for programmatic access. They update layouts without notice, use JavaScript rendering (prices loaded via AJAX after page load), and may implement anti-bot measures
- CSS class names like `.gold-price` or `#sjc-buy` are *not stable contracts*. Frontend code is built for users, not scrapers. A class rename from `price` to `current-price` silently breaks extraction
- Vietnamese gold sites may serve different content based on time of day (some only update prices during trading hours), or show cached/holiday prices
- 10–15% of industries now require scraper fixes on a weekly basis due to website structure changes
- The biggest trap: scrapers that return 200 OK but serve incomplete, throttled, or dynamically rendered placeholder content ("Loading...", "Vui lòng chờ...", or stale cached values)

**How to avoid:**
- **Design for failure, not for success.** Every scraper run should produce a health report: HTTP status, response time, number of fields extracted, validation pass/fail for each field
- **Implement schema validation on every record.** Price must be > 0, must be within X% of yesterday's price (flag if not), buy price must be < sell price, price must match expected format (VND currency pattern). If validation fails, mark data as stale — don't silently use it
- **Use multiple independent sources and cross-validate.** If SJC.com.vn shows VND 180M/tael but Doji shows VND 175M, the spread is unusual — flag it. If one source stops updating, fall back to others
- **Track data freshness explicitly.** Store a `last_successful_scrape_at` timestamp. If it's older than your SLA (e.g., 2 hours for gold prices), display a "DATA MAY BE STALE" warning on the dashboard
- **Build canary checks.** Have a small set of known SKUs/prices that you manually verify daily. If the canary diverges from scraped data, alert immediately
- **Monitor rate of null fields and data volume.** If the scraper starts returning more null values or fewer total records than usual, that's a warning sign even if the pipeline "succeeds"

**Warning signs:**
- Dashboard prices don't match what users see on the actual gold shop websites
- Buy-sell spread suddenly inverts or becomes unreasonably wide/narrow
- Price changes are suspiciously smooth or static (no volatility where there should be some)
- One source consistently diverges from others
- Alert rate for "data validation failure" drops to zero (false confidence — likely the checks aren't running)

**Phase to address:**
Phase 1 (Data pipeline). Data quality infrastructure must be built before any analysis or signals are generated on top of it.

---

### Pitfall 4: State Bank Policy Changes Invalidating All Signal Logic Overnight

**What goes wrong:**
The agent's signal model is built on historical patterns of the SJC-international price gap. It identifies that "when the gap narrows below VND 5M/tael, it's a good time to buy." Then the State Bank of Vietnam issues Decree 232/2025 (August 2025), abolishing the SJC monopoly on gold bar production and opening imports to licensed enterprises. The fundamental market structure changes. Historical gap patterns become meaningless because supply dynamics are entirely different. The agent continues issuing signals based on pre-decimal-232 patterns.

**Why it happens:**
- Vietnam's gold market is heavily regulated and subject to abrupt policy shifts. Between 2024-2025, the State Bank implemented surprise inspections, gold auctions, import quota changes, and monopoly reforms — any of which can fundamentally alter price dynamics
- In April 2025, the SJC-international gap surged to VND 14.48M/tael (13.62%) from VND 1M/tael in Q1 — a 14x swing in weeks, driven by supply constraints and speculative behavior
- Decree 24 (gold trading management) was amended by Decree 232 in August 2025 — a structural reform that invalidates many historical assumptions
- The State Bank has explicitly warned about "businesses and individuals taking advantage of market fluctuations to speculate, inflate prices, and seek profit" and has coordinated with the Ministry of Public Security for enforcement
- Gaps that previously ranged 3-5% can spike to 25% (seen in late 2024) and back — a regime that makes any statistical model trained on "normal" periods fragile

**How to avoid:**
- **Make the agent aware of regulatory regime changes.** Maintain a curated policy timeline (Decree 24, Decree 232, SBV interventions, import approvals). When a policy change occurs, the agent should flag: "Market structure has changed. Historical patterns may not apply."
- **Track the "regime" explicitly.** Define market regimes (monopoly era, transition era, competitive era post-Decree-232) and only use training data from the current regime for signal generation
- **Weight recent data more heavily.** Patterns from 2020-2023 are less relevant after Decree 232. Use exponential decay or rolling windows of 6-12 months max
- **Include State Bank action as a first-class signal, not an edge case.** Monitor for SBV announcements, auction schedules, and inspection campaigns. These override all other signals
- **Build a manual override.** When a major policy change occurs, the system should default to "reduced confidence" mode until new patterns stabilize

**Warning signs:**
- Signal accuracy drops sharply after a known policy date
- The gap behaves differently than historical patterns would predict
- Official Vietnamese news sources (SBV, government portals) announce gold market policy changes
- Gap volatility increases beyond historical norms

**Phase to address:**
Phase 1 (Signal design). The signal model must natively handle regime changes. Phase 2 (Policy monitoring). Automated policy tracking must be operational before signals go live.

---

### Pitfall 5: Overpromising Prediction Accuracy and Facing Liability Exposure

**What goes wrong:**
The product marketing or UX language implies the agent can "predict" gold price movements. A user buys gold based on a "strong buy" signal, prices drop 15%, and the user loses significant money. They blame the agent. The project faces reputational damage and potential legal action. This is not hypothetical: Betterment paid $9M to settle SEC charges over overpromised tax-loss harvesting, and Schwab paid $187M over misleading robo-advisor disclosures.

**Why it happens:**
- The temptation to sound confident. "Our AI analyzes X factors to identify optimal buy/sell timing" sounds much better than "Our system displays current market data and historical patterns for your consideration"
- Users naturally anthropomorphize AI agents. If the agent says "buy now," users treat it as expert advice, not informational context
- Vietnam's legal framework for AI-generated financial advice is evolving. While the project is "advice only" and doesn't execute transactions, the line between "informational" and "advisory" can be blurry
- SEC/FINRA precedent (while US-specific) shows regulators take a dim view of AI tools making financial recommendations without proper disclosures and human oversight
- Vietnamese consumer protection law and e-commerce regulations may apply even to free advisory tools

**How to avoid:**
- **Never use prediction language.** Replace "predicts" with "tracks," "analyzes," "monitors." Replace "buy signal" with "favorable conditions observed." Replace "confidence level" with "signal strength" (different connotation)
- **Prominent disclaimers on every output.** Not buried in fine print — visible on every dashboard view and every messenger alert. "This is market information, not financial advice. Past patterns do not guarantee future results. The SJC-international gap is one of many factors to consider."
- **Show the data, not just the conclusion.** Instead of "BUY: Gap is narrowing," show the actual gap value, the historical range, and let the user draw their own conclusion
- **Track and display historical signal accuracy.** If the agent has been running, show "over the last 6 months, signals of this type were followed by X outcome Y% of the time." Transparency builds more trust than confidence
- **Include a "what could go wrong" section.** For each signal, list the factors that could invalidate it (SBV intervention, geopolitical shock, gap inversion)

**Warning signs:**
- Marketing copy uses words like "predict," "forecast," "guarantee," or "optimize"
- The agent's output format looks like a stock tip ("STRONG BUY SJC BARS")
- Users in testing treat the agent as a financial advisor rather than an information tool
- The team internally frames the product as "telling people when to buy/sell gold"

**Phase to address:**
Phase 1 (UX/wording). Language choices are hard to retroactively change and set user expectations permanently. Phase 3 (Legal review). Formal legal assessment of disclaimer language and liability exposure.

---

### Pitfall 6: Vietnamese Gold Market Cultural Complexity Oversimplified

**What goes wrong:**
The agent treats SJC bar gold and nhẫn trơn as interchangeable assets with similar pricing dynamics. It misses that nhẫn trơn pricing varies significantly between shops (PNJ, Doji, Bao Tin Minh Chau each have different premiums, purity standards, and buyback policies). It fails to account for the fact that Vietnamese gold buying is deeply cultural — Tet gifting, wedding trousseaus, Vu Lan filial piety offerings — and demand surges during these periods are not "signals" but predictable calendar events that smart buyers plan around. The agent's signals become noise because they don't distinguish between a gap widening due to genuine market inefficiency vs. seasonal demand that always happens.

**Why it happens:**
- Technical teams often model financial assets as price series without understanding the cultural context that drives demand
- SJC bars and nhẫn trơn have fundamentally different market structures: SJC bars have a single producer (SJC) with standardized weight/purity, while nhẫn trơn are produced by multiple jewelers with varying premiums
- Buy/sell spreads for nhẫn trơn can be 3-5%, much wider than SJC bars, because jewelers factor in fabrication costs
- Seasonal patterns (Tet: Jan/Feb, wedding season: after Tet through spring, Vu Lan: August) create predictable demand surges that temporarily widen gaps — but this is *expected*, not a timing signal
- The "one market" problem identified by SBV: SJC's monopoly meant domestic prices couldn't track international prices, creating a persistent structural premium

**How to avoid:**
- **Model SJC bars and nhẫn trơn as separate products with separate signals.** Different pricing dynamics, different spreads, different optimal timing
- **Build a Vietnamese cultural calendar into the signal model.** Tet, wedding season, Vu Lan, and other demand events should be *inputs* that explain gap widening, not *signals* themselves
- **Account for shop-specific premiums.** PNJ commands a brand premium over smaller jewelers. The agent should track the *spread between shops* as well as the international gap
- **Distinguish between "structural premium" and "timing opportunity."** A VND 5M/tael gap during Tet is normal (structural demand). A VND 5M gap during a quiet August is unusual and potentially a better buying opportunity
- **Include buy/sell spread as a cost factor.** A "buy signal" that ignores the 3-5% round-trip cost on nhẫn trơn will produce negative real returns

**Warning signs:**
- The model treats all gold products the same way
- Seasonal demand periods aren't explicitly modeled
- Buy/sell transaction costs are not factored into signal evaluation
- The agent doesn't explain *why* the gap is wide (demand surge vs. supply shortage vs. speculation)

**Phase to address:**
Phase 1 (Signal model design). Cultural and product-specific factors must be in the model from the start. Phase 2 (Data collection). Need shop-specific price data for nhẫn trơn, not just SJC bars.

---

## Technical Debt Patterns

Shortcuts that seem reasonable but create long-term problems.

| Shortcut | Immediate Benefit | Long-term Cost | When Acceptable |
|----------|-------------------|----------------|-----------------|
| Hardcoded CSS selectors for gold shop scrapers | Works immediately, no infra needed | Breaks silently every time shop updates website, hours of debugging per incident | Never for production. OK for initial prototyping if replaced before users see data |
| Single data source (only SJC.com.vn) | Simple architecture, one scraper to maintain | No cross-validation, no fallback when source goes down, no way to detect stale data | First week of development only. Add second source before Phase 1 complete |
| Caching scraped prices without TTL | Faster dashboard loads, fewer API calls | Stale data served as current, users make decisions on outdated prices, no detection | Only with explicit TTL of < 30 min and visible "last updated" timestamp |
| Using LLM to generate numerical signals (e.g., "gap is 15% → confidence HIGH") | Quick to implement, leverages LLM reasoning | Unpredictable outputs, hallucinated thresholds, non-deterministic, impossible to audit | Never. All numerical calculations and thresholds must be in deterministic code |
| Manual data quality checks ("we'll spot-check daily") | No engineering effort | Inconsistent, doesn't scale, human forgets, gap between check and failure | During first 2 weeks of beta with < 10 users. Automate before public launch |
| Running scraper on single server with no monitoring | Zero infra cost | No alerting when scraper breaks, no redundancy, no incident history | Only for local development. Deploy with monitoring before any user access |

---

## Integration Gotchas

Common mistakes when connecting to external services.

| Integration | Common Mistake | Correct Approach |
|-------------|----------------|------------------|
| SJC.com.vn scraping | Assuming the gold price page is static HTML. It likely loads prices via JavaScript/AJAX after initial page load | Use headless browser (Playwright) for initial scraping. Cache and validate the page structure. Have a fallback to a secondary source |
| International gold APIs (Kitco, etc.) | Assuming API returns data in consistent timezone/format across endpoints | Normalize all timestamps to UTC immediately on ingestion. Validate price format matches expected pattern before storage |
| USD/VND exchange rate (Vietcombank or SBV) | Using the "official" rate for gap calculation when the market rate diverges significantly (4.6% gap observed in 2025) | Track both official and market rates. Use the market rate for gap calculations since that reflects actual import cost. Document which rate is used |
| Telegram/Zalo messenger alerts | Sending raw signal text without formatting, context, or disclaimer. Users forward the alert as "hot tip" | Format alerts with: (1) the signal, (2) the data behind it, (3) the uncertainty, (4) the disclaimer, (5) a link to the full dashboard context |
| State Bank policy news | Trying to auto-scrape policy changes from SBV website (unreliable, delayed, may miss important context) | Use a hybrid approach: automated monitoring of official SBV RSS/channels + manual curation of policy changes by a human who understands the market context |

---

## Performance Traps

Patterns that work at small scale but fail as usage grows.

| Trap | Symptoms | Prevention | When It Breaks |
|------|----------|------------|----------------|
| Scraping on every user request | Dashboard feels responsive, but gold shop servers start rate-limiting or blocking your IP | Cache prices with short TTL (5-15 min). Scrape on schedule, not on demand. Serve from cache | At 50+ concurrent users making repeated page loads |
| Running full signal calculation for every dashboard load | Dashboard takes 10+ seconds to load as data grows | Pre-compute signals on a schedule. Store results. Dashboard reads pre-computed data | At 6+ months of historical data and 5+ macro indicators |
| Storing every scraped price point forever | Database grows unbounded, queries slow down | Implement data retention (keep raw prices for 2 years, aggregate older data to daily summaries) | After 1 year of hourly scraping from 4+ sources |
| Sending individual Telegram messages per user | Rate limits hit, some users don't get alerts, order matters | Batch similar alerts. Use Telegram channel (broadcast) for general signals, individual DMs only for personalized | At 100+ alert recipients |
| LLM call per user query | Slow responses (5-15s), high API costs, rate limits | Cache common responses, use templates for repetitive signal formats, only invoke LLM for novel questions | At 50+ daily queries |

---

## Security Mistakes

Domain-specific security issues beyond general web security.

| Mistake | Risk | Prevention |
|---------|------|------------|
| Storing user phone numbers/Telegram IDs in plaintext | PII exposure if database compromised, Vietnamese cybersecurity law compliance risk | Encrypt PII at rest, minimize data collection, only store what's needed for alerts |
| Exposing scraping target URLs in client-side code | Competitors copy your scraping targets, gold shops detect and block scraping | All scraping logic server-side only. Client never knows source URLs |
| No rate limiting on alert subscription | Spam signups, abuse of messenger integration, potential for phishing | Require verification (Telegram link, Zalo OTP), rate limit signups |
| Scraper credentials (proxies, API keys) in code repository | Compromised scraping infrastructure, financial cost if proxy services are abused | Environment variables, secrets manager, rotate keys regularly |
| No input validation on user preferences (price thresholds, alert targets) | SQL injection if using raw queries, XSS if rendering user inputs | Parameterized queries, sanitize all user inputs, use ORM |

---

## UX Pitfalls

Common user experience mistakes in this domain.

| Pitfall | User Impact | Better Approach |
|---------|-------------|-----------------|
| Showing a single "BUY/SELL" verdict without context | Users treat it as gospel, don't understand the reasoning, blame the agent when wrong | Show the full picture: gap value, historical range, macro factors, seasonal context, uncertainty level. Let the conclusion be implicit |
| Using technical jargon ("SJC-international spread is 2.3 standard deviations above mean") | Regular savers — a core user segment — can't understand the signal | Use plain Vietnamese: "Hiện tại giá vàng SJC cao hơn giá thế giới khoảng 5 triệu/lượng, cao hơn bình thường" |
| No mobile optimization | Vietnamese users access financial info primarily via phone, especially Zalo/Telegram | Mobile-first dashboard. Messenger alerts are more important than the web dashboard for many users |
| Alert fatigue (too many signals) | Users ignore alerts entirely, miss genuinely important signals | Only alert on significant threshold crossings. Let users set their own sensitivity. Don't alert on every minor gap change |
| Showing price data without "last updated" timestamp | Users assume real-time data. If scraper broke 3 days ago, they make decisions on stale prices | Always show "Cập nhật lúc: HH:MM, DD/MM/YYYY". Flash warning if data is stale (> 2 hours) |
| No historical track record visible | Users have no basis to trust the agent's signals. "Why should I listen to this?" | Publish a public track record: "In the last 3 months, X signals were issued. Y% were followed by the expected outcome." Transparency builds trust |

---

## "Looks Done But Isn't" Checklist

Things that appear complete but are missing critical pieces.

- [ ] **Scraper:** Extracts prices in dev but hasn't been tested against real-world scenarios — verify: What happens when the shop website is down? When prices aren't updated (holidays)? When JavaScript rendering fails? When the page structure changes?
- [ ] **Gap calculation:** Converts international price to VND but uses the wrong exchange rate (official vs. market) — verify: Which rate are you using? Does it match what Vietnamese gold shops actually pay for imports?
- [ ] **Signal logic:** Produces buy/sell recommendations in testing — verify: Has the signal been backtested with walk-forward validation on data the model hasn't seen? What's the directional accuracy? Does it beat a naive baseline?
- [ ] **Dashboard:** Shows prices and signals — verify: Is there a "data stale" indicator? Are disclaimers visible? Is there a mobile version? Does it load in under 3 seconds on a mid-range phone?
- [ ] **Messenger alerts:** Send a message when triggered — verify: Do alerts include context (not just "BUY")? Do they include disclaimers? Is there rate limiting to prevent spam? Can users unsubscribe?
- [ ] **Agent responses:** The LLM produces coherent analysis — verify: Are there grounding checks that prevent fabrication of data points? Are responses logged for audit? Is there a fallback if the LLM service is down?
- [ ] **Seasonal model:** Includes Tet and wedding season — verify: Are exact dates mapped for the relevant year? Is the seasonal factor subtracted from gap-based signals (not double-counted)?
- [ ] **Disclaimers:** Legal text exists on the website — verify: Is it visible on the dashboard (not buried in footer)? Is it included in every messenger alert? Does it cover the specific risks of Vietnamese gold market (SBV intervention, gap volatility)?

---

## Recovery Strategies

When pitfalls occur despite prevention, how to recover.

| Pitfall | Recovery Cost | Recovery Steps |
|---------|---------------|----------------|
| Scraper breaks silently | LOW-MEDIUM | 1. Alert triggers on data freshness check. 2. Switch to fallback source. 3. Display "data may be delayed" on dashboard. 4. Fix scraper (usually selector update, 1-4 hours). 5. Backfill missing data from fallback source if available |
| LLM hallucination reaches user | HIGH | 1. Immediately send correction message to affected users. 2. Log the hallucinated output and trace to prompt/context. 3. Add a validation rule to prevent the specific hallucination type. 4. Review and tighten system prompt constraints. 5. Audit recent outputs for similar hallucinations |
| Signal model gives wrong direction | MEDIUM | 1. Signal accuracy tracking catches this automatically. 2. Increase confidence threshold (fewer signals, higher quality). 3. Review which factors the signal missed (SBV intervention? Seasonal? Black swan?). 4. Add missed factor to model or flag as override condition |
| State Bank policy change invalidates model | MEDIUM-HIGH | 1. Human-curated policy feed detects the change. 2. Switch to "reduced confidence" mode automatically. 3. Display "Market structure changed. Signals may be unreliable." 4. Recalibrate model on post-policy-change data (2-4 weeks of new data needed). 5. Resume normal signals only after recalibration |
| User loses money following signal | HIGH | 1. Review signal history and disclaimers shown to user. 2. The disclaimer should legally cover informational-only products. 3. Respond empathetically, review the specific case. 4. If the signal was based on bad data (not bad prediction), fix the data pipeline. 5. Consider publishing a "lessons learned" to build trust through transparency |
| All gold shop sites block scraping | MEDIUM | 1. Switch to any remaining unblocked sources. 2. Reduce scrape frequency dramatically. 3. Investigate proxy rotation and stealth measures. 4. Long-term: explore API partnerships with gold shops or third-party data providers. 5. Manual price entry as last resort (sustainable only at small scale) |

---

## Pitfall-to-Phase Mapping

How roadmap phases should address these pitfalls.

| Pitfall | Prevention Phase | Verification |
|---------|------------------|--------------|
| Gold prediction as solvable ML problem | Phase 1 (Signal design) | Walk-forward backtest shows directional accuracy above naive baseline. Confidence intervals are wide, not narrow |
| LLM hallucinating financial advice | Phase 1 (Agent architecture) | 100% of numerical claims in LLM output match structured data store. Zero fabricated statistics in 100-output audit |
| Scraped data going stale/wrong | Phase 1 (Data pipeline) | Data freshness alerts fire within 30 min of staleness. Cross-source validation catches 95%+ of data errors. Dashboard shows "last updated" timestamp |
| SBV policy invalidating signals | Phase 2 (Policy monitoring) | Policy feed detects major SBV announcements within 24 hours. Signal confidence drops automatically after policy changes |
| Overpromising accuracy / liability | Phase 1 (UX language) + Phase 3 (Legal review) | All user-facing text reviewed by legal. No "predict," "guarantee," or "optimize" language. Disclaimers visible on every output |
| Vietnamese cultural complexity oversimplified | Phase 1 (Signal model) + Phase 2 (Data expansion) | Separate signals for SJC bars vs nhẫn trơn. Seasonal calendar explicitly modeled. Buy/sell spreads included in signal evaluation |
| Alert fatigue | Phase 2 (Messenger integration) | Users can configure alert sensitivity. Average user receives < 2 alerts/week during normal markets. Unsubscribe is one-click |
| Mobile UX failure | Phase 2 (Dashboard) | Dashboard loads < 3s on mid-range phone. Core signal view works on 360px width. Telegram/Zalo alerts contain complete information |

---

## Sources

- AhaSignals research on gold forecast consensus gap (March 2026) — HIGH confidence
- FINRA 2026 Annual Regulatory Oversight Report on GenAI hallucinations and AI agents — HIGH confidence
- Debevoise analysis of FINRA 2026 report on GenAI governance expectations — HIGH confidence
- SEC speech on AI and investment management (Feb 2026) — HIGH confidence
- VietNamNet / Vietnam Investment Review / The Investor reporting on Vietnam gold market dynamics (2025-2026) — HIGH confidence for factual claims, MEDIUM for expert opinions
- World Gold Council (WGC) reporting on Vietnam gold price gap (Dec 2024-May 2025) — HIGH confidence
- State Bank of Vietnam reports to National Assembly on gold market (2025) — HIGH confidence
- Decree 24 / Decree 232 on gold trading management — HIGH confidence
- Research papers on gold price forecasting (Springer, ResearchGate 2025-2026) — MEDIUM confidence (academic, but limitations acknowledged by authors)
- Betterment SEC settlement ($9M, 2023) — HIGH confidence
- Charles Schwab SEC settlement ($187M, 2022) — HIGH confidence
- Web scraping pitfall articles (Firecrawl, AIMultiple, BinaryBits, ScrapeGraphAI, Grepsr 2025-2026) — MEDIUM-HIGH confidence (industry consensus, consistent findings across sources)
- DLA Piper / WilmerHale analysis of FINRA AI guidance — HIGH confidence

---

*Pitfalls research for: Vietnamese Gold Advisory Agent*
*Researched: 2026-03-25*
