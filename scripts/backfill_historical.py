#!/usr/bin/env python
"""
One-time backfill script for historical gold price data.

Populates the price_history table with ~2 years of historical data:
- SJC bar gold prices from sjc.com.vn API (ring gold not available in historical endpoint)
- XAU/USD, USD/VND, DXY from yfinance

Usage:
    uv run python scripts/backfill_historical.py
    uv run python scripts/backfill_historical.py --dry-run
    uv run python scripts/backfill_historical.py --force
"""

import argparse
import logging
import re
import sqlite3
import time
from datetime import datetime, timedelta, time as dt_time
from typing import Any

import httpx
import yfinance

# Suppress yfinance logging
logging.getLogger("yfinance").setLevel(logging.CRITICAL)
logging.getLogger("peewee").setLevel(logging.CRITICAL)
logging.getLogger("urllib3").setLevel(logging.CRITICAL)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)

DB_PATH = "gold_advisor.db"
SJC_API_URL = "https://sjc.com.vn/GoldPrice/Services/PriceService.ashx"
SJC_HEADERS = {
    "Content-Type": "application/x-www-form-urlencoded",
    "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
    "X-Requested-With": "XMLHttpRequest",
    "Referer": "https://sjc.com.vn/",
    "Origin": "https://sjc.com.vn",
}

# Cutoff date: existing data starts from 2026-03-25, so skip anything on or after that
CUTOFF_DATE = datetime(2026, 3, 25)


def get_db_connection() -> sqlite3.Connection:
    """Create a database connection."""
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def clear_historical_data(conn: sqlite3.Connection) -> int:
    """Clear all historical data before the cutoff date."""
    cursor = conn.cursor()
    cursor.execute(
        "DELETE FROM price_history WHERE timestamp < ?",
        (CUTOFF_DATE.strftime("%Y-%m-%d %H:%M:%S"),),
    )
    deleted = cursor.rowcount
    conn.commit()
    return deleted


def record_exists(
    conn: sqlite3.Connection,
    source: str,
    product_type: str,
    timestamp: datetime,
) -> bool:
    """Check if a record already exists."""
    cursor = conn.cursor()
    cursor.execute(
        """
        SELECT 1 FROM price_history
        WHERE source = ? AND product_type = ? AND timestamp = ?
        """,
        (source, product_type, timestamp.strftime("%Y-%m-%d %H:%M:%S")),
    )
    return cursor.fetchone() is not None


def insert_price_record(
    conn: sqlite3.Connection,
    source: str,
    product_type: str,
    buy_price: float | None,
    sell_price: float | None,
    price_usd: float | None,
    price_vnd: float | None,
    currency: str,
    timestamp: datetime,
    dry_run: bool = False,
) -> bool:
    """Insert a price record into the database."""
    if record_exists(conn, source, product_type, timestamp):
        logger.debug(
            f"Skipping duplicate: {source}/{product_type} @ {timestamp.date()}"
        )
        return False

    fetched_at = datetime.utcnow()
    spread = None
    if buy_price is not None and sell_price is not None:
        spread = sell_price - buy_price

    if dry_run:
        logger.info(
            f"[DRY-RUN] Would insert: {source}/{product_type} @ {timestamp.date()} "
            f"buy={buy_price} sell={sell_price} price_usd={price_usd} price_vnd={price_vnd}"
        )
        return True

    cursor = conn.cursor()
    cursor.execute(
        """
        INSERT INTO price_history (
            source, product_type, buy_price, sell_price,
            price_usd, price_vnd, currency, timestamp,
            fetched_at, spread, validation_status
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            source,
            product_type,
            buy_price,
            sell_price,
            price_usd,
            price_vnd,
            currency,
            timestamp.strftime("%Y-%m-%d %H:%M:%S"),
            fetched_at.strftime("%Y-%m-%d %H:%M:%S"),
            spread,
            "valid",
        ),
    )
    conn.commit()
    return True


def parse_sjc_product_type(type_name: str) -> str | None:
    """
    Parse SJC product type from TypeName.

    Returns:
        'sjc_bar' for SJC gold bars (not rings)
        'ring_gold' for gold rings
        None for other products
    """
    type_name_lower = type_name.lower()

    # Check for rings first (more specific)
    if re.search(r"vàng\s+nhẫn", type_name_lower) or "nhẫn" in type_name_lower:
        return "ring_gold"

    # Check for SJC bars (must contain "Vàng SJC" but not be rings)
    if re.search(r"vàng\s+sjc", type_name_lower) and "nhẫn" not in type_name_lower:
        return "sjc_bar"

    return None


def fetch_sjc_prices(date: datetime) -> dict[str, dict[str, Any]] | None:
    """
    Fetch SJC gold prices for a specific date.

    Returns:
        Dict mapping product_type to price data, or None if fetch failed.
    """
    date_str = date.strftime("%d/%m/%Y")

    try:
        with httpx.Client(timeout=30.0) as client:
            response = client.post(
                SJC_API_URL,
                headers=SJC_HEADERS,
                data=f"method=GetSJCGoldPriceByDate&toDate={date_str}",
            )
            response.raise_for_status()
            data = response.json()

        if not data.get("success"):
            logger.warning(f"SJC API returned success=false for {date_str}")
            return None

        # Parse the actual date from response (handles holidays/weekends)
        current_date_str = data.get("currentDate")
        if current_date_str:
            actual_date = datetime.strptime(current_date_str, "%d/%m/%Y")
        else:
            actual_date = date

        results: dict[str, dict[str, Any]] = {}

        for item in data.get("data", []):
            branch = item.get("BranchName", "")
            if branch != "Hồ Chí Minh":
                continue

            type_name = item.get("TypeName", "")
            product_type = parse_sjc_product_type(type_name)

            if product_type is None:
                continue

            buy_value = item.get("BuyValue")
            sell_value = item.get("SellValue")

            # Convert to float if they're strings
            if isinstance(buy_value, str):
                buy_value = float(buy_value.replace(",", ""))
            if isinstance(sell_value, str):
                sell_value = float(sell_value.replace(",", ""))

            results[product_type] = {
                "buy_price": buy_value,
                "sell_price": sell_value,
                "timestamp": actual_date,
            }

        return results

    except Exception as e:
        logger.error(f"Error fetching SJC prices for {date_str}: {e}")
        return None


def backfill_sjc(conn: sqlite3.Connection, dry_run: bool = False) -> dict[str, int]:
    """
    Backfill SJC historical data.

    Returns:
        Dict with counts per product_type.
    """
    logger.info("Starting SJC historical backfill...")

    end_date = CUTOFF_DATE - timedelta(days=1)
    start_date = end_date - timedelta(days=730)

    counts: dict[str, int] = {"sjc_bar": 0, "ring_gold": 0}
    current_date = start_date
    total_days = (end_date - start_date).days + 1
    processed = 0

    logger.info(
        f"Fetching SJC data from {start_date.date()} to {end_date.date()} ({total_days} days)"
    )

    while current_date <= end_date:
        processed += 1

        if processed % 50 == 0:
            logger.info(f"Progress: {processed}/{total_days} days processed")

        prices = fetch_sjc_prices(current_date)

        if prices:
            for product_type, price_data in prices.items():
                # Check if this date is before cutoff
                if price_data["timestamp"] >= CUTOFF_DATE:
                    logger.debug(
                        f"Skipping {product_type} @ {price_data['timestamp'].date()} (>= cutoff)"
                    )
                    continue

                inserted = insert_price_record(
                    conn=conn,
                    source="sjc",
                    product_type=product_type,
                    buy_price=price_data["buy_price"],
                    sell_price=price_data["sell_price"],
                    price_usd=None,
                    price_vnd=price_data["buy_price"],
                    currency="VND",
                    timestamp=price_data["timestamp"],
                    dry_run=dry_run,
                )

                if inserted:
                    counts[product_type] = counts.get(product_type, 0) + 1

        # Rate limiting
        time.sleep(0.3)
        current_date += timedelta(days=1)

    logger.info(f"SJC backfill complete: {counts}")
    return counts


def backfill_yfinance(
    conn: sqlite3.Connection, dry_run: bool = False
) -> dict[str, int]:
    """
    Backfill yfinance historical data.

    Returns:
        Dict with counts per product_type.
    """
    logger.info("Starting yfinance historical backfill...")

    tickers_config = {
        "GC=F": {"product_type": "xau_usd", "currency": "USD"},
        "USDVND=X": {"product_type": "usd_vnd", "currency": "VND"},
        "DX-Y.NYB": {"product_type": "dxy", "currency": "USD"},
    }

    counts: dict[str, int] = {}

    for ticker_symbol, config in tickers_config.items():
        product_type = config["product_type"]
        currency = config["currency"]

        logger.info(f"Downloading {ticker_symbol} ({product_type})...")

        try:
            ticker = yfinance.Ticker(ticker_symbol)
            df = ticker.history(period="2y", interval="1d")

            if df.empty:
                logger.warning(f"No data returned for {ticker_symbol}")
                continue

            logger.info(f"Downloaded {len(df)} rows for {ticker_symbol}")

            inserted_count = 0

            for date_idx, row in df.iterrows():
                # Convert pandas Timestamp to Python datetime (noon UTC)
                date = date_idx.to_pydatetime().date()
                timestamp = datetime.combine(date, dt_time(12, 0))

                # Skip if on or after cutoff
                if timestamp >= CUTOFF_DATE:
                    continue

                close_price = float(row["Close"])

                inserted = insert_price_record(
                    conn=conn,
                    source="yfinance",
                    product_type=product_type,
                    buy_price=close_price,
                    sell_price=close_price,
                    price_usd=close_price if currency == "USD" else None,
                    price_vnd=close_price if currency == "VND" else None,
                    currency=currency,
                    timestamp=timestamp,
                    dry_run=dry_run,
                )

                if inserted:
                    inserted_count += 1

            counts[product_type] = inserted_count
            logger.info(f"Inserted {inserted_count} rows for {product_type}")

        except Exception as e:
            logger.error(f"Error fetching {ticker_symbol}: {e}")

    logger.info(f"yfinance backfill complete: {counts}")
    return counts


def print_summary(
    sjc_counts: dict[str, int],
    yfinance_counts: dict[str, int],
    conn: sqlite3.Connection,
) -> None:
    """Print a summary of the backfill."""
    logger.info("=" * 60)
    logger.info("BACKFILL SUMMARY")
    logger.info("=" * 60)

    # SJC data
    logger.info("\nSJC Data (from sjc.com.vn API):")
    for product_type, count in sjc_counts.items():
        logger.info(f"  {product_type}: {count} rows")

    # yfinance data
    logger.info("\nyfinance Data:")
    for product_type, count in yfinance_counts.items():
        logger.info(f"  {product_type}: {count} rows")

    # Database stats
    cursor = conn.cursor()
    cursor.execute(
        """
        SELECT source, product_type, MIN(timestamp) as min_date,
               MAX(timestamp) as max_date, COUNT(*) as count
        FROM price_history
        GROUP BY source, product_type
        ORDER BY source, product_type
        """
    )

    logger.info("\nDatabase contents after backfill:")
    for row in cursor.fetchall():
        logger.info(
            f"  {row['source']}/{row['product_type']}: "
            f"{row['count']} rows, {row['min_date']} to {row['max_date']}"
        )

    # Total
    cursor.execute("SELECT COUNT(*) as total FROM price_history")
    total = cursor.fetchone()["total"]
    logger.info(f"\nTotal rows in price_history: {total}")
    logger.info("=" * 60)


def main() -> None:
    parser = argparse.ArgumentParser(description="Backfill historical gold price data")
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Print what would be inserted without actually inserting",
    )
    parser.add_argument(
        "--force",
        action="store_true",
        help="Clear existing historical data before backfill (use with caution)",
    )
    args = parser.parse_args()

    logger.info("Starting historical data backfill...")
    logger.info(f"Dry run: {args.dry_run}")
    logger.info(f"Force clear: {args.force}")
    logger.info(
        f"Cutoff date: {CUTOFF_DATE.date()} (data on/after this date will be skipped)"
    )

    conn = get_db_connection()

    try:
        if args.force and not args.dry_run:
            logger.warning("Force flag set - clearing existing historical data...")
            deleted = clear_historical_data(conn)
            logger.info(f"Deleted {deleted} existing rows")

        # Backfill SJC data
        sjc_counts = backfill_sjc(conn, dry_run=args.dry_run)

        # Backfill yfinance data
        yfinance_counts = backfill_yfinance(conn, dry_run=args.dry_run)

        # Print summary
        print_summary(sjc_counts, yfinance_counts, conn)

    finally:
        conn.close()

    logger.info("Backfill complete!")


if __name__ == "__main__":
    main()
