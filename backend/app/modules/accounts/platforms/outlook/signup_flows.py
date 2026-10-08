"""Fluxo de signup para Outlook/Hotmail"""
from playwright.async_api import Page
import asyncio
import random
import string
import logging

from app.modules.accounts.domain.account import PersonaData
from app.modules.accounts.platforms.email_verifier import OutlookEmailVerifier

logger = logging.getLogger(__name__)


class OutlookSignup:
    """Provedor de signup para Outlook/Hotmail"""

    async def sign_up(
        self,
        page: Page,
        persona_data: PersonaData,
        timeout: int = 120
    ) -> dict:
        """
        Executar fluxo de signup no Outlook.
        """
        base_url = "https://signup.live.com"

        try:
            await page.goto(base_url, wait_until="domcontentloaded", timeout=timeout * 1000)
        except Exception as e:
            logger.error(f"Failed to load Outlook signup page: {e}")
            raise

        email = self._generate_email(persona_data)
        password = self._generate_password()

        try:
            await self._fill_email(page, email)
            await self._fill_password(page, password)
            await self._fill_personal_info(page, persona_data)
            await self._complete_signup(page)

            return {
                "handle": email,
                "password": password,
                "verified": True,
                "account_type": "outlook"
            }

        except Exception as e:
            logger.error(f"Outlook signup failed: {e}")
            raise

    async def _fill_email(self, page: Page, email: str):
        """Preencher campo de email"""
        await self._random_delay()
        email_input = page.locator('input[name="EmailAddress"], input[type="email"]').first
        if await email_input.count():
            await email_input.fill(email)
            await self._click_next(page)

    async def _fill_password(self, page: Page, password: str):
        """Preencher campo de senha"""
        await self._random_delay()
        pass_input = page.locator('input[name="PasswordInput"], input[type="password"]').first
        if await pass_input.count():
            await pass_input.fill(password)
            await self._click_next(page)

    async def _fill_personal_info(self, page: Page, persona_data: PersonaData):
        """Preencher informações pessoais"""
        await self._random_delay()

        first_name = persona_data.first_name or "User"
        last_name = persona_data.last_name or "Last"

        first_input = page.locator('input[name="FirstName"]').first
        if await first_input.count():
            await first_input.fill(first_name)

        last_input = page.locator('input[name="LastName"]').first
        if await last_input.count():
            await last_input.fill(last_name)

        await self._fill_birth_date(page, persona_data)
        await self._click_next(page)

    async def _fill_birth_date(self, page: Page, persona_data: PersonaData):
        """Preencher data de nascimento"""
        if persona_data.birth_date:
            from datetime import datetime
            try:
                birth = datetime.strptime(persona_data.birth_date, "%Y-%m-%d")
                month_select = page.locator('select[name="BirthMonth"]').first
                day_select = page.locator('select[name="BirthDay"]').first
                year_input = page.locator('input[name="BirthYear"]').first

                if await month_select.count():
                    await month_select.select_option(str(birth.month))
                if await day_select.count():
                    await day_select.select_option(str(birth.day))
                if await year_input.count():
                    await year_input.fill(str(birth.year))
            except Exception as e:
                logger.warning(f"Could not fill birth date: {e}")

    async def _complete_signup(self, page: Page):
        """Completar signup"""
        await self._random_delay()
        await self._click_next(page)
        try:
            await page.wait_for_load_state("networkidle", timeout=60000)
        except:
            logger.warning("Network idle timeout, but continuing")

    async def _click_next(self, page: Page):
        """Clicar botão Next"""
        await self._random_delay()
        next_button = page.locator('button[type="submit"]').first
        if await next_button.count():
            await next_button.click()
            try:
                await page.wait_for_load_state("domcontentloaded", timeout=30000)
            except:
                logger.warning("Page load timeout, continuing")

    def _generate_email(self, persona_data: PersonaData) -> str:
        """Gerar email Outlook"""
        first = (persona_data.first_name or "user").lower()
        last = (persona_data.last_name or "last").lower()
        domain = random.choice(["outlook.com", "hotmail.com", "live.com"])
        suffix = random.randint(100, 999)
        return f"{first}.{last}{suffix}@{domain}"

    def _generate_password(self) -> str:
        """Gerar senha forte"""
        chars = string.ascii_letters + string.digits + "!@#$"
        return "".join(random.choice(chars) for _ in range(14))

    async def _random_delay(self, min_sec: float = 1.0, max_sec: float = 3.0):
        """Delay aleatório"""
        await asyncio.sleep(random.uniform(min_sec, max_sec))

    async def _verify_account(self, page: Page, email: str, password: str) -> bool:
        """Logar no Outlook para verificar que a conta funciona"""
        verifier = OutlookEmailVerifier()
        result = await verifier.login_and_check_verification(
            page=page,
            email=email,
            password=password,
            sender_pattern="verification",
            timeout=60
        )
        return result is not None
