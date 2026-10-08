import asyncio
from typing import Optional, Tuple, Dict


async def find_next_button(page) -> Optional:
    selectors = [
        "button:has-text('Next')",
        "button:has-text('Próximo')",
        "button:has-text('Sign Up')",
        "button:has-text('Entrar')",
        "button:has-text('Create Account')",
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


async def detect_checkpoint_type(page) -> Dict:
    url = page.url
    content = await page.content()
    text = content.lower()
    
    if "checkpoint" in url or "challenge" in url:
        if "enter the code" in text or "número de telefone" in text or "6-digit" in text:
            return {
                "type": "sms_verification",
                "severity": "medium",
                "auto_solvable": False,
                "message": "SMS verification required"
            }
        
        if "verify your email" in text or "email" in text and "code" in text:
            return {
                "type": "email_verification",
                "severity": "low",
                "auto_solvable": False,
                "message": "Email verification required"
            }
        
        if "recaptcha" in text or "hcaptcha" in text or "captcha" in text:
            return {
                "type": "captcha_challenge",
                "severity": "medium",
                "auto_solvable": True,
                "message": "Captcha challenge detected"
            }
        
        if "suspicious" in text or "unusual" in text:
            return {
                "type": "suspicious_activity",
                "severity": "high",
                "auto_solvable": False,
                "message": "Suspicious activity detected"
            }
        
        return {
            "type": "unknown_checkpoint",
            "severity": "high",
            "auto_solvable": False,
            "message": f"Unknown checkpoint: {url}"
        }
    
    if "try again later" in text or "temporarily blocked" in text:
        return {
            "type": "rate_limited",
            "severity": "medium",
            "auto_solvable": False,
            "message": "Rate limited by Instagram"
        }
    
    return {
        "type": "none",
        "severity": "none",
        "auto_solvable": True,
        "message": "No checkpoint detected"
    }


async def is_straight_to_checkpoint(page, initial_url: str) -> bool:
    current_url = page.url
    if "checkpoint" in current_url or "challenge" in current_url:
        if initial_url != current_url:
            return True
    return False
