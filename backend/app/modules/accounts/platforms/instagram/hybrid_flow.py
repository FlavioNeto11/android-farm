import asyncio
import json
import base64
import os
import random
from typing import Dict, Optional, Tuple
from datetime import datetime
from openai import OpenAI

from app.modules.accounts.platforms.instagram.element_detection import (
    find_next_button,
    wait_for_element_stable,
    is_instagram_blocking,
)


class HybridInstagramFlow:
    DETERMINISTIC_ACTIONS = {
        "fill_email": "playwright",
        "fill_password": "playwright",
        "fill_name": "playwright",
        "fill_birth_date": "playwright",
        "click_next": "playwright",
        "click_sign_up": "playwright",
    }
    
    AI_REQUIRED_STEPS = {
        "solve_captcha",
        "handle_error",
        "verify_phone",
        "confirm_email",
        "navigate_unknown",
    }
    
    MAX_DIRECT_RETRIES = 3
    PLAYWRIGHT_TIMEOUT = 10000
    
    def __init__(self):
        self.client = OpenAI(
            api_key=os.getenv("VENICE_API_KEY"),
            base_url="https://api.venice.ai/api/v1"
        )
        self.model = os.getenv("VENICE_MODEL", "openai-gpt-4o-2024-11-20")
        self.log = []
    
    async def execute_step(self, step_name: str, page, context: Dict) -> Dict:
        action_mode = self.DETERMINISTIC_ACTIONS.get(step_name, "ai")
        
        if step_name in self.AI_REQUIRED_STEPS:
            action_mode = "ai"
        
        self._log(f"Step: {step_name}, Mode: {action_mode}")
        
        if action_mode == "playwright":
            success, error = await self._execute_playwright_action(step_name, page, context)
            if success:
                return {"success": True, "mode": "playwright", "step": step_name}
            
            for attempt in range(self.MAX_DIRECT_RETRIES - 1):
                self._log(f"Playwright failed for {step_name}, retry {attempt + 1}")
                await asyncio.sleep(2)
                success, error = await self._execute_playwright_action(step_name, page, context)
                if success:
                    return {"success": True, "mode": "playwright", "step": step_name}
            
            self._log(f"Playwright exhausted for {step_name}, falling back to AI")
            return await self._ai_navigation_decision(page, context, error)
        
        else:
            return await self._ai_navigation_decision(page, context, None)
    
    async def _execute_playwright_action(self, step_name: str, page, context: Dict) -> Tuple[bool, Optional[str]]:
        try:
            if step_name == "fill_email":
                email = context.get("email", "")
                locator = page.locator('input[name="emailOrPhone"]').first
                if await locator.count() == 0:
                    locator = page.locator('input[type="email"]').first
                if await locator.count() > 0:
                    await locator.fill(email)
                    await asyncio.sleep(0.5)
                    value = await locator.input_value()
                    return email.lower() in value.lower(), None
                return False, "Email field not found"
            
            elif step_name == "fill_password":
                password = context.get("password", "")
                locator = page.locator('input[name="password"]').first
                if await locator.count() == 0:
                    locator = page.locator('input[type="password"]').first
                if await locator.count() > 0:
                    await locator.fill(password)
                    await asyncio.sleep(0.5)
                    return True, None
                return False, "Password field not found"
            
            elif step_name == "fill_name":
                name = f"{context.get('first_name', '')} {context.get('last_name', '')}"
                locator = page.locator('input[name="fullName"]').first
                if await locator.count() == 0:
                    locator = page.locator('input[name*="name"]').first
                if await locator.count() > 0:
                    await locator.fill(name)
                    await asyncio.sleep(0.5)
                    return True, None
                return False, "Name field not found"
            
            elif step_name == "fill_birth_date":
                birth_date = context.get("birth_date", "")
                if birth_date:
                    from datetime import datetime
                    try:
                        birth = datetime.strptime(birth_date, "%Y-%m-%d")
                        month_sel = page.locator('select[title*="Month"]').first
                        day_sel = page.locator('select[title*="Day"]').first
                        year_sel = page.locator('select[title*="Year"]').first
                        
                        if await month_sel.count() > 0:
                            await month_sel.select_option(str(birth.month))
                        if await day_sel.count() > 0:
                            await day_sel.select_option(str(birth.day))
                        if await year_sel.count() > 0:
                            await year_sel.select_option(str(birth.year))
                        await asyncio.sleep(0.5)
                        return True, None
                    except:
                        pass
                return False, "Birth date fields not found"
            
            elif step_name in ("click_next", "click_sign_up"):
                btn = await find_next_button(page)
                if btn:
                    prev_url = page.url
                    await btn.click(timeout=self.PLAYWRIGHT_TIMEOUT)
                    await asyncio.sleep(2)
                    if page.url != prev_url:
                        return True, None
                    locator = page.locator('button:has-text("Next")').first
                    if await locator.count() > 0:
                        return True, None
                    return True, None
                return False, "Next button not found"
            
            return False, f"Unknown step: {step_name}"
            
        except Exception as e:
            return False, str(e)
    
    async def _ai_navigation_decision(self, page, context: Dict, last_error: Optional[str]) -> Dict:
        screenshot = await page.screenshot(type="jpeg", quality=80)
        base64_image = base64.b64encode(screenshot).decode("utf-8")
        
        current_url = page.url
        
        elements = []
        try:
            buttons = await page.locator("button").all()
            for btn in buttons[:5]:
                try:
                    text = await btn.text_content()
                    if text.strip():
                        elements.append(f"button: '{text.strip()}'")
                except:
                    pass
        except:
            pass
        
        prompt = f"""Analyze this Instagram signup page.
Current URL: {current_url}
Current step context: {context}
Last action failed: {last_error or 'N/A'}
Visible elements: {', '.join(elements) if elements else 'Could not enumerate'}

What is the next action?
Options: [fill_field, click_button, solve_captcha, wait, scroll, report_error]

Return JSON:
{{
  "action": "fill_field|click_button|solve_captcha|wait|scroll|report_error",
  "selector": "CSS selector or description",
  "value": "text to type if fill_field",
  "reason": "why this action"
}}"""
        
        response = self.client.chat.completions.create(
            model=self.model,
            messages=[
                {
                    "role": "user",
                    "content": [
                        {"type": "text", "text": prompt},
                        {"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{base64_image}"}}
                    ]
                }
            ],
            response_format={"type": "json_object"}
        )
        
        decision = json.loads(response.choices[0].message.content)
        self._log(f"AI decision: {decision}")
        
        action = decision.get("action", "")
        selector = decision.get("selector", "")
        value = decision.get("value", "")
        reason = decision.get("reason", "")
        
        try:
            if action == "click_button":
                if selector.startswith(("button[", "input[", ".", "#")):
                    locator = page.locator(selector).first
                    if await locator.count() > 0:
                        await locator.click()
                    else:
                        await page.get_by_text(selector).first.click()
                else:
                    btn = page.get_by_role("button", name=selector)
                    if await btn.count() > 0:
                        await btn.click()
                    else:
                        await page.get_by_text(selector).first.click()
                await asyncio.sleep(2)
                return {"success": True, "mode": "ai", "action": action, "reason": reason}
            
            elif action == "fill_field":
                locator = page.locator(selector).first
                if await locator.count() > 0:
                    await locator.fill(value)
                else:
                    await page.locator("input:visible").first.fill(value)
                await asyncio.sleep(1)
                return {"success": True, "mode": "ai", "action": action, "reason": reason}
            
            elif action == "scroll":
                await page.mouse.wheel(0, 300)
                await asyncio.sleep(1)
                return {"success": True, "mode": "ai", "action": action, "reason": reason}
            
            elif action == "wait":
                await asyncio.sleep(3)
                return {"success": True, "mode": "ai", "action": action, "reason": reason}
            
            elif action == "report_error":
                return {"success": False, "mode": "ai", "action": action, "reason": reason, "error": reason}
            
            else:
                await asyncio.sleep(2)
                return {"success": True, "mode": "ai", "action": "unknown", "reason": reason}
                
        except Exception as e:
            return {"success": False, "mode": "ai", "action": action, "reason": reason, "error": str(e)}
    
    async def execute_full_flow(self, page, context: Dict) -> Dict:
        steps = [
            ("fill_email", "Preenchendo email"),
            ("fill_password", "Preenchendo senha"),
            ("click_next", "Clicando Next após email/senha"),
            ("fill_name", "Preenchendo nome"),
            ("click_next", "Clicando Next após nome"),
            ("fill_birth_date", "Preenchendo data de nascimento"),
            ("click_next", "Clicando Next após data"),
        ]
        
        for step_name, description in steps:
            self._log(f"Starting: {description}")
            
            is_blocked, block_msg = await is_instagram_blocking(page)
            if is_blocked:
                self._log(f"Blocking detected: {block_msg}")
                result = await self._ai_navigation_decision(page, context, f"Blocking: {block_msg}")
                if not result.get("success"):
                    return {"success": False, "error": f"Instagram blocking: {block_msg}", "log": self.log}
            
            result = await self.execute_step(step_name, page, context)
            self._log(f"Result: {result}")
            
            if not result.get("success"):
                return {"success": False, "error": result.get("error", f"Step {step_name} failed"), "log": self.log}
            
            await asyncio.sleep(random.uniform(2, 4))
        
        await asyncio.sleep(3)
        url = page.url
        import re
        match = re.search(r'instagram\.com/([a-zA-Z0-9_.]+)/', url)
        if match and match.group(1) not in ("accounts", "explore", "reels"):
            return {"success": True, "handle": match.group(1), "log": self.log}
        
        if "/feed" in url or "/direct" in url:
            return {"success": True, "handle": None, "log": self.log}
        
        return {"success": False, "error": "Could not extract handle after signup", "log": self.log}
    
    def _log(self, message: str):
        entry = {
            "timestamp": datetime.now().isoformat(),
            "message": message,
        }
        self.log.append(entry)
        print(f"[HYBRID] {message}", flush=True)
    
    async def _broadcast(self, event_type, detail):
        import sys
        print(f"[HYBRID-WS] {event_type}: {detail}", flush=True, file=sys.stderr)
        try:
            from app.api.websocket_manager import manager
            await manager.broadcast({
                "type": event_type,
                "detail": detail,
                "timestamp": datetime.now().isoformat()
            })
        except ImportError:
            pass
