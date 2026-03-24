"""Tests for alert pipeline integration (Plan 06-03)."""

from datetime import datetime, timedelta, timezone
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from src.engine.types import Recommendation, Signal, SignalMode


def _make_signal(
    recommendation=Recommendation.HOLD,
    confidence=50,
    reasoning="Test",
    mode=SignalMode.SAVER,
):
    return Signal(
        recommendation=recommendation,
        confidence=confidence,
        reasoning=reasoning,
        mode=mode,
        timestamp=datetime.now(timezone.utc),
    )


class TestCheckAndDispatchAlerts:
    @pytest.fixture(autouse=True)
    def reset_dispatcher(self):
        import src.ingestion.scheduler as sched

        sched._dispatcher = None
        yield
        sched._dispatcher = None

    def test_creates_dispatcher(self):
        from src.ingestion.scheduler import check_and_dispatch_alerts

        settings = MagicMock()
        settings.database_url = "sqlite+aiosqlite:///test.db"

        with (
            patch("src.engine.pipeline.compute_signal") as mock_signal,
            patch("src.alerts.dispatcher.AlertDispatcher") as mock_dispatcher_cls,
        ):
            mock_signal.return_value = _make_signal(confidence=0)
            mock_dispatcher = MagicMock()
            mock_dispatcher.check_signal = AsyncMock(return_value=False)
            mock_dispatcher.check_price_movement = AsyncMock(return_value=False)
            mock_dispatcher_cls.return_value = mock_dispatcher

            check_and_dispatch_alerts(settings)

        mock_dispatcher_cls.assert_called()

    def test_calls_dispatcher_with_signal(self):
        from src.ingestion.scheduler import check_and_dispatch_alerts

        settings = MagicMock()
        settings.database_url = "sqlite+aiosqlite:///test.db"
        signal = _make_signal(Recommendation.BUY, 70)

        with (
            patch("src.engine.pipeline.compute_signal", return_value=signal),
            patch("src.alerts.dispatcher.AlertDispatcher") as mock_cls,
        ):
            mock_dispatcher = MagicMock()
            mock_dispatcher.check_signal = AsyncMock(return_value=True)
            mock_dispatcher.check_price_movement = AsyncMock(return_value=False)
            mock_cls.return_value = mock_dispatcher

            check_and_dispatch_alerts(settings)

        mock_dispatcher.check_signal.assert_called_once_with(signal)

    def test_handles_insufficient_data_no_crash(self):
        from src.ingestion.scheduler import check_and_dispatch_alerts

        settings = MagicMock()
        settings.database_url = "sqlite+aiosqlite:///test.db"
        signal = _make_signal(Recommendation.HOLD, 0)

        with (
            patch("src.engine.pipeline.compute_signal", return_value=signal),
            patch("src.alerts.dispatcher.AlertDispatcher") as mock_cls,
        ):
            mock_dispatcher = MagicMock()
            mock_dispatcher.check_signal = AsyncMock(return_value=False)
            mock_dispatcher.check_price_movement = AsyncMock(return_value=False)
            mock_cls.return_value = mock_dispatcher

            check_and_dispatch_alerts(settings)

        mock_dispatcher.check_signal.assert_called_once()

    def test_no_subscribers_no_crash(self):
        from src.ingestion.scheduler import check_and_dispatch_alerts

        settings = MagicMock()
        settings.database_url = "sqlite+aiosqlite:///test.db"
        signal = _make_signal(Recommendation.BUY, 70)

        with (
            patch("src.engine.pipeline.compute_signal", return_value=signal),
            patch("src.alerts.bot.SUBSCRIBED_CHATS", set()),
            patch("src.alerts.dispatcher.AlertDispatcher") as mock_cls,
        ):
            mock_dispatcher = MagicMock()
            mock_dispatcher.check_signal = AsyncMock(return_value=False)
            mock_dispatcher.check_price_movement = AsyncMock(return_value=False)
            mock_cls.return_value = mock_dispatcher

            check_and_dispatch_alerts(settings)

    def test_dispatcher_error_does_not_propagate(self):
        from src.ingestion.scheduler import check_and_dispatch_alerts

        settings = MagicMock()
        settings.database_url = "sqlite+aiosqlite:///test.db"

        with (
            patch(
                "src.engine.pipeline.compute_signal", side_effect=Exception("DB error")
            ),
            patch("src.alerts.dispatcher.AlertDispatcher") as mock_cls,
        ):
            mock_dispatcher = MagicMock()
            mock_dispatcher.check_signal = AsyncMock()
            mock_dispatcher.check_price_movement = AsyncMock()
            mock_cls.return_value = mock_dispatcher

            check_and_dispatch_alerts(settings)

        mock_dispatcher.check_signal.assert_not_called()


class TestSchedulerIntegration:
    def test_alert_job_added_to_scheduler(self):
        from src.ingestion.scheduler import start_scheduler

        app_state = {}
        settings = MagicMock()
        settings.fetch_interval_minutes = 5
        start_scheduler(app_state, [], MagicMock(), settings)

        jobs = app_state["scheduler"].get_jobs()
        job_ids = [j.id for j in jobs]
        assert "alert_dispatch" in job_ids

        app_state["scheduler"].shutdown(wait=False)


class TestLifespanWiring:
    @pytest.mark.asyncio
    async def test_start_bot_called_in_lifespan(self):
        from src.api.main import lifespan

        settings_mock = MagicMock()
        settings_mock.database_url = "sqlite+aiosqlite:///test.db"

        with (
            patch("src.api.main.init_db", new_callable=AsyncMock),
            patch("src.api.main.start_bot") as mock_start_bot,
            patch("src.api.main.stop_bot") as mock_stop_bot,
            patch("src.api.main.start_scheduler"),
            patch("src.api.main.stop_scheduler"),
            patch("src.api.main.set_app_state"),
            patch("src.api.main.Settings", return_value=settings_mock),
            patch("src.api.main.YFinanceGoldFetcher"),
            patch("src.api.main.VietcombankFxRateFetcher"),
            patch("src.api.main.DojiScraper"),
            patch("src.api.main.PhuQuyScraper"),
            patch("src.api.main.SJCScraper"),
            patch("src.api.main.PNJScraper"),
            patch("src.api.main.BTMCScraper"),
        ):
            from fastapi import FastAPI

            app = FastAPI(lifespan=lifespan)
            async with lifespan(app):
                pass

        mock_start_bot.assert_called_once()
        mock_stop_bot.assert_called_once()
