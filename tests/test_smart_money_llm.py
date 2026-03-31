"""Tests for LLM-powered smart money signal explanations."""

import pytest
from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock, patch

from src.engine.smart_money_llm import (
    SmartMoneyExplanation,
    _cache,
    generate_smart_money_explanation,
)


@pytest.fixture(autouse=True)
def clear_llm_cache():
    _cache.clear()
    yield


# ---------------------------------------------------------------------------
# SmartMoneyExplanation model tests
# ---------------------------------------------------------------------------


class TestSmartMoneyExplanationModel:
    def test_model_with_valid_data(self):
        """Test SmartMoneyExplanation model with all fields."""
        explanation = SmartMoneyExplanation(
            what_happened={"en": "Price moved up 5%", "vn": "Giá tăng 5%"},
            why_significant={"en": "Contrary to news", "vn": "Trái ngược tin tức"},
            gold_implication={"en": "Gold may rise", "vn": "Vàng có thể tăng"},
        )
        assert explanation.what_happened["en"] == "Price moved up 5%"
        assert explanation.what_happened["vn"] == "Giá tăng 5%"
        assert explanation.why_significant["en"] == "Contrary to news"
        assert explanation.why_significant["vn"] == "Trái ngược tin tức"
        assert explanation.gold_implication is not None
        assert explanation.gold_implication["en"] == "Gold may rise"
        assert explanation.gold_implication["vn"] == "Vàng có thể tăng"

    def test_model_without_gold_implication(self):
        """Test SmartMoneyExplanation model without optional gold_implication."""
        explanation = SmartMoneyExplanation(
            what_happened={"en": "Price moved up 5%", "vn": "Giá tăng 5%"},
            why_significant={"en": "Contrary to news", "vn": "Trái ngược tin tức"},
        )
        assert explanation.gold_implication is None

        assert explanation.what_happened["en"] == "Price moved up 5%"
        assert explanation.why_significant["en"] == "Contrary to news"


# ---------------------------------------------------------------------------
# generate_smart_money_explanation tests
# ---------------------------------------------------------------------------


class TestGenerateSmartMoneyExplanation:
    def _make_signal(self):
        """Create a mock PolymarketSmartSignal for testing."""
        mock = MagicMock()
        mock.id = 123
        mock.title = "Fed rate decision in June"
        mock.slug = "fed-rate-june-2025"
        mock.category = "Finance"
        mock.signal_type = "contrarian"
        mock.price_before = 0.45
        mock.price_after = 0.65
        mock.move_cents = 20.0
        mock.move_direction = "up"
        mock.news_count_4h = 2
        mock.news_consensus = "contradicts"
        mock.confidence = 0.85
        return mock

    @pytest.mark.asyncio
    async def test_returns_explanation_with_valid_response(self):
        """Test generate_smart_money_explanation with mocked OpenAI response."""
        mock_signal = self._make_signal()

        mock_response = MagicMock()
        mock_response.choices = [MagicMock()]
        mock_response.choices[0].message = MagicMock()
        mock_response.choices[0].message.content = """
{
    "what_happened": {
        "en": "The probability of a Fed rate cut in June jumped from 45% to 65%, representing a significant shift in market expectations.",
        "vn": "Xác suất cắt lãi suất liên quan đến Fed vào tháng 6 đã tăng từ 45% lên 65%, cho thấy sự thay đổi đáng kể trọng kỳ kỳ kỳ kỳ kỳ kỳ kỳ thị thị biểu kỳ thị trường."
    },
    "why_significant": {
        "en": "This move contradicts recent news suggesting rates will stay higher, suggesting informed traders are betting against the consensus.",
        "vn": "Biến động này trái ngược với tin tức gần đây cho thấy lãi suất sẽ giữ nguyên, cho thấy các nhà giao dịch đang đặt cược ngược với xu hướng chung."
    },
    "gold_implication": {
        "en": "A Fed rate cut would typically weaken the USD and support gold prices. This signal suggests gold may be in focus.",
        "vn": "Việc cắt giảm lãi suất của Fed thường làm làm đồng đô USD và hỗ trợ giá vàng. Tín hiệu này cho thấy vàng có thể là tâm điểm chú ý."
    }
}
"""

        with (
            patch(
                "src.engine.smart_money_llm._resolve_api_key",
                return_value="test-api-key",
            ),
            patch(
                "src.engine.smart_money_llm.Settings",
                return_value=MagicMock(
                    openai_api_key="test-key", openai_base_url="https://test.url"
                ),
            ),
            patch("openai.AsyncOpenAI") as mock_openai,
        ):
            mock_client = AsyncMock()
            mock_client.chat.completions.create = AsyncMock(return_value=mock_response)
            mock_openai.return_value = mock_client

            mock_openai.assert_not_called()

            result = await generate_smart_money_explanation(mock_signal)

            assert result is not None
            assert isinstance(result, SmartMoneyExplanation)
            assert (
                result.what_happened["en"]
                == "The probability of a Fed rate cut in June jumped from 45% to 65%, representing a significant shift in market expectations."
            )
            assert (
                result.why_significant["vn"]
                == "Biến động này trái ngược với tin tức gần đây cho thấy lãi suất sẽ giữ nguyên, cho thấy các nhà giao dịch đang đặt cược ngược với xu hướng chung."
            )

            assert result.gold_implication is not None
            assert "gold" in result.gold_implication["en"].lower()

    @pytest.mark.asyncio
    async def test_returns_none_on_openai_error(self):
        """Test generate_smart_money_explanation returns None on OpenAI error."""
        mock_signal = self._make_signal()

        with (
            patch(
                "src.engine.smart_money_llm._resolve_api_key",
                return_value="test-api-key",
            ),
            patch("openai.AsyncOpenAI") as mock_openai,
        ):
            mock_client = AsyncMock()
            mock_client.chat.completions.create = AsyncMock(
                side_effect=Exception("Connection refused")
            )
            mock_openai.return_value = mock_client

            result = await generate_smart_money_explanation(mock_signal)

            assert result is None

    @pytest.mark.asyncio
    async def test_returns_none_on_bad_json(self):
        """Test generate_smart_money_explanation returns None on bad JSON response."""
        mock_signal = self._make_signal()

        mock_response = MagicMock()
        mock_response.choices = [MagicMock()]
        mock_response.choices[0].message = MagicMock()
        mock_response.choices[0].message.content = '{"invalid": "json"}'

        with (
            patch(
                "src.engine.smart_money_llm._resolve_api_key",
                return_value="test-api-key",
            ),
            patch("openai.AsyncOpenAI") as mock_openai,
        ):
            mock_client = AsyncMock()
            mock_client.chat.completions.create = AsyncMock(return_value=mock_response)
            mock_openai.return_value = mock_client

            mock_openai.assert_not_called()

            result = await generate_smart_money_explanation(mock_signal)
            assert result is None

    @pytest.mark.asyncio
    async def test_returns_none_on_missing_required_fields(self):
        """Test generate_smart_money_explanation returns None when required fields are missing."""
        mock_signal = self._make_signal()

        mock_response = MagicMock()
        mock_response.choices = [MagicMock()]
        mock_response.choices[0].message = MagicMock()
        # Missing 'why_significant' entirely
        mock_response.choices[0].message.content = """
{
    "what_happened": {
        "en": "Price moved up"
    }
}
"""

        with (
            patch(
                "src.engine.smart_money_llm._resolve_api_key",
                return_value="test-api-key",
            ),
            patch("openai.AsyncOpenAI") as mock_openai,
        ):
            mock_client = AsyncMock()
            mock_client.chat.completions.create = AsyncMock(return_value=mock_response)
            mock_openai.return_value = mock_client
            mock_openai.assert_not_called()

            result = await generate_smart_money_explanation(mock_signal)
            assert result is None

    @pytest.mark.asyncio
    async def test_returns_none_on_no_api_key(self):
        """Test generate_smart_money_explanation returns None when no API key available."""
        mock_signal = self._make_signal()

        with patch(
            "src.engine.smart_money_llm._resolve_api_key",
            return_value="",
        ):
            result = await generate_smart_money_explanation(mock_signal)
            assert result is None

    @pytest.mark.asyncio
    async def test_cache_returns_cached_result(self):
        """Test that same signal.id returns cached result on second call."""
        mock_signal = self._make_signal()

        mock_response = MagicMock()
        mock_response.choices = [MagicMock()]
        mock_response.choices[0].message = MagicMock()
        mock_response.choices[0].message.content = """
{
    "what_happened": {
        "en": "Price moved up 5%",
        "vn": "Giá tăng 5%"
    },
    "why_significant": {
        "en": "Contrary to news",
        "vn": "Trái ngược tin tức"
    }
}
"""

        with (
            patch(
                "src.engine.smart_money_llm._resolve_api_key",
                return_value="test-api-key",
            ),
            patch("openai.AsyncOpenAI") as mock_openai,
        ):
            mock_client = AsyncMock()
            mock_client.chat.completions.create = AsyncMock(return_value=mock_response)
            mock_openai.return_value = mock_client
            mock_openai.assert_not_called()

            # First call
            result1 = await generate_smart_money_explanation(mock_signal)
            assert result1 is not None

            # Second call - should return cached result
            result2 = await generate_smart_money_explanation(mock_signal)
            assert result2 is not None
            assert result2 is result1  # Same object

            # OpenAI should only be called once
            assert mock_client.chat.completions.create.call_count == 1
