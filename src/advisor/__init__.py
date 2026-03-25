"""AgentScope-based gold advisor module."""

from src.advisor.agent import ask_advisor, create_advisor
from src.advisor.models import AdvisoryResponse

__all__ = ["ask_advisor", "create_advisor", "AdvisoryResponse"]
