"""Rotas de gerenciamento de contas"""
from fastapi import APIRouter, HTTPException, status
from pydantic import BaseModel
from sqlalchemy.orm import Session
from typing import List, Optional
import asyncio
import json
import logging
import os
from datetime import datetime, timedelta

from app.db import get_db_context
from app.modules.accounts.application.account_service import get_account_service
from app.modules.accounts.domain.account import PersonaData
from app.models import Account, AccountStatus, Credential
from app.security.secret_store import get_secret_store

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/accounts", tags=["accounts"])


class AccountCreationRequest(BaseModel):
    profile_id: str
    platforms: List[str]
    persona_data: dict


@router.post("/request", status_code=status.HTTP_202_ACCEPTED)
async def request_account_creation(request: AccountCreationRequest):
    """Solicitar criação de conta(s) para uma persona"""
    try:
        with get_db_context() as db:
            service = get_account_service()
            
            if "instagram" in request.platforms and len(request.platforms) == 1:
                account = Account(
                    platform="instagram",
                    profile_id=request.profile_id,
                    status=AccountStatus.creating
                )
                db.add(account)
                db.commit()
                db.refresh(account)
                
                async def create_instagram_with_ai():
                    import random
                    headless = os.getenv("BROWSER_HEADLESS", "false").lower() == "true"
                    from app.modules.accounts.platforms.instagram.hybrid_flow import HybridInstagramFlow
                    from app.modules.accounts.platforms.instagram.human_behavior import HumanBehaviorSimulator
                    from app.modules.accounts.platforms.instagram.proxy_config import load_proxy_from_env, ProxyConfig
                    from app.modules.browsers.domain.browser_profile import get_browser_manager
                    from app.api.websocket_manager import manager
                    
                    acct_id_str = str(account.id)
                    
                    first_names = ["maria", "joao", "ana", "pedro", "carla", "lucas", "julia", "gabriel", "rafael", "camila"]
                    last_names = ["silva", "santos", "oliveira", "pereira", "costa", "ferreira", "almeida", "rocha"]
                    domains = ["gmail.com", "outlook.com", "yahoo.com", "hotmail.com"]
                    
                    random.seed(hash(account.profile_id) % (2**32))
                    first = random.choice(first_names)
                    last = random.choice(last_names)
                    number = random.randint(100, 999)
                    domain = random.choice(domains)
                    realistic_email = f"{first}.{last}{number}@{domain}"
                    realistic_password = f"{first.capitalize()}{last.capitalize()}{number}!"
                    
                    await manager.broadcast({
                        "account_id": acct_id_str,
                        "type": "step_started",
                        "detail": f"Iniciando criação da conta para {first} {last}",
                        "timestamp": datetime.utcnow().isoformat()
                    })
                    
                    browser_manager = get_browser_manager()
                    viewport = HumanBehaviorSimulator.get_random_viewport()
                    
                    proxy_config = load_proxy_from_env()
                    if not proxy_config:
                        with get_db_context() as db_proxy:
                            from app.models import Proxy as ProxyModel, ProxyStatus as PS
                            active_proxy = db_proxy.query(ProxyModel).filter(ProxyModel.status == PS.active, ProxyModel.failed_count < 5).order_by(ProxyModel.used_count.asc()).first()
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
                            "account_id": acct_id_str,
                            "type": "step_completed",
                            "detail": f"Proxy configurado: {proxy_config.host}:{proxy_config.port}",
                            "timestamp": datetime.utcnow().isoformat()
                        })
                    
                    context = await browser_manager.create_context(**context_kwargs)
                    page = await context.new_page()
                    
                    user_agent = HumanBehaviorSimulator.get_random_user_agent()
                    await page.set_extra_http_headers({"User-Agent": user_agent})
                    
                    try:
                        await manager.broadcast({
                            "account_id": acct_id_str,
                            "type": "step_executed",
                            "detail": "Navegando para Instagram signup...",
                            "timestamp": datetime.utcnow().isoformat()
                        })
                        
                        await page.goto("https://www.instagram.com/accounts/emailsignup/", wait_until="domcontentloaded", timeout=60000)
                        
                        await manager.broadcast({
                            "account_id": acct_id_str,
                            "type": "step_completed",
                            "detail": "Página de signup carregada",
                            "timestamp": datetime.utcnow().isoformat()
                        })
                        
                        flow = HybridInstagramFlow(account_id=acct_id_str)
                        
                        flow_context = {
                            "email": realistic_email,
                            "password": realistic_password,
                            "first_name": request.persona_data.get("first_name", first),
                            "last_name": request.persona_data.get("last_name", last),
                            "birth_date": request.persona_data.get("birth_date", "1995-01-01"),
                        }
                        
                        result = await asyncio.wait_for(
                            flow.execute_full_flow(page, flow_context),
                            timeout=600
                        )
                        
                        automation_log = json.dumps(result.get("log", []))
                        
                        with get_db_context() as db2:
                            acc = db2.query(Account).filter(Account.id == account.id).first()
                            if acc:
                                acc.automation_log = automation_log
                                if result["success"]:
                                    acc.handle = result.get("handle", realistic_email)
                                    acc.status = AccountStatus.ready
                                    await manager.broadcast({
                                        "account_id": acct_id_str,
                                        "type": "complete",
                                        "detail": f"Conta criada com sucesso! @{result.get('handle', 'handle não capturado')}",
                                        "timestamp": datetime.utcnow().isoformat()
                                    })
                                else:
                                    acc.status = AccountStatus.failed
                                    acc.error_message = result.get("error", "Hybrid automation failed")
                                    await manager.broadcast({
                                        "account_id": acct_id_str,
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
                                acc.error_message = "Automação interrompida por timeout (10 minutos)"
                                db2.commit()
                        await manager.broadcast({
                            "account_id": acct_id_str,
                            "type": "error",
                            "detail": "Timeout na automação",
                            "timestamp": datetime.utcnow().isoformat()
                        })
                    
                    except Exception as e:
                        import traceback
                        error_detail = f"Exception during automation: {str(e)}"
                        logger.error(f"AI automation failed: {error_detail}\n{traceback.format_exc()}")
                        with get_db_context() as db2:
                            acc = db2.query(Account).filter(Account.id == account.id).first()
                            if acc:
                                acc.status = AccountStatus.failed
                                acc.error_message = error_detail
                                db2.commit()
                        await manager.broadcast({
                            "account_id": acct_id_str,
                            "type": "error",
                            "detail": error_detail,
                            "timestamp": datetime.utcnow().isoformat()
                        })
                    
                    finally:
                        await context.close()
                
                asyncio.create_task(create_instagram_with_ai())
                
                return {
                    "account_id": account.id,
                    "platform": account.platform,
                    "status": account.status.value,
                    "message": "Account creation request submitted - AI automation started"
                }
            else:
                account = await service.request_account_creation(
                    db=db,
                    profile_id=request.profile_id,
                    platforms=request.platforms,
                    persona_data=request.persona_data
                )

                if not account:
                    raise HTTPException(
                        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                        detail="No valid account platforms found"
                    )

                return {
                    "account_id": account.id,
                    "platform": account.platform,
                    "status": account.status.value,
                    "message": "Account creation request submitted"
                }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Account creation request failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )


@router.get("/{account_id}")
async def get_account(account_id: str):
    """Obter status de uma conta"""
    with get_db_context() as db:
        service = get_account_service()
        account = service.get_account(db, account_id)

        if not account:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Account not found"
            )

        return {
            "id": account.id,
            "platform": account.platform,
            "handle": account.handle,
            "status": account.status.value,
            "profile_id": account.profile_id,
            "created_at": account.created_at.isoformat() if account.created_at else None,
            "updated_at": account.updated_at.isoformat() if account.updated_at else None,
            "error_message": account.error_message
        }


@router.get("")
async def list_accounts(
    platform: Optional[str] = None,
    status: Optional[str] = None,
    profile_id: Optional[str] = None
):
    """Listar contas com filtros opcionais"""
    with get_db_context() as db:
        service = get_account_service()
        accounts = service.list_accounts(
            db=db,
            platform=platform,
            status=status,
            profile_id=profile_id
        )

        return {
            "accounts": [
                {
                    "id": a.id,
                    "platform": a.platform,
                    "handle": a.handle,
                    "status": a.status.value,
                    "profile_id": a.profile_id,
                    "created_at": a.created_at.isoformat() if a.created_at else None,
                }
                for a in accounts
            ],
            "total": len(accounts)
        }


@router.post("/{account_id}/assign")
async def assign_account(account_id: str, profile_id: str):
    """Atribuir conta a uma persona"""
    try:
        with get_db_context() as db:
            service = get_account_service()
            success = service.assign_account(db=db, account_id=account_id, profile_id=profile_id)

            if not success:
                raise HTTPException(
                    status_code=status.HTTP_409_CONFLICT,
                    detail="Persona already has a ready account"
                )

            return {
                "message": "Account assigned successfully",
                "account_id": account_id,
                "profile_id": profile_id
            }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Account assignment failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )


@router.delete("/{account_id}")
async def delete_account(account_id: str):
    """Deletar conta"""
    with get_db_context() as db:
        service = get_account_service()
        success = service.delete_account(db=db, account_id=account_id)

        if not success:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Account not found"
            )

        return {
            "message": "Account deleted successfully",
            "account_id": account_id
        }


@router.get("/{account_id}/credentials")
async def get_account_credentials(account_id: str):
    """Obter credenciais descriptografadas de uma conta"""
    with get_db_context() as db:
        account = db.query(Account).filter(Account.id == account_id).first()
        if not account:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Account not found")

        credential = db.query(Credential).filter(Credential.account_id == account_id).first()
        if not credential:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Credential not found")

        try:
            secret_store = get_secret_store()
            password = secret_store.decrypt(credential.secret_ref)
            return {
                "email": credential.login_identifier,
                "password": password,
                "platform": account.platform,
            }
        except Exception as e:
            logger.error(f"Failed to decrypt credential: {e}")
            raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Failed to decrypt credential")


@router.get("/{account_id}/evidence")
async def get_account_evidence(account_id: str):
    """Obter evidências de uma conta (screenshots, logs)"""
    from pathlib import Path
    evidence_dir = Path("./data/evidence")
    evidence_dir.mkdir(parents=True, exist_ok=True)
    evidence_files = []

    for f in evidence_dir.iterdir():
        if f.name.startswith(account_id):
            if f.suffix in (".png", ".jpg", ".jpeg"):
                evidence_files.append({
                    "account_id": account_id,
                    "evidence_type": "screenshot",
                    "filename": f.name,
                    "timestamp": "",
                    "screenshot_url": f"/api/evidence/{f.name}",
                    "description": f"Evidência: {f.name}",
                })
            elif f.suffix == ".json":
                try:
                    data = json.loads(f.read_text())
                    evidence_files.append({
                        "account_id": account_id,
                        "evidence_type": "metadata",
                        "filename": f.name,
                        "step": data.get("step", ""),
                        "timestamp": data.get("timestamp", ""),
                        "description": f"Metadata: {data.get('step', '')}",
                    })
                except json.JSONDecodeError:
                    pass

    evidence_files.sort(key=lambda x: x.get("timestamp", x.get("filename", "")), reverse=True)
    return evidence_files


@router.get("/{account_id}/automation-log")
async def get_account_automation_log(account_id: str):
    """Retorna log de automação de uma conta"""
    with get_db_context() as db:
        account = db.query(Account).filter(Account.id == account_id).first()
        if not account:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Account not found")

        automation_log = []
        if account.automation_log:
            try:
                automation_log = json.loads(account.automation_log)
            except json.JSONDecodeError:
                automation_log = []

        return {
            "account_id": account_id,
            "status": account.status.value if hasattr(account.status, 'value') else account.status,
            "handle": account.handle,
            "error_message": account.error_message,
            "log": automation_log,
            "created_at": account.created_at.isoformat() if account.created_at else None,
            "updated_at": account.updated_at.isoformat() if account.updated_at else None,
        }


@router.post("/cleanup-stuck")
async def cleanup_stuck_accounts(minutes_threshold: int = 30):
    """Marca contas stuck em 'creating' há mais de X minutos como 'failed'"""
    with get_db_context() as db:
        threshold = datetime.utcnow() - timedelta(minutes=minutes_threshold)
        stuck_accounts = db.query(Account).filter(
            Account.status == AccountStatus.creating,
            Account.created_at < threshold
        ).all()

        cleaned = []
        for acc in stuck_accounts:
            acc.status = AccountStatus.failed
            acc.error_message = f"Stuck - timeout não detectado após {minutes_threshold} minutos"
            cleaned.append({
                "account_id": acc.id,
                "platform": acc.platform,
                "profile_id": acc.profile_id,
                "created_at": acc.created_at.isoformat() if acc.created_at else None,
            })

        db.commit()

        return {
            "cleaned_count": len(cleaned),
            "minutes_threshold": minutes_threshold,
            "accounts": cleaned,
        }
