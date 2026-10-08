"""Verificador de contas do Instagram"""
import logging
import asyncio
import os
from typing import Optional, Dict

try:
    from app.config import settings
    USE_SETTINGS = True
except:
    USE_SETTINGS = False

try:
    from app.modules.accounts.domain.account import AccountResult
    HAS_ACCOUNT_RESULT = True
except:
    HAS_ACCOUNT_RESULT = False

try:
    from playwright.async_api import Page
    HAS_PLAYWRIGHT = True
except:
    HAS_PLAYWRIGHT = False

logger = logging.getLogger(__name__)

class InstagramAccountVerifier:
    """Verificador da existência de contas Instagram baseado em HTTP"""

    def __init__(self):
        if USE_SETTINGS:
            self.verify_accounts = settings.instagram_verify_accounts
            self.max_retries = settings.instagram_verification_retries
            self.timeout = settings.instagram_verification_timeout
        else:
            self.verify_accounts = True
            self.max_retries = 3
            self.timeout = 10

    async def verify_account(self, handle: str, timeout: int = 10) -> Dict:
        """
        Verificar se uma conta do Instagram existe.

        Args:
            handle: Username da conta a verificar
            timeout: Tempo máximo por verificação em segundos

        Returns:
            Dict com status de verificação e informações
        """
        if not self.verify_accounts:
            return {
                "success": True,
                "verified": False,
                "verified_at": None,
                "error": "Account verification disabled"
            }

        try:
            import aiohttp

            url = f"https://www.instagram.com/{handle}/"
            headers = {
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
            }

            attempts = 0
            last_error = None

            while attempts < self.max_retries:
                attempts += 1

                try:
                    async with aiohttp.ClientSession(timeout=aiohttp.ClientTimeout(total=timeout)) as session:
                        async with session.get(url, headers=headers) as response:
                            content = await response.text()
                            status = response.status

                            if status == 200:
                                logger.info(f"Received HTTP 200 for {handle}")

                                logger.debug(f"Content snippet: {content[:300]}")

                                unavailable_keywords = [
                                    'página não encontrada',
                                    'sorry, this page isn', 'available',
                                    'profile isn', 'available',
                                    'sorry, this page isnt available',
                                    'instagram does not exist',
                                    "page isn't available",
                                    'this page is unavailable',
                                    "sorry this page isn't available"
                                ]

                                is_unavailable = content and any(keyword in content.lower() for keyword in unavailable_keywords)

                                if is_unavailable:
                                    logger.info(f"Profile not found or hidden - content contains unavailable message")
                                    return {
                                        "success": True,
                                        "verified": False,
                                        "verified_at": asyncio.get_event_loop().time(),
                                        "error": "Profile not found or hidden",
                                        "status": status,
                                        "content_sample": content[:200]
                                    }

                                profile_indicators = [
                                    ' posts',
                                    ' posts counter',
                                    'followers',
                                    'following',
                                    'po.sts',
                                    'po.st',
                                    'dir.lo'
                                ]

                                has_profile_indicators = content and any(indicator in content.lower() for indicator in profile_indicators)

                                if has_profile_indicators:
                                    logger.info(f"Profile indicators detected in content - likely exists")
                                    return {
                                        "success": True,
                                        "verified": True,
                                        "verified_at": asyncio.get_event_loop().time(),
                                        "error": None,
                                        "status": status,
                                        "content_sample": content[:300]
                                    }

                                logger.warning(f"HTTP 200 but cannot confirm profile exists - no indicators found")
                                return {
                                    "success": True,
                                    "verified": False,
                                    "verified_at": asyncio.get_event_loop().time(),
                                    "error": "HTTP 200 but cannot confirm profile exists",
                                    "status": status,
                                    "content_sample": content[:200]
                                }
                            elif status == 404:
                                logger.warning(f"Account not found (404): {handle}")
                                return {
                                    "success": True,
                                    "verified": False,
                                    "verified_at": asyncio.get_event_loop().time(),
                                    "error": "Account not found",
                                    "status": status
                                }
                            else:
                                logger.warning(f"Unexpected status {status} for {handle}")

                except asyncio.TimeoutError:
                    last_error = "Verification timeout"
                    logger.warning(f"Timeout on attempt {attempts} for {handle}")

                except Exception as e:
                    last_error = str(e)
                    logger.warning(f"Error on attempt {attempts} for {handle}: {e}")

                if attempts < self.max_retries:
                    delay = 2 * attempts
                    logger.info(f"Retrying in {delay} seconds...")
                    await asyncio.sleep(delay)

            logger.error(f"Failed to verify account {handle} after {self.max_retries} attempts")
            return {
                "success": False,
                "verified": False,
                "verified_at": asyncio.get_event_loop().time(),
                "error": last_error or "Unknown error",
                "attempts": attempts
            }

        except ImportError:
            logger.warning("aiohttp not available, skipping verification")
            return {
                "success": True,
                "verified": False,
                "verified_at": None,
                "error": "aiohttp library not installed"
            }

    def enable_verification(self, enabled: bool = True):
        """Habilitar ou desabilitar verificação de contas"""
        self.verify_accounts = enabled
        logger.info(f"Account verification {'enabled' if enabled else 'disabled'}")

    def set_config(self, retries: int = 3, timeout: int = 10):
        """Configurar número de tentativas e timeout"""
        self.max_retries = max(1, retries)
        self.timeout = max(5, timeout)
        logger.info(f"Verifier config: retries={self.max_retries}, timeout={self.timeout}")

class InstagramLoginVerifier:
    """Verificador de login de contas Instagram"""

    def __init__(self):
        self.headless: bool = True

    async def login_and_verify(
        self,
        page: Page,
        handle: str,
        password: str,
        timeout: int = 30
    ) -> Dict:
        """
        Tentar fazer login na conta Instagram e verificar se foi bem-sucedido.

        Args:
            page: Playwright Page object
            handle: Username da conta
            password: Senha da conta
            timeout: Tempo máximo em segundos

        Returns:
            Dict com status de login e informações
        """
        if not HAS_PLAYWRIGHT:
            logger.warning("Playwright not available, skipping login verification")
            return {
                "success": True,
                "logged_in": False,
                "verified_at": None,
                "error": "Playwright library not installed",
                "screenshot_path": None
            }

        try:
            import time
            screenshot_dir = "logs/verification"
            timestamp = int(time.time())
            screenshot_path = f"{screenshot_dir}/login_verification_{timestamp}.png"
            os.makedirs(screenshot_dir, exist_ok=True)

            logger.info(f"Starting Instagram login verification for {handle}")

            login_url = "https://www.instagram.com/accounts/login/"

            try:
                await page.goto(login_url, wait_until="load", timeout=timeout * 1000)
                await asyncio.sleep(2)
            except Exception as e:
                logger.error(f"Failed to load login page: {e}")

            try:
                email_input = page.locator('input[name="username"], input[name="emailOrPhone"], input[placeholder*="phone"], input[placeholder*="email"]').first
                await email_input.fill(handle)
                logger.info(f"Filled username: {handle}")
            except Exception as e:
                logger.error(f"Failed to fill username field: {e}")
                return {
                    "success": True,
                    "logged_in": False,
                    "verified_at": None,
                    "error": f"Cannot fill username field: {e}",
                    "screenshot_path": screenshot_path
                }

            await asyncio.sleep(1)

            try:
                password_input = page.locator('input[name="password"], input[type="password"]').first
                await password_input.fill(password)
                logger.info(f"Filled password")
            except Exception as e:
                logger.error(f"Failed to fill password field: {e}")
                return {
                    "success": True,
                    "logged_in": False,
                    "verified_at": None,
                    "error": f"Cannot fill password field: {e}",
                    "screenshot_path": screenshot_path
                }

            await asyncio.sleep(1)

            try:
                login_button = page.locator('button[type="submit"], button:has-text("Log In"), button:has-text("Entrar")').first
                await login_button.click()
                logger.info("Clicked login button")
            except Exception as e:
                logger.error(f"Failed to click login button: {e}")
                return {
                    "success": True,
                    "logged_in": False,
                    "verified_at": None,
                    "error": f"Cannot click login button: {e}",
                    "screenshot_path": screenshot_path
                }

            await asyncio.sleep(3)

            try:
                screenshot = await page.screenshot(path=screenshot_path)
                logger.info(f"Captured screenshot: {screenshot_path}")
            except Exception as e:
                logger.warning(f"Failed to capture screenshot: {e}")

            current_url = page.url

            if "login" in current_url and ("error" in current_url or "wrong" in current_url):
                logger.error(f"Login failed, URL indicates error: {current_url}")
                return {
                    "success": True,
                    "logged_in": False,
                    "verified_at": time.time(),
                    "error": "Login failed (bad credentials or account not found)",
                    "screenshot_path": screenshot_path,
                    "final_url": current_url
                }

            if current_url and ("/feed" in current_url or "/home" in current_url or "/direct/" in current_url):
                logger.info(f"Login successful! URL: {current_url}")
                return {
                    "success": True,
                    "logged_in": True,
                    "verified_at": time.time(),
                    "error": None,
                    "screenshot_path": screenshot_path,
                    "final_url": current_url
                }

            logger.warning(f"Login verification inconclusive, final URL: {current_url}")
            return {
                "success": True,
                "logged_in": False,
                "verified_at": time.time(),
                "error": "Login verification completed but could not confirm success",
                "screenshot_path": screenshot_path,
                "final_url": current_url
            }

        except Exception as e:
            logger.error(f"Login verification failed: {e}", exc_info=True)
            return {
                "success": False,
                "logged_in": False,
                "verified_at": time.time(),
                "error": str(e),
                "screenshot_path": screenshot_path
            }

        finally:
            try:
                screenshot = await page.screenshot(path=screenshot_path)
            except:
                pass

class InstagramSignupResult:
    """Resultado da tentativa de signup do Instagram"""

    def __init__(self, success: bool, handle: str, error_message: Optional[str] = None, error_step: Optional[str] = None):
        self.success = success
        self.handle = handle
        self.error_message = error_message
        self.error_step = error_step

    def is_successful(self) -> bool:
        """Retornar se o signup foi bem-sucedido"""
        return self.success

    def has_error(self) -> bool:
        """Retornar se houve algum erro"""
        return not self.success or self.error_message is not None
