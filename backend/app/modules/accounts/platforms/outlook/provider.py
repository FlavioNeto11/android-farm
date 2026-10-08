from typing import Optional, Dict
import logging
from datetime import datetime

from app.modules.accounts.domain.account import PlatformProvider, PersonaData, AccountResult
from app.modules.accounts.platforms.outlook.signup_flows import OutlookSignup
from app.modules.browsers.domain.browser_profile import get_browser_manager
from app.security.secret_store import get_secret_store

logger = logging.getLogger(__name__)


class OutlookProvider(PlatformProvider):
    """Provedor de conta Outlook/Hotmail"""

    def __init__(self, config: Dict):
        self.config = config
        self.signup = OutlookSignup()

    def get_platform_name(self) -> str:
        return "outlook"

    def get_signup_url(self) -> str:
        return self.config.get("platform_outlook_signup_url", "https://signup.live.com")

    def get_config(self) -> Dict:
        return {
            "signup_url": self.get_signup_url(),
            "timeout": self.config.get("platform_outlook_timeout", 60),
            "account_age_days": self.config.get("platform_outlook_account_age_days", 365),
        }

    async def create_account(
        self,
        persona_data: PersonaData,
        proxy_host: Optional[str] = None,
        proxy_port: Optional[int] = None,
        proxy_username: Optional[str] = None,
        proxy_password: Optional[str] = None,
        timeout: int = 60
    ) -> AccountResult:
        """Criar conta no Outlook"""
        browser_manager = get_browser_manager()

        try:
            context = await browser_manager.create_context(
                account_id=persona_data.profile_id,
                proxy_host=proxy_host,
                proxy_port=proxy_port,
                proxy_username=proxy_username,
                proxy_password=proxy_password,
                viewport_size={"width": 1280, "height": 720}
            )

            page = await context.new_page()

            try:
                result = await self.signup.sign_up(
                    page,
                    persona_data,
                    timeout=timeout
                )

                handle = result["handle"]
                password = result.get("password", "")

                secret_store = get_secret_store()
                secret_ref = secret_store.encrypt(password) if password else None

                return AccountResult(
                    success=True,
                    handle=handle,
                    login_identifier=handle,
                    password=password,
                    credential_ref=secret_ref,
                    verification_needed=not result.get("verified", True)
                )

            finally:
                await page.close()
                await context.close()

        except Exception as e:
            logger.error(f"Failed to create Outlook account: {e}")
            return AccountResult(
                success=False,
                error_message=str(e)
            )


outlook_provider = OutlookProvider({})
