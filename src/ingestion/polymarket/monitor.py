def flag_significant_moves(
    events: list[dict],
    threshold: float = 5.0,
    volume_min: float = 1000,
) -> list[dict]:
    for e in events:
        change = e.get("one_day_price_change")
        vol = e.get("volume_24h", 0)
        e["is_flagged"] = (
            change is not None and abs(change) > threshold and vol > volume_min
        )
    return events
