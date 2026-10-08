import asyncio
from typing import Optional, Tuple


async def find_next_button(page) -> Optional:
    selectors = [
        "button:has-text('Next')",
        "button:has-text('Próximo')",
        "button:has-text('Sign Up')",
        "button:has-text('Entrar')",
        "[type='submit']",
        "button:not([disabled])",
    ]
    
    for selector in selectors:
        try:
            locator = page.locator(selector).first
            if await locator.count() > 0:
                is_visible = await locator.is_visible()
                is_enabled = await locator.is_enabled()
                if is_visible and is_enabled:
                    return locator
        except:
            continue
    return None


async def wait_for_element_stable(page, selector: str, timeout: int = 5000) -> bool:
    try:
        await page.wait_for_selector(selector, state="visible", timeout=timeout)
        await asyncio.sleep(0.5)
        locator = page.locator(selector).first
        if await locator.count() > 0:
            return await locator.is_visible()
    except:
        pass
    return False


async def is_instagram_blocking(page) -> Tuple[bool, Optional[str]]:
    blocking_messages = [
        "Try Again Later",
        "Suspicious Activity",
        "Rate Limited",
        "action_blocked",
        "We restrict certain activity",
        "Your account has been disabled",
        "checkpoint",
        "confirm_email",
        "verify_phone",
    ]
    
    page_content = await page.content()
    page_text = page_content.lower()
    
    for message in blocking_messages:
        if message.lower() in page_text:
            return True, message
    
    url = page.url
    if "challenge" in url or "checkpoint" in url or "confirm" in url:
        return True, f"Instagram challenge page detected: {url}"
    
    return False, None
