"""Mode-specific signal interpretation: weights and thresholds.

SAVER: long-term accumulation guidance — trend matters most.
TRADER: timing-precision guidance — gap matters most.
"""

from src.engine.types import SignalMode

MODE_WEIGHTS: dict[SignalMode, dict[str, float]] = {
    SignalMode.SAVER: {"gap": 0.4, "spread": 0.1, "trend": 0.5},
    SignalMode.TRADER: {"gap": 0.6, "spread": 0.3, "trend": 0.1},
}

MODE_THRESHOLDS: dict[SignalMode, tuple[float, float]] = {
    SignalMode.SAVER: (0.05, -0.05),
    SignalMode.TRADER: (0.25, -0.25),
}


def get_mode_weights(mode: SignalMode) -> dict[str, float]:
    return dict(MODE_WEIGHTS[mode])


def get_mode_thresholds(mode: SignalMode) -> tuple[float, float]:
    return MODE_THRESHOLDS[mode]
