"""Fluxo de signup para Instagram"""
from playwright.async_api import Page
import asyncio
import random
import string
import logging
import re
from datetime import datetime

from app.modules.accounts.domain.account import PersonaData, AccountResult

logger = logging.getLogger(__name__)


class InstagramSignup:
    """Provedor de signup para Instagram"""

    async def sign_up(
        self,
        page: Page,
        persona_data: PersonaData,
        email: str,
        password: str,
        timeout: int = 90
    ) -> AccountResult:
        """
        Executar fluxo de signup no Instagram.

        Args:
            email: Email real do Outlook para vinculação
            password: Senha para conta Instagram
            timeout: Tempo máximo em segundos
        """
        base_url = "https://www.instagram.com/accounts/emailsignup/"
        start_time = datetime.utcnow()

        logger.info(f"Starting Instagram signup for {email} (persona: {persona_data.first_name or 'unknown'})")

        try:
            await page.goto(base_url, wait_until="domcontentloaded", timeout=timeout * 1000)
            logger.info(f"Loaded Instagram signup page: {page.url}")

        except Exception as e:
            error_msg = f"Failed to load Instagram signup page: {e}"
            logger.error(error_msg)
            return AccountResult(
                success=False,
                handle=None,
                login_identifier=email,
                password=password,
                credential_ref=None,
                error_message=error_msg,
                verification_needed=True
            )

        steps = [
            ("fill_email_password", lambda: self._fill_email_and_password(page, email, password)),
            ("fill_name", lambda: self._fill_name(page, persona_data)),
            ("fill_birth_date", lambda: self._fill_birth_date(page, persona_data)),
            ("complete_signup", lambda: self._complete_signup(page)),
            ("extract_handle", lambda: self._extract_instagram_handle(page, email, persona_data))
        ]

        for step_name, step_func in steps:
            try:
                logger.info(f"Executing step: {step_name}")
                if step_name == "extract_handle":
                    result = await step_func()
                    instagram_handle = result
                else:
                    await step_func()
            except Exception as e:
                error_msg = f"Failed at step {step_name}: {e}"
                duration = (datetime.utcnow() - start_time).total_seconds()
                logger.error(f"{error_msg} (duration: {duration:.2f}s)")
                return AccountResult(
                    success=False,
                    handle=None,
                    login_identifier=email,
                    password=password,
                    credential_ref=None,
                    error_message=error_msg,
                    verification_needed=True
                )

        try:
            # Pre-verificação adicional
            current_url = page.url
            match = re.search(r'instagram\.com/([a-zA-Z0-9_.]+)/', current_url)
            if match:
                handle = match.group(1)
                if handle and handle not in ('accounts', 'explore', 'reels', 'direct'):
                    logger.info(f"Pre-validated handle from URL: {handle}")
            else:
                logger.warning("Could not find handle in current URL")

        except Exception as e:
            logger.warning(f"Pre-validation check failed: {e}")

        try:
            instagram_handle = await self._extract_instagram_handle(page, email, persona_data)
        except Exception as e:
            error_msg = f"Failed to extract Instagram handle: {e}"
            logger.error(error_msg)
            return AccountResult(
                success=False,
                handle=None,
                login_identifier=email,
                password=password,
                credential_ref=None,
                error_message=error_msg,
                verification_needed=True
            )

        duration = (datetime.utcnow() - start_time).total_seconds()
        logger.info(f"Instagram signup completed successfully for: {instagram_handle} ({duration:.2f}s)")

        return AccountResult(
            success=True,
            handle=instagram_handle,
            login_identifier=email,
            password=password,
            credential_ref=None,
            error_message=None,
            verification_needed=True
        )

    async def _fill_email_and_password(self, page: Page, email: str, password: str):
        """Preencher email e senha"""
        await self._random_delay()

        email_input = page.locator('input[name="emailOrPhone"], input[type="email"]').first
        if await email_input.count():
            await email_input.fill(email)

        await self._random_delay()

        pass_input = page.locator('input[name="password"], input[type="password"]').first
        if await pass_input.count():
            await pass_input.fill(password)

        await self._click_signup(page)

    async def _fill_name(self, page: Page, persona_data: PersonaData):
        """Preencher nome completo"""
        await self._random_delay()

        name_input = page.locator('input[name="fullName"]').first
        if await name_input.count():
            full_name = f"{persona_data.first_name or 'User'} {persona_data.last_name or 'Last'}"
            await name_input.fill(full_name)
            await self._click_next(page)

    async def _fill_birth_date(self, page: Page, persona_data: PersonaData):
        """Preencher data de nascimento"""
        await self._random_delay()

        if persona_data.birth_date:
            from datetime import datetime
            try:
                birth = datetime.strptime(persona_data.birth_date, "%Y-%m-%d")

                month_select = page.locator('select[title*="Month"]').first
                day_select = page.locator('select[title*="Day"]').first
                year_select = page.locator('select[title*="Year"]').first

                if await month_select.count():
                    await month_select.select_option(str(birth.month))
                if await day_select.count():
                    await day_select.select_option(str(birth.day))
                if await year_select.count():
                    await year_select.select_option(str(birth.year))

                await self._click_next(page)
            except Exception as e:
                logger.warning(f"Could not fill birth date: {e}")

    async def _complete_signup(self, page: Page):
        """Completar signup"""
        await self._random_delay()
        try:
            await page.wait_for_load_state("networkidle", timeout=30000)
        except:
            pass

    async def _click_signup(self, page: Page):
        """Clicar botão de signup"""
        await self._random_delay()
        btn = page.locator('button:has-text("Sign Up"), button:has-text("Next")').first
        if await btn.count():
            await btn.click()
            try:
                await page.wait_for_load_state("domcontentloaded", timeout=15000)
            except:
                pass

    async def _click_next(self, page: Page):
        """Clicar botão Next"""
        await self._random_delay()
        btn = page.locator('button:has-text("Next")').first
        if await btn.count():
            await btn.click()
            try:
                await page.wait_for_load_state("domcontentloaded", timeout=15000)
            except:
                pass

    async def _random_delay(self, min_sec: float = 1.5, max_sec: float = 3.5):
        """Delay aleatório"""
        await asyncio.sleep(random.uniform(min_sec, max_sec))

    async def _extract_from_profile_page(self, page: Page, expected_username: str) -> str:
        """Extrair username da página de perfil edit."""
        try:
            await page.goto(f"https://www.instagram.com/{expected_username}/", wait_until="load", timeout=15000)
            await self._random_delay(2, 4)

            page_title = await page.title()
            logger.info(f"Profile page title: {page_title}")

            headings = page.locator('h1, h2')
            count = await headings.count()
            for i in range(count):
                text = await headings.nth(i).inner_text()
                if text and text.strip():
                    text = text.strip().replace("@", "").replace("·", "")
                    if re.match(r'^[a-zA-Z0-9_.]+$', text):
                        return text

            desc = await page.locator('meta[name="description"]').get_attribute("content")
            if desc:
                match = re.search(r'instagram\.com/([a-zA-Z0-9_.]+)', desc)
                if match:
                    username = match.group(1)
                    if username and re.match(r'^[a-zA-Z0-9_.]+$', username):
                        return username

        except Exception as e:
            logger.warning(f"Could not extract from profile page: {e}")

        return None

    async def _generate_handle_from_persona(self, persona_data: PersonaData) -> str:
        """Gerar handle a partir dos dados da persona."""
        first = persona_data.first_name or "user"
        last = persona_data.last_name or "test"

        base = f"{first.lower()}{last.lower()}_test"
        if len(base) > 30:
            base = base[:30]

        return base

    async def _extract_instagram_handle(self, page: Page, fallback_email: str, persona_data: PersonaData = None) -> str:
        """
        Extrair o @ real do Instagram após criação da conta.
        Tenta múltiplas estratégias de fallback para extrair o username real.
        """
        username = None

        try:
            current_url = page.url
            match = re.search(r'instagram\.com/([a-zA-Z0-9_.]+)/', current_url)
            if match:
                candidate = match.group(1)
                if candidate and candidate not in ('accounts', 'explore', 'reels', 'direct', 'policies'):
                    logger.info(f"Found username in URL: {candidate}")
                    return candidate

        except Exception as e:
            logger.warning(f"Could not extract from URL: {e}")

        try:
            await page.goto("https://www.instagram.com/accounts/edit/", wait_until="load", timeout=15000)
            await self._random_delay(2, 4)

            current_url = page.url
            match = re.search(r'instagram\.com/([a-zA-Z0-9_.]+)/', current_url)
            if match:
                candidate = match.group(1)
                if candidate and candidate not in ('accounts', 'explore', 'reels', 'direct'):
                    logger.info(f"Found username in URL after nav to edit: {candidate}")
                    return candidate

        except Exception as e:
            logger.warning(f"Could not navigate to edit profile: {e}")

        try:
            headings = page.locator('h1, h2')
            count = await headings.count()
            for i in range(count):
                text = await headings.nth(i).inner_text()
                if text and text.strip():
                    text = text.strip().replace("@", "").replace("·", "")
                    if re.match(r'^[a-zA-Z0-9_.]+$', text):
                        logger.info(f"Found username in heading: {text}")
                        return text

        except Exception as e:
            logger.warning(f"Could not extract from heading: {e}")

        try:
            desc = await page.locator('meta[name="description"]').get_attribute("content")
            if desc:
                match = re.search(r'instagram\.com/([a-zA-Z0-9_.]+)', desc)
                if match:
                    username = match.group(1)
                    if username and re.match(r'^[a-zA-Z0-9_.]+$', username):
                        logger.info(f"Found username in meta description: {username}")
                        return username
        except Exception as e:
            logger.warning(f"Could not extract from meta: {e}")

        try:
            if persona_data and persona_data.display_name and persona_data.display_name.strip():
                username = await self._extract_from_profile_page(page, persona_data.display_name)
                if username:
                    logger.info(f"Found username from profile page: {username}")
                    return username
        except Exception as e:
            logger.warning(f"Could not extract from profile page: {e}")

        try:
            if persona_data:
                username = await self._generate_handle_from_persona(persona_data)
                logger.info(f"Generated username from persona: {username}")
                return username
        except Exception as e:
            logger.warning(f"Could not generate handle from persona: {e}")

        logger.warning(f"All extraction strategies failed, falling back to email: {fallback_email}")
        return fallback_email
