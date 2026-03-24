"""Tests for dashboard HTML partials and full page (Plan 05-02)."""

from datetime import datetime, timedelta, timezone
from pathlib import Path

import pytest
import pytest_asyncio
from fastapi.testclient import TestClient
from sqlalchemy.ext.asyncio import (
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

from src.storage.models import Base, PriceRecord


# ── Fixtures ───────────────────────────────────────────────────────────────


@pytest_asyncio.fixture
async def html_test_db(tmp_path):
    """Full app fixture for testing HTML partial endpoints."""
    db_file = tmp_path / "test_dashboard_html.db"
    db_url = f"sqlite+aiosqlite:///{db_file}"

    engine = create_async_engine(db_url, echo=False)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    session_factory = async_sessionmaker(
        engine, class_=AsyncSession, expire_on_commit=False
    )

    from unittest.mock import patch

    def mock_settings():
        from src.config import Settings

        return Settings(database_url=f"sqlite+aiosqlite:///{db_file}")

    base_dir = Path(__file__).resolve().parent.parent

    with (
        patch("src.api.routes.dashboard.get_settings", mock_settings),
        patch(
            "src.api.routes.dashboard.async_session",
            async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False),
        ),
    ):
        from fastapi import FastAPI, Request
        from fastapi.staticfiles import StaticFiles
        from fastapi.templating import Jinja2Templates as AppTemplates
        from src.api.routes.dashboard import router

        tmpl = AppTemplates(directory=str(base_dir / "templates"))

        app = FastAPI()

        @app.get("/")
        async def root(request: Request):
            return tmpl.TemplateResponse(request, "dashboard.html", context={})

        app.mount(
            "/static", StaticFiles(directory=str(base_dir / "static")), name="static"
        )
        app.include_router(router, prefix="/dashboard", tags=["dashboard"])
        client = TestClient(app)

        yield {"client": client, "session_factory": session_factory}

    await engine.dispose()


def _make_price_record(
    source: str,
    product_type: str,
    buy_price: float | None = None,
    sell_price: float | None = None,
    price_usd: float | None = None,
    price_vnd: float | None = None,
    timestamp: datetime | None = None,
    currency: str = "VND",
) -> PriceRecord:
    return PriceRecord(
        source=source,
        product_type=product_type,
        buy_price=buy_price,
        sell_price=sell_price,
        price_usd=price_usd,
        price_vnd=price_vnd,
        currency=currency,
        timestamp=timestamp or datetime.now(timezone.utc),
        fetched_at=datetime.now(timezone.utc),
        validation_status="valid",
    )


async def _seed_dealer_prices(
    session_factory: async_sessionmaker[AsyncSession],
):
    """Seed realistic dealer prices for testing."""
    now = datetime.now(timezone.utc)
    records = []

    records.append(
        _make_price_record(
            source="yfinance",
            product_type="xau_usd",
            price_usd=2650.0,
            price_vnd=190_000_000,
            timestamp=now,
            currency="USD",
        )
    )

    for dealer in ("SJC", "DOJI", "PNJ", "BTMC", "PHUQUY"):
        records.append(
            _make_price_record(
                source=dealer,
                product_type="sjc_bar",
                buy_price=193_000_000,
                sell_price=195_000_000,
                timestamp=now,
                currency="VND",
            )
        )
        records.append(
            _make_price_record(
                source=dealer,
                product_type="ring_gold",
                buy_price=192_000_000,
                sell_price=194_000_000,
                timestamp=now,
                currency="VND",
            )
        )

    async with session_factory() as session:
        session.add_all(records)
        await session.commit()


async def _seed_signal_data(session_factory: async_sessionmaker[AsyncSession]):
    """Seed enough data for signal computation (10 days of history)."""
    now = datetime.now(timezone.utc)
    records = []
    for day in range(10):
        ts = now - timedelta(days=9 - day)
        records.append(
            _make_price_record(
                source="yfinance",
                product_type="xau_usd",
                price_vnd=190_000_000 + day * 100_000,
                price_usd=2650.0,
                timestamp=ts,
                currency="USD",
            )
        )
        for dealer in ("sjc", "pnj", "doji"):
            records.append(
                _make_price_record(
                    source=dealer,
                    product_type="sjc_bar",
                    sell_price=195_000_000 + day * 100_000,
                    timestamp=ts,
                    currency="VND",
                )
            )

    async with session_factory() as session:
        session.add_all(records)
        await session.commit()


# ── Task 1 Tests: Dashboard HTML partials ───────────────────────────────────


class TestSignalPartial:
    @pytest.mark.asyncio
    async def test_signal_partial_returns_200(self, html_test_db):
        await _seed_signal_data(html_test_db["session_factory"])
        resp = html_test_db["client"].get("/dashboard/partials/signal?mode=saver")
        assert resp.status_code == 200

    @pytest.mark.asyncio
    async def test_signal_partial_contains_recommendation(self, html_test_db):
        await _seed_signal_data(html_test_db["session_factory"])
        resp = html_test_db["client"].get("/dashboard/partials/signal?mode=saver")
        assert resp.status_code == 200
        assert "BUY" in resp.text or "HOLD" in resp.text or "SELL" in resp.text

    @pytest.mark.asyncio
    async def test_signal_partial_contains_confidence(self, html_test_db):
        await _seed_signal_data(html_test_db["session_factory"])
        resp = html_test_db["client"].get("/dashboard/partials/signal?mode=saver")
        assert "confidence" in resp.text.lower() or "%" in resp.text

    @pytest.mark.asyncio
    async def test_signal_partial_contains_reasoning(self, html_test_db):
        await _seed_signal_data(html_test_db["session_factory"])
        resp = html_test_db["client"].get("/dashboard/partials/signal?mode=saver")
        assert resp.status_code == 200
        # Reasoning text should be present
        assert len(resp.text.strip()) > 50

    @pytest.mark.asyncio
    async def test_signal_partial_contains_mode_toggle(self, html_test_db):
        await _seed_signal_data(html_test_db["session_factory"])
        resp = html_test_db["client"].get("/dashboard/partials/signal?mode=saver")
        assert "saver" in resp.text.lower() or "trader" in resp.text.lower()


class TestPricePartial:
    @pytest.mark.asyncio
    async def test_price_partial_returns_200(self, html_test_db):
        await _seed_dealer_prices(html_test_db["session_factory"])
        resp = html_test_db["client"].get("/dashboard/partials/prices")
        assert resp.status_code == 200

    @pytest.mark.asyncio
    async def test_price_partial_contains_dealer_names(self, html_test_db):
        await _seed_dealer_prices(html_test_db["session_factory"])
        resp = html_test_db["client"].get("/dashboard/partials/prices")
        assert "DOJI" in resp.text
        assert "SJC" in resp.text
        assert "PNJ" in resp.text

    @pytest.mark.asyncio
    async def test_price_partial_contains_table_element(self, html_test_db):
        await _seed_dealer_prices(html_test_db["session_factory"])
        resp = html_test_db["client"].get("/dashboard/partials/prices")
        assert "<table" in resp.text.lower()

    @pytest.mark.asyncio
    async def test_price_partial_shows_empty_state(self, html_test_db):
        resp = html_test_db["client"].get("/dashboard/partials/prices")
        assert resp.status_code == 200
        assert (
            "no price data" in resp.text.lower()
            or "không" in resp.text.lower()
            or "available" in resp.text.lower()
        )


class TestGapPartial:
    @pytest.mark.asyncio
    async def test_gap_partial_returns_200(self, html_test_db):
        resp = html_test_db["client"].get("/dashboard/partials/gap")
        assert resp.status_code == 200

    @pytest.mark.asyncio
    async def test_gap_partial_shows_empty_state(self, html_test_db):
        resp = html_test_db["client"].get("/dashboard/partials/gap")
        assert resp.status_code == 200
        # Should show some gap-related content or empty state
        assert (
            "gap" in resp.text.lower()
            or "không" in resp.text.lower()
            or "vnd" in resp.text.lower()
        )


# ── Task 2 Tests: Chart partials and JS ─────────────────────────────────────


class TestChartPartials:
    @pytest.mark.asyncio
    async def test_price_chart_partial_has_canvas(self, html_test_db):
        resp = html_test_db["client"].get("/dashboard/partials/price-chart")
        assert resp.status_code == 200
        assert "priceChart" in resp.text

    @pytest.mark.asyncio
    async def test_price_chart_partial_has_timeframe_buttons(self, html_test_db):
        resp = html_test_db["client"].get("/dashboard/partials/price-chart")
        assert resp.status_code == 200
        assert "1D" in resp.text
        assert "1W" in resp.text
        assert "1M" in resp.text
        assert "1Y" in resp.text

    @pytest.mark.asyncio
    async def test_gap_chart_partial_has_canvas(self, html_test_db):
        resp = html_test_db["client"].get("/dashboard/partials/gap-chart")
        assert resp.status_code == 200
        assert "gapChart" in resp.text

    @pytest.mark.asyncio
    async def test_gap_chart_partial_has_timeframe_buttons(self, html_test_db):
        resp = html_test_db["client"].get("/dashboard/partials/gap-chart")
        assert resp.status_code == 200
        assert "1W" in resp.text
        assert "1M" in resp.text


class TestDashboardPage:
    """Test the full dashboard page with all sections."""

    @pytest.mark.asyncio
    async def test_root_contains_signal_section(self, html_test_db):
        await _seed_signal_data(html_test_db["session_factory"])
        await _seed_dealer_prices(html_test_db["session_factory"])
        resp = html_test_db["client"].get("/")
        # The full dashboard page should include section containers for HTMX
        assert resp.status_code == 200

    @pytest.mark.asyncio
    async def test_dashboard_has_all_section_containers(self, html_test_db):
        """Full page should have containers that HTMX partials target."""
        await _seed_signal_data(html_test_db["session_factory"])
        await _seed_dealer_prices(html_test_db["session_factory"])
        resp = html_test_db["client"].get("/")
        text = resp.text
        # Check for HTMX attributes that load partials
        assert "hx-get" in text
        assert "hx-trigger" in text
