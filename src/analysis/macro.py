from datetime import datetime, timedelta, timezone

from src.analysis.connection import get_duckdb_connection


def calculate_fx_trend(db_path: str, lookback_days: int = 30) -> dict | None:
    cutoff = datetime.now(timezone.utc) - timedelta(days=lookback_days)

    con = get_duckdb_connection(db_path)
    try:
        cursor = con.execute(
            """
            WITH prices AS (
                SELECT timestamp, sell_price as rate
                FROM db.price_history
                WHERE product_type = 'usd_vnd'
                  AND sell_price IS NOT NULL
                  AND sell_price > 0
                  AND timestamp >= ?
                ORDER BY timestamp ASC
            ),
            with_ma AS (
                SELECT
                    timestamp,
                    rate,
                    CASE WHEN row_number() OVER () >= 7
                        THEN AVG(rate) OVER (ORDER BY timestamp ROWS BETWEEN 6 PRECEDING AND CURRENT ROW)
                    END as ma_7d,
                    CASE WHEN row_number() OVER () >= 30
                        THEN AVG(rate) OVER (ORDER BY timestamp ROWS BETWEEN 29 PRECEDING AND CURRENT ROW)
                    END as ma_30d
                FROM prices
            )
            SELECT rate, ma_7d, ma_30d
            FROM with_ma
            ORDER BY timestamp DESC
            LIMIT 1
            """,
            [cutoff],
        )

        result = cursor.fetchone()
        if result is None:
            return None

        current_rate, ma_7d, ma_30d = result
        if current_rate is None:
            return None

        reference_ma = ma_30d if ma_30d is not None else ma_7d
        if reference_ma is None:
            return None

        change_pct = (current_rate - reference_ma) / reference_ma * 100

        if change_pct > 1.0:
            trend = "up"
        elif change_pct < -1.0:
            trend = "down"
        else:
            trend = "neutral"

        return {
            "current_rate": float(current_rate),
            "ma_7d": float(ma_7d) if ma_7d is not None else None,
            "ma_30d": float(ma_30d) if ma_30d is not None else None,
            "trend": trend,
            "change_pct": round(float(change_pct), 2),
        }
    finally:
        con.close()


def calculate_gold_trend(db_path: str, lookback_days: int = 30) -> dict | None:
    cutoff = datetime.now(timezone.utc) - timedelta(days=lookback_days)

    con = get_duckdb_connection(db_path)
    try:
        cursor = con.execute(
            """
            WITH prices AS (
                SELECT timestamp, price_usd
                FROM db.price_history
                WHERE product_type = 'xau_usd'
                  AND price_usd IS NOT NULL
                  AND price_usd > 0
                  AND timestamp >= ?
                ORDER BY timestamp ASC
            ),
            with_ma AS (
                SELECT
                    timestamp,
                    price_usd,
                    CASE WHEN row_number() OVER () >= 7
                        THEN AVG(price_usd) OVER (ORDER BY timestamp ROWS BETWEEN 6 PRECEDING AND CURRENT ROW)
                    END as ma_7d,
                    CASE WHEN row_number() OVER () >= 30
                        THEN AVG(price_usd) OVER (ORDER BY timestamp ROWS BETWEEN 29 PRECEDING AND CURRENT ROW)
                    END as ma_30d
                FROM prices
            )
            SELECT price_usd, ma_7d, ma_30d
            FROM with_ma
            ORDER BY timestamp DESC
            LIMIT 1
            """,
            [cutoff],
        )

        result = cursor.fetchone()
        if result is None:
            return None

        current_price, ma_7d, ma_30d = result
        if current_price is None:
            return None

        reference_ma = ma_30d if ma_30d is not None else ma_7d
        if reference_ma is None:
            return None

        change_pct = (current_price - reference_ma) / reference_ma * 100

        if change_pct > 1.0:
            trend = "up"
        elif change_pct < -1.0:
            trend = "down"
        else:
            trend = "neutral"

        return {
            "current_price": float(current_price),
            "ma_7d": float(ma_7d) if ma_7d is not None else None,
            "ma_30d": float(ma_30d) if ma_30d is not None else None,
            "trend": trend,
            "momentum": round(float(change_pct), 2),
        }
    finally:
        con.close()
