import asyncio
import os
from typing import Optional, Dict, List
from datetime import datetime
from playwright.async_api import async_playwright, Browser, BrowserContext, Page, Playwright
import random
import logging

logger = logging.getLogger(__name__)

STEALTH_SCRIPT = """
    // Override navigator.webdriver
    Object.defineProperty(navigator, 'webdriver', { get: () => undefined });
    // Override languages
    Object.defineProperty(navigator, 'languages', { get: () => ['pt-BR', 'en-US', 'en'] });
    // Override plugins
    Object.defineProperty(navigator, 'plugins', { get: () => [
        { name: 'Chrome PDF Plugin', filename: 'internal-pdf-viewer', description: '' },
        { name: 'Chrome PDF Viewer', filename: 'mhjfbmdgcfjbbpaeojofohoefgiehjai', description: '' },
        { name: 'Native Client', filename: 'internal-nacl-plugin', description: '' },
    ]});
    // Override permissions
    const originalQuery = window.navigator.permissions.query;
    window.navigator.permissions.query = (parameters) => (
        parameters.name === 'notifications' ?
            Promise.resolve({ state: Notification.permission }) :
            originalQuery(parameters)
    );
    // Override hardwareConcurrency
    Object.defineProperty(navigator, 'hardwareConcurrency', { get: () => 8 });
    // Override deviceMemory
    Object.defineProperty(navigator, 'deviceMemory', { get: () => 8 });
    // Override platform
    Object.defineProperty(navigator, 'platform', { get: () => 'Win32' });
    // Canvas fingerprint noise
    const originalToDataURL = HTMLCanvasElement.prototype.toDataURL;
    HTMLCanvasElement.prototype.toDataURL = function(type) {
        const result = originalToDataURL.apply(this, arguments);
        return result;
    };
    // Remove cdc_ properties (Playwright signature)
    delete window.cdc_adoQpoasnfa76pfcZLmcfl_Array;
    delete window.cdc_adoQpoasnfa76pfcZLmcfl_Promise;
    delete window.cdc_adoQpoasnfa76pfcZLmcfl_Symbol;
"""


class AntiDetectionContext:
    """Contexto com measures anti-detect"""

    def __init__(self, config: dict):
        self.config = config
        self.user_agents = config.get("user_agents", [])

    def get_fingerprint(self) -> str:
        """Gerar identidade do navegador"""
        return f"{random.randint(1000, 9999)}-{datetime.now().timestamp()}"

    def random_delay(self, min_seconds: float = 1.0, max_seconds: float = 3.0):
        """Delay aleatório para simular comportamento humano"""
        delay = random.uniform(min_seconds, max_seconds)
        asyncio.sleep(delay)

    async def random_move(self, page: Page, x: int, y: int):
        """Simular movimento de mouse"""
        dest_x = x + random.randint(-50, 50)
        dest_y = y + random.randint(-50, 50)
        await page.mouse.move(dest_x, dest_y)


class BrowserManager:
    """Gerenciador de contexto de navegador"""

    def __init__(self, headless: bool = True, anti_detect: bool = True):
        self.headless = headless
        self.anti_detect = anti_detect
        self.playwright: Optional[Playwright] = None
        self._fingerprint_cache: Dict[str, str] = {}
        self.anti_detect_ctx = AntiDetectionContext({}) if anti_detect else None

    async def start(self):
        """Inicializar Playwright"""
        self.playwright = await async_playwright().start()
        logger.info("Browser playwright started")

    async def stop(self):
        """Parar Playwright"""
        if self.playwright:
            await self.playwright.stop()
            logger.info("Browser playwright stopped")

    def get_fingerprint(self, account_id: str) -> str:
        """Obter ou gerar fingerprint para conta"""
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

        context_options = {
            "viewport": viewport_size or {"width": 1280, "height": 720},
            "ignore_https_errors": True,
        }

        if self.anti_detect:
            context_options["user_agent"] = self._generate_user_agent()
            
            # Sync locale/timezone with proxy geolocation
            if proxy_host and "brd" in proxy_host:
                context_options["locale"] = "pt-BR"
                context_options["timezone_id"] = "America/Sao_Paulo"
            else:
                context_options["locale"] = "en-US"
                context_options["timezone_id"] = "America/New_York"

            fingerprint = self.get_fingerprint(account_id)
            state_file = f"./data/fingerprint_{fingerprint}.json"
            if self.headless and os.path.exists(state_file):
                context_options["storage_state"] = state_file

            logger.debug(f"Created context with fingerprint {fingerprint}, locale={context_options['locale']}, tz={context_options['timezone_id']}")

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

        if proxy_host and proxy_port:
            proxy_server = f"http://{proxy_host}:{proxy_port}"
            launch_kwargs["proxy"] = {
                "server": proxy_server,
                "username": proxy_username or "",
                "password": proxy_password or "",
            }
            launch_kwargs["slow_mo"] = 100
            logger.info(f"Browser launch configured with proxy {proxy_host}:{proxy_port}")
            logger.debug(f"Proxy username length: {len(proxy_username or '')}")

        browser = await self.playwright.chromium.launch(**launch_kwargs)
        
        if proxy_host and proxy_port:
            try:
                test_context = await browser.new_context()
                test_page = await test_context.new_page()
                await test_page.goto("https://geo.brdtest.com/welcome.txt", timeout=15000)
                await test_page.close()
                await test_context.close()
                logger.info("Proxy test successful at browser launch (HTTP check)")
                
                test_context2 = await browser.new_context()
                test_page2 = await test_context2.new_page()
                await test_page2.goto("https://www.instagram.com/", timeout=15000)
                await test_page2.close()
                await test_context2.close()
                logger.info("Proxy test successful for Instagram (HTTPS check)")
            except Exception as e:
                logger.warning(f"Proxy test failed: {e}")
                logger.warning("Closing browser and reopening without proxy")
                await browser.close()
                
                launch_kwargs.pop("proxy", None)
                launch_kwargs.pop("slow_mo", None)
                browser = await self.playwright.chromium.launch(**launch_kwargs)
                logger.info("Browser launched without proxy (fallback)")
        
        context = await browser.new_context(**context_options)
        
        # Inject stealth scripts
        if self.anti_detect:
            try:
                await context.add_init_script(STEALTH_SCRIPT)
                logger.debug("Stealth scripts injected")
            except Exception as e:
                logger.warning(f"Failed to inject stealth scripts: {e}")
        
        return context

    def _generate_user_agent(self) -> str:
        """Gerar User-Agent randomizado com pool expandido"""
        user_agents = [
            # Chrome Windows
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36",
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/130.0.0.0 Safari/537.36",
            # Chrome Mac
            "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/130.0.0.0 Safari/537.36",
            # Edge Windows
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36 Edg/120.0.0.0",
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/130.0.0.0 Safari/537.36 Edg/130.0.0.0",
            # Firefox Windows
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:121.0) Gecko/20100101 Firefox/121.0",
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:130.0) Gecko/20100101 Firefox/130.0",
            # Firefox Mac
            "Mozilla/5.0 (Macintosh; Intel Mac OS X 10.15; rv:121.0) Gecko/20100101 Firefox/121.0",
            # Safari Mac
            "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.1 Safari/605.1.15",
            "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.2 Safari/605.1.15",
            # Linux Chrome
            "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            # Older Chrome
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/118.0.0.0 Safari/537.36",
            # Mobile
            "Mozilla/5.0 (iPhone; CPU iPhone OS 17_2 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.2 Mobile/15E148 Safari/604.1",
            "Mozilla/5.0 (Linux; Android 14; SM-S918B) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.6099.43 Mobile Safari/537.36",
        ]
        return random.choice(user_agents)

    async def close_context(self, context: BrowserContext):
        """Fechar contexto específico"""
        await context.close()

    async def close_all(self):
        """Fechar todos os contextos e launcher"""
        if self.playwright:
            await self.playwright.stop()
            self.playwright = None


# Global browser manager
browser_manager = None


def init_browser_manager(headless: bool = True, anti_detect: bool = True):
    """Inicializar browser manager global"""
    global browser_manager
    browser_manager = BrowserManager(headless=headless, anti_detect=anti_detect)
    logger.info("Browser manager initialized")


def get_browser_manager() -> BrowserManager:
    """Obter browser manager global"""
    if browser_manager is None:
        raise RuntimeError("Browser manager not initialized. Call init_browser_manager() first.")
    return browser_manager
