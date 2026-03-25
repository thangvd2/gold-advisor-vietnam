"""Pydantic models for structured advisory responses."""

from typing import Literal

from pydantic import BaseModel, Field


class AdvisoryResponse(BaseModel):
    """Structured output from the gold advisor agent."""

    recommendation: Literal["BUY", "HOLD", "SELL"] = Field(
        description="Current gold recommendation"
    )
    confidence: int = Field(description="Confidence level 0-100", ge=0, le=100)
    reasoning_vn: str = Field(description="Explanation in Vietnamese, 2-4 sentences")
    risk_notes: str = Field(description="Risk warnings in Vietnamese, 1-2 sentences")
    gap_analysis: str = Field(
        description="Brief SJC-international gap analysis in Vietnamese"
    )
