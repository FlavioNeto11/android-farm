"""Módulo de verificação de email Outlook"""
from playwright.async_api import Page, Locator
import asyncio
import re
import random
import logging
from typing import Optional

logger = logging.getLogger(__name__)


class OutlookEmailVerifier:
    """Verificador de email Outlook para captura de códigos de verificação"""

    async def login_and_check_verification(
        self,
        page: Page,
        email: str,
        password: str,
        sender_pattern: str = "instagram",
        timeout: int = 60
    ) -> Optional[str]:
        """
        Logar em conta Outlook e buscar código de verificação.

        Args:
            page: Página Playwright
            email: Endereço de email Outlook
            password: Senha do email
            sender_pattern: Padrão do remetente (ex: "instagram", "verification")
            timeout: Tempo máximo para esperar emails (segundos)

        Returns:
            Código de verificação encontrado ou None
        """
        try:
            await self._login_to_outlook(page, email, password)
            verification_code = await self._find_verification_email(page, sender_pattern, timeout)
            return verification_code
        except Exception as e:
            logger.error(f"Outlook email verification failed: {e}")
            return None

    async def _login_to_outlook(self, page: Page, email: str, password: str):
        """Fazer login na conta Outlook"""
        await self._random_delay(1.0, 2.0)
        await page.goto("https://outlook.live.com/mail/0/", timeout=30000)
        await self._wait_for_login_page(page, timeout=20000)

        await self._fill_login_form(page, email, password)
        await self._wait_for_dashboard(page, timeout=20000)

    async def _fill_login_form(self, page: Page, email: str, password: str):
        """Preencher formulário de login"""
        email_input = page.locator('input[name="username"], input[type="email"]').first
        if await email_input.count():
            await email_input.fill(email)

        pass_input = page.locator('input[name="password"], input[type="password"]').first
        if await pass_input.count():
            await pass_input.fill(password)

        await self._click_login_button(page)

        await page.wait_for_load_state("networkidle", timeout=15000)

    async def _click_login_button(self, page: Page):
        """Clicar botão de login"""
        login_button = page.locator('button:has-text("Sign in"), input[type="submit"]').first
        if await login_button.count():
            await login_button.click()

        await asyncio.sleep(5)

    async def _wait_for_login_page(self, page: Page, timeout: int = 10000):
        """Aguardar página de login estar carregada"""
        try:
            await page.wait_for_selector('input[name="username"], input[type="email"], input[name="password"]', timeout=timeout)
        except:
            pass

    async def _wait_for_dashboard(self, page: Page, timeout: int = 20000):
        """Aguardar dashboard Outlook aparecer"""
        try:
            await page.wait_for_selector('div[title="Inbox"], .ms-CommandBar-primaryCommand', timeout=timeout)
            logger.info("Successfully login to Outlook")
        except:
            logger.warning("Could not verify dashboard, but login might be successful")

    async def _find_verification_email(self, page: Page, sender_pattern: str, timeout: int) -> Optional[str]:
        """Buscar email de verificação e extrair código"""
        await self._random_delay(2.0, 3.0)

        try:
            inbox_button = page.locator('div[title="Inbox"], a[title*="Inbox"]').first
            if await inbox_button.count():
                await inbox_button.click()
                await asyncio.sleep(3)

            await self._search_for_verification_email(page, sender_pattern, timeout)
        except Exception as e:
            logger.error(f"Navigation to Inbox failed: {e}")

        return await self._extract_verification_code(page)

    async def _search_for_verification_email(self, page: Page, sender_pattern: str, timeout: int):
        """Implementação básica - simples navegação para inbox"""
        logger.info(f"Checking Inbox for verification emails from sender: {sender_pattern}")

        inbox_tab = page.locator('a[data-automation-id="Inbox"]').first
        if await inbox_tab.count():
            await inbox_tab.click()
        else:
            await page.goto("https://outlook.live.com/mail/0/inbox/", timeout=20000)

        try:
            await page.wait_for_selector('div.mail-item, tr[role="row"]', timeout=5000)
        except:
            pass

    async def _extract_verification_code(self, page: Page) -> Optional[str]:
        """Extrair código de verificação de email (padrão 6 dígitos)"""
        try:
            inbox_item = page.locator('div.mail-item, tr[role="row"]').first
            if await inbox_item.count():
                await inbox_item.click()

                await self._random_delay(1.0, 2.0)

                email_content = page.locator('div[role="textbox"], .js_email_content, .MailMessage-Read').first

                if await email_content.count():
                    text = await email_content.inner_text()

                    pattern = r'\b(\d{6})\b'
                    matches = re.findall(pattern, text)

                    if matches:
                        code = matches[0]
                        logger.info(f"Found verification code: {code}")
                        return code

            logger.warning("No code found in email content")
            return None
        except Exception as e:
            logger.error(f"Could not extract verification code: {e}")
            return None

    async def _random_delay(self, min_sec: float = 1.0, max_sec: float = 2.0):
        """Delay aleatório"""
        await asyncio.sleep(random.uniform(min_sec, max_sec))


outlook_email_verifier = OutlookEmailVerifier()
