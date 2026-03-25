from zoneinfo import ZoneInfo

from pydantic_settings import BaseSettings, SettingsConfigDict

VNTZ = ZoneInfo("Asia/Ho_Chi_Minh")


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
    )

    app_name: str = "gold_advisor"
    database_url: str = "sqlite+aiosqlite:///./gold_advisor.db"
    log_level: str = "INFO"
    fetch_interval_minutes: int = 5
    freshness_threshold_minutes: int = 15
    anomaly_threshold_percent: float = 10.0
    telegram_bot_token: str = ""
    news_fetch_interval_minutes: int = 30
    openai_api_key: str = ""
    openai_model_name: str = "glm-5-turbo"
    openai_base_url: str = "https://api.z.ai/api/coding/paas/v4"
    goldapi_key: str = ""
