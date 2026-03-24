import pytest
from httpx import ASGITransport, AsyncClient

from src.api.main import app


@pytest.mark.asyncio
async def test_health_returns_200():
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as client:
        response = await client.get("/health")
        assert response.status_code == 200


@pytest.mark.asyncio
async def test_health_response_structure():
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as client:
        response = await client.get("/health")
        data = response.json()
        assert data["status"] == "ok"
        assert data["app"] == "gold_advisor"
        assert "database" in data
        assert "scheduler" in data
        assert data["scheduler"] == "not_started"
