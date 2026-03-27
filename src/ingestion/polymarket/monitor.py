def flag_significant_moves(
    events: list[dict],
    threshold: float = 0.05,
    volume_min: float = 100000,
) -> list[dict]:
    for e in events:
        one_day_change = e.get("one_day_price_change")
        volume_24h = e.get("volume_24h", 0)
        is_flagged = False
        if one_day_change is not None and volume_24h is not None:
            if abs(one_day_change) > threshold and volume_24h > volume_min:
                is_flagged = True
        e["is_flagged"] = is_flagged
    return events
