"""Fetches historical Polymarket price data from the CLOB API.

CLOB API: GET https://clob.polymarket.com/prices-history
  - market: clobTokenId (YES token)
  - startTs / endTs: unix seconds (always use these, not interval=max)
  - fidelity: minutes (default 1)
  - Rate limit: 1,000 req / 10s
  - No auth required
"""

from __future__ import annotations

import asyncio
import logging
import time
from dataclasses import dataclass

import httpx

logger = logging.getLogger(__name__)

CLOB_PRICES_URL = "https://clob.polymarket.com/prices-history"
CLOB_DATA_URL = "https://data-api.polymarket.com/trades"
CHUNK_SECONDS = 15 * 86400  # 15 days
BATCH_DELAY = 11.0  # seconds between batches (rate limit: 1000/10s)


@dataclass
class PricePoint:
    t: int  # unix timestamp (seconds)
    p: float  # price 0.0 - 1.0


async def fetch_price_history(
    client: httpx.AsyncClient,
    token_id: str,
    start_ts: int,
    end_ts: int,
    fidelity: int = 60,
) -> list[PricePoint]:
    """Fetch price history in 15-day chunks with rate limiting.

    Uses startTs/endTs instead of interval=max to avoid timeout bugs
    on long-lived or resolved markets.
    """
    all_points: list[PricePoint] = []
    current_start = start_ts

    while current_start < end_ts:
        current_end = min(current_start + CHUNK_SECONDS, end_ts)

        try:
            logger.debug(
                "→ Polymarket CLOB /prices-history %s [%d→%d]",
                token_id[:12],
                current_start,
                current_end,
            )
            resp = await client.get(
                CLOB_PRICES_URL,
                params={
                    "market": token_id,
                    "startTs": current_start,
                    "endTs": current_end,
                    "fidelity": fidelity,
                },
                timeout=30.0,
            )
            resp.raise_for_status()
            data = resp.json()
            history = data.get("history", [])
            for point in history:
                all_points.append(PricePoint(t=point["t"], p=point["p"]))

            remaining = int(resp.headers.get("X-RateLimit-Remaining", "999"))
            if remaining < 50:
                reset_ts = int(resp.headers.get("X-RateLimit-Reset", "0"))
                wait = max(reset_ts - time.time() + 0.5, 1.0)
                logger.debug(
                    "Rate limit low (%d remaining), waiting %.1fs", remaining, wait
                )
                await asyncio.sleep(wait)
            else:
                await asyncio.sleep(1.0)

        except httpx.HTTPStatusError as e:
            if e.response.status_code == 429:
                logger.warning("Rate limited for token %s, waiting 15s", token_id[:16])
                await asyncio.sleep(15.0)
                continue
            logger.warning(
                "HTTP %d fetching price history for %s: %s",
                e.response.status_code,
                token_id[:16],
                e,
            )
            break
        except Exception:
            logger.warning(
                "Error fetching price history for %s", token_id[:16], exc_info=True
            )
            break

        current_start = current_end

    return all_points


async def fetch_price_history_fallback(
    client: httpx.AsyncClient,
    token_id: str,
) -> list[PricePoint]:
    """Fallback to Data API /trades for resolved markets where prices-history is empty."""
    try:
        logger.debug("→ Polymarket CLOB /data/trades %s (fallback)", token_id[:12])
        resp = await client.get(
            params={"asset": token_id, "limit": 100},
            timeout=30.0,
        )
        resp.raise_for_status()
        trades = resp.json()
        points = []
        for trade in trades:
            price = trade.get("price")
            ts = trade.get("timestamp") or trade.get("createdAt")
            if price is not None and ts is not None:
                try:
                    points.append(PricePoint(t=int(ts), p=float(price)))
                except (ValueError, TypeError):
                    continue
        return points
    except Exception:
        logger.warning("Data API fallback failed for %s", token_id[:16], exc_info=True)
        return []
