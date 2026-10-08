import asyncio
import json
import base64
import os
import random
from typing import Dict, Optional, Tuple
from datetime import datetime
from pathlib import Path
from openai import OpenAI

from app.modules.accounts.platforms.instagram.element_detection import (
    find_next_button,
    wait_for_element_stable,
    is_instagram_blocking,
    detect_checkpoint_type,
    is_straight_to_checkpoint,
)
from app.modules.accounts.platforms.instagram.human_behavior import HumanBehaviorSimulator, DelayConfig
from app.modules.accounts.platforms.instagram.proxy_config import (
    load_proxy_from_env, get_proxy_url, get_masked_url, layered_proxy_fallback,
    diagnose_proxy_error, ProxyAuthenticationError, ProxyConnectionError, ProxyResult
)

EVIDENCE_DIR = Path("./data/evidence")


def _save_evidence(account_id: str, step_name: str, image_bytes: bytes):
    """Save screenshot to evidence directory."""
    EVIDENCE_DIR.mkdir(parents=True, exist_ok=True)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S_%f")
    filename = f"{account_id}_{step_name}_{timestamp}.png"
    (EVIDENCE_DIR / filename).write_bytes(image_bytes)


def _save_evidence_metadata(account_id: str, step_name: str, metadata: Dict):
    """Save step metadata JSON."""
    EVIDENCE_DIR.mkdir(parents=True, exist_ok=True)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S_%f")
    filename = f"{account_id}_{step_name}_{timestamp}.json"
    data = {"account_id": account_id, "step": step_name, "timestamp": datetime.now().isoformat(), **metadata}
    (EVIDENCE_DIR / filename).write_text(json.dumps(data, indent=2, ensure_ascii=False))


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
    
    def __init__(self, account_id: Optional[str] = None, delay_config: Optional[DelayConfig] = None, log_callback=None):
        self.account_id = account_id
        self.delay_config = delay_config or DelayConfig.conservative()
        self.log_callback = log_callback  # Called after each log entry to save incrementally
        self.client = OpenAI(
            api_key=os.getenv("VENICE_API_KEY"),
            base_url="https://api.venice.ai/api/v1"
        )
        self.model = os.getenv("VENICE_MODEL", "openai-gpt-4o-2024-11-20")
        self.log = []
        self.proxy_config = load_proxy_from_env()
        self.proxy_result: Optional[ProxyResult] = None
        self.using_proxy = False
        
        if self.proxy_config:
            self._log(f"Proxy configured: {get_masked_url(self.proxy_config)}")
            self._log("Testing proxy with layered fallback...")
            try:
                self.proxy_result = layered_proxy_fallback(self.proxy_config)
                self.using_proxy = self.proxy_result.using_proxy
                self._log(f"Proxy result: method={self.proxy_result.method}, using_proxy={self.using_proxy}, ip={self.proxy_result.ip}")
                if not self.using_proxy:
                    self._log("FALLBACK: Running without proxy. Instagram checkpoint expected.")
                    self.proxy_config = None
            except (ProxyAuthenticationError, ProxyConnectionError) as e:
                diagnosis = diagnose_proxy_error(e)
                self._log(f"Proxy validation failed: {diagnosis}")
                self._log("FALLBACK: Running without proxy. Instagram checkpoint expected.")
                self.proxy_config = None
                self.using_proxy = False
        else:
            self._log("Proxy disabled - running without proxy (checkpoint expected)")
    
    def _emit(self, event_type: str, detail: str):
        """Sync emit: logs locally and queues WS broadcast"""
        self._log(detail)
        if self.account_id:
            self._pending_broadcasts.append({
                "account_id": self.account_id,
                "type": event_type,
                "detail": detail,
                "timestamp": datetime.now().isoformat()
            })
        # Save log incrementally to DB
        if self.log_callback:
            try:
                self.log_callback(self.log)
            except Exception:
                pass
    
    async def _flush_broadcasts(self):
        """Flush all pending WS broadcasts"""
        from app.api.websocket_manager import manager
        for msg in self._pending_broadcasts:
            try:
                await manager.broadcast(msg)
            except Exception:
                pass
        self._pending_broadcasts.clear()
    
    async def _save_step_screenshot(self, page, step_name: str):
        """Save screenshot evidence for a step."""
        if not self.account_id:
            return
        try:
            screenshot = await page.screenshot(type="png")
            _save_evidence(self.account_id, step_name, screenshot)
            _save_evidence_metadata(self.account_id, step_name, {"url": page.url})
        except Exception as e:
            self._log(f"Failed to save screenshot for {step_name}: {e}")
    
    async def execute_step(self, step_name: str, page, context: Dict) -> Dict:
        action_mode = self.DETERMINISTIC_ACTIONS.get(step_name, "ai")
        
        if step_name in self.AI_REQUIRED_STEPS:
            action_mode = "ai"
        
        self._emit("step_started", f"Step: {step_name}, Mode: {action_mode}")
        await self._flush_broadcasts()
        
        if action_mode == "playwright":
            success, error = await self._execute_playwright_action(step_name, page, context)
            if success:
                self._emit("step_completed", f"Step {step_name} completed (playwright)")
                await self._flush_broadcasts()
                return {"success": True, "mode": "playwright", "step": step_name}
            
            for attempt in range(self.MAX_DIRECT_RETRIES - 1):
                self._emit("warning", f"Playwright failed for {step_name}, retry {attempt + 1}")
                await self._flush_broadcasts()
                await asyncio.sleep(2)
                success, error = await self._execute_playwright_action(step_name, page, context)
                if success:
                    self._emit("step_completed", f"Step {step_name} completed (playwright retry)")
                    await self._flush_broadcasts()
                    return {"success": True, "mode": "playwright", "step": step_name}
            
            self._emit("warning", f"Playwright exhausted for {step_name}, falling back to AI")
            await self._flush_broadcasts()
            return await self._ai_navigation_decision(page, context, error)
        
        else:
            return await self._ai_navigation_decision(page, context, None)
    
    async def _execute_playwright_action(self, step_name: str, page, context: Dict) -> Tuple[bool, Optional[str]]:
        try:
            if step_name == "fill_email":
                email = context.get("email", "")
                self._emit("step_executed", f"Preenchendo email: {email}")
                await self._flush_broadcasts()
                await HumanBehaviorSimulator.random_delay(config=self.delay_config)
                
                # Try multiple selectors for email field
                email_selectors = [
                    'input[name="emailOrPhone"]',
                    'input[name="email"]',
                    'input[aria-label="Mobile number or email"]',
                    'input[placeholder*="Mobile number"]',
                    'input[placeholder*="email"]',
                    'input[type="email"]',
                    'input[type="text"]',
                ]
                
                filled = False
                for sel in email_selectors:
                    locator = page.locator(sel).first
                    if await locator.count() > 0:
                        try:
                            # Clear the field first to avoid duplication
                            await locator.click()
                            await asyncio.sleep(0.3)
                            # Select all and delete
                            await page.keyboard.press("Control+A")
                            await asyncio.sleep(0.1)
                            await page.keyboard.press("Delete")
                            await asyncio.sleep(0.2)
                            # Now type the email
                            await HumanBehaviorSimulator.type_like_human(page, sel, email, config=self.delay_config)
                            await asyncio.sleep(0.5)
                            # Verify the field contains the email
                            try:
                                value = await locator.input_value()
                                if email.lower() in value.lower():
                                    self._emit("step_completed", f"Email preenchido: {email}")
                                    await self._flush_broadcasts()
                                    filled = True
                                    break
                                else:
                                    self._emit("warning", f"Email field has unexpected value: {value[:50]}")
                            except:
                                self._emit("step_completed", f"Email preenchido: {email}")
                                await self._flush_broadcasts()
                                filled = True
                                break
                        except Exception as e:
                            self._emit("warning", f"Failed to fill email with {sel}: {e}")
                            continue
                
                if not filled:
                    self._emit("error", "Email field not found")
                    await self._flush_broadcasts()
                    return False, "Email field not found"
                return True, None
            
            elif step_name == "fill_password":
                self._emit("step_executed", "Preenchendo senha")
                await self._flush_broadcasts()
                password = context.get("password", "")
                await HumanBehaviorSimulator.random_delay(config=self.delay_config)
                
                locator = page.locator('input[name="password"]').first
                if await locator.count() == 0:
                    locator = page.locator('input[type="password"]').first
                if await locator.count() > 0:
                    await HumanBehaviorSimulator.type_like_human(page, 'input[name="password"]', password, config=self.delay_config)
                    await asyncio.sleep(0.5)
                    self._emit("step_completed", "Senha preenchida")
                    await self._flush_broadcasts()
                    return True, None
                self._emit("error", "Password field not found")
                await self._flush_broadcasts()
                return False, "Password field not found"
            
            elif step_name == "fill_username":
                # Use username from context or generate one
                username = context.get('username')
                if not username:
                    first = context.get('first_name', '').lower().replace(' ', '').replace('-', '')
                    last = context.get('last_name', '').lower().replace(' ', '').replace('-', '')
                    number = random.randint(100, 999)
                    username = f"{first}{last}{number}"
                    context['username'] = username
                self._emit("step_executed", f"Preenchendo username: {username}")
                await self._flush_broadcasts()
                await HumanBehaviorSimulator.random_delay(config=self.delay_config)
                
                # Try multiple selectors for username field
                username_selectors = [
                    'input[name="username"]',
                    'input[name="full_name"]',
                    'input[aria-label="Username"]',
                    'input[placeholder*="username"]',
                    'input[placeholder*="Username"]',
                    'input[type="text"]',
                ]
                for sel in username_selectors:
                    locator = page.locator(sel).first
                    if await locator.count() > 0:
                        try:
                            await locator.fill(username)
                            self._emit("step_completed", f"Username preenchido: {username}")
                            await self._flush_broadcasts()
                            return True, None
                        except Exception:
                            continue
                
                self._emit("error", "Username field not found")
                await self._flush_broadcasts()
                return False, "Username field not found"
            
            elif step_name == "fill_name":
                name = f"{context.get('first_name', '')} {context.get('last_name', '')}"
                self._emit("step_executed", f"Preenchendo nome: {name}")
                await self._flush_broadcasts()
                await HumanBehaviorSimulator.random_delay(config=self.delay_config)
                
                # Try multiple selectors for name field
                name_selectors = [
                    'input[name="fullName"]',
                    'input[name="full_name"]',
                    'input[name*="name"]',
                    'input[aria-label="Full Name"]',
                    'input[aria-label="Nome completo"]',
                    'input[placeholder*="name"]',
                    'input[placeholder*="Name"]',
                    'input[type="text"]',
                ]
                for sel in name_selectors:
                    locator = page.locator(sel).first
                    if await locator.count() > 0:
                        try:
                            await HumanBehaviorSimulator.type_like_human(page, sel, name, config=self.delay_config)
                            self._emit("step_completed", f"Nome preenchido: {name}")
                            await self._flush_broadcasts()
                            return True, None
                        except Exception:
                            continue
                
                self._emit("error", "Name field not found")
                await self._flush_broadcasts()
                return False, "Name field not found"
            
            elif step_name == "fill_birth_date":
                birth_date = context.get("birth_date", "")
                if birth_date:
                    from datetime import datetime
                    try:
                        birth = datetime.strptime(birth_date, "%Y-%m-%d")
                        self._emit("step_executed", f"Preenchendo data de nascimento: {birth_date}")
                        await self._flush_broadcasts()
                        await HumanBehaviorSimulator.random_delay(config=self.delay_config)
                        
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
                        await self._flush_broadcasts()
                        return True, None
                    except:
                        pass
                self._emit("error", "Birth date fields not found")
                await self._flush_broadcasts()
                return False, "Birth date fields not found"
            
            elif step_name in ("click_next", "click_sign_up"):
                self._emit("step_executed", "Clicando no botão Next")
                await self._flush_broadcasts()
                
                # Try multiple strategies to find the Next/Submit button
                btn = await find_next_button(page)
                
                # If not found, try additional Instagram-specific selectors
                if not btn:
                    next_selectors = [
                        "button:has-text('Next')",
                        "button:has-text('Próximo')",
                        "button:has-text('Sign up')",
                        "button:has-text('Cadastre-se')",
                        "button:has-text('Continue')",
                        "button:has-text('Continuar')",
                        "button:has-text('Create Account')",
                        "button:has-text('Criar conta')",
                        "button[type='submit']",
                        "div[role='button']:has-text('Next')",
                        "div[role='button']:has-text('Sign up')",
                        "a:has-text('Next')",
                        "button:not([disabled]):visible",
                    ]
                    for sel in next_selectors:
                        try:
                            locator = page.locator(sel).first
                            if await locator.count() > 0 and await locator.is_visible():
                                btn = locator
                                break
                        except Exception:
                            continue
                
                if btn:
                    await HumanBehaviorSimulator.move_mouse_human_like(page, "")
                    await HumanBehaviorSimulator.random_delay(config=self.delay_config)
                    
                    prev_url = page.url
                    try:
                        await btn.click(timeout=5000)
                    except Exception as e:
                        self._emit("warning", f"Click failed: {e}, trying JS click")
                        try:
                            await btn.evaluate("el => el.click()")
                        except Exception:
                            pass
                    await asyncio.sleep(random.uniform(2, 4))
                    
                    if page.url != prev_url:
                        self._emit("step_completed", "Página navegada com sucesso")
                    else:
                        self._emit("step_completed", "Botão clicado (mesma página)")
                    await self._flush_broadcasts()
                    return True, None
                self._emit("warning", "Next button not found, continuing anyway")
                await self._flush_broadcasts()
                return True, None  # Continue even if button not found
            
            self._emit("error", f"Unknown step: {step_name}")
            await self._flush_broadcasts()
            return False, f"Unknown step: {step_name}"
            
        except Exception as e:
            self._emit("error", f"Exception in {step_name}: {str(e)}")
            await self._flush_broadcasts()
            return False, str(e)
    
    async def _ai_navigation_decision(self, page, context: Dict, last_error: Optional[str]) -> Dict:
        # Save screenshot before sending to AI
        if self.account_id:
            try:
                screenshot = await page.screenshot(type="png")
                _save_evidence(self.account_id, "ai_vision", screenshot)
            except Exception:
                pass
        
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

Instagram signup button patterns (try these in order):
- button:has-text('Next') or button:has-text('Próximo')
- button:has-text('Sign up') or button:has-text('Cadastre-se')
- button:has-text('Continue') or button:has-text('Continuar')
- button[type='submit']
- div[role='button'] with button text
- Any visible button at the bottom of the form

What is the next action?
Options:
- fill_field: Fill a text input field (use selector like input[name='fieldName'] or input[aria-label='Label'])
- click_button: Click a button (use selector like button:has-text('Text') or button[type='submit'])
- continue: Continue with the normal flow (page looks OK despite warning)
- solve_captcha: Attempt to solve a captcha
- wait_retry: Wait and retry (for temporary blocks)
- scroll: Scroll the page
- report_error: Report an unrecoverable error

Return JSON:
{{
  "action": "fill_field|click_button|continue|solve_captcha|wait_retry|scroll|report_error",
  "selector": "CSS selector or button text",
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
        await self._flush_broadcasts()
        
        action = decision.get("action", "")
        selector = decision.get("selector", "")
        value = decision.get("value", "")
        reason = decision.get("reason", "")
        
        try:
            if action == "click_button":
                self._emit("step_executed", f"AI: Clicando botão '{selector}'")
                await self._flush_broadcasts()
                
                # Try multiple strategies to find and click the button
                clicked = False
                
                # Strategy 1: Direct CSS locator
                if selector and selector.startswith(("button[", "input[", ".", "#", "[", "a[")):
                    try:
                        locator = page.locator(selector).first
                        if await locator.count() > 0 and await locator.is_visible():
                            await locator.click(timeout=5000)
                            clicked = True
                    except Exception:
                        pass
                
                # Strategy 2: Role-based button
                if not clicked and selector:
                    try:
                        btn = page.get_by_role("button", name=selector)
                        if await btn.count() > 0 and await btn.is_visible():
                            await btn.click(timeout=5000)
                            clicked = True
                    except Exception:
                        pass
                
                # Strategy 3: Text-based button
                if not clicked and selector:
                    try:
                        btn = page.get_by_text(selector, exact=False).first
                        if await btn.count() > 0 and await btn.is_visible():
                            await btn.click(timeout=5000)
                            clicked = True
                    except Exception:
                        pass
                
                # Strategy 4: Common Instagram signup buttons
                if not clicked:
                    common_selectors = [
                        "button:has-text('Next')",
                        "button:has-text('Sign up')",
                        "button:has-text('Create account')",
                        "button:has-text('Continue')",
                        "button[type='submit']",
                        "button:not([disabled]):visible",
                    ]
                    for cs in common_selectors:
                        try:
                            locator = page.locator(cs).first
                            if await locator.count() > 0 and await locator.is_visible():
                                await locator.click(timeout=5000)
                                clicked = True
                                break
                        except Exception:
                            pass
                
                if clicked:
                    await asyncio.sleep(2)
                    self._emit("step_completed", f"AI: Botão clicado - {reason}")
                    await self._flush_broadcasts()
                    return {"success": True, "mode": "ai", "action": action, "reason": reason}
                else:
                    self._emit("warning", f"AI: Botão não encontrado '{selector}', tentando continuar")
                    await self._flush_broadcasts()
                    await asyncio.sleep(2)
                    return {"success": True, "mode": "ai", "action": action, "reason": f"Button not found, continuing: {reason}"}
            
            elif action == "fill_field":
                self._emit("step_executed", f"AI: Preenchendo campo '{selector}' com '{value}'")
                await self._flush_broadcasts()
                
                filled = False
                
                # Strategy 1: Direct CSS locator
                if selector and selector.startswith(("input[", "textarea[", ".", "#", "[")):
                    try:
                        locator = page.locator(selector).first
                        if await locator.count() > 0 and await locator.is_visible():
                            await locator.fill(value)
                            filled = True
                    except Exception:
                        pass
                
                # Strategy 2: Label-based
                if not filled and selector:
                    try:
                        locator = page.get_by_label(selector).first
                        if await locator.count() > 0 and await locator.is_visible():
                            await locator.fill(value)
                            filled = True
                    except Exception:
                        pass
                
                # Strategy 3: Placeholder-based
                if not filled and selector:
                    try:
                        locator = page.locator(f"input[placeholder*='{selector}']").first
                        if await locator.count() > 0 and await locator.is_visible():
                            await locator.fill(value)
                            filled = True
                    except Exception:
                        pass
                
                # Strategy 4: First visible input
                if not filled:
                    try:
                        locator = page.locator("input:visible, textarea:visible").first
                        if await locator.count() > 0:
                            await locator.fill(value)
                            filled = True
                    except Exception:
                        pass
                
                if filled:
                    await asyncio.sleep(1)
                    self._emit("step_completed", f"AI: Campo preenchido - {reason}")
                    await self._flush_broadcasts()
                    return {"success": True, "mode": "ai", "action": action, "reason": reason}
                else:
                    self._emit("warning", f"AI: Campo não encontrado '{selector}'")
                    await self._flush_broadcasts()
                    return {"success": False, "mode": "ai", "action": action, "reason": f"Field not found: {selector}", "error": f"Field not found: {selector}"}
            
            elif action == "scroll":
                self._emit("step_executed", "AI: Scrollando página")
                await self._flush_broadcasts()
                await page.mouse.wheel(0, 300)
                await asyncio.sleep(1)
                self._emit("step_completed", "AI: Scroll completado")
                await self._flush_broadcasts()
                return {"success": True, "mode": "ai", "action": action, "reason": reason}
            
            elif action == "wait":
                self._emit("step_executed", "AI: Aguardando...")
                await self._flush_broadcasts()
                await asyncio.sleep(3)
                self._emit("step_completed", "AI: Espera completada")
                await self._flush_broadcasts()
                return {"success": True, "mode": "ai", "action": action, "reason": reason}
            
            elif action == "continue":
                self._emit("info", f"AI: Continuando fluxo - {reason}")
                await self._flush_broadcasts()
                return {"success": True, "mode": "ai", "action": action, "reason": reason}
            
            elif action == "solve_captcha":
                self._emit("warning", f"AI: Tentando resolver captcha - {reason}")
                await self._flush_broadcasts()
                await asyncio.sleep(5)
                self._emit("step_completed", "AI: Tentativa de captcha completada")
                await self._flush_broadcasts()
                return {"success": True, "mode": "ai", "action": action, "reason": reason}
            
            elif action == "wait_retry":
                self._emit("warning", f"AI: Aguardando para retry - {reason}")
                await self._flush_broadcasts()
                await asyncio.sleep(10)
                self._emit("step_completed", "AI: Wait retry completado")
                await self._flush_broadcasts()
                return {"success": True, "mode": "ai", "action": action, "reason": reason}
            
            elif action == "report_error":
                self._emit("error", f"AI reportou erro: {reason}")
                await self._flush_broadcasts()
                return {"success": False, "mode": "ai", "action": action, "reason": reason, "error": reason}
            
            else:
                self._emit("warning", f"AI ação desconhecida: {action}")
                await self._flush_broadcasts()
                await asyncio.sleep(2)
                return {"success": True, "mode": "ai", "action": "unknown", "reason": reason}
                
        except Exception as e:
            self._emit("error", f"AI action failed: {str(e)}")
            await self._flush_broadcasts()
            return {"success": False, "mode": "ai", "action": action, "reason": reason, "error": str(e)}
    
    async def execute_full_flow(self, page, context: Dict) -> Dict:
        self._pending_broadcasts = []
        self._filled_fields = set()  # Track which fields have been filled to prevent duplication
        initial_url = page.url
        
        # Save initial screenshot
        await self._save_step_screenshot(page, "start")
        
        self._emit("info", "=== Iniciando fluxo de criação de conta Instagram ===")
        self._emit("info", f"Email: {context.get('email', 'N/A')}")
        self._emit("info", f"Nome: {context.get('first_name', '')} {context.get('last_name', '')}")
        self._emit("info", f"Nascimento: {context.get('birth_date', 'N/A')}")
        await self._flush_broadcasts()
        
        # Warmup delay
        self._emit("info", f"Warmup delay ({self.delay_config.warmup[0]}-{self.delay_config.warmup[1]}s)...")
        await self._flush_broadcasts()
        await HumanBehaviorSimulator.warmup_delay(self.delay_config)
        
        checkpoint_info = await detect_checkpoint_type(page)
        if checkpoint_info["type"] != "none":
            self._emit("warning", f"Checkpoint detectado imediatamente: {checkpoint_info['type']}")
            await self._flush_broadcasts()
            # Save checkpoint evidence
            if self.account_id:
                try:
                    screenshot = await page.screenshot(type="png")
                    _save_evidence(self.account_id, f"checkpoint_{checkpoint_info['type']}", screenshot)
                    _save_evidence_metadata(self.account_id, f"checkpoint_{checkpoint_info['type']}", {
                        "checkpoint_type": checkpoint_info["type"],
                        "url": page.url,
                        "severity": checkpoint_info.get("severity", "high"),
                    })
                except Exception:
                    pass
            
            # Handle by type
            if checkpoint_info["type"] == "interstitial":
                self._emit("info", "Interstitial detected - continuing flow")
                await self._flush_broadcasts()
            elif checkpoint_info["type"] == "false_positive":
                self._emit("info", "False positive checkpoint - continuing flow")
                await self._flush_broadcasts()
            elif is_straight_to_checkpoint(page, initial_url):
                self._emit("error", "Straight to checkpoint - IP likely flagged")
                await self._flush_broadcasts()
                return {"success": False, "error": "Straight to checkpoint - IP flagged", "log": self.log}
            elif checkpoint_info["type"] == "rate_limited":
                self._emit("error", f"Rate limited: {checkpoint_info['message']}")
                await self._flush_broadcasts()
                return {"success": False, "error": f"Rate limited: {checkpoint_info['message']}", "log": self.log}
            else:
                # real_checkpoint, sms_verification, etc - try to continue
                self._emit("warning", f"Real checkpoint detected, will attempt to continue")
                await self._flush_broadcasts()
        
        steps = [
            ("fill_email", "Preenchendo email"),
            ("fill_password", "Preenchendo senha"),
            ("click_next", "Clicando Next após email/senha"),
            ("fill_username", "Preenchendo username"),
            ("fill_name", "Preenchendo nome"),
            ("click_next", "Clicando Next após nome"),
            ("fill_birth_date", "Preenchendo data de nascimento"),
            ("click_next", "Clicando Next após data"),
        ]
        
        for step_name, description in steps:
            self._emit("step_started", f"Iniciando: {description}")
            await self._flush_broadcasts()
            
            is_blocked, block_msg = await is_instagram_blocking(page)
            if is_blocked:
                self._emit("warning", f"Blocking detectado: {block_msg}")
                checkpoint = await detect_checkpoint_type(page)
                self._emit("warning", f"Checkpoint type: {checkpoint['type']}")
                await self._flush_broadcasts()
                # Save checkpoint evidence
                if self.account_id:
                    try:
                        screenshot = await page.screenshot(type="png")
                        _save_evidence(self.account_id, f"blocking_{checkpoint['type']}", screenshot)
                        _save_evidence_metadata(self.account_id, f"blocking_{checkpoint['type']}", {
                            "checkpoint_type": checkpoint["type"],
                            "url": page.url,
                            "block_msg": block_msg,
                        })
                    except Exception:
                        pass
                
                # Handle by type
                if checkpoint["type"] in ("interstitial", "false_positive"):
                    self._emit("info", "Interstitial/false-positive - continuing with step")
                    await self._flush_broadcasts()
                    # Continue to execute the step anyway
                elif checkpoint["type"] == "rate_limited":
                    self._emit("error", f"Rate limited: {checkpoint['message']}")
                    await self._flush_broadcasts()
                    return {"success": False, "error": f"Rate limited: {checkpoint['message']}", "log": self.log}
                else:
                    # Real checkpoint - try AI navigation
                    result = await self._ai_navigation_decision(page, context, f"Blocking: {block_msg}, Type: {checkpoint['type']}")
                    if not result.get("success"):
                        self._emit("error", f"Não foi possível resolver blocking: {block_msg}")
                        await self._flush_broadcasts()
                        return {"success": False, "error": f"Instagram blocking: {block_msg}", "log": self.log}
            
            result = await self.execute_step(step_name, page, context)
            
            if not result.get("success"):
                self._emit("error", f"Step {step_name} falhou: {result.get('error', 'Unknown')}")
                await self._flush_broadcasts()
                # Save error screenshot
                if self.account_id:
                    try:
                        screenshot = await page.screenshot(type="png")
                        _save_evidence(self.account_id, f"error_{step_name}", screenshot)
                    except Exception:
                        pass
                return {"success": False, "error": result.get("error", f"Step {step_name} failed"), "log": self.log}
            
            self._emit("step_completed", f"Step {step_name} completado com sucesso")
            await self._flush_broadcasts()
            
            # Save screenshot after each step
            await self._save_step_screenshot(page, f"after_{step_name}")
            
            await HumanBehaviorSimulator.random_delay(config=self.delay_config)
        
        self._emit("info", "Todos os steps completados, extraindo handle...")
        await self._flush_broadcasts()
        await asyncio.sleep(3)
        url = page.url
        import re
        match = re.search(r'instagram\.com/([a-zA-Z0-9_.]+)/', url)
        if match and match.group(1) not in ("accounts", "explore", "reels", "p", "direct"):
            handle = match.group(1)
            self._emit("success", f"Conta criada com sucesso! Handle: @{handle}")
            await self._flush_broadcasts()
            # Save success screenshot
            if self.account_id:
                try:
                    screenshot = await page.screenshot(type="png")
                    _save_evidence(self.account_id, "success", screenshot)
                    _save_evidence_metadata(self.account_id, "success", {
                        "handle": handle,
                        "url": page.url,
                    })
                except Exception:
                    pass
            return {"success": True, "handle": handle, "log": self.log}
        
        if "/feed" in url or "/direct" in url:
            self._emit("success", "Conta criada (handle não extraído, mas na feed/direct)")
            await self._flush_broadcasts()
            return {"success": True, "handle": None, "log": self.log}
        
        checkpoint = await detect_checkpoint_type(page)
        if checkpoint["type"] != "none":
            # If it's just an interstitial or false positive, consider it success
            # since all steps completed successfully
            if checkpoint["type"] in ("interstitial", "false_positive"):
                self._emit("success", "Conta criada com sucesso! (página final detectada)")
                await self._flush_broadcasts()
                # Save success screenshot
                if self.account_id:
                    try:
                        screenshot = await page.screenshot(type="png")
                        _save_evidence(self.account_id, "success", screenshot)
                        _save_evidence_metadata(self.account_id, "success", {
                            "url": page.url,
                            "note": "All steps completed, interstitial page detected",
                        })
                    except Exception:
                        pass
                return {"success": True, "handle": None, "log": self.log}
            
            self._emit("error", f"Checkpoint no final: {checkpoint['type']}")
            await self._flush_broadcasts()
            # Save checkpoint evidence
            if self.account_id:
                try:
                    screenshot = await page.screenshot(type="png")
                    _save_evidence(self.account_id, f"checkpoint_final_{checkpoint['type']}", screenshot)
                    _save_evidence_metadata(self.account_id, f"checkpoint_final_{checkpoint['type']}", {
                        "checkpoint_type": checkpoint["type"],
                        "url": page.url,
                    })
                except Exception:
                    pass
            return {"success": False, "error": f"Checkpoint at end: {checkpoint['type']}", "log": self.log}
        
        self._emit("error", "Não foi possível extrair handle após signup")
        await self._flush_broadcasts()
        return {"success": False, "error": "Could not extract handle after signup", "log": self.log}
    
    def _log(self, message: str):
        entry = {
            "timestamp": datetime.now().isoformat(),
            "message": message,
        }
        self.log.append(entry)
        print(f"[HYBRID] {message}", flush=True)
