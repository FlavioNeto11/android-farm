import asyncio
import os
from typing import Optional, Dict, List
from datetime import datetime
from playwright.async_api import async_playwright, Browser, BrowserContext, Page, Playwright
import random
import logging

logger = logging.getLogger(__name__)


class AntiDetectionContext:
    """Contexto com measures anti-detect"""

    def __init__(self, config: dict):
        self.config = config
        self.user_agents = config.get("user_agents", [])

    def get_fingerprint(self) -> str:
        """Gerar identidade do navegador"""
        # Algoritmo para gerar fingerprint único
        return f"{random.randint(1000, 9999)}-{datetime.now().timestamp()}"

    def random_delay(self, min_seconds: float = 1.0, max_seconds: float = 3.0):
        """Delay aleatório para simular comportamento humano"""
        delay = random.uniform(min_seconds, max_seconds)
        asyncio.sleep(delay)

    async def random_move(self, page: Page, x: int, y: int):
        """Simular movimento de mouse"""
        # Gerar ponto aleatório perto do destino
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
        """
        Criar contexto de browser com configurações específicas para conta.

        Args:
            account_id: ID único da conta (para fingerprint)
            proxy_host: Host do proxy obrigatório
            proxy_port: Porta do proxy
            proxy_username: Usuário do proxy
            proxy_password: Senha do proxy
            viewport_size: Tamanho da viewport

        Returns:
            BrowserContext configurado
        """
        if not self.playwright:
            await self.start()

        context_options = {
            "viewport": viewport_size or {"width": 1280, "height": 720},
            "ignore_https_errors": True,
        }

        # Anti-detection options
        if self.anti_detect:
            context_options["user_agent"] = self._generate_user_agent()
            context_options["locale"] = "en-US"
            context_options["timezone_id"] = "America/New_York"

            fingerprint = self.get_fingerprint(account_id)

            # Settings anti-detect extras (moved to launch args)

            # Storage state persistence per account (only if file exists)
            state_file = f"./data/fingerprint_{fingerprint}.json"
            if self.headless and os.path.exists(state_file):
                context_options["storage_state"] = state_file

            logger.debug(f"Created context with fingerprint {fingerprint}")

        # Proxy configuration
        if proxy_host and proxy_port:
            proxy_config = {
                "server": f"http://{proxy_host}:{proxy_port}"
            }

            if proxy_username and proxy_password:
                proxy_config["username"] = proxy_username
                proxy_config["password"] = proxy_password

            context_options["proxy"] = proxy_config

            logger.debug(f"Context configured with proxy {proxy_host}:{proxy_port}")

        # Create context
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

        browser = await self.playwright.chromium.launch(**launch_kwargs)

        context = await browser.new_context(**context_options)
        return context

    def _generate_user_agent(self) -> str:
        """Gerar User-Agent randomizado"""
        user_agents = [
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:121.0) Gecko/20100101 Firefox/121.0",
            "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.1 Safari/605.1.15",
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
