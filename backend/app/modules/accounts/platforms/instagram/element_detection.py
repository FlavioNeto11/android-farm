import asyncio
from typing import Optional, Tuple, Dict, Literal

CheckpointType = Literal["real_checkpoint", "interstitial", "false_positive", "rate_limited", "none"]


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
    """Check if Instagram is showing a blocking page.
    Returns (is_blocking, reason). Only returns True for REAL blocking pages,
    not for interstitials that mention 'checkpoint' in passing.
    """
    blocking_messages = [
        "Try Again Later",
        "Suspicious Activity",
        "Rate Limited",
        "action_blocked",
        "We restrict certain activity",
        "Your account has been disabled",
        "confirm_email",
        "verify_phone",
    ]
    
    page_content = await page.content()
    page_text = page_content.lower()
    
    for message in blocking_messages:
        if message.lower() in page_text:
            return True, message
    
    # Only consider URL-based blocking if it's a real checkpoint URL
    url = page.url
    if "/challenge/" in url or "/checkpoint/" in url:
        return True, f"Instagram challenge/checkpoint page: {url}"
    
    return False, None


async def detect_checkpoint_type(page) -> Dict:
    """Precise checkpoint detection.
    
    Returns:
        - real_checkpoint: URL contains /checkpoint/ or /challenge/ AND has real form elements
        - interstitial: Page mentions 'checkpoint' but no real blocking elements
        - false_positive: No checkpoint indicators at all
        - rate_limited: "Try again later" type messages
        - none: Clean page
    """
    url = page.url
    content = await page.content()
    text = content.lower()
    
    # Check for real checkpoint URL patterns
    is_checkpoint_url = "/checkpoint/" in url or "/challenge/" in url
    
    # Check for real blocking elements
    has_code_input = await page.locator('input[inputmode="numeric"], input[name="code"], input[placeholder*="code"]').count() > 0
    has_confirm_button = await page.locator("button:has-text('Confirm'), button:has-text('Submit'), button:has-text('Send Code')").count() > 0
    has_captcha = "recaptcha" in text or "hcaptcha" in text or "g-recaptcha" in text
    has_email_verify = "verify your email" in text or "confirm your email" in text
    has_phone_verify = "phone number" in text or "número de telefone" in text or "6-digit" in text
    has_suspicious = "suspicious" in text or "unusual activity" in text
    
    # Real checkpoint: URL + actual form elements
    if is_checkpoint_url and (has_code_input or has_confirm_button or has_captcha):
        if has_captcha:
            return {
                "type": "captcha_challenge",
                "severity": "medium",
                "auto_solvable": True,
                "message": "Captcha challenge detected"
            }
        if has_phone_verify or has_code_input:
            return {
                "type": "sms_verification",
                "severity": "medium",
                "auto_solvable": False,
                "message": "SMS verification required"
            }
        if has_email_verify:
            return {
                "type": "email_verification",
                "severity": "low",
                "auto_solvable": False,
                "message": "Email verification required"
            }
        return {
            "type": "real_checkpoint",
            "severity": "high",
            "auto_solvable": False,
            "message": f"Real checkpoint detected: {url}"
        }
    
    # Interstitial: mentions checkpoint but no real blocking elements
    if "checkpoint" in text and not is_checkpoint_url:
        return {
            "type": "interstitial",
            "severity": "low",
            "auto_solvable": True,
            "message": "Checkpoint mentioned but no blocking elements (interstitial)"
        }
    
    # Rate limited
    if "try again later" in text or "temporarily blocked" in text or "rate limit" in text:
        return {
            "type": "rate_limited",
            "severity": "medium",
            "auto_solvable": False,
            "message": "Rate limited by Instagram"
        }
    
    # False positive: URL has checkpoint but no content
    if is_checkpoint_url and not has_code_input and not has_confirm_button:
        return {
            "type": "false_positive",
            "severity": "low",
            "auto_solvable": True,
            "message": "Checkpoint URL but no blocking content"
        }
    
    return {
        "type": "none",
        "severity": "none",
        "auto_solvable": True,
        "message": "No checkpoint detected"
    }


async def is_straight_to_checkpoint(page, initial_url: str) -> bool:
    current_url = page.url
    if "/checkpoint/" in current_url or "/challenge/" in current_url:
        if initial_url != current_url:
            return True
    return False
