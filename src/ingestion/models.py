"""Pydantic models for normalized price data from external sources."""

from datetime import datetime, timezone
from enum import Enum

from pydantic import BaseModel, field_validator, Field


class ProductType(str, Enum):
    XAU_USD = "xau_usd"
    USD_VND = "usd_vnd"
    SJC_BAR = "sjc_bar"
    RING_GOLD = "ring_gold"


class FetchedPrice(BaseModel):
    source: str
    product_type: str
    buy_price: float | None = None
    sell_price: float | None = None
    price_usd: float | None = None
    price_vnd: float | None = None
    currency: str
    timestamp: datetime
    fetched_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

    @field_validator("buy_price", "sell_price", "price_usd", "price_vnd", mode="before")
    @classmethod
    def price_must_be_positive_if_present(cls, v: float | None) -> float | None:
        if v is not None and v <= 0:
            raise ValueError("Price must be positive")
        return v


GRAMS_PER_OZ = 31.1034768
GRAMS_PER_LUONG = 37.5


def convert_usd_to_vnd_per_luong(usd_per_oz: float, vnd_per_usd: float) -> float:
    price_per_gram_usd = usd_per_oz / GRAMS_PER_OZ
    price_per_luong_vnd = price_per_gram_usd * GRAMS_PER_LUONG * vnd_per_usd
    return price_per_luong_vnd
