"""Tests básicos da api farm de contas"""
import pytest
from httpx import ASGITransport, AsyncClient
from app.main import app


@pytest.mark.asyncio
async def test_health_check():
    """Test endpoint de health"""
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        response = await ac.get("/api/health")
        assert response.status_code == 200
        assert response.json()["status"] == "healthy"
        assert response.json()["version"] == "1.0.0"
        assert response.json()["platforms"] == ["outlook", "instagram"]


@pytest.mark.asyncio
async def test_api_info():
    """Test endpoint info"""
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        response = await ac.get("/api")
        assert response.status_code == 200
        assert response.json() == {
            "title": "Android Farm API",
            "version": "1.0.0",
            "description": "Account factory for automated account creation",
            "health": "/api/health",
            "accounts": "/api/accounts",
            "proxies": "/api/proxies",
        }
