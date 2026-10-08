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
    detect_checkpoint_type,
    is_straight_to_checkpoint,
)
from app.modules.accounts.platforms.instagram.human_behavior import HumanBehaviorSimulator
from app.modules.accounts.platforms.instagram.proxy_config import (
    load_proxy_from_env, get_proxy_url, get_masked_url, validate_proxy_connection,
    diagnose_proxy_error, ProxyAuthenticationError, ProxyConnectionError
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
    
    def __init__(self, account_id: Optional[str] = None):
        self.account_id = account_id
        self.client = OpenAI(
            api_key=os.getenv("VENICE_API_KEY"),
            base_url="https://api.venice.ai/api/v1"
        )
        self.model = os.getenv("VENICE_MODEL", "openai-gpt-4o-2024-11-20")
        self.log = []
        self.proxy_config = load_proxy_from_env()
        self.using_proxy = False
        self._setup_system_proxy_if_needed()
        
        if self.proxy_config:
            self._emit("info", f"Proxy configured: {get_masked_url(self.proxy_config)}")
            self._emit("info", "Testing proxy connection...")
            try:
                validate_proxy_connection(self.proxy_config)
                self.using_proxy = True
                self._emit("success", "Proxy connection successful - will use proxy for automation")
            except (ProxyAuthenticationError, ProxyConnectionError) as e:
                diagnosis = diagnose_proxy_error(e)
                self._emit("warning", f"Proxy validation failed: {diagnosis}")
                self._emit("warning", "FALLBACK: Running without proxy. Instagram checkpoint expected.")
                self.proxy_config = None
                self.using_proxy = False
        else:
            self._emit("warning", "Proxy disabled - running without proxy (checkpoint expected)")
    
    def _setup_system_proxy_if_needed(self):
        if not self.proxy_config:
            return
        proxy_url = get_proxy_url(self.proxy_config)
        current_http = os.environ.get("HTTP_PROXY", "")
        current_https = os.environ.get("HTTPS_PROXY", "")
        if proxy_url != current_http or proxy_url != current_https:
            os.environ["HTTP_PROXY"] = proxy_url
            os.environ["HTTPS_PROXY"] = proxy_url
            os.environ["http_proxy"] = proxy_url
            os.environ["https_proxy"] = proxy_url
            self._emit("info", "System proxy environment variables set")
    
    async def _emit(self, event_type: str, detail: str):
        self._log(detail)
        if self.account_id:
            try:
                from app.api.websocket_manager import manager
                await manager.broadcast({
                    "account_id": self.account_id,
                    "type": event_type,
                    "detail": detail,
                    "timestamp": datetime.now().isoformat()
                })
            except Exception:
                pass
    
    async def execute_step(self, step_name: str, page, context: Dict) -> Dict:
        action_mode = self.DETERMINISTIC_ACTIONS.get(step_name, "ai")
        
        if step_name in self.AI_REQUIRED_STEPS:
            action_mode = "ai"
        
        self._emit("step_started", f"Step: {step_name}, Mode: {action_mode}")
        
        if action_mode == "playwright":
            success, error = await self._execute_playwright_action(step_name, page, context)
            if success:
                self._emit("step_completed", f"Step {step_name} completed (playwright)")
                return {"success": True, "mode": "playwright", "step": step_name}
            
            for attempt in range(self.MAX_DIRECT_RETRIES - 1):
                self._emit("warning", f"Playwright failed for {step_name}, retry {attempt + 1}")
                await asyncio.sleep(2)
                success, error = await self._execute_playwright_action(step_name, page, context)
                if success:
                    self._emit("step_completed", f"Step {step_name} completed (playwright retry)")
                    return {"success": True, "mode": "playwright", "step": step_name}
            
            self._emit("warning", f"Playwright exhausted for {step_name}, falling back to AI")
            return await self._ai_navigation_decision(page, context, error)
        
        else:
            return await self._ai_navigation_decision(page, context, None)
    
    async def _execute_playwright_action(self, step_name: str, page, context: Dict) -> Tuple[bool, Optional[str]]:
        try:
            if step_name == "fill_email":
                email = context.get("email", "")
                self._emit("step_executed", f"Preenchendo email: {email}")
                await HumanBehaviorSimulator.random_delay(0.5, 2)
                await HumanBehaviorSimulator.random_scroll(page)
                
                locator = page.locator('input[name="emailOrPhone"]').first
                if await locator.count() == 0:
                    locator = page.locator('input[type="email"]').first
                if await locator.count() > 0:
                    await HumanBehaviorSimulator.type_like_human(page, 'input[name="emailOrPhone"]', email)
                    await asyncio.sleep(0.5)
                    try:
                        value = await locator.input_value()
                        self._emit("step_completed", f"Email preenchido: {email}")
                        return email.lower() in value.lower(), None
                    except:
                        self._emit("step_completed", f"Email preenchido: {email}")
                        return True, None
                self._emit("error", "Email field not found")
                return False, "Email field not found"
            
            elif step_name == "fill_password":
                self._emit("step_executed", "Preenchendo senha")
                password = context.get("password", "")
                await HumanBehaviorSimulator.random_delay(0.5, 1.5)
                
                locator = page.locator('input[name="password"]').first
                if await locator.count() == 0:
                    locator = page.locator('input[type="password"]').first
                if await locator.count() > 0:
                    await HumanBehaviorSimulator.type_like_human(page, 'input[name="password"]', password)
                    await asyncio.sleep(0.5)
                    self._emit("step_completed", "Senha preenchida")
                    return True, None
                self._emit("error", "Password field not found")
                return False, "Password field not found"
            
            elif step_name == "fill_name":
                name = f"{context.get('first_name', '')} {context.get('last_name', '')}"
                self._emit("step_executed", f"Preenchendo nome: {name}")
                await HumanBehaviorSimulator.random_delay(0.5, 1.5)
                
                locator = page.locator('input[name="fullName"]').first
                if await locator.count() == 0:
                    locator = page.locator('input[name*="name"]').first
                if await locator.count() > 0:
                    await HumanBehaviorSimulator.type_like_human(page, 'input[name="fullName"]', name)
                    await asyncio.sleep(0.5)
                    self._emit("step_completed", f"Nome preenchido: {name}")
                    return True, None
                self._emit("error", "Name field not found")
                return False, "Name field not found"
            
            elif step_name == "fill_birth_date":
                birth_date = context.get("birth_date", "")
                if birth_date:
                    from datetime import datetime
                    try:
                        birth = datetime.strptime(birth_date, "%Y-%m-%d")
                        self._emit("step_executed", f"Preenchendo data de nascimento: {birth_date}")
                        await HumanBehaviorSimulator.random_delay(0.3, 1)
                        
                        month_sel = page.locator('select[title*="Month"]').first
                        day_sel = page.locator('select[title*="Day"]').first
                        year_sel = page.locator('select[title*="Year"]').first
                        
                        if await month_sel.count() > 0:
                            await month_sel.select_option(str(birth.month))
                            await asyncio.sleep(random.uniform(0.2, 0.5))
                        if await day_sel.count() > 0:
                            await day_sel.select_option(str(birth.day))
                            await asyncio.sleep(random.uniform(0.2, 0.5))
                        if await year_sel.count() > 0:
                            await year_sel.select_option(str(birth.year))
                            await asyncio.sleep(0.5)
                        self._emit("step_completed", "Data de nascimento preenchida")
                        return True, None
                    except:
                        pass
                self._emit("error", "Birth date fields not found")
                return False, "Birth date fields not found"
            
            elif step_name in ("click_next", "click_sign_up"):
                self._emit("step_executed", "Clicando no botão Next")
                btn = await find_next_button(page)
                if btn:
                    await HumanBehaviorSimulator.move_mouse_human_like(page, "")
                    await HumanBehaviorSimulator.random_delay(0.3, 1)
                    
                    prev_url = page.url
                    try:
                        await btn.click(timeout=self.PLAYWRIGHT_TIMEOUT)
                    except:
                        pass
                    await asyncio.sleep(random.uniform(2, 4))
                    
                    if page.url != prev_url:
                        self._emit("step_completed", "Página navegada com sucesso")
                    else:
                        self._emit("step_completed", "Botão clicado (mesma página)")
                    return True, None
                self._emit("error", "Next button not found")
                return False, "Next button not found"
            
            self._emit("error", f"Unknown step: {step_name}")
            return False, f"Unknown step: {step_name}"
            
        except Exception as e:
            self._emit("error", f"Exception in {step_name}: {str(e)}")
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
        self._emit("ai_decision", f"AI decision: {decision.get('action', 'unknown')} - {decision.get('reason', '')}")
        
        action = decision.get("action", "")
        selector = decision.get("selector", "")
        value = decision.get("value", "")
        reason = decision.get("reason", "")
        
        try:
            if action == "click_button":
                self._emit("step_executed", f"AI: Clicando botão '{selector}'")
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
                self._emit("step_completed", f"AI: Botão clicado - {reason}")
                return {"success": True, "mode": "ai", "action": action, "reason": reason}
            
            elif action == "fill_field":
                self._emit("step_executed", f"AI: Preenchendo campo '{selector}' com '{value}'")
                locator = page.locator(selector).first
                if await locator.count() > 0:
                    await locator.fill(value)
                else:
                    await page.locator("input:visible").first.fill(value)
                await asyncio.sleep(1)
                self._emit("step_completed", f"AI: Campo preenchido - {reason}")
                return {"success": True, "mode": "ai", "action": action, "reason": reason}
            
            elif action == "scroll":
                self._emit("step_executed", "AI: Scrollando página")
                await page.mouse.wheel(0, 300)
                await asyncio.sleep(1)
                self._emit("step_completed", "AI: Scroll completado")
                return {"success": True, "mode": "ai", "action": action, "reason": reason}
            
            elif action == "wait":
                self._emit("step_executed", "AI: Aguardando...")
                await asyncio.sleep(3)
                self._emit("step_completed", "AI: Espera completada")
                return {"success": True, "mode": "ai", "action": action, "reason": reason}
            
            elif action == "report_error":
                self._emit("error", f"AI reportou erro: {reason}")
                return {"success": False, "mode": "ai", "action": action, "reason": reason, "error": reason}
            
            else:
                self._emit("warning", f"AI ação desconhecida: {action}")
                await asyncio.sleep(2)
                return {"success": True, "mode": "ai", "action": "unknown", "reason": reason}
                
        except Exception as e:
            self._emit("error", f"AI action failed: {str(e)}")
            return {"success": False, "mode": "ai", "action": action, "reason": reason, "error": str(e)}
    
    async def execute_full_flow(self, page, context: Dict) -> Dict:
        initial_url = page.url
        
        self._emit("info", "=== Iniciando fluxo de criação de conta Instagram ===")
        self._emit("info", f"Email: {context.get('email', 'N/A')}")
        self._emit("info", f"Nome: {context.get('first_name', '')} {context.get('last_name', '')}")
        self._emit("info", f"Nascimento: {context.get('birth_date', 'N/A')}")
        
        checkpoint_info = await detect_checkpoint_type(page)
        if checkpoint_info["type"] != "none":
            self._emit("warning", f"Checkpoint detectado imediatamente: {checkpoint_info['type']}")
            if is_straight_to_checkpoint(page, initial_url):
                self._emit("error", "Straight to checkpoint - IP likely flagged")
                return {"success": False, "error": "Straight to checkpoint - IP flagged", "log": self.log}
        
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
            self._emit("step_started", f"Iniciando: {description}")
            
            is_blocked, block_msg = await is_instagram_blocking(page)
            if is_blocked:
                self._emit("warning", f"Blocking detectado: {block_msg}")
                checkpoint = await detect_checkpoint_type(page)
                self._emit("warning", f"Checkpoint type: {checkpoint['type']}")
                result = await self._ai_navigation_decision(page, context, f"Blocking: {block_msg}, Type: {checkpoint['type']}")
                if not result.get("success"):
                    self._emit("error", f"Não foi possível resolver blocking: {block_msg}")
                    return {"success": False, "error": f"Instagram blocking: {block_msg}", "log": self.log}
            
            result = await self.execute_step(step_name, page, context)
            
            if not result.get("success"):
                self._emit("error", f"Step {step_name} falhou: {result.get('error', 'Unknown')}")
                return {"success": False, "error": result.get("error", f"Step {step_name} failed"), "log": self.log}
            
            self._emit("step_completed", f"Step {step_name} completado com sucesso")
            await HumanBehaviorSimulator.random_delay(2, 4)
        
        self._emit("info", "Todos os steps completados, extraindo handle...")
        await asyncio.sleep(3)
        url = page.url
        import re
        match = re.search(r'instagram\.com/([a-zA-Z0-9_.]+)/', url)
        if match and match.group(1) not in ("accounts", "explore", "reels", "p", "direct"):
            handle = match.group(1)
            self._emit("success", f"Conta criada com sucesso! Handle: @{handle}")
            return {"success": True, "handle": handle, "log": self.log}
        
        if "/feed" in url or "/direct" in url:
            self._emit("success", "Conta criada (handle não extraído, mas na feed/direct)")
            return {"success": True, "handle": None, "log": self.log}
        
        checkpoint = await detect_checkpoint_type(page)
        if checkpoint["type"] != "none":
            self._emit("error", f"Checkpoint no final: {checkpoint['type']}")
            return {"success": False, "error": f"Checkpoint at end: {checkpoint['type']}", "log": self.log}
        
        self._emit("error", "Não foi possível extrair handle após signup")
        return {"success": False, "error": "Could not extract handle after signup", "log": self.log}
    
    def _log(self, message: str):
        entry = {
            "timestamp": datetime.now().isoformat(),
            "message": message,
        }
        self.log.append(entry)
        print(f"[HYBRID] {message}", flush=True)
