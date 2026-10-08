from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from contextlib import asynccontextmanager
import os

# Setup system proxy before any other imports if configured
if os.getenv("PROXY_ENABLED") == "true" and os.getenv("PROXY_AUTO_SETUP") == "true":
    try:
        import sys
        sys.path.insert(0, os.path.dirname(__file__))
        from scripts.setup_system_proxy import setup_brightdata_system_proxy
        setup_brightdata_system_proxy()
    except Exception as e:
        print(f"Warning: Could not setup system proxy: {e}")

from dotenv import load_dotenv
from app.config import settings
from app.db import init_db, seed_platform_configs
from app.security.secret_store import init_secret_store
from app.modules.proxies.domain.proxy import init_proxy_manager
from app.modules.browsers.domain.browser_profile import init_browser_manager
from app.api.accounts import router as accounts_router
from app.api.proxies import router as proxies_router
from app.api.websocket import router as websocket_router
from app.api.proxy_status import router as proxy_status_router
from app.api.account_import import router as account_import_router
from app.api.instagram_ai import router as instagram_ai_router

import logging

load_dotenv()

os.makedirs("./data", exist_ok=True)
os.makedirs("./logs", exist_ok=True)
os.makedirs("./data/secrets", exist_ok=True)
os.makedirs("./data/evidence", exist_ok=True)

logging.basicConfig(
    level=getattr(logging, settings.logging_level),
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[
        logging.FileHandler(settings.logging_file),
        logging.StreamHandler()
    ]
)

logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Lifecycle manager"""
    logger.info("Starting android-farm")

    try:
        init_db(settings.database_url)
        seed_platform_configs()

        init_secret_store(
            key_file=settings.secret_store_key_file,
            storage_path=settings.secret_store_storage_path
        )

        init_proxy_manager(
            pool_size=settings.proxy_pool_size,
            rotation_strategy=settings.proxy_rotation_strategy
        )

        init_browser_manager(
            headless=settings.browser_headless,
            anti_detect=settings.browser_anti_detect
        )

        logger.info("android-farm initialized successfully")

        yield

    except Exception as e:
        logger.error(f"Failed to initialize android-farm: {e}")
        raise

    finally:
        logger.info("Shutting down android-farm")


app = FastAPI(
    title="Android Farm",
    description="Account factory for Outlook and Instagram",
    version="1.0.0",
    lifespan=lifespan
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# API routes
app.include_router(accounts_router, prefix="/api")
app.include_router(proxies_router, prefix="/api")
app.include_router(websocket_router, prefix="/api")
app.include_router(proxy_status_router, prefix="/api")
app.include_router(account_import_router, prefix="/api")
app.include_router(instagram_ai_router, prefix="/api")

# Serve evidence files
@app.get("/api/evidence/{filename}")
async def serve_evidence(filename: str):
    """Serve evidence screenshot files"""
    file_path = f"./data/evidence/{filename}"
    if os.path.exists(file_path):
        return FileResponse(file_path)
    raise Exception("File not found")


@app.get("/api/health")
async def health_check():
    """Health check endpoint"""
    return {
        "status": "healthy",
        "version": "1.0.0",
        "platforms": ["outlook", "instagram"]
    }


@app.get("/api")
async def api_info():
    """API info endpoint"""
    return {
        "title": "Android Farm API",
        "version": "1.0.0",
        "description": "Account factory for automated account creation",
        "health": "/api/health",
        "accounts": "/api/accounts",
        "proxies": "/api/proxies"
    }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "app.main:app",
        host=settings.server_host,
        port=settings.server_port,
        reload=settings.server_debug
    )
