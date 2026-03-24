import os
import tempfile
from datetime import datetime, timedelta, timezone

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from src.storage.models import Base, PolicyEvent


@pytest.fixture
def db_with_events():
    fd, path = tempfile.mkstemp(suffix=".db")
    os.close(fd)
    engine = create_engine(f"sqlite:///{path}")
    Base.metadata.create_all(engine)
    now = datetime.now(timezone.utc)

    with Session(engine) as session:
        session.add(
            PolicyEvent(
                event_type="auction",
                description="SBV gold auction announced",
                impact="bearish",
                severity="high",
                effective_date=now - timedelta(days=2),
                is_active=True,
            )
        )
        session.add(
            PolicyEvent(
                event_type="import_approval",
                description="Import licenses approved for 5 enterprises",
                impact="bullish",
                severity="medium",
                effective_date=now - timedelta(days=5),
                is_active=True,
            )
        )
        session.add(
            PolicyEvent(
                event_type="inspection",
                description="Market inspection campaign completed",
                impact="neutral",
                severity="low",
                effective_date=now - timedelta(days=10),
                is_active=True,
            )
        )
        session.add(
            PolicyEvent(
                event_type="regulation_change",
                description="Decree 232 enacted",
                impact="neutral",
                severity="high",
                effective_date=now - timedelta(days=60),
                expires_at=now - timedelta(days=1),
                is_active=True,
            )
        )
        session.add(
            PolicyEvent(
                event_type="auction",
                description="Old inactive auction",
                impact="bearish",
                severity="high",
                effective_date=now - timedelta(days=30),
                is_active=False,
            )
        )
        session.commit()
    yield path
    os.unlink(path)


@pytest.fixture
def empty_db():
    fd, path = tempfile.mkstemp(suffix=".db")
    os.close(fd)
    engine = create_engine(f"sqlite:///{path}")
    Base.metadata.create_all(engine)
    yield path
    os.unlink(path)


class TestPolicyEventModel:
    def test_create_event_with_required_fields(self, empty_db):
        now = datetime.now(timezone.utc)
        engine = create_engine(f"sqlite:///{empty_db}")
        with Session(engine) as session:
            event = PolicyEvent(
                event_type="auction",
                description="Test event",
                impact="bearish",
                severity="high",
                effective_date=now,
            )
            session.add(event)
            session.commit()
            assert event.id is not None
            assert event.is_active is True
            assert event.created_at is not None

    def test_event_with_expiry(self, empty_db):
        now = datetime.now(timezone.utc)
        engine = create_engine(f"sqlite:///{empty_db}")
        with Session(engine) as session:
            event = PolicyEvent(
                event_type="auction",
                description="Test event",
                impact="bearish",
                severity="high",
                effective_date=now,
                expires_at=now + timedelta(days=30),
            )
            session.add(event)
            session.commit()
            assert event.expires_at is not None


class TestComputePolicySignal:
    def test_no_events_returns_no_override(self, empty_db):
        from src.engine.policy import compute_policy_signal

        result = compute_policy_signal(empty_db)
        assert result["has_override"] is False
        assert result["override_type"] is None
        assert result["confidence_cap"] == 1.0
        assert result["active_events"] == []

    def test_active_high_severity_creates_override(self, db_with_events):
        from src.engine.policy import compute_policy_signal

        result = compute_policy_signal(db_with_events)
        assert result["has_override"] is True
        assert result["confidence_cap"] < 1.0

    def test_expired_events_excluded(self, db_with_events):
        from src.engine.policy import compute_policy_signal

        result = compute_policy_signal(db_with_events)
        active_types = [e.event_type for e in result["active_events"]]
        assert "regulation_change" not in active_types

    def test_inactive_events_excluded(self, db_with_events):
        from src.engine.policy import compute_policy_signal

        result = compute_policy_signal(db_with_events)
        active_ids = [e.id for e in result["active_events"]]
        assert 5 not in active_ids

    def test_high_severity_caps_confidence_at_0_3(self, db_with_events):
        from src.engine.policy import compute_policy_signal

        result = compute_policy_signal(db_with_events)
        assert result["confidence_cap"] == 0.3

    def test_only_medium_severity_caps_at_0_6(self, empty_db):
        from src.engine.policy import compute_policy_signal

        now = datetime.now(timezone.utc)
        engine = create_engine(f"sqlite:///{empty_db}")
        with Session(engine) as session:
            session.add(
                PolicyEvent(
                    event_type="import_approval",
                    description="Import approved",
                    impact="bullish",
                    severity="medium",
                    effective_date=now,
                    is_active=True,
                )
            )
            session.commit()
        result = compute_policy_signal(empty_db)
        assert result["confidence_cap"] == 0.6

    def test_only_low_severity_no_cap(self, empty_db):
        from src.engine.policy import compute_policy_signal

        now = datetime.now(timezone.utc)
        engine = create_engine(f"sqlite:///{empty_db}")
        with Session(engine) as session:
            session.add(
                PolicyEvent(
                    event_type="inspection",
                    description="Inspection",
                    impact="neutral",
                    severity="low",
                    effective_date=now,
                    is_active=True,
                )
            )
            session.commit()
        result = compute_policy_signal(empty_db)
        assert result["confidence_cap"] == 1.0

    def test_summary_contains_event_description(self, db_with_events):
        from src.engine.policy import compute_policy_signal

        result = compute_policy_signal(db_with_events)
        assert "auction" in result["summary"].lower()

    def test_bearish_impact_sets_override_type(self, empty_db):
        from src.engine.policy import compute_policy_signal

        now = datetime.now(timezone.utc)
        engine = create_engine(f"sqlite:///{empty_db}")
        with Session(engine) as session:
            session.add(
                PolicyEvent(
                    event_type="auction",
                    description="SBV auction",
                    impact="bearish",
                    severity="high",
                    effective_date=now,
                    is_active=True,
                )
            )
            session.commit()
        result = compute_policy_signal(empty_db)
        assert result["override_type"] == "bearish"


class TestAdminAPI:
    @pytest.fixture
    def admin_test_db(self, tmp_path):
        from unittest.mock import patch
        from fastapi import FastAPI
        from fastapi.testclient import TestClient
        from sqlalchemy.ext.asyncio import (
            AsyncSession,
            async_sessionmaker,
            create_async_engine,
        )

        db_file = tmp_path / "test_admin_api.db"
        db_url = f"sqlite+aiosqlite:///{db_file}"

        engine = create_async_engine(db_url, echo=False)

        async def _init():
            async with engine.begin() as conn:
                await conn.run_sync(Base.metadata.create_all)

        import asyncio

        asyncio.get_event_loop().run_until_complete(_init())

        session_factory = async_sessionmaker(
            engine, class_=AsyncSession, expire_on_commit=False
        )

        with patch(
            "src.api.routes.admin.async_session",
            session_factory,
        ):
            from src.api.routes.admin import router

            app = FastAPI()
            app.include_router(router, prefix="/api/admin", tags=["admin"])
            client = TestClient(app)
            yield {"client": client, "session_factory": session_factory}

        import asyncio

        asyncio.get_event_loop().run_until_complete(engine.dispose())

    def test_create_policy_event(self, admin_test_db):
        client = admin_test_db["client"]
        response = client.post(
            "/api/admin/policy-events",
            json={
                "event_type": "auction",
                "description": "SBV gold auction",
                "impact": "bearish",
                "severity": "high",
                "effective_date": datetime.now(timezone.utc).isoformat(),
            },
        )
        assert response.status_code == 200
        data = response.json()
        assert data["event_type"] == "auction"
        assert data["is_active"] is True

    def test_list_policy_events(self, admin_test_db):
        client = admin_test_db["client"]
        client.post(
            "/api/admin/policy-events",
            json={
                "event_type": "auction",
                "description": "Test event",
                "impact": "bearish",
                "severity": "high",
                "effective_date": datetime.now(timezone.utc).isoformat(),
            },
        )
        response = client.get("/api/admin/policy-events")
        assert response.status_code == 200
        data = response.json()
        assert len(data) == 1

    def test_list_active_only(self, admin_test_db):
        client = admin_test_db["client"]
        now = datetime.now(timezone.utc)
        client.post(
            "/api/admin/policy-events",
            json={
                "event_type": "auction",
                "description": "Active event",
                "impact": "bearish",
                "severity": "high",
                "effective_date": now.isoformat(),
            },
        )
        client.post(
            "/api/admin/policy-events",
            json={
                "event_type": "inspection",
                "description": "Another active event",
                "impact": "neutral",
                "severity": "low",
                "effective_date": (now - timedelta(days=10)).isoformat(),
            },
        )
        all_resp = client.get("/api/admin/policy-events")
        assert len(all_resp.json()) == 2
        active_resp = client.get("/api/admin/policy-events?active_only=true")
        assert len(active_resp.json()) == 2

    def test_delete_policy_event(self, admin_test_db):
        client = admin_test_db["client"]
        create_resp = client.post(
            "/api/admin/policy-events",
            json={
                "event_type": "auction",
                "description": "To delete",
                "impact": "bearish",
                "severity": "high",
                "effective_date": datetime.now(timezone.utc).isoformat(),
            },
        )
        event_id = create_resp.json()["id"]
        delete_resp = client.delete(f"/api/admin/policy-events/{event_id}")
        assert delete_resp.status_code == 200
        assert delete_resp.json()["is_active"] is False

    def test_invalid_event_type_rejected(self, admin_test_db):
        client = admin_test_db["client"]
        response = client.post(
            "/api/admin/policy-events",
            json={
                "event_type": "invalid_type",
                "description": "Bad event",
                "impact": "bearish",
                "severity": "high",
                "effective_date": datetime.now(timezone.utc).isoformat(),
            },
        )
        assert response.status_code == 422

    def test_invalid_impact_rejected(self, admin_test_db):
        client = admin_test_db["client"]
        response = client.post(
            "/api/admin/policy-events",
            json={
                "event_type": "auction",
                "description": "Bad impact",
                "impact": "unknown",
                "severity": "high",
                "effective_date": datetime.now(timezone.utc).isoformat(),
            },
        )
        assert response.status_code == 422
