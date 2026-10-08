"""Tests básicos da api farm de contas"""
import pytest
from httpx import AsyncClient
from app.main import app


@pytest.mark.asyncio
async def test_health_check():
    """Test endpoint de health"""
    async with AsyncClient(app=app, base_url="http://test") as ac:
        response = await ac.get("/api/health")
        assert response.status_code == 200
        assert response.json()["status"] == "healthy"


@pytest.mark.asyncio
async def test_api_info():
    """Test endpoint info"""
    async with AsyncClient(app=app, base_url="http://test") as ac:
        response = await ac.get("/api")
        assert response.status_code == 200
        assert "title" in response.json()
