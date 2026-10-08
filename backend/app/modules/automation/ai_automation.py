import asyncio
import json
import random
import base64
import os
import time
import hashlib
import re
from datetime import datetime
from typing import Dict, List, Optional
from openai import OpenAI


class ActionCache:
    """Cache de ações em memória com TTL para reduzir chamadas à API Venice"""
    
    def __init__(self):
        self._cache = {}
        self.ttl = int(os.getenv('VENICE_CACHE_TTL', '3600'))
    
    def get(self, screen_hash: str) -> Optional[Dict]:
        cached = self._cache.get(screen_hash)
        if cached and (time.time() - cached['timestamp']) < self.ttl:
            return cached['action']
        return None
    
    def set(self, screen_hash: str, action: Dict):
        self._cache[screen_hash] = {
            'action': action,
            'timestamp': time.time()
        }
    
    def clear(self):
        self._cache.clear()


class FlowState:
    """Gerencia o estado do fluxo de signup do Instagram"""
    
    FLOW_STEPS = [
        {"id": "preencher_email_senha", "description": "Preencher campos de email e senha", "expected_elements": ["input[type='email']", "input[type='password']"]},
        {"id": "clicar_next_email", "description": "Clicar no botão Next após email/senha", "expected_elements": ["button:has-text('Next')", "button:has-text('Sign Up')"]},
        {"id": "preencher_nome", "description": "Preencher campo de nome completo", "expected_elements": ["input[name*='name']", "input[name='fullName']"]},
        {"id": "clicar_next_nome", "description": "Clicar no botão Next após nome", "expected_elements": ["button:has-text('Next')"]},
        {"id": "preencher_data_nascimento", "description": "Preencher data de nascimento", "expected_elements": ["select[name*='birth']", "input[name*='birth']"]},
        {"id": "clicar_next_data", "description": "Clicar no botão Next após data de nascimento", "expected_elements": ["button:has-text('Next')"]},
        {"id": "aguardar_confirmacao", "description": "Aguardar confirmação ou verificação", "expected_elements": [".confirmation", ".verification", "code"]}
    ]
    
    def __init__(self):
        self.current_step_index = 0
        self.completed_steps = []
    
    def get_current_step(self):
        if self.current_step_index < len(self.FLOW_STEPS):
            return self.FLOW_STEPS[self.current_step_index]
        return None
    
    def advance_step(self):
        if self.current_step_index < len(self.FLOW_STEPS) - 1:
            self.completed_steps.append(self.FLOW_STEPS[self.current_step_index]["id"])
            self.current_step_index += 1
            return True
        return False
    
    def get_next_expected_action(self):
        if self.current_step_index < len(self.FLOW_STEPS) - 1:
            return self.FLOW_STEPS[self.current_step_index + 1]["description"]
        return "Verificar se signup completou"
    
    def reset(self):
        self.current_step_index = 0
        self.completed_steps = []


class AIAutomation:
    """Automação de browser guiada por IA com visão e cache de ações"""
    
    MAX_STEPS = 50
    MIN_DELAY = 2
    MAX_DELAY = 5
    TIMEOUT = 600
    
    def __init__(self):
        self.action_cache = ActionCache()
        self.flow_state = FlowState()
        self.client = OpenAI(
            api_key=os.getenv("VENICE_API_KEY"),
            base_url="https://api.venice.ai/api/v1"
        )
        self.model = os.getenv("VENICE_MODEL", "openai-gpt-4o-mini")
        
    async def check_venice_credits(self):
        try:
            return True, "Créditos suficientes (verificação simulada)"
        except Exception as e:
            return True, f"Não foi possível verificar créditos: {str(e)}"
    
    async def execute_signup_flow(self, page, persona_data, email, password):
        steps_log = []
        failed_actions = []
        
        credits_ok, message = await self.check_venice_credits()
        if not credits_ok:
            await self._broadcast("error", message)
            return {"success": False, "error": message, "steps": steps_log}
        
        await self._broadcast("credits_checked", message)
        
        await page.goto("https://www.instagram.com/accounts/emailsignup/", wait_until="domcontentloaded")
        await self._broadcast("navigating", "Indo para página de signup do Instagram")
        
        try:
            step = 0
            while step < self.MAX_STEPS:
                step += 1
                
                screenshot = await page.screenshot(type="jpeg", quality=80)
                
                if await self._check_success(page):
                    handle = await self._extract_handle(page)
                    await self._broadcast("complete", f"Conta criada com sucesso! Handle: {handle}")
                    return {"success": True, "handle": handle, "steps": steps_log}
                
                if await self._detect_captcha(page):
                    await self._broadcast("captcha_detected", "Captcha detectado - tentando resolver")
                    solved = await self._solve_captcha_with_ai(page, screenshot)
                    if solved:
                        steps_log.append({"step": step, "action": "captcha_solved"})
                        continue
                    else:
                        await self._broadcast("error", "Não foi possível resolver o captcha")
                        return {"success": False, "error": "Captcha não resolvido - requer serviço externo", "steps": steps_log}
                
                screen_hash = await self._generate_screen_hash(screenshot)
                cached_action = self.action_cache.get(screen_hash)
                
                if cached_action:
                    action = cached_action
                    steps_log.append({"step": step, "action": action["type"], "detail": f"{action['description']} (cacheado)"})
                else:
                    action = await self._analyze_and_get_action(screenshot, page.url, persona_data, email, password, failed_actions)
                    if action.get("cacheable", True):
                        self.action_cache.set(screen_hash, action)
                
                try:
                    await self._execute_action(page, action)
                    steps_log.append({"step": step, "action": action["type"], "detail": action["description"]})
                    
                    current_step = self.flow_state.get_current_step()
                    if current_step and await self._is_current_step_completed(page, current_step):
                        self.flow_state.advance_step()
                        await self._broadcast("step_completed", f"Passo {current_step['description']} completado")
                        failed_actions.clear()
                    else:
                        failed_actions.append(action)
                        if len(failed_actions) >= 8:
                            await self._broadcast("error", "Muitas ações sem progresso - possível loop detectado")
                            return {"success": False, "error": "Loop detectado - ações não estão progredindo", "steps": steps_log}
                    
                    await self._broadcast("step_executed", f"Passo {step}: {action['description']}")
                    await self._broadcast("url_update", f"URL atual: {page.url}")
                    
                    delay = random.uniform(self.MIN_DELAY, self.MAX_DELAY)
                    await asyncio.sleep(delay)
                    
                except Exception as e:
                    failed_actions.append(action)
                    steps_log.append({"step": step, "action": "failed", "detail": f"Falha ao executar: {str(e)}"})
                    await self._broadcast("step_failed", f"Passo {step} falhou: {str(e)}")
            
            return {"success": False, "error": "Limite de passos atingido", "steps": steps_log}
            
        except asyncio.TimeoutError:
            await self._broadcast("error", "Automação interrompida por timeout (10 minutos)")
            return {"success": False, "error": "Automação interrompida por timeout", "steps": steps_log}
        except Exception as e:
            await self._broadcast("error", f"Erro na automação: {str(e)}")
            return {"success": False, "error": f"Erro na automação: {str(e)}", "steps": steps_log}
    
    async def _generate_screen_hash(self, screenshot_bytes) -> str:
        return hashlib.md5(screenshot_bytes).hexdigest()
    
    async def _detect_field_errors(self, page):
        for selector in ["[role='alert']", ".error-message", ".field-error", "[aria-invalid='true']", ".error-text"]:
            error_element = page.locator(selector).first
            if await error_element.count() > 0:
                try:
                    error_text = await error_element.text_content()
                    if error_text and len(error_text.strip()) > 0:
                        return True, error_text.strip()
                except:
                    pass
        return False, None
    
    async def _is_current_step_completed(self, page, current_step) -> bool:
        step_id = current_step["id"]
        
        if step_id == "preencher_email_senha":
            email_input = page.locator("input[type='email']").first
            password_input = page.locator("input[type='password']").first
            
            if await email_input.count() > 0 and await password_input.count() > 0:
                try:
                    email_value = await email_input.input_value()
                    password_value = await password_input.input_value()
                    has_error, _ = await self._detect_field_errors(page)
                    return bool(email_value and password_value and not has_error)
                except:
                    return False
        
        elif step_id == "preencher_nome":
            name_input = page.locator("input[name*='name']").first
            if await name_input.count() > 0:
                try:
                    name_value = await name_input.input_value()
                    has_error, _ = await self._detect_field_errors(page)
                    return bool(name_value and not has_error)
                except:
                    return False
        
        elif step_id in ("clicar_next_email", "clicar_next_nome", "clicar_next_data"):
            await asyncio.sleep(1)
            current_url = page.url
            if "/accounts/emailsignup" not in current_url and "/accounts/" not in current_url:
                return True
            return False
        
        return False
    
    async def _analyze_and_get_action(self, screenshot_bytes, url, persona_data, email, password, failed_actions=None):
        failed_actions = failed_actions or []
        
        base64_image = base64.b64encode(screenshot_bytes).decode("utf-8")
        failed_actions_str = "\n".join([f"- {a.get('description', a.get('type', 'unknown'))}" for a in failed_actions])
        
        current_step = self.flow_state.get_current_step()
        completed_steps = self.flow_state.completed_steps
        next_expected_action = self.flow_state.get_next_expected_action()
        
        current_step_desc = current_step["description"] if current_step else "Verificação final"
        current_elements = ', '.join(current_step["expected_elements"]) if current_step else "N/A"
        completed_str = ', '.join(completed_steps)
        
        prompt = f"""Você está automatizando a criação de uma conta no Instagram.

URL atual: {url}
Dados da persona:
- Nome: {persona_data.first_name} {persona_data.last_name}
- Email: {email}
- Senha: {password}
- Data de nascimento: {persona_data.birth_date}

ESTADO DO FLUXO:
Passo atual esperado: {current_step_desc}
Elementos esperados nesta etapa: {current_elements}
Passos já completados: {completed_str}
Próxima ação esperada: {next_expected_action}

AÇÕES REPETIDAS DETECTADAS (EVITAR REPETIR):
{failed_actions_str}

ATENÇÃO: Se você já tentou a mesma ação 3 vezes sem sucesso, mude de estratégia:
1. Verifique se há mensagens de erro na tela
2. Tente fazer scroll para encontrar elementos escondidos
3. Aguarde a página carregar completamente
4. Tente um seletor CSS diferente

Analise a screenshot e retorne a PRÓXIMA ação como JSON:
{{
  "type": "click" | "type" | "scroll" | "wait" | "select",
  "target": "seletor CSS ou descrição do elemento",
  "value": "texto para digitar (se type)",
  "description": "descrição em português do que está fazendo",
  "cacheable": true/false
}}

Regras:
- Foque nos elementos esperados para o passo atual: {current_elements}
- Se os elementos esperados não estão visíveis, faça scroll e aguarde
- EVITE ações que já foram tentadas sem sucesso
- Use seletores CSS específicos quando possível
- Se o campo já está preenchido, avance para o próximo passo
"""
        
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
        
        return json.loads(response.choices[0].message.content)
    
    async def _execute_action(self, page, action):
        action_type = action["type"]
        target = action.get("target", "")
        max_retries = 2
        
        for attempt in range(max_retries):
            try:
                if action_type == "click":
                    if target.startswith(("input[", "button[", "select[", "textarea[", ".", "#")):
                        locator = page.locator(target).first
                        if await locator.count() > 0:
                            await locator.click()
                        else:
                            await page.wait_for_timeout(2000)
                            locator = page.locator(target).first
                            if await locator.count() > 0:
                                await locator.click()
                    else:
                        btn = page.get_by_role("button", name=target)
                        if await btn.count() > 0:
                            await btn.click()
                        else:
                            await page.get_by_text(target).first.click()
                
                elif action_type == "type":
                    if target.startswith(("input[", "button[", "select[", "textarea[", ".", "#")):
                        locator = page.locator(target).first
                        if await locator.count() > 0:
                            await locator.fill(action.get("value", ""))
                        else:
                            await page.locator("input:visible, textarea:visible").first.fill(action.get("value", ""))
                    else:
                        await page.get_by_label(target).first.fill(action.get("value", ""))
                
                elif action_type == "scroll":
                    await page.mouse.wheel(0, 300)
                
                elif action_type == "wait":
                    await asyncio.sleep(2)
                
                elif action_type == "select":
                    await page.locator(target).select_option(action.get("value", ""))
                
                return
                
            except Exception as e:
                if attempt == max_retries - 1:
                    raise e
                await asyncio.sleep(1)
    
    async def _check_success(self, page):
        url = page.url
        success_indicators = ["/feed", "/direct", "/explore", "/stories"]
        for indicator in success_indicators:
            if indicator in url:
                return True
        
        match = re.search(r'instagram\.com/([a-zA-Z0-9_.]+)/', url)
        if match and match.group(1) not in ("accounts", "explore", "reels", "p", "direct"):
            return True
        return False
    
    async def _extract_handle(self, page):
        url = page.url
        match = re.search(r'instagram\.com/([a-zA-Z0-9_.]+)/', url)
        if match:
            return match.group(1)
        return None
    
    async def _detect_captcha(self, page):
        selectors = [
            'iframe[src*="recaptcha"]',
            'iframe[src*="hcaptcha"]',
            '[data-sitekey]',
            '.g-recaptcha',
            '.captcha',
            '#captcha'
        ]
        for selector in selectors:
            if await page.locator(selector).count() > 0:
                return True
        return False
    
    async def _solve_captcha_with_ai(self, page, screenshot):
        try:
            base64_image = base64.b64encode(screenshot).decode("utf-8")
            
            prompt = """Analise esta imagem e identifique se há um captcha. 
            Se houver, descreva o tipo e como resolvê-lo.
            Responda em JSON:
            {
              "has_captcha": true/false,
              "type": "text/image/checkbox",
              "solution": "descrição da solução ou texto do captcha"
            }
            """
            
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
            
            result = json.loads(response.choices[0].message.content)
            
            if result.get("has_captcha"):
                captcha_type = result.get("type")
                
                if captcha_type == "checkbox":
                    checkbox = page.locator('.recaptcha-checkbox').first
                    if await checkbox.count() > 0:
                        await checkbox.click()
                        await asyncio.sleep(3)
                        return True
                
                elif captcha_type == "text":
                    solution = result.get("solution")
                    if solution:
                        captcha_input = page.locator('input[name*="captcha"]').first
                        if await captcha_input.count() > 0:
                            await captcha_input.fill(solution)
                            await page.locator('button[type="submit"]').first.click()
                            await asyncio.sleep(3)
                            return True
            
            return False
            
        except Exception:
            return False
    
    async def _broadcast(self, event_type, detail):
        import sys
        print(f"[AI-AUTOMATION] {event_type}: {detail}", flush=True, file=sys.stderr)
        try:
            from app.api.websocket_manager import manager
            await manager.broadcast({
                "type": event_type, 
                "detail": detail, 
                "timestamp": datetime.now().isoformat()
            })
        except ImportError:
            pass
