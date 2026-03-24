MONTHLY_DEMAND_LEVELS: dict[int, str] = {
    1: "very_high",
    2: "very_high",
    3: "medium",
    4: "medium",
    5: "low",
    6: "low",
    7: "low",
    8: "medium",
    9: "low",
    10: "low",
    11: "high",
    12: "high",
}

MONTH_NAMES = {
    1: "January",
    2: "February",
    3: "March",
    4: "April",
    5: "May",
    6: "June",
    7: "July",
    8: "August",
    9: "September",
    10: "October",
    11: "November",
    12: "December",
}

SEASONAL_MODIFIERS: dict[str, float] = {
    "very_high": 0.7,
    "high": 0.85,
    "medium": 1.0,
    "low": 1.0,
}


def get_seasonal_demand_level(month: int) -> str:
    if month not in MONTHLY_DEMAND_LEVELS:
        raise ValueError(f"Invalid month: {month}. Must be 1-12.")
    return MONTHLY_DEMAND_LEVELS[month]


def get_month_name(month: int) -> str:
    if month not in MONTH_NAMES:
        raise ValueError(f"Invalid month: {month}. Must be 1-12.")
    return MONTH_NAMES[month]


def compute_seasonal_modifier(month: int) -> float:
    level = get_seasonal_demand_level(month)
    return SEASONAL_MODIFIERS[level]


def compute_seasonal_signal(month: int, weight: float = 0.0) -> "SignalFactor":
    from src.engine.types import SignalFactor

    modifier = compute_seasonal_modifier(month)

    return SignalFactor(
        name="seasonal",
        direction=0.0,
        weight=weight,
        confidence=modifier,
    )
