from datetime import datetime, timedelta, timezone

from src.analysis.connection import get_duckdb_connection

RANGE_MAP = {
    "1D": timedelta(days=1),
    "1W": timedelta(days=7),
    "1M": timedelta(days=30),
    "3M": timedelta(days=90),
    "1Y": timedelta(days=365),
}


def calculate_dealer_spreads(db_path: str) -> list[float]:
    con = get_duckdb_connection(db_path)
    try:
        cursor = con.execute("""
            WITH latest_per_dealer AS (
                SELECT source, sell_price, buy_price,
                       ROW_NUMBER() OVER (PARTITION BY source ORDER BY timestamp DESC) as rn
                FROM db.price_history
                WHERE product_type = 'sjc_bar'
                  AND sell_price IS NOT NULL
            )
            SELECT (sell_price - buy_price) / sell_price * 100 as spread_pct
            FROM latest_per_dealer
            WHERE rn = 1 AND buy_price IS NOT NULL AND sell_price > 0
        """)
        return [float(row[0]) for row in cursor.fetchall()]
    finally:
        con.close()


def calculate_current_gap(db_path: str | str) -> dict | None:
    con = get_duckdb_connection(db_path)
    try:
        cursor = con.execute("""
            WITH latest_intl AS (
                SELECT price_vnd, price_usd, timestamp
                FROM db.price_history
                WHERE product_type = 'xau_usd'
                  AND price_vnd IS NOT NULL
                ORDER BY timestamp DESC
                LIMIT 1
            ),
            latest_domestic AS (
                SELECT AVG(sell_price) as avg_sjc_sell,
                       COUNT(DISTINCT source) as dealer_count
                FROM db.price_history
                WHERE product_type = 'sjc_bar'
                  AND sell_price IS NOT NULL
                  AND timestamp = (
                      SELECT MAX(timestamp)
                      FROM db.price_history
                      WHERE product_type = 'sjc_bar'
                  )
            )
            SELECT
                d.avg_sjc_sell - i.price_vnd as gap_vnd,
                (d.avg_sjc_sell - i.price_vnd) / i.price_vnd * 100 as gap_pct,
                d.avg_sjc_sell,
                i.price_vnd as intl_price_vnd,
                i.price_usd as intl_price_usd,
                d.dealer_count,
                i.timestamp
            FROM latest_intl i, latest_domestic d
        """)

        result = cursor.fetchone()

        if result is None:
            return None

        columns = [desc[0] for desc in cursor.description]
        row = dict(zip(columns, result))
        if row["avg_sjc_sell"] is None or row["intl_price_vnd"] is None:
            return None

        row["gap_vnd"] = float(row["gap_vnd"])
        row["gap_pct"] = float(row["gap_pct"])
        row["avg_sjc_sell"] = float(row["avg_sjc_sell"])
        row["intl_price_vnd"] = float(row["intl_price_vnd"])
        row["intl_price_usd"] = float(row["intl_price_usd"])
        row["dealer_count"] = int(row["dealer_count"])
        row["timestamp"] = row["timestamp"].isoformat()
        return row
    finally:
        con.close()


def calculate_historical_gaps(db_path: str, range: str = "1W") -> list[dict]:
    if range not in RANGE_MAP:
        raise ValueError(
            f"Invalid range: {range}. Must be one of {list(RANGE_MAP.keys())}"
        )

    cutoff = datetime.now(timezone.utc) - RANGE_MAP[range]

    con = get_duckdb_connection(db_path)
    try:
        cursor = con.execute(
            """
            WITH intl AS (
                SELECT
                    to_timestamp(floor(epoch(cast(timestamp as timestamp)) / 300) * 300) as bucket,
                    AVG(price_vnd) as intl_price_vnd
                FROM db.price_history
                WHERE product_type = 'xau_usd'
                  AND price_vnd IS NOT NULL
                GROUP BY 1
            ),
            domestic AS (
                SELECT
                    to_timestamp(floor(epoch(cast(timestamp as timestamp)) / 300) * 300) as bucket,
                    AVG(sell_price) as avg_sjc_sell
                FROM db.price_history
                WHERE product_type = 'sjc_bar'
                  AND sell_price IS NOT NULL
                GROUP BY 1
            ),
            joined AS (
                SELECT
                    COALESCE(i.bucket, d.bucket) as bucket_ts,
                    i.intl_price_vnd,
                    d.avg_sjc_sell,
                    CASE
                        WHEN i.intl_price_vnd IS NOT NULL AND d.avg_sjc_sell IS NOT NULL
                        THEN d.avg_sjc_sell - i.intl_price_vnd
                    END as gap_vnd,
                    CASE
                        WHEN i.intl_price_vnd IS NOT NULL AND d.avg_sjc_sell IS NOT NULL AND i.intl_price_vnd > 0
                        THEN (d.avg_sjc_sell - i.intl_price_vnd) / i.intl_price_vnd * 100
                    END as gap_pct
                FROM intl i
                FULL OUTER JOIN domestic d ON i.bucket = d.bucket
            )
            SELECT
                bucket_ts,
                gap_vnd,
                gap_pct,
                CASE WHEN bucket_ts - MIN(bucket_ts) OVER () >= INTERVAL 7 DAYS
                    THEN AVG(gap_pct) OVER (
                        ORDER BY bucket_ts ASC
                        RANGE BETWEEN INTERVAL 6 DAYS PRECEDING AND CURRENT ROW
                    )
                END as ma_7d,
                CASE WHEN bucket_ts - MIN(bucket_ts) OVER () >= INTERVAL 30 DAYS
                    THEN AVG(gap_pct) OVER (
                        ORDER BY bucket_ts ASC
                        RANGE BETWEEN INTERVAL 29 DAYS PRECEDING AND CURRENT ROW
                    )
                END as ma_30d
            FROM joined
            WHERE bucket_ts >= ?
            ORDER BY bucket_ts ASC
        """,
            [cutoff],
        )

        columns = [desc[0] for desc in cursor.description]
        rows = [dict(zip(columns, r)) for r in cursor.fetchall()]

        return [
            {
                "timestamp": r["bucket_ts"].isoformat(),
                "gap_vnd": float(r["gap_vnd"]) if r["gap_vnd"] is not None else None,
                "gap_pct": float(r["gap_pct"]) if r["gap_pct"] is not None else None,
                "ma_7d": float(r["ma_7d"]) if r["ma_7d"] is not None else None,
                "ma_30d": float(r["ma_30d"]) if r["ma_30d"] is not None else None,
            }
            for r in rows
        ]
    finally:
        con.close()


def get_local_ring_gold_data(db_path: str) -> dict:
    cutoff = datetime.now(timezone.utc) - timedelta(days=30)

    result = {
        "latest_buy": None,
        "latest_sell": None,
        "spread_vnd": None,
        "spread_pct": None,
        "price_history": [],
        "trend_7d": None,
        "trend_30d": None,
        "data_points": 0,
    }

    con = get_duckdb_connection(db_path)
    try:
        cursor = con.execute("""
            SELECT buy_price, sell_price, timestamp
            FROM db.price_history
            WHERE source = 'local' AND product_type = 'ring_gold'
            ORDER BY timestamp DESC
            LIMIT 1
        """)
        latest = cursor.fetchone()

        if latest is None:
            return result

        latest_buy, latest_sell, _ = latest
        result["latest_buy"] = float(latest_buy) if latest_buy is not None else None
        result["latest_sell"] = float(latest_sell) if latest_sell is not None else None

        if latest_buy is not None and latest_sell is not None and latest_sell > 0:
            result["spread_vnd"] = float(latest_sell - latest_buy)
            result["spread_pct"] = float((latest_sell - latest_buy) / latest_sell * 100)

        cursor = con.execute(
            """
            SELECT
                DATE(timestamp) as day,
                AVG(buy_price) as avg_buy,
                AVG(sell_price) as avg_sell
            FROM db.price_history
            WHERE source = 'local'
              AND product_type = 'ring_gold'
              AND timestamp >= ?
            GROUP BY 1
            ORDER BY day ASC
        """,
            [cutoff],
        )
        columns = [desc[0] for desc in cursor.description]
        history_rows = [dict(zip(columns, r)) for r in cursor.fetchall()]
        result["data_points"] = len(history_rows)

        result["price_history"] = [
            {
                "timestamp": r["day"].isoformat(),
                "buy_price": float(r["avg_buy"]) if r["avg_buy"] is not None else None,
                "sell_price": float(r["avg_sell"])
                if r["avg_sell"] is not None
                else None,
            }
            for r in history_rows
        ]

        cursor = con.execute(
            """
            WITH recent AS (
                SELECT AVG(sell_price) as avg_sell
                FROM db.price_history
                WHERE source = 'local'
                  AND product_type = 'ring_gold'
                  AND sell_price IS NOT NULL
                  AND timestamp >= ?
                  AND timestamp < ?
            ),
            prior AS (
                SELECT AVG(sell_price) as avg_sell
                FROM db.price_history
                WHERE source = 'local'
                  AND product_type = 'ring_gold'
                  AND sell_price IS NOT NULL
                  AND timestamp >= ?
                  AND timestamp < ?
            )
            SELECT r.avg_sell as recent_avg, p.avg_sell as prior_avg
            FROM recent r, prior p
        """,
            [
                datetime.now(timezone.utc) - timedelta(days=3),
                datetime.now(timezone.utc),
                datetime.now(timezone.utc) - timedelta(days=7),
                datetime.now(timezone.utc) - timedelta(days=4),
            ],
        )
        trend_7d = cursor.fetchone()
        if (
            trend_7d
            and trend_7d[0] is not None
            and trend_7d[1] is not None
            and trend_7d[1] > 0
        ):
            result["trend_7d"] = float((trend_7d[0] - trend_7d[1]) / trend_7d[1] * 100)

        cursor = con.execute(
            """
            WITH recent AS (
                SELECT AVG(sell_price) as avg_sell
                FROM db.price_history
                WHERE source = 'local'
                  AND product_type = 'ring_gold'
                  AND sell_price IS NOT NULL
                  AND timestamp >= ?
                  AND timestamp < ?
            ),
            prior AS (
                SELECT AVG(sell_price) as avg_sell
                FROM db.price_history
                WHERE source = 'local'
                  AND product_type = 'ring_gold'
                  AND sell_price IS NOT NULL
                  AND timestamp >= ?
                  AND timestamp < ?
            )
            SELECT r.avg_sell as recent_avg, p.avg_sell as prior_avg
            FROM recent r, prior p
        """,
            [
                datetime.now(timezone.utc) - timedelta(days=3),
                datetime.now(timezone.utc),
                datetime.now(timezone.utc) - timedelta(days=30),
                datetime.now(timezone.utc) - timedelta(days=27),
            ],
        )
        trend_30d = cursor.fetchone()
        if (
            trend_30d
            and trend_30d[0] is not None
            and trend_30d[1] is not None
            and trend_30d[1] > 0
        ):
            result["trend_30d"] = float(
                (trend_30d[0] - trend_30d[1]) / trend_30d[1] * 100
            )

        return result
    finally:
        con.close()
