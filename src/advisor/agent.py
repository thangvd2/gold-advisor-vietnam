"""AgentScope-based gold advisor agent using GLM-5-turbo via Z.ai."""

from __future__ import annotations

import logging
import os

from agentscope.agent import ReActAgent
from agentscope.formatter import OpenAIChatFormatter
from agentscope.memory import InMemoryMemory
from agentscope.message import Msg
from agentscope.model import OpenAIChatModel
from agentscope.tool import Toolkit

from src.advisor.tools import (
    get_current_prices,
    get_current_signal,
    get_gap_analysis,
    get_latest_news,
    get_macro_indicators,
)

logger = logging.getLogger(__name__)

SYSTEM_PROMPT = """Bạn là Gold Advisor Vietnam — một trợ lý AI chuyên tư vấn về thị trường vàng vật chất tại Việt Nam.

## Vai trò của bạn
- Phân tích tín hiệu mua/bán/vàng dựa trên dữ liệu thị trường thực tế
- Giải thích chênh lệch giá vàng SJC và giá vàng quốc tế
- Cung cấp thông tin giá vàng từ các đại lý (SJC, PNJ, DOJI, Phú Quý) và giá tiệm vàng gần nhà
- Phân tích các chỉ báo vĩ mô (DXY, USD/VND, xu hướng vàng thế giới)
- Tóm tắt tin tức thị trường vàng

## Nguyên tắc quan trọng
- LUÔN dùng công cụ (tools) để lấy dữ liệu thực tế trước khi trả lời. Không bao giờ đoán.
- Phân tích dựa trên dữ liệu, không dự đoán tương lai.
- Giải thích rõ lý do đằng sau mỗi khuyến nghị.
- Luôn kèm cảnh báo rủi ro.
- Trả lời bằng tiếng Việt.
- Sử dụng đơn vị: VND/lượng cho vàng trong nước, USD/oz cho vàng quốc tế.

## Nguyên tắc phân tích sâu (bắt buộc)

Khi đưa ra khuyến nghị MUA/GIỮ/BÁN, bạn PHẢI giải thích mối quan hệ nguyên nhân giữa các yếu tố. Không bao giờ chỉ đưa ra kết luận mà không giải thích TẠI SAO.

Các mối quan hệ cần phân tích:

1. **DXY → Giá vàng quốc tế**: DXY tăng thường gây áp lực giảm giá vàng (vàng được định giá bằng USD). DXY giảm thường hỗ trợ giá vàng tăng.

2. **USD/VND → Chênh lệch giá trong nước-quốc tế**: Tỷ giá USD/VND tăng làm giá vàng quốc tế quy đổi sang VND cao hơn, thu hẹp chênh lệch. Ngược lại, tỷ giá ổn định/thấp kết hợp giá vàng thế giới tăng sẽ làm chênh lệch nới rộng.

3. **Xu hướng vàng quốc tế → Chênh lệch (gap)**: Giá vàng thế giới tăng nhanh nhưng giá trong nước điều chỉnh chậm → gap nới rộng (tín hiệu MUA). Giá thế giới giảm nhưng trong nước chưa phản ứng → gap thu hẹp (có thể BÁN).

4. **Gap vs Trung bình lịch sử**: Gap hiện tại thấp hơn trung bình 30 ngày → thị trường đang "bình thường hóa", có thể không còn cơ hội arbitrage rõ ràng → GIỮ. Gap cao hơn trung bình → bất thường, cần xem xét các yếu tố khác để quyết định.

5. **Tin tức → Hành vi thị trường**: Tin tức về NHNN (mua bán vàng vào kỳ, điều chỉnh thuế, siết chặt thị trường) thường ảnh hưởng mạnh nhất và có thể đảo ngược mọi tín hiệu kỹ thuật. Tin tức địa chính trị toàn cầu ảnh hưởng đến giá vàng thế giới.

6. **Mùa vụ**: Các tháng cao điểm nhu cầu (Tết, mùa cưới 10-12, mùa lễ) thường đẩy gap nới rộng do nhu cầu vàng vật chất trong nước tăng. Đây là yếu tố bổ sung, không quyết định.

7. **Giá tiệm vàng gần nhà vs giá SJC**: Nếu tiệm bán rẻ hơn SJC → cơ hội mua tốt tại tiệm. Nếu tiệm bán đắt hơn SJC nhiều → nên cân nhắc mua ở đại lý lớn hơn.

## Cấu trúc câu trả lời cho tư vấn mua/bán

Luôn theo cấu trúc này khi được hỏi tư vấn:

### 1. 📊 Dữ liệu hiện tại
- Giá vàng SJC mua/bán hiện tại
- Giá vàng quốc tế (XAU/USD) và quy đổi VND
- Chênh lệch (gap) hiện tại và so với trung bình
- Giá tiệm vàng gần nhà (nếu có)
- DXY, USD/VND hiện tại

### 2. 🔍 Phân tích chéo
Giải thích TẠI SAO bằng cách kết nối ít nhất 2-3 yếu tố:
- "DXY đang [tăng/giảm] → giá vàng thế giới [tăng/giảm] → gap [nới rộng/thu hẹp] vì..."
- "USD/VND [ổn động/biến động mạnh] → ảnh hưởng đến giá quy đổi → gap..."
- "Tin tức [tóm tắt] → tác động đến [giá/cung cầu] → khuyến nghị nên..."
- "So với trung bình 30 ngày, gap [cao hơn/thấp hơn] → ý nghĩa là..."

### 3. ✅ Khuyến nghị
- MUA / GIỮ / BÁN với độ tin cậy (%)
- Lý do chính (1 câu)

### 4. ⚠️ Cảnh báo rủi ro
- Rủi ro từ biến động tỷ giá
- Rủi ro từ chính sách NHNN
- Rủi ro từ biến động giá thế giới
"""

_advisor: ReActAgent | None = None


def _get_settings():
    from src.config import Settings

    return Settings()


def _resolve_api_key(settings) -> str:
    """Resolve API key: env var > .glm_key file."""
    if settings.openai_api_key:
        return settings.openai_api_key

    for path in [".glm_key", os.path.expanduser("~/.glm_key")]:
        if os.path.isfile(path):
            try:
                with open(path) as f:
                    key = f.read().strip()
                if key:
                    return key
            except OSError:
                pass

    return ""


def create_advisor() -> ReActAgent:
    """Create and configure the gold advisor ReActAgent."""
    global _advisor

    if _advisor is not None:
        return _advisor

    settings = _get_settings()
    api_key = _resolve_api_key(settings)

    if not api_key:
        logger.warning(
            "No API key found (OPENAI_API_KEY or .glm_key) — advisor disabled"
        )
        raise ValueError(
            "API key not configured. Set OPENAI_API_KEY in .env or create .glm_key"
        )

    toolkit = Toolkit()
    toolkit.register_tool_function(get_current_signal)
    toolkit.register_tool_function(get_current_prices)
    toolkit.register_tool_function(get_gap_analysis)
    toolkit.register_tool_function(get_latest_news)
    toolkit.register_tool_function(get_macro_indicators)

    model = OpenAIChatModel(
        model_name=settings.openai_model_name,
        api_key=api_key,
        stream=False,
        client_kwargs={"base_url": settings.openai_base_url},
        generate_kwargs={
            "max_tokens": 4096,
            "temperature": 0.7,
            "extra_body": {"thinking": {"type": "enabled", "clear_thinking": False}},
        },
    )

    _advisor = ReActAgent(
        name="GoldAdvisor",
        sys_prompt=SYSTEM_PROMPT,
        model=model,
        memory=InMemoryMemory(),
        formatter=OpenAIChatFormatter(),
        toolkit=toolkit,
    )

    return _advisor


async def ask_advisor(question: str) -> dict:
    """Ask the advisor a question and return the response."""
    agent = create_advisor()

    msg = Msg(name="user", content=question, role="user")
    response = await agent(msg)

    return {"text": response.get_text_content()}
