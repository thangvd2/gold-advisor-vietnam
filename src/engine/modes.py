"""Mode-specific signal interpretation: weights and thresholds.

SAVER: long-term accumulation guidance — trend matters most.
TRADER: timing-precision guidance — gap matters most.
"""

from src.engine.types import SignalMode

MODE_WEIGHTS: dict[SignalMode, dict[str, float]] = {
    SignalMode.SAVER: {
        "gap": 0.25,
        "spread": 0.05,
        "trend": 0.30,
        "fx_trend": 0.10,
        "gold_trend": 0.10,
        "local_spread": 0.05,
        "local_trend": 0.15,
    },
    SignalMode.TRADER: {
        "gap": 0.35,
        "spread": 0.10,
        "trend": 0.10,
        "fx_trend": 0.10,
        "gold_trend": 0.10,
        "local_spread": 0.10,
        "local_trend": 0.15,
    },
}

MODE_THRESHOLDS: dict[SignalMode, tuple[float, float]] = {
    SignalMode.SAVER: (0.05, -0.05),
    SignalMode.TRADER: (0.25, -0.25),
}


def get_mode_weights(mode: SignalMode) -> dict[str, float]:
    return dict(MODE_WEIGHTS[mode])


def get_mode_thresholds(mode: SignalMode) -> tuple[float, float]:
    return MODE_THRESHOLDS[mode]
