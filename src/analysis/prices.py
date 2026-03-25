from datetime import datetime, timedelta, timezone

from src.analysis.connection import get_duckdb_connection

RANGE_MAP = {
    "1D": (timedelta(days=1), 300),
    "1W": (timedelta(days=7), 900),
    "1M": (timedelta(days=30), 3600),
    "3M": (timedelta(days=90), 86400),
    "1Y": (timedelta(days=365), 86400),
}

VALID_PRODUCT_TYPES = {"sjc_bar", "ring_gold", "xau_usd"}


def get_price_series(
    db_path: str, product_type: str, range: str = "1M", source: str | None = None
) -> list[dict]:
    if range not in RANGE_MAP:
        raise ValueError(
            f"Invalid range: {range}. Must be one of {list(RANGE_MAP.keys())}"
        )

    if product_type not in VALID_PRODUCT_TYPES:
        raise ValueError(
            f"Invalid product_type: {product_type}. "
            f"Must be one of {list(VALID_PRODUCT_TYPES)}"
        )

    time_delta, bucket_seconds = RANGE_MAP[range]
    cutoff = datetime.now(timezone.utc) - time_delta

    source_filter = ""
    params: list = [product_type, cutoff]
    if source:
        source_filter = "AND source = ?"
        params.append(source)

    con = get_duckdb_connection(db_path)
    try:
        if product_type == "xau_usd":
            cursor = con.execute(
                f"""
                WITH gold_raw AS (
                    SELECT timestamp, price_usd, price_vnd
                    FROM db.price_history
                    WHERE product_type = ?
                      AND price_usd IS NOT NULL
                      AND timestamp >= ?
                      {source_filter}
                ),
                fx AS (
                    SELECT timestamp, sell_price as fx_rate
                    FROM db.price_history
                    WHERE product_type = 'usd_vnd'
                      AND sell_price IS NOT NULL
                      AND sell_price > 0
                ),
                fx_filled AS (
                    SELECT
                        g.timestamp,
                        g.price_usd,
                        COALESCE(g.price_vnd, g.price_usd * f.fx_rate) as price_vnd
                    FROM gold_raw g
                    LEFT JOIN fx f ON f.timestamp = (
                        SELECT MAX(f2.timestamp)
                        FROM fx f2
                        WHERE f2.timestamp <= g.timestamp
                    )
                )
                SELECT
                    to_timestamp(
                        floor(epoch(cast(timestamp as timestamp)) / {bucket_seconds})
                        * {bucket_seconds}
                    ) as bucket,
                    AVG(price_vnd) as avg_price
                FROM fx_filled
                WHERE price_vnd IS NOT NULL
                GROUP BY 1
                ORDER BY 1 ASC
                """,
                params,
            )
        else:
            price_field = "sell_price"
            cursor = con.execute(
                f"""
                SELECT
                    to_timestamp(
                        floor(epoch(cast(timestamp as timestamp)) / {bucket_seconds})
                        * {bucket_seconds}
                    ) as bucket,
                    AVG({price_field}) as avg_price
                FROM db.price_history
                WHERE product_type = ?
                  AND {price_field} IS NOT NULL
                  AND timestamp >= ?
                  {source_filter}
                GROUP BY 1
                ORDER BY 1 ASC
                """,
                params,
            )

        columns = [desc[0] for desc in cursor.description]
        rows = [dict(zip(columns, r)) for r in cursor.fetchall()]

        return [
            {
                "x": r["bucket"].isoformat(),
                "y": float(r["avg_price"]) if r["avg_price"] is not None else None,
            }
            for r in rows
        ]
    finally:
        con.close()
