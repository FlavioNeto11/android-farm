"""Fluxo completo de criação de conta: Outlook + Instagram"""
from playwright.async_api import Page, BrowserContext
from typing import Optional, Dict
from app.modules.accounts.domain.account import PersonaData
from app.modules.accounts.platforms.outlook.provider import OutlookProvider
from app.modules.accounts.platforms.instagram.provider import InstagramProvider
from app.modules.accounts.platforms.outlook.signup_flows import OutlookSignup
from app.modules.accounts.platforms.instagram.signup_flows import InstagramSignup
from app.modules.accounts.platforms.instagram.verifier import InstagramAccountVerifier
from app.modules.browsers.domain.browser_profile import get_browser_manager
from app.security.secret_store import SecretStore
import logging
import random
import asyncio

logger = logging.getLogger(__name__)


class FullAccountSignup:
    """Orquestrador para criação completa de conta com Outlook + Instagram"""

    def __init__(self):
        self.outlook_signup = OutlookSignup()
        self.instagram_signup = InstagramSignup()

    async def create_full_account(
        self,
        persona_data: PersonaData,
        proxy_config: Optional[Dict] = None,
        timeout: int = 120
    ) -> Dict[str, any]:
        """
        Criar conta Outlook + Instagram completa.

        Returns:
            {
                "outlook_email": "nome@outlook.com",
                "outlook_password": "senha123",
                "instagram_handle": "email_instagram_usado",
                "instagram_password": "senha456",
                "verified": True/False,
                "outlook_account_id": "uuid",
                "instagram_account_id": "uuid"
            }
        """
        result = {
            "outlook_email": None,
            "outlook_password": None,
            "instagram_handle": None,
            "instagram_password": None,
            "verified": False,
            "outlook_account_id": None,
            "instagram_account_id": None
        }

        try:
            browser_manager = get_browser_manager()

            context = await browser_manager.create_context(
                account_id=persona_data.profile_id,
                proxy_host=proxy_config.get("host") if proxy_config else None,
                proxy_port=proxy_config.get("port") if proxy_config else None,
                proxy_username=proxy_config.get("username") if proxy_config else None,
                proxy_password=proxy_config.get("password") if proxy_config else None,
                viewport_size={"width": 1280, "height": 720}
            )

            first_page = await context.new_page()

            try:
                logger.info(f"Starting full account creation flow for {persona_data.profile_id}")

                outlook_result = await self._create_outlook_account(
                    first_page, persona_data, timeout
                )

                if not outlook_result["success"]:
                    logger.error(f"Failed to create Outlook account")
                    result["verified"] = False
                    return result

                logger.info(f"Outlook account created: {outlook_result['handle']}")

                outlook_email = outlook_result["handle"]
                outlook_password = outlook_result["password"]

                await first_page.close()
                first_page = None

                second_page = await context.new_page()

                try:
                    instagram_result = await self._create_instagram_account(
                        second_page, persona_data, outlook_email, outlook_password, timeout
                    )

                    if instagram_result["success"]:
                        logger.info(f"Instagram account created successfully")
                        result["verified"] = True
                    else:
                        logger.error(f"Failed to create Instagram account")
                        result["verified"] = False

                    result.update({
                        "outlook_email": outlook_email,
                        "outlook_password": outlook_password,
                        "instagram_handle": instagram_result.get("handle"),
                        "instagram_password": instagram_result.get("password"),
                        "verified": result["verified"]
                    })
                finally:
                    if second_page:
                        await second_page.close()

            finally:
                if first_page:
                    await first_page.close()
                await context.close()

        except Exception as e:
            logger.error(f"Full account creation failed: {e}", exc_info=True)
            result["verified"] = False

        return result

    async def _create_outlook_account(
        self,
        page: Page,
        persona_data: PersonaData,
        timeout: int
    ) -> Dict[str, any]:
        """Criar conta Outlook"""
        try:
            result = await self.outlook_signup.sign_up(
                page=page,
                persona_data=persona_data,
                timeout=timeout
            )

            success = result.get("verified", True)

            return {
                "success": success,
                "handle": result["handle"],
                "password": result["password"]
            }

        except Exception as e:
            logger.error(f"Outlook account creation failed: {e}")
            return {
                "success": False,
                "handle": None,
                "password": None
            }

    async def _create_instagram_account(
        self,
        page: Page,
        persona_data: PersonaData,
        outlook_email: str,
        outlook_password: str,
        timeout: int
    ) -> Dict[str, any]:
        """Criar conta Instagram usando email Outlook"""
        verifier = InstagramAccountVerifier()
        max_retries = 2
        retry_delay = 5

        for retry in range(max_retries):
            try:
                logger.info(f"Attempting Instagram account creation (attempt {retry + 1}/{max_retries})")

                result = await self.instagram_signup.sign_up(
                    page=page,
                    persona_data=persona_data,
                    email=outlook_email,
                    password=self._generate_instagram_password(),
                    timeout=timeout
                )

                instagram_handle = result.handle

                if not result.success or instagram_handle is None:
                    error_msg = result.error_message or "Account creation failed or handle extraction returned None"
                    logger.error(f"Instagram account creation failed: {error_msg}")
                    if retry < max_retries - 1:
                        await asyncio.sleep(retry_delay)
                        continue
                    else:
                        return {
                            "success": False,
                            "handle": None,
                            "password": None
                        }

                logger.info(f"Instagram account created with handle: {instagram_handle}")

                # Check if handle looks like a fake/generated handle
                if instagram_handle and ("_test" in instagram_handle.lower() or len(instagram_handle) < 4):
                    logger.warning(f"Handle looks fake/generated: {instagram_handle}")
                    logger.error(f"Instagram account creation appears to have failed - handle is not valid")
                    if retry < max_retries - 1:
                        await asyncio.sleep(retry_delay)
                        retry_delay *= 2
                        continue
                    else:
                        return {
                            "success": False,
                            "handle": None,
                            "password": None
                        }

                if not verifier.verify_accounts:
                    logger.info("Account verification disabled, skipping verification")
                    return {
                        "success": True,
                        "handle": instagram_handle,
                        "password": result.password
                    }

                logger.info(f"Verifying Instagram account: {instagram_handle}")

                verification_result = await verifier.verify_account(instagram_handle, timeout=10)

                if verification_result["verified"]:
                    logger.info(f"Instagram account verification successful: {instagram_handle}")
                    return {
                        "success": True,
                        "handle": instagram_handle,
                        "password": result.password
                    }
                else:
                    verification_error = verification_result.get("error", "Unknown verification error")
                    logger.warning(f"Instagram account verification failed: {verification_error}")
                    logger.error(f"Not marking account as ready due to verification failure")
                    return {
                        "success": False,
                        "handle": None,
                        "password": None
                    }

            except Exception as e:
                logger.error(f"Instagram account creation retry {retry + 1} failed: {e}")

                if retry < max_retries - 1:
                    await asyncio.sleep(retry_delay)
                    retry_delay *= 2
                else:
                    logger.error(f"All Instagram account creation attempts failed: {e}")
                    return {
                        "success": False,
                        "handle": None,
                        "password": None
                    }

        return {
            "success": False,
            "handle": None,
            "password": None
        }

    def _generate_instagram_password(self) -> str:
        """Gerar senha para Instagram"""
        import random
        import string
        chars = string.ascii_letters + string.digits + "!@#$%^&*()"
        return "".join(random.choice(chars) for _ in range(14))


outlook_full_signup = FullAccountSignup()
