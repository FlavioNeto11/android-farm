"""Test script para debug de extração de handle Instagram."""
import asyncio
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.db import init_db
from app.modules.browsers.domain.browser_profile import init_browser_manager, get_browser_manager
from app.security.secret_store import init_secret_store
from app.config import settings


async def test_extract():
    init_db(settings.database_url)
    init_browser_manager(headless=True, anti_detect=True)
    init_secret_store(key_file=settings.secret_store_key_file, storage_path=settings.secret_store_storage_path)

    from scripts.update_instagram_handles import extract_instagram_handle

    # Testar com primeira conta
    result = await extract_instagram_handle(
        "25cd216d-789f-4dc0-9cf6-112d020f81da",
        "beatriz.rocha902@outlook.com",
        "Test@123456"  # senha exemplo
    )
    print(f"Resultado: {result}")


if __name__ == "__main__":
    asyncio.run(test_extract())
