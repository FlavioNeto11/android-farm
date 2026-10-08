from fastapi import APIRouter, HTTPException, BackgroundTasks
from typing import List, Optional
import asyncio
import json
import logging
import os
import random
import sys
import threading
from datetime import datetime

from app.db import get_db_context
from app.models import Account, AccountStatus, Proxy as ProxyModel, ProxyStatus as PS
from app.services.android_persona_client import android_client

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/personas", tags=["personas"])


@router.get("/")
async def list_personas():
    personas = await android_client.list_personas()
    return personas


@router.get("/{persona_id}")
async def get_persona(persona_id: str):
    persona = await android_client.get_persona(persona_id)
    if not persona:
        raise HTTPException(404, "Persona not found")
    return persona


@router.get("/{persona_id}/image")
async def get_persona_image(persona_id: str):
    image_url = await android_client.get_persona_image_url(persona_id)
    return {"image_url": image_url}


@router.post("/{persona_id}/create-account")
async def create_account_for_persona(persona_id: str):
    persona = await android_client.get_persona(persona_id)
    if not persona:
        raise HTTPException(404, "Persona not found")

    first_names = ["maria", "joao", "ana", "pedro", "carla", "lucas", "julia", "gabriel", "rafael", "camila"]
    last_names = ["silva", "santos", "oliveira", "pereira", "costa", "ferreira", "almeida", "rocha"]
    domains = ["gmail.com", "outlook.com", "yahoo.com", "hotmail.com"]

    first = persona.get("first_name") or random.choice(first_names)
    last = persona.get("last_name") or random.choice(last_names)
    number = random.randint(100, 999)
    domain = random.choice(domains)
    email = f"{first}.{last}{number}@{domain}"
    password = f"{first.capitalize()}{last.capitalize()}{number}!"

    birth_date = persona.get("birth_date", "1995-01-01")

    with get_db_context() as db:
        account = Account(
            platform="instagram",
            profile_id=persona_id,
            status=AccountStatus.creating
        )
        db.add(account)
        db.commit()
        db.refresh(account)

    account_id_str = str(account.id)

    def run_automation_sync():
        """Run Playwright automation in a separate thread with ProactorEventLoop"""
        if sys.platform == "win32":
            asyncio.set_event_loop_policy(asyncio.WindowsProactorEventLoopPolicy())

        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        try:
            loop.run_until_complete(_run_instagram_automation(
                account_id_str, persona_id, first, last, email, password, birth_date
            ))
        finally:
            loop.close()

    async def _run_instagram_automation(account_id_str, persona_id, first, last, email, password, birth_date):
        from app.modules.accounts.platforms.instagram.hybrid_flow import HybridInstagramFlow
        from app.modules.accounts.platforms.instagram.human_behavior import HumanBehaviorSimulator
        from app.modules.accounts.platforms.instagram.proxy_config import load_proxy_from_env, ProxyConfig
        from app.modules.browsers.domain.browser_profile import get_browser_manager
        from app.api.websocket_manager import manager

        try:
            await manager.broadcast({
                "account_id": account_id_str,
                "type": "step_started",
                "detail": f"Iniciando criação da conta para {first} {last}",
                "timestamp": datetime.utcnow().isoformat()
            })

            browser_manager = get_browser_manager()
            viewport = HumanBehaviorSimulator.get_random_viewport()

            proxy_config = load_proxy_from_env()
            if not proxy_config:
                with get_db_context() as db_proxy:
                    active_proxy = db_proxy.query(ProxyModel).filter(
                        ProxyModel.status == PS.active,
                        ProxyModel.failed_count < 5
                    ).order_by(ProxyModel.used_count.asc()).first()
                    if active_proxy:
                        proxy_config = ProxyConfig(
                            host=active_proxy.host,
                            port=active_proxy.port,
                            username=active_proxy.username or "",
                            password=active_proxy.password_ref or ""
                        )
                        active_proxy.used_count += 1
                        db_proxy.commit()

            context_kwargs = {
                "account_id": persona_id,
                "viewport_size": viewport,
            }
            if proxy_config:
                context_kwargs["proxy_host"] = proxy_config.host
                context_kwargs["proxy_port"] = proxy_config.port
                context_kwargs["proxy_username"] = proxy_config.username
                context_kwargs["proxy_password"] = proxy_config.password
                await manager.broadcast({
                    "account_id": account_id_str,
                    "type": "step_completed",
                    "detail": f"Proxy configurado: {proxy_config.host}:{proxy_config.port}",
                    "timestamp": datetime.utcnow().isoformat()
                })

            await manager.broadcast({
                "account_id": account_id_str,
                "type": "step_executed",
                "detail": "Iniciando navegador...",
                "timestamp": datetime.utcnow().isoformat()
            })

            context = await browser_manager.create_context(**context_kwargs)
            page = await context.new_page()

            user_agent = HumanBehaviorSimulator.get_random_user_agent()
            await page.set_extra_http_headers({"User-Agent": user_agent})

            await manager.broadcast({
                "account_id": account_id_str,
                "type": "step_executed",
                "detail": "Navegando para Instagram signup...",
                "timestamp": datetime.utcnow().isoformat()
            })

            await page.goto("https://www.instagram.com/accounts/emailsignup/", wait_until="domcontentloaded", timeout=60000)

            await manager.broadcast({
                "account_id": account_id_str,
                "type": "step_completed",
                "detail": "Página de signup carregada",
                "timestamp": datetime.utcnow().isoformat()
            })

            flow = HybridInstagramFlow(account_id=account_id_str)
            flow_context = {
                "email": email,
                "password": password,
                "first_name": first,
                "last_name": last,
                "birth_date": birth_date,
            }

            await manager.broadcast({
                "account_id": account_id_str,
                "type": "step_executed",
                "detail": "Executando fluxo de criação...",
                "timestamp": datetime.utcnow().isoformat()
            })

            result = await asyncio.wait_for(
                flow.execute_full_flow(page, flow_context),
                timeout=600
            )

            automation_log = json.dumps(result.get("log", []))

            with get_db_context() as db2:
                acc = db2.query(Account).filter(Account.id == account.id).first()
                if acc:
                    acc.automation_log = automation_log
                    if result.get("success"):
                        acc.handle = result.get("handle", email)
                        acc.status = AccountStatus.ready
                        await manager.broadcast({
                            "account_id": account_id_str,
                            "type": "complete",
                            "detail": f"Conta criada com sucesso! @{result.get('handle', 'handle não capturado')}",
                            "timestamp": datetime.utcnow().isoformat()
                        })
                    else:
                        acc.status = AccountStatus.failed
                        acc.error_message = result.get("error", "Hybrid automation failed")
                        await manager.broadcast({
                            "account_id": account_id_str,
                            "type": "error",
                            "detail": f"Falha: {acc.error_message}",
                            "timestamp": datetime.utcnow().isoformat()
                        })
                    db2.commit()

        except asyncio.TimeoutError:
            with get_db_context() as db2:
                acc = db2.query(Account).filter(Account.id == account.id).first()
                if acc:
                    acc.status = AccountStatus.failed
                    acc.error_message = "Timeout na automação (10 minutos)"
                    db2.commit()
            try:
                await manager.broadcast({
                    "account_id": account_id_str,
                    "type": "error",
                    "detail": "Timeout na automação",
                    "timestamp": datetime.utcnow().isoformat()
                })
            except Exception:
                pass

        except NotImplementedError as e:
            error_detail = f"Playwright não suportado neste ambiente: {str(e)}. Instale browsers: playwright install chromium"
            logger.error(f"Playwright error: {error_detail}")
            with get_db_context() as db2:
                acc = db2.query(Account).filter(Account.id == account.id).first()
                if acc:
                    acc.status = AccountStatus.failed
                    acc.error_message = error_detail
                    db2.commit()
            try:
                await manager.broadcast({
                    "account_id": account_id_str,
                    "type": "error",
                    "detail": error_detail,
                    "timestamp": datetime.utcnow().isoformat()
                })
            except Exception:
                pass

        except Exception as e:
            import traceback
            error_detail = f"Erro na automação: {str(e)}"
            logger.error(f"AI automation failed: {error_detail}\n{traceback.format_exc()}")
            with get_db_context() as db2:
                acc = db2.query(Account).filter(Account.id == account.id).first()
                if acc:
                    acc.status = AccountStatus.failed
                    acc.error_message = error_detail
                    db2.commit()
            try:
                await manager.broadcast({
                    "account_id": account_id_str,
                    "type": "error",
                    "detail": error_detail,
                    "timestamp": datetime.utcnow().isoformat()
                })
            except Exception:
                pass

        finally:
            try:
                await context.close()
            except Exception:
                pass

    thread = threading.Thread(target=run_automation_sync, daemon=True)
    thread.start()

    return {
        "account_id": account_id_str,
        "persona_id": persona_id,
        "email": email,
        "status": "creating",
        "message": "Account creation started. Check WebSocket for progress."
    }
