"""Rotas de automação IA para Instagram"""
from fastapi import APIRouter, HTTPException, status
from pydantic import BaseModel
from typing import Optional
import asyncio
import logging
import os

from app.db import get_db_context
from app.models import Account, AccountStatus, Proxy as ProxyModel, ProxyStatus as PS

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/instagram", tags=["instagram-automation"])


class CreateAccountAIRequest(BaseModel):
    platform: str = "instagram"
    use_proxy: bool = True
    proxy_session_id: Optional[str] = None
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    birth_date: Optional[str] = None
    gender: Optional[str] = None


@router.post("/create-account-ai", status_code=status.HTTP_202_ACCEPTED)
async def create_account_ai(req: CreateAccountAIRequest):
    """Criar conta Instagram usando automação IA com proxy"""
    try:
        with get_db_context() as db:
            account = Account(
                platform="instagram",
                profile_id=req.proxy_session_id or f"session_{int(__import__('time').time())}",
                status=AccountStatus.creating
            )
            db.add(account)
            db.commit()
            db.refresh(account)

            async def run_instagram_automation():
                import random
                from app.modules.accounts.platforms.instagram.hybrid_flow import HybridInstagramFlow
                from app.modules.accounts.platforms.instagram.human_behavior import HumanBehaviorSimulator
                from app.modules.accounts.platforms.instagram.proxy_config import load_proxy_from_env, ProxyConfig
                from app.modules.browsers.domain.browser_profile import get_browser_manager
                from app.api.websocket_manager import manager

                first_names = ["maria", "joao", "ana", "pedro", "carla", "lucas", "julia", "gabriel", "rafael", "camila"]
                last_names = ["silva", "santos", "oliveira", "pereira", "costa", "ferreira", "almeida", "rocha"]
                domains = ["gmail.com", "outlook.com", "yahoo.com", "hotmail.com"]

                random.seed(hash(account.profile_id) % (2**32))
                first = req.first_name or random.choice(first_names)
                last = req.last_name or random.choice(last_names)
                number = random.randint(100, 999)
                domain = random.choice(domains)
                email = f"{first}.{last}{number}@{domain}"
                password = f"{first.capitalize()}{last.capitalize()}{number}!"

                await manager.broadcast({
                    "account_id": str(account.id),
                    "type": "step_executed",
                    "detail": f"Iniciando criação da conta para {first} {last}",
                    "timestamp": __import__('datetime').datetime.utcnow().isoformat()
                })

                browser_manager = get_browser_manager()
                viewport = HumanBehaviorSimulator.get_random_viewport()

                proxy_config = None
                if req.use_proxy:
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
                    "account_id": account.profile_id,
                    "viewport_size": viewport,
                }
                if proxy_config:
                    context_kwargs["proxy_host"] = proxy_config.host
                    context_kwargs["proxy_port"] = proxy_config.port
                    context_kwargs["proxy_username"] = proxy_config.username
                    context_kwargs["proxy_password"] = proxy_config.password
                    await manager.broadcast({
                        "account_id": str(account.id),
                        "type": "step_completed",
                        "detail": f"Proxy configurado: {proxy_config.host}:{proxy_config.port}",
                        "timestamp": __import__('datetime').datetime.utcnow().isoformat()
                    })

                context = await browser_manager.create_context(**context_kwargs)
                page = await context.new_page()

                user_agent = HumanBehaviorSimulator.get_random_user_agent()
                await page.set_extra_http_headers({"User-Agent": user_agent})

                try:
                    await manager.broadcast({
                        "account_id": str(account.id),
                        "type": "step_executed",
                        "detail": "Navegando para Instagram signup...",
                        "timestamp": __import__('datetime').datetime.utcnow().isoformat()
                    })

                    await page.goto("https://www.instagram.com/accounts/emailsignup/", wait_until="domcontentloaded", timeout=60000)

                    await manager.broadcast({
                        "account_id": str(account.id),
                        "type": "step_completed",
                        "detail": "Página de signup carregada",
                        "timestamp": __import__('datetime').datetime.utcnow().isoformat()
                    })

                    flow = HybridInstagramFlow()
                    flow_context = {
                        "email": email,
                        "password": password,
                        "first_name": first,
                        "last_name": last,
                        "birth_date": req.birth_date or "1995-01-01",
                    }

                    await manager.broadcast({
                        "account_id": str(account.id),
                        "type": "step_executed",
                        "detail": "Executando fluxo de criação...",
                        "timestamp": __import__('datetime').datetime.utcnow().isoformat()
                    })

                    result = await asyncio.wait_for(
                        flow.execute_full_flow(page, flow_context),
                        timeout=600
                    )

                    with get_db_context() as db2:
                        acc = db2.query(Account).filter(Account.id == account.id).first()
                        if acc:
                            if result.get("success"):
                                acc.handle = result.get("handle", email)
                                acc.status = AccountStatus.ready
                                await manager.broadcast({
                                    "account_id": str(account.id),
                                    "type": "complete",
                                    "detail": "Conta criada com sucesso!",
                                    "timestamp": __import__('datetime').datetime.utcnow().isoformat()
                                })
                            else:
                                acc.status = AccountStatus.failed
                                acc.error_message = result.get("error", "Hybrid automation failed")
                                await manager.broadcast({
                                    "account_id": str(account.id),
                                    "type": "error",
                                    "detail": f"Falha: {acc.error_message}",
                                    "timestamp": __import__('datetime').datetime.utcnow().isoformat()
                                })
                            db2.commit()

                except asyncio.TimeoutError:
                    with get_db_context() as db2:
                        acc = db2.query(Account).filter(Account.id == account.id).first()
                        if acc:
                            acc.status = AccountStatus.failed
                            acc.error_message = "Timeout na automação (10 minutos)"
                            db2.commit()
                    await manager.broadcast({
                        "account_id": str(account.id),
                        "type": "error",
                        "detail": "Timeout na automação",
                        "timestamp": __import__('datetime').datetime.utcnow().isoformat()
                    })

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
                    await manager.broadcast({
                        "account_id": str(account.id),
                        "type": "error",
                        "detail": error_detail,
                        "timestamp": __import__('datetime').datetime.utcnow().isoformat()
                    })

                finally:
                    await context.close()

            asyncio.create_task(run_instagram_automation())

            return {
                "account_id": str(account.id),
                "platform": "instagram",
                "status": "creating",
                "message": "AI automation started"
            }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Create account AI failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )
