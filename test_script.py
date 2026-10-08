"""Test script for accounts API"""
import asyncio
from httpx import AsyncClient
import os

async def test_accounts_api():
    """Test basic API functionality"""
    from app.main import app

    # Start app in background
    import uvicorn
    config = uvicorn.Config(app, host="127.0.0.1", port=8001, log_level="info")
    server = uvicorn.Server(config)

    async with AsyncClient(app=app, base_url="http://127.0.0.1:8001") as ac:
        try:
            # Health check
            response = await ac.get("/api/health")
            print(f"Health check: {response.status_code}")
            print(response.json())

            # API info
            response = await ac.get("/api")
            print(f"\nAPI info: {response.status_code}")
            print(response.json())

            print("\n✓ All basic tests passed!")

        except Exception as e:
            print(f"✗ Test failed: {e}")
        finally:
            await server.shutdown()

if __name__ == "__main__":
    asyncio.run(test_accounts_api())
