# Phase 2 Discovery: Vietnamese Gold Price Scraping

**Discovered:** 2026-03-25
**Level:** 2 — Standard Research (multiple external sources, integration patterns)
**Confidence:** MEDIUM-HIGH

## Dealer Website Analysis

### 1. DOJI — `giavang.doji.vn` (BEST TARGET — Static HTML)

| Property | Value |
|----------|-------|
| URL | `https://giavang.doji.vn` |
| Format | Static HTML with plain text prices |
| JS Rendering | NO — httpx + BeautifulSoup sufficient |
| Confidence | HIGH — verified via live fetch |

**Data fields:** SJC bar buy/sell, Ring gold (9999) buy/sell, Raw material 99.99/99.9 buy/sell, Jewelry gold 9999/999/99 buy/sell, Update timestamp, Regional tables (HN, DN, HCM)
**Unit:** nghìn/chỉ (×10,000 = VND/lượng)
**Parsing:** Clean text in table cells, regex or BS4 text extraction

### 2. Phú Quý — `phuquygroup.vn` (EXCELLENT — Static HTML)

| Property | Value |
|----------|-------|
| URL | `https://phuquygroup.vn` |
| Format | Static HTML with price table |
| JS Rendering | NO — httpx + BeautifulSoup sufficient |
| Confidence | HIGH — verified via live fetch |

**Data fields:** SJC bar buy/sell, Phu Quy ring gold 999.9 buy/sell, Jewelry gold 999.9/999/99/98 buy/sell, Raw gold 999.9/999.0 buy, Silver buy/sell, Update timestamp
**Unit:** VNĐ/Chỉ (×10 = VND/lượng)

### 3. BTMC — `api.btmc.vn/api/BTMCAPI/getpricebtmc` (JSON API — unverified)

| Property | Value |
|----------|-------|
| URL | `https://api.btmc.vn/api/BTMCAPI/getpricebtmc` |
| Format | JSON API (REST) |
| JS Rendering | NO — httpx JSON response |
| Confidence | MEDIUM — endpoint confirmed but connection refused from outside VN |

**Data fields:** SJC bar buy/sell, Ring gold (Vàng Rồng) buy/sell, Jewelry gold buy/sell
**Risk:** May require Vietnam-origin IP. Fallback: Playwright scrape of btmc.vn website.

### 4. SJC — `sjc.com.vn/giavang/textContent.php` (JS-rendered)

| Property | Value |
|----------|-------|
| URL | `https://sjc.com.vn/giavang/textContent.php` |
| Format | HTML table (data injected via JS/AJAX) |
| JS Rendering | YES — Playwright required |
| Confidence | HIGH — confirmed by namtrhg/vn-gold-price-api reference |

**Data fields:** SJC bar buy/sell, SJC ring buy/sell, Update timestamp
**Unit:** nghìn đồng/lượng (×1,000 = VND/lượng)
**CSS Selectors** (from namtrhg repo): `document.querySelectorAll("table tbody tr")`, timestamp via `.w350.m5l.float_left.red_text.bg_white`
**Risk:** 404 from outside VN, may need specific User-Agent or VN-origin IP

### 5. PNJ — `giavang.pnj.com.vn` (React SPA)

| Property | Value |
|----------|-------|
| URL | `https://www.giavang.pnj.com.vn` |
| Format | React SPA (`<div id="root"></div>`) |
| JS Rendering | YES — Playwright required |
| Confidence | HIGH — confirmed React SPA |

**Data fields:** SJC bar buy/sell, PNJ ring gold buy/sell, PNJ jewelry gold buy/sell, Update timestamp
**CSS Selectors** (from namtrhg repo): `.bang-gia-vang-outer table`, timestamp `#time-now`
**Risk:** Cloudflare protection possible. Uses cache-buster `?r=timestamp`.

### 6. Mi Hồng — NO PUBLIC API FOUND

No public gold price page, API endpoint, or scraping patterns discovered. Skip for Phase 2. With SJC + DOJI + PNJ + BTMC + Phú Quý = 5 dealers, DATA-01 is satisfied.

## Unit Conversion Reference

| Dealer | Unit | Conversion to VND/lượng |
|--------|------|------------------------|
| DOJI | nghìn/chỉ | ×10,000 |
| Phú Quý | VNĐ/Chỉ | ×10 |
| SJC | nghìn đồng/lượng | ×1,000 |
| BTMC | Unknown (needs VN test) | TBD |
| PNJ | Unknown (needs Playwright test) | TBD |

Standard storage unit: **VND/lượng** (to match existing PriceRecord pattern from Phase 1 where `price_vnd` is per lượng).

## Reference: namtrhg/vn-gold-price-api

Node.js/Express + Puppeteer scraper covering SJC, DOJI, PNJ. Only 3 dealers. Uses Puppeteer even for static DOJI page. Last updated Mar 2024. Confirms HTML structure and CSS selectors for SJC and PNJ.

## Scraping Priority

1. **DOJI** — static HTML, most reliable, provides SJC bar + ring gold
2. **Phú Quý** — static HTML, reliable, provides SJC bar + ring gold
3. **BTMC** — JSON API if accessible, cleanest data source if it works
4. **SJC** — needs Playwright, primary brand but harder to scrape
5. **PNJ** — needs Playwright, Cloudflare risk, lowest priority

## Key Risks

1. **VN-only access**: SJC, BTMC may block non-Vietnam IPs. Plan: test from VN server, add proxy support if needed.
2. **HTML structure changes**: All HTML-based scrapers are fragile. Plan: quality checks detect stale/broken data (PITFALLS.md §3).
3. **Playwright complexity**: Adds browser binary dependency. Plan: install only when needed (Plans 02+).

## Dependencies to Add

- `beautifulsoup4>=4.12` — HTML parsing for DOJI, Phú Quý
- `lxml>=5.0` — Fast HTML parser (BS4 backend)
- `playwright>=1.49` — JS rendering for SJC, PNJ (Plan 02)

## Normalizer Compatibility

The existing `fetch_and_store()` function works for VND-native prices:
- Condition `fetched_price.currency == "USD"` skips USD→VND conversion → ✅
- Anomaly checks compare `price_vnd` → ✅ (Vietnamese scrapers set `price_vnd`)
- Freshness checks work per source → ✅
- Source name extraction: `"ClassName".replace("Fetcher", "")` doesn't handle "Scraper" suffix → ⚠️ NEEDS FIX

---
*Discovery for: 02-vietnamese-gold-price-scraping*
*Completed: 2026-03-25*
