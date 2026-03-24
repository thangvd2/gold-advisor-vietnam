# Phase 1: Project Foundation & International Data - Discussion Log

> **Audit trail only.** Do not use as input to planning, research, or execution agents.
> Decisions are captured in CONTEXT.md — this log preserves the alternatives considered.

**Date:** 2026-03-25
**Phase:** 1-project-foundation-international-data
**Areas discussed:** International gold price API, USD/VND exchange rate source

---

## Gold Price API Source

| Option | Description | Selected |
|--------|-------------|----------|
| Paid gold API (Recommended) | GoldAPI.io basic tier (~$10/mo) — dedicated gold API, reliable, supports VND directly | |
| Free first, pay if needed | Try free sources first (yfinance, etc.), pay only if free is unreliable | ✓ |
| I'll specify | User has a specific API or preference | |

**User's choice:** Free first, pay if needed
**Notes:** User prefers to start with free sources and only pay if they prove unreliable during testing. Researcher should evaluate available free options (yfinance, Frankfurter, etc.) during phase research.

---

## USD/VND Exchange Rate

| Option | Description | Selected |
|--------|-------------|----------|
| Market rate (Recommended) | Vietcombank or similar — reflects actual import costs, more accurate for gap calc | ✓ |
| Official SBV rate | More stable but can diverge 4-5% from market rate | |
| Both rates | Track both, use market for gap calc, show official as reference | |

**User's choice:** Market rate (Recommended)
**Notes:** PITFALLS.md explicitly warns about 4.6% divergence between official and market rates. Market rate is more accurate for the SJC-international gap calculation.

---

## Claude's Discretion

- Specific free gold price API selection
- Data quality threshold values
- Database schema details
- Project directory structure
- APScheduler integration pattern

## Deferred Ideas

None
