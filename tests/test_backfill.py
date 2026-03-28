"""Tests for Polymarket CLOB gap backfill."""

import pytest
from datetime import datetime, timedelta, timezone
from unittest.mock import AsyncMock, MagicMock, patch

from src.ingestion.polymarket.backfill import run_gap_backfill


def _make_settings(**overrides):
    defaults = {
        "polymarket_backfill_interval_hours": 6,
        "polymarket_backfill_fidelity": 60,
        "polymarket_backfill_default_hours": 24,
        "polymarket_backfill_max_days": 7,
    }
    defaults.update(overrides)
    settings = MagicMock()
    for k, v in defaults.items():
        setattr(settings, k, v)
    return settings


def _make_event(
    slug="test-event",
    title="Test Event",
    clob_token_id_yes="0xtoken123",
    category="Finance",
):
    event = MagicMock()
    event.slug = slug
    event.title = title
    event.clob_token_id_yes = clob_token_id_yes
    event.category = category
    return event


def _make_price_point(ts_offset_seconds=0, price=0.65):
    pt = MagicMock()
    pt.t = int(datetime.now(timezone.utc).timestamp()) - ts_offset_seconds
    pt.p = price
    return pt


@pytest.mark.asyncio
async def test_no_events_with_clob_tokens():
    settings = _make_settings()

    with (
        patch("src.storage.database.async_session") as mock_async_session,
        patch(
            "src.storage.repository.get_events_with_clob_tokens",
            new_callable=AsyncMock,
            return_value=[],
        ),
    ):
        mock_session = AsyncMock()
        mock_session.__aenter__ = AsyncMock(return_value=mock_session)
        mock_session.__aexit__ = AsyncMock(return_value=False)
        mock_async_session.return_value = mock_session

        result = await run_gap_backfill(settings)

    assert result == {
        "events_processed": 0,
        "snapshots_saved": 0,
        "signals_detected": 0,
    }


@pytest.mark.asyncio
async def test_no_gap_needed():
    settings = _make_settings()
    event = _make_event()
    now = datetime.now(timezone.utc)

    with (
        patch("src.storage.database.async_session") as mock_async_session,
        patch(
            "src.storage.repository.get_events_with_clob_tokens", new_callable=AsyncMock
        ) as mock_get_events,
        patch(
            "src.storage.repository.get_latest_snapshot_ts_per_slug",
            new_callable=AsyncMock,
        ) as mock_get_ts,
    ):
        mock_session = AsyncMock()
        mock_session.__aenter__ = AsyncMock(return_value=mock_session)
        mock_session.__aexit__ = AsyncMock(return_value=False)
        mock_async_session.return_value = mock_session

        mock_get_events.return_value = [event]
        mock_get_ts.return_value = {event.slug: now - timedelta(minutes=30)}

        result = await run_gap_backfill(settings)

    assert result["snapshots_saved"] == 0
    assert result["events_processed"] == 0


@pytest.mark.asyncio
async def test_gap_backfill_fills_missing_data():
    settings = _make_settings()
    event = _make_event()
    gap_start = datetime.now(timezone.utc) - timedelta(hours=3)
    points = [
        _make_price_point(ts_offset_seconds=7200, price=0.60),
        _make_price_point(ts_offset_seconds=3600, price=0.65),
    ]

    with (
        patch("src.storage.database.async_session") as mock_async_session,
        patch(
            "src.storage.repository.get_events_with_clob_tokens", new_callable=AsyncMock
        ) as mock_get_events,
        patch(
            "src.storage.repository.get_latest_snapshot_ts_per_slug",
            new_callable=AsyncMock,
        ) as mock_get_ts,
        patch(
            "src.ingestion.fetchers.polymarket_clob.fetch_price_history",
            new_callable=AsyncMock,
        ) as mock_fetch,
        patch(
            "src.storage.repository.save_price_snapshots_backfill",
            new_callable=AsyncMock,
        ) as mock_save,
        patch("src.ingestion.polymarket.backfill.httpx.AsyncClient"),
        patch(
            "src.ingestion.polymarket.backfill._get_pre_gap_snapshots",
            new_callable=AsyncMock,
            return_value=[],
        ),
        patch(
            "src.storage.repository.get_recent_news",
            new_callable=AsyncMock,
            return_value=[],
        ),
        patch(
            "src.ingestion.polymarket.smart_money.detect_smart_moves", return_value=[]
        ),
    ):
        mock_session = AsyncMock()
        mock_session.__aenter__ = AsyncMock(return_value=mock_session)
        mock_session.__aexit__ = AsyncMock(return_value=False)
        mock_session.commit = AsyncMock()
        mock_async_session.return_value = mock_session

        mock_get_events.return_value = [event]
        mock_get_ts.return_value = {event.slug: gap_start}
        mock_fetch.return_value = points
        mock_save.return_value = len(points)

        result = await run_gap_backfill(settings)

    assert result["snapshots_saved"] == 2
    assert result["events_processed"] == 1
    mock_fetch.assert_called_once()


@pytest.mark.asyncio
async def test_no_snapshots_uses_default_hours():
    settings = _make_settings(polymarket_backfill_default_hours=24)
    event = _make_event()
    now = datetime.now(timezone.utc)
    points = [_make_price_point(ts_offset_seconds=86400, price=0.55)]

    with (
        patch("src.storage.database.async_session") as mock_async_session,
        patch(
            "src.storage.repository.get_events_with_clob_tokens", new_callable=AsyncMock
        ) as mock_get_events,
        patch(
            "src.storage.repository.get_latest_snapshot_ts_per_slug",
            new_callable=AsyncMock,
        ) as mock_get_ts,
        patch(
            "src.ingestion.fetchers.polymarket_clob.fetch_price_history",
            new_callable=AsyncMock,
        ) as mock_fetch,
        patch(
            "src.storage.repository.save_price_snapshots_backfill",
            new_callable=AsyncMock,
        ) as mock_save,
        patch("src.ingestion.polymarket.backfill.httpx.AsyncClient"),
        patch(
            "src.ingestion.polymarket.backfill._get_pre_gap_snapshots",
            new_callable=AsyncMock,
            return_value=[],
        ),
        patch(
            "src.storage.repository.get_recent_news",
            new_callable=AsyncMock,
            return_value=[],
        ),
        patch(
            "src.ingestion.polymarket.smart_money.detect_smart_moves", return_value=[]
        ),
    ):
        mock_session = AsyncMock()
        mock_session.__aenter__ = AsyncMock(return_value=mock_session)
        mock_session.__aexit__ = AsyncMock(return_value=False)
        mock_session.commit = AsyncMock()
        mock_async_session.return_value = mock_session

        mock_get_events.return_value = [event]
        mock_get_ts.return_value = {}
        mock_fetch.return_value = points
        mock_save.return_value = 1

        result = await run_gap_backfill(settings)

    call_args = mock_fetch.call_args
    start_ts = call_args[0][2]
    expected_start = int(now.timestamp()) - 24 * 3600
    assert abs(start_ts - expected_start) < 5
    assert result["snapshots_saved"] == 1


@pytest.mark.asyncio
async def test_backfill_runs_smart_money_detection():
    settings = _make_settings()
    event = _make_event()
    gap_start = datetime.now(timezone.utc) - timedelta(hours=3)
    points = [_make_price_point(ts_offset_seconds=7200, price=0.50)]
    signal = {
        "slug": event.slug,
        "title": event.title,
        "signal_type": "no_news",
        "price_before": 0.40,
        "price_after": 0.50,
        "move_cents": 10.0,
        "move_direction": "up",
        "news_count_4h": 0,
        "news_consensus": "none",
        "confidence": 0.5,
        "reasoning_en": "Price moved up 10.0c",
        "reasoning_vn": "Gia tang 10.0c",
        "category": "Finance",
    }

    with (
        patch("src.storage.database.async_session") as mock_async_session,
        patch(
            "src.storage.repository.get_events_with_clob_tokens", new_callable=AsyncMock
        ) as mock_get_events,
        patch(
            "src.storage.repository.get_latest_snapshot_ts_per_slug",
            new_callable=AsyncMock,
        ) as mock_get_ts,
        patch(
            "src.ingestion.fetchers.polymarket_clob.fetch_price_history",
            new_callable=AsyncMock,
        ) as mock_fetch,
        patch(
            "src.storage.repository.save_price_snapshots_backfill",
            new_callable=AsyncMock,
        ) as mock_save,
        patch("src.ingestion.polymarket.backfill.httpx.AsyncClient"),
        patch(
            "src.ingestion.polymarket.backfill._get_pre_gap_snapshots",
            new_callable=AsyncMock,
            return_value=[],
        ),
        patch(
            "src.storage.repository.get_recent_news",
            new_callable=AsyncMock,
            return_value=[],
        ),
        patch(
            "src.ingestion.polymarket.smart_money.detect_smart_moves",
            return_value=[signal],
        ),
        patch(
            "src.storage.repository.save_smart_signal", new_callable=AsyncMock
        ) as mock_save_signal,
        patch("src.alerts.dispatcher.AlertDispatcher") as mock_dispatcher_cls,
    ):
        mock_session = AsyncMock()
        mock_session.__aenter__ = AsyncMock(return_value=mock_session)
        mock_session.__aexit__ = AsyncMock(return_value=False)
        mock_session.commit = AsyncMock()
        mock_async_session.return_value = mock_session

        mock_get_events.return_value = [event]
        mock_get_ts.return_value = {event.slug: gap_start}
        mock_fetch.return_value = points
        mock_save.return_value = 1

        mock_dispatcher = MagicMock()
        mock_dispatcher.dispatch_smart_money_alerts = AsyncMock()
        mock_dispatcher_cls.return_value = mock_dispatcher

        result = await run_gap_backfill(settings)

    assert result["signals_detected"] == 1
    mock_save_signal.assert_called_once()


@pytest.mark.asyncio
async def test_one_event_failure_doesnt_block_others():
    settings = _make_settings()
    event1 = _make_event(slug="event-1", clob_token_id_yes="0xtoken1")
    event2 = _make_event(slug="event-2", clob_token_id_yes="0xtoken2")
    gap_start = datetime.now(timezone.utc) - timedelta(hours=3)
    points = [_make_price_point(ts_offset_seconds=7200, price=0.65)]

    with (
        patch("src.storage.database.async_session") as mock_async_session,
        patch(
            "src.storage.repository.get_events_with_clob_tokens", new_callable=AsyncMock
        ) as mock_get_events,
        patch(
            "src.storage.repository.get_latest_snapshot_ts_per_slug",
            new_callable=AsyncMock,
        ) as mock_get_ts,
        patch(
            "src.ingestion.fetchers.polymarket_clob.fetch_price_history",
            new_callable=AsyncMock,
        ) as mock_fetch,
        patch(
            "src.storage.repository.save_price_snapshots_backfill",
            new_callable=AsyncMock,
        ) as mock_save,
        patch("src.ingestion.polymarket.backfill.httpx.AsyncClient"),
        patch(
            "src.ingestion.polymarket.backfill._get_pre_gap_snapshots",
            new_callable=AsyncMock,
            return_value=[],
        ),
        patch(
            "src.storage.repository.get_recent_news",
            new_callable=AsyncMock,
            return_value=[],
        ),
        patch(
            "src.ingestion.polymarket.smart_money.detect_smart_moves", return_value=[]
        ),
    ):
        mock_session = AsyncMock()
        mock_session.__aenter__ = AsyncMock(return_value=mock_session)
        mock_session.__aexit__ = AsyncMock(return_value=False)
        mock_session.commit = AsyncMock()
        mock_async_session.return_value = mock_session

        mock_get_events.return_value = [event1, event2]
        mock_get_ts.return_value = {
            event1.slug: gap_start,
            event2.slug: gap_start,
        }
        mock_fetch.side_effect = [Exception("API error"), points]
        mock_save.return_value = 1

        result = await run_gap_backfill(settings)

    assert result["events_processed"] == 1
    assert result["snapshots_saved"] == 1


@pytest.mark.asyncio
async def test_backfill_capped_at_max_days():
    settings = _make_settings(polymarket_backfill_max_days=3)
    event = _make_event()
    old_ts = datetime.now(timezone.utc) - timedelta(days=10)
    points = [_make_price_point(ts_offset_seconds=86400, price=0.55)]

    with (
        patch("src.storage.database.async_session") as mock_async_session,
        patch(
            "src.storage.repository.get_events_with_clob_tokens", new_callable=AsyncMock
        ) as mock_get_events,
        patch(
            "src.storage.repository.get_latest_snapshot_ts_per_slug",
            new_callable=AsyncMock,
        ) as mock_get_ts,
        patch(
            "src.ingestion.fetchers.polymarket_clob.fetch_price_history",
            new_callable=AsyncMock,
        ) as mock_fetch,
        patch(
            "src.storage.repository.save_price_snapshots_backfill",
            new_callable=AsyncMock,
        ) as mock_save,
        patch("src.ingestion.polymarket.backfill.httpx.AsyncClient"),
        patch(
            "src.ingestion.polymarket.backfill._get_pre_gap_snapshots",
            new_callable=AsyncMock,
            return_value=[],
        ),
        patch(
            "src.storage.repository.get_recent_news",
            new_callable=AsyncMock,
            return_value=[],
        ),
        patch(
            "src.ingestion.polymarket.smart_money.detect_smart_moves", return_value=[]
        ),
    ):
        mock_session = AsyncMock()
        mock_session.__aenter__ = AsyncMock(return_value=mock_session)
        mock_session.__aexit__ = AsyncMock(return_value=False)
        mock_session.commit = AsyncMock()
        mock_async_session.return_value = mock_session

        mock_get_events.return_value = [event]
        mock_get_ts.return_value = {event.slug: old_ts}
        mock_fetch.return_value = points
        mock_save.return_value = 1

        result = await run_gap_backfill(settings)

    call_args = mock_fetch.call_args
    start_ts = call_args[0][2]
    now_ts = int(datetime.now(timezone.utc).timestamp())
    max_back_seconds = 3 * 86400
    actual_span = now_ts - start_ts
    assert actual_span <= max_back_seconds + 5
    assert result["snapshots_saved"] == 1


@pytest.mark.asyncio
async def test_empty_clob_response_uses_fallback():
    settings = _make_settings()
    event = _make_event()
    gap_start = datetime.now(timezone.utc) - timedelta(hours=3)
    fallback_points = [_make_price_point(ts_offset_seconds=3600, price=0.70)]

    with (
        patch("src.storage.database.async_session") as mock_async_session,
        patch(
            "src.storage.repository.get_events_with_clob_tokens", new_callable=AsyncMock
        ) as mock_get_events,
        patch(
            "src.storage.repository.get_latest_snapshot_ts_per_slug",
            new_callable=AsyncMock,
        ) as mock_get_ts,
        patch(
            "src.ingestion.fetchers.polymarket_clob.fetch_price_history",
            new_callable=AsyncMock,
        ) as mock_fetch,
        patch(
            "src.ingestion.fetchers.polymarket_clob.fetch_price_history_fallback",
            new_callable=AsyncMock,
        ) as mock_fallback,
        patch(
            "src.storage.repository.save_price_snapshots_backfill",
            new_callable=AsyncMock,
        ) as mock_save,
        patch("src.ingestion.polymarket.backfill.httpx.AsyncClient"),
        patch(
            "src.ingestion.polymarket.backfill._get_pre_gap_snapshots",
            new_callable=AsyncMock,
            return_value=[],
        ),
        patch(
            "src.storage.repository.get_recent_news",
            new_callable=AsyncMock,
            return_value=[],
        ),
        patch(
            "src.ingestion.polymarket.smart_money.detect_smart_moves", return_value=[]
        ),
    ):
        mock_session = AsyncMock()
        mock_session.__aenter__ = AsyncMock(return_value=mock_session)
        mock_session.__aexit__ = AsyncMock(return_value=False)
        mock_session.commit = AsyncMock()
        mock_async_session.return_value = mock_session

        mock_get_events.return_value = [event]
        mock_get_ts.return_value = {event.slug: gap_start}
        mock_fetch.return_value = []
        mock_fallback.return_value = fallback_points
        mock_save.return_value = 1

        result = await run_gap_backfill(settings)

    mock_fetch.assert_called_once()
    mock_fallback.assert_called_once()
    assert result["snapshots_saved"] == 1
