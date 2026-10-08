import asyncio
import os
from typing import Optional, Dict, List
from datetime import datetime
from pathlib import Path
from playwright.async_api import async_playwright, Browser, BrowserContext, Page, Playwright
import random
import logging

from app.modules.accounts.platforms.instagram.proxy_config import (
    ProxyConfig, ProxyResult, layered_proxy_fallback, get_proxy_url
)

logger = logging.getLogger(__name__)

STEALTH_SCRIPT = """
    Object.defineProperty(navigator, 'webdriver', { get: () => undefined });
    Object.defineProperty(navigator, 'languages', { get: () => ['pt-BR', 'en-US', 'en'] });
    Object.defineProperty(navigator, 'plugins', { get: () => [
        { name: 'Chrome PDF Plugin', filename: 'internal-pdf-viewer', description: '' },
        { name: 'Chrome PDF Viewer', filename: 'mhjfbmdgcfjbbpaeojofohoefgiehjai', description: '' },
        { name: 'Native Client', filename: 'internal-nacl-plugin', description: '' },
    ]});
    const originalQuery = window.navigator.permissions.query;
    window.navigator.permissions.query = (parameters) => (
        parameters.name === 'notifications' ?
            Promise.resolve({ state: Notification.permission }) :
            originalQuery(parameters)
    );
    Object.defineProperty(navigator, 'hardwareConcurrency', { get: () => 8 });
    Object.defineProperty(navigator, 'deviceMemory', { get: () => 8 });
    Object.defineProperty(navigator, 'platform', { get: () => 'Win32' });
    delete window.cdc_adoQpoasnfa76pfcZLmcfl_Array;
    delete window.cdc_adoQpoasnfa76pfcZLmcfl_Promise;
    delete window.cdc_adoQpoasnfa76pfcZLmcfl_Symbol;
"""


class AntiDetectionContext:
    def __init__(self, config: dict):
        self.config = config
        self.user_agents = config.get("user_agents", [])

    def get_fingerprint(self) -> str:
        return f"{random.randint(1000, 9999)}-{datetime.now().timestamp()}"

    async def random_move(self, page: Page, x: int, y: int):
        dest_x = x + random.randint(-50, 50)
        dest_y = y + random.randint(-50, 50)
        await page.mouse.move(dest_x, dest_y)


class BrowserManager:
    def __init__(self, headless: bool = True, anti_detect: bool = True):
        self.headless = headless
        self.anti_detect = anti_detect
        self.playwright: Optional[Playwright] = None
        self._fingerprint_cache: Dict[str, str] = {}
        self.anti_detect_ctx = AntiDetectionContext({}) if anti_detect else None
        self.proxy_result: Optional[ProxyResult] = None

    async def start(self):
        self.playwright = await async_playwright().start()
        logger.info("Browser playwright started")

    async def stop(self):
        if self.playwright:
            await self.playwright.stop()
            logger.info("Browser playwright stopped")

    def get_fingerprint(self, account_id: str) -> str:
        if account_id not in self._fingerprint_cache:
            self._fingerprint_cache[account_id] = self.anti_detect_ctx.get_fingerprint() if self.anti_detect_ctx else ""
        return self._fingerprint_cache[account_id]

    async def create_context(
        self,
        account_id: str,
        proxy_host: Optional[str] = None,
        proxy_port: Optional[int] = None,
        proxy_username: Optional[str] = None,
        proxy_password: Optional[str] = None,
        viewport_size: Dict = None
    ) -> BrowserContext:
        if not self.playwright:
            await self.start()

        # Run layered proxy fallback
        proxy_config = None
        if proxy_host and proxy_port:
            proxy_config = ProxyConfig(
                host=proxy_host,
                port=proxy_port,
                username=proxy_username or "",
                password=proxy_password or "",
            )
        
        self.proxy_result = layered_proxy_fallback(proxy_config)
        logger.info(f"Proxy result: method={self.proxy_result.method}, using_proxy={self.proxy_result.using_proxy}, ip={self.proxy_result.ip}")

        context_options = {
            "viewport": viewport_size or {"width": 1280, "height": 720},
            "ignore_https_errors": True,
        }

        if self.anti_detect:
            context_options["user_agent"] = self._generate_user_agent()
            
            # Sync locale/timezone with proxy geolocation
            if self.proxy_result.using_proxy and "brd" in (proxy_host or ""):
                context_options["locale"] = "pt-BR"
                context_options["timezone_id"] = "America/Sao_Paulo"
            else:
                context_options["locale"] = "en-US"
                context_options["timezone_id"] = "America/New_York"

            # Session persistence per persona
            session_dir = Path("./data/sessions")
            session_dir.mkdir(parents=True, exist_ok=True)
            session_file = session_dir / f"{account_id}.json"
            if session_file.exists():
                context_options["storage_state"] = str(session_file)
                logger.info(f"Loaded session state for {account_id}")

            fingerprint = self.get_fingerprint(account_id)
            logger.debug(f"Context: fingerprint={fingerprint}, locale={context_options['locale']}, tz={context_options['timezone_id']}")

        launch_args = [
            "--disable-blink-features=AutomationControlled",
            "--disable-dev-shm-usage",
            "--no-sandbox"
        ] if self.headless else []

        launch_kwargs = {
            "headless": self.headless,
            "args": launch_args,
        }

        if self.anti_detect:
            launch_kwargs["ignore_default_args"] = ["--enable-automation"]

        # Only use native proxy if Layer A succeeded
        if self.proxy_result.method == "native" and proxy_host and proxy_port:
            proxy_server = f"http://{proxy_host}:{proxy_port}"
            launch_kwargs["proxy"] = {
                "server": proxy_server,
                "username": proxy_username or "",
                "password": proxy_password or "",
            }
            launch_kwargs["slow_mo"] = 100
            logger.info(f"Browser launch with native proxy {proxy_host}:{proxy_port}")

        browser = await self.playwright.chromium.launch(**launch_kwargs)
        
        context = await browser.new_context(**context_options)
        
        if self.anti_detect:
            try:
                await context.add_init_script(STEALTH_SCRIPT)
                logger.debug("Stealth scripts injected")
            except Exception as e:
                logger.warning(f"Failed to inject stealth scripts: {e}")
        
        return context

    def _generate_user_agent(self) -> str:
        user_agents = [
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36",
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/130.0.0.0 Safari/537.36",
            "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/130.0.0.0 Safari/537.36",
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36 Edg/120.0.0.0",
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/130.0.0.0 Safari/537.36 Edg/130.0.0.0",
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:121.0) Gecko/20100101 Firefox/121.0",
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:130.0) Gecko/20100101 Firefox/130.0",
            "Mozilla/5.0 (Macintosh; Intel Mac OS X 10.15; rv:121.0) Gecko/20100101 Firefox/121.0",
            "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.1 Safari/605.1.15",
            "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.2 Safari/605.1.15",
            "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/118.0.0.0 Safari/537.36",
            "Mozilla/5.0 (iPhone; CPU iPhone OS 17_2 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.2 Mobile/15E148 Safari/604.1",
            "Mozilla/5.0 (Linux; Android 14; SM-S918B) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.6099.43 Mobile Safari/537.36",
        ]
        return random.choice(user_agents)

    async def close_context(self, context: BrowserContext, account_id: Optional[str] = None):
        """Fechar contexto e salvar session state"""
        if account_id and self.anti_detect:
            try:
                session_dir = Path("./data/sessions")
                session_dir.mkdir(parents=True, exist_ok=True)
                session_file = session_dir / f"{account_id}.json"
                await context.storage_state(path=str(session_file))
                logger.info(f"Saved session state for {account_id}")
            except Exception as e:
                logger.warning(f"Failed to save session state: {e}")
        await context.close()

    async def close_all(self):
        if self.playwright:
            await self.playwright.stop()
            self.playwright = None


browser_manager = None


def init_browser_manager(headless: bool = True, anti_detect: bool = True):
    global browser_manager
    browser_manager = BrowserManager(headless=headless, anti_detect=anti_detect)
    logger.info("Browser manager initialized")


def get_browser_manager() -> BrowserManager:
    if browser_manager is None:
        raise RuntimeError("Browser manager not initialized. Call init_browser_manager() first.")
    return browser_manager
