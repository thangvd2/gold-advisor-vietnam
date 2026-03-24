from datetime import datetime, timedelta, timezone

from src.analysis.connection import get_duckdb_connection

RANGE_MAP = {
    "1D": (timedelta(days=1), 300),
    "1W": (timedelta(days=7), 900),
    "1M": (timedelta(days=30), 3600),
    "1Y": (timedelta(days=365), 3600),
}

VALID_PRODUCT_TYPES = {"sjc_bar", "ring_gold", "xau_usd"}


def get_price_series(db_path: str, product_type: str, range: str = "1M") -> list[dict]:
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

    price_field = "price_vnd" if product_type == "xau_usd" else "sell_price"
    null_filter = "AND price_vnd IS NOT NULL" if product_type == "xau_usd" else ""

    con = get_duckdb_connection(db_path)
    try:
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
              {null_filter}
              AND timestamp >= ?
            GROUP BY 1
            ORDER BY 1 ASC
        """,
            [product_type, cutoff],
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
