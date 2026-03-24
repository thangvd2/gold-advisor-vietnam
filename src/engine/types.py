"""Signal engine type contracts.

All numerical signal computation uses these types.
No LLM involvement — pure, testable, deterministic functions.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from enum import StrEnum


class Recommendation(StrEnum):
    """Actionable recommendation from signal analysis."""

    BUY = "BUY"
    HOLD = "HOLD"
    SELL = "SELL"


class SignalMode(StrEnum):
    """Risk profile mode for signal threshold tuning."""

    SAVER = "SAVER"
    TRADER = "TRADER"


@dataclass(frozen=True)
class SignalFactor:
    """A single factor contributing to the composite signal.

    direction: -1.0 (strong sell) to 1.0 (strong buy)
    weight:    0.0 (ignored) to 1.0 (maximum influence)
    confidence: 0.0 (no data) to 1.0 (high certainty)
    """

    name: str
    direction: float = field(metadata={"description": "-1.0 to 1.0"})
    weight: float = field(metadata={"description": "0.0 to 1.0"})
    confidence: float = field(metadata={"description": "0.0 to 1.0"})

    def __post_init__(self) -> None:
        object.__setattr__(self, "direction", max(-1.0, min(1.0, self.direction)))
        object.__setattr__(self, "weight", max(0.0, min(1.0, self.weight)))
        object.__setattr__(self, "confidence", max(0.0, min(1.0, self.confidence)))


@dataclass
class Signal:
    """Complete signal output: recommendation, confidence, and supporting factors.

    confidence is an integer 0-100 for display purposes.
    reasoning is filled by the reasoning module (Plan 02), empty initially.
    """

    recommendation: Recommendation
    confidence: int = field(metadata={"description": "0-100"})
    factors: list[SignalFactor] = field(default_factory=list)
    reasoning: str = ""
    mode: SignalMode = SignalMode.SAVER
    timestamp: datetime = field(default_factory=lambda: datetime.now())
    gap_vnd: float | None = None
    gap_pct: float | None = None

    def __post_init__(self) -> None:
        object.__setattr__(self, "confidence", max(0, min(100, self.confidence)))
