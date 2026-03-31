from datetime import datetime, timezone

from sqlalchemy import (
    Boolean,
    Date,
    DateTime,
    Float,
    func,
    Index,
    Integer,
    String,
    Text,
)
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


class Base(DeclarativeBase):
    pass


class PriceRecord(Base):
    __tablename__ = "price_history"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    source: Mapped[str] = mapped_column(String(50))
    product_type: Mapped[str] = mapped_column(String(50))
    buy_price: Mapped[float | None] = mapped_column(Float, nullable=True)
    sell_price: Mapped[float | None] = mapped_column(Float, nullable=True)
    price_usd: Mapped[float | None] = mapped_column(Float, nullable=True)
    price_vnd: Mapped[float | None] = mapped_column(Float, nullable=True)
    currency: Mapped[str] = mapped_column(String(10))
    timestamp: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc)
    )
    fetched_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc)
    )
    spread: Mapped[float | None] = mapped_column(Float, nullable=True)
    validation_status: Mapped[str] = mapped_column(String(20), default="valid")

    __table_args__ = (
        Index("idx_source_product_timestamp", "source", "product_type", "timestamp"),
    )


class DataQualityAlert(Base):
    __tablename__ = "data_quality_alerts"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    check_type: Mapped[str] = mapped_column(String(50))
    severity: Mapped[str] = mapped_column(String(20))
    source: Mapped[str] = mapped_column(String(50))
    message: Mapped[str] = mapped_column(String(500))
    detected_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc)
    )


class SignalRecord(Base):
    __tablename__ = "signal_history"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    recommendation: Mapped[str] = mapped_column(String(10))
    confidence: Mapped[int] = mapped_column(Integer)
    gap_vnd: Mapped[float | None] = mapped_column(Float, nullable=True)
    gap_pct: Mapped[float | None] = mapped_column(Float, nullable=True)
    mode: Mapped[str] = mapped_column(String(20))
    reasoning: Mapped[str] = mapped_column(String(500))
    factor_data: Mapped[str] = mapped_column(String(2000))
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc)
    )

    __table_args__ = (Index("idx_signal_mode_created", "mode", "created_at"),)


class PolicyEvent(Base):
    __tablename__ = "policy_events"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    event_type: Mapped[str] = mapped_column(String(50))
    description: Mapped[str] = mapped_column(Text)
    impact: Mapped[str] = mapped_column(String(20))
    severity: Mapped[str] = mapped_column(String(20))
    effective_date: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    expires_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc)
    )


class NewsItem(Base):
    __tablename__ = "news_items"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    title: Mapped[str] = mapped_column(String(500))
    url: Mapped[str] = mapped_column(String(1000), unique=True)
    source: Mapped[str] = mapped_column(String(100))
    published_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    excerpt: Mapped[str | None] = mapped_column(Text, nullable=True)
    category: Mapped[str | None] = mapped_column(String(50), nullable=True)
    is_manual: Mapped[bool] = mapped_column(Boolean, default=False, server_default="0")
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        server_default=func.now(),
    )


class FedWatchSnapshot(Base):
    __tablename__ = "fedwatch_snapshots"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    implied_rate: Mapped[float] = mapped_column(Float)
    futures_price: Mapped[float] = mapped_column(Float)
    contract_symbol: Mapped[str] = mapped_column(String(20))
    timestamp: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc)
    )
    fetched_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc)
    )


class PolymarketEvent(Base):
    __tablename__ = "polymarket_events"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    slug: Mapped[str] = mapped_column(String(200))
    title: Mapped[str] = mapped_column(String(500))
    question: Mapped[str | None] = mapped_column(String(500), nullable=True)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    market_questions: Mapped[str | None] = mapped_column(Text, nullable=True)
    outcome_prices: Mapped[str | None] = mapped_column(Text, nullable=True)
    volume_24h: Mapped[float | None] = mapped_column(Float, nullable=True)
    liquidity: Mapped[float | None] = mapped_column(Float, nullable=True)
    one_day_price_change: Mapped[float | None] = mapped_column(Float, nullable=True)
    one_hour_price_change: Mapped[float | None] = mapped_column(Float, nullable=True)
    event_type: Mapped[str] = mapped_column(String(20), default="market_mover")
    category: Mapped[str | None] = mapped_column(String(50), nullable=True)
    is_flagged: Mapped[bool] = mapped_column(Boolean, default=False)
    condition_id: Mapped[str | None] = mapped_column(String(200), nullable=True)
    clob_token_id_yes: Mapped[str | None] = mapped_column(String(200), nullable=True)
    timestamp: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc)
    )
    fetched_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc)
    )

    __table_args__ = (
        Index("idx_polymarket_slug", "slug", unique=True),
        Index("idx_polymarket_category", "category"),
        Index("idx_polymarket_flagged", "is_flagged"),
    )


class PolymarketPriceSnapshot(Base):
    """Append-only price history for Polymarket events (one row per event per fetch)."""

    __tablename__ = "polymarket_price_snapshots"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    slug: Mapped[str] = mapped_column(String(200))
    title: Mapped[str] = mapped_column(String(500))
    yes_price: Mapped[float] = mapped_column(Float)
    volume_24h: Mapped[float | None] = mapped_column(Float, nullable=True)
    liquidity: Mapped[float | None] = mapped_column(Float, nullable=True)
    one_day_change: Mapped[float | None] = mapped_column(Float, nullable=True)
    category: Mapped[str | None] = mapped_column(String(50), nullable=True)
    fetched_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc)
    )

    __table_args__ = (
        Index("idx_pm_snap_slug_fetched", "slug", "fetched_at"),
        Index("idx_pm_snap_fetched", "fetched_at"),
    )


class PolymarketSmartSignal(Base):
    """Detected smart money signals from contrarian Polymarket moves."""

    __tablename__ = "polymarket_smart_signals"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    slug: Mapped[str] = mapped_column(String(200))
    title: Mapped[str] = mapped_column(String(500))
    signal_type: Mapped[str] = mapped_column(String(20))  # contrarian, no_news
    price_before: Mapped[float] = mapped_column(Float)
    price_after: Mapped[float] = mapped_column(Float)
    move_cents: Mapped[float] = mapped_column(Float)
    move_direction: Mapped[str] = mapped_column(String(5))  # up, down
    news_count_4h: Mapped[int] = mapped_column(Integer, default=0)
    news_consensus: Mapped[str] = mapped_column(
        String(20)
    )  # supports, contradicts, none
    confidence: Mapped[float] = mapped_column(Float)
    reasoning_en: Mapped[str] = mapped_column(Text)
    reasoning_vn: Mapped[str] = mapped_column(Text)
    category: Mapped[str | None] = mapped_column(String(50), nullable=True)
    detected_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc)
    )
    is_dismissed: Mapped[bool] = mapped_column(
        Boolean, default=False, server_default="0"
    )
    llm_explanation_en: Mapped[str | None] = mapped_column(Text)
    llm_explanation_vn: Mapped[str | None] = mapped_column(Text)
    llm_generated_at: Mapped[datetime | None] = mapped_column(DateTime)

    __table_args__ = (
        Index("idx_pm_signal_slug", "slug"),
        Index("idx_pm_signal_detected", "detected_at"),
        Index("idx_pm_signal_dismissed", "is_dismissed"),
    )


class PolymarketVolumeSnapshot(Base):
    __tablename__ = "polymarket_volume_snapshots"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    slug: Mapped[str] = mapped_column(String(200))
    market_token_id: Mapped[str] = mapped_column(String(200))
    market_question: Mapped[str] = mapped_column(String(500))
    volume_24h: Mapped[float] = mapped_column(Float)
    snapshot_date: Mapped[str] = mapped_column(String(10))
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc)
    )

    __table_args__ = (
        Index("idx_pm_vol_unique", "market_token_id", "snapshot_date", unique=True),
        Index("idx_pm_vol_slug", "slug"),
    )
