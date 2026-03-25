"""Chat endpoint for the AI gold advisor agent."""

import logging

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from src.advisor.agent import ask_advisor

logger = logging.getLogger(__name__)

router = APIRouter()


class ChatRequest(BaseModel):
    question: str = Field(
        ...,
        min_length=1,
        max_length=1000,
        description="User question in Vietnamese or English",
    )


class ChatResponse(BaseModel):
    text: str = Field(..., description="Advisor's response text")
    error: str | None = Field(None, description="Error message if request failed")


@router.post("", response_model=ChatResponse)
async def chat(request: ChatRequest) -> ChatResponse:
    """Send a question to the gold advisor agent and get a response."""
    try:
        result = await ask_advisor(request.question)
        return ChatResponse(text=result["text"])
    except ValueError as e:
        raise HTTPException(status_code=503, detail=str(e))
    except Exception as e:
        logger.exception("Advisor chat error")
        raise HTTPException(status_code=500, detail=f"Advisor error: {e}")
