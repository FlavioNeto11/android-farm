from fastapi import APIRouter, HTTPException, Depends
from sqlalchemy.orm import Session
from datetime import datetime
import logging

from app.db import get_db_context
from app.models import AccountProxyMapping
from app.schemas.account_import import AccountImportRequest
from app.services.proxy_pool import ProxyPoolManager

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/proxy-accounts", tags=["proxy-accounts"])


@router.post("/import")
async def import_account_from_creation_platform(
    account_data: AccountImportRequest,
):
    """
    Recebe conta criada pela plataforma de automação IA.
    Mantém o mesmo proxy_session para consistência de IP.
    """
    try:
        with get_db_context() as db:
            existing = db.query(AccountProxyMapping).filter(
                AccountProxyMapping.account_email == account_data.email
            ).first()
            
            if existing:
                return {
                    "status": "already_exists",
                    "account_id": existing.id,
                    "proxy_session": existing.proxy_session_id,
                    "assigned_ip": existing.assigned_ip
                }
            
            pool = ProxyPoolManager.get_instance()
            proxy_config = pool.get_proxy_for_session(account_data.proxy_session_id)
            
            new_mapping = AccountProxyMapping(
                account_email=account_data.email,
                account_type=account_data.platform,
                proxy_session_id=account_data.proxy_session_id,
                proxy_host=account_data.proxy_host or proxy_config.host,
                proxy_port=account_data.proxy_port or proxy_config.port,
                proxy_user=account_data.proxy_user or proxy_config.username,
                proxy_pass=account_data.proxy_pass or proxy_config.password,
                status="pending_activation",
                notes=account_data.notes
            )
            
            db.add(new_mapping)
            db.commit()
            db.refresh(new_mapping)
            
            logger.info(f"Account imported: {account_data.email} with session {account_data.proxy_session_id}")
            
            return {
                "status": "imported",
                "account_id": new_mapping.id,
                "proxy_session": account_data.proxy_session_id,
                "message": "Account imported, scheduled for activation with consistent IP"
            }
            
    except Exception as e:
        logger.error(f"Failed to import account: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to import account: {str(e)}")


@router.get("/proxy-mappings")
async def list_proxy_mappings(
    status: str = None,
    session_id: str = None,
):
    """Lista mapeamentos de conta+proxy"""
    try:
        with get_db_context() as db:
            query = db.query(AccountProxyMapping)
            
            if status:
                query = query.filter(AccountProxyMapping.status == status)
            if session_id:
                query = query.filter(AccountProxyMapping.proxy_session_id == session_id)
            
            mappings = query.order_by(AccountProxyMapping.created_at.desc()).all()
            
            return {
                "mappings": [
                    {
                        "id": m.id,
                        "email": m.account_email,
                        "platform": m.account_type,
                        "session_id": m.proxy_session_id,
                        "assigned_ip": m.assigned_ip,
                        "status": m.status,
                        "created_at": m.created_at.isoformat() if m.created_at else None,
                        "last_used_at": m.last_used_at.isoformat() if m.last_used_at else None,
                        "use_count": m.use_count
                    }
                    for m in mappings
                ],
                "total": len(mappings)
            }
    except Exception as e:
        logger.error(f"Failed to list mappings: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/proxy-mappings/{mapping_id}")
async def get_proxy_mapping(mapping_id: int):
    """Obter mapeamento específico"""
    try:
        with get_db_context() as db:
            mapping = db.query(AccountProxyMapping).filter(
                AccountProxyMapping.id == mapping_id
            ).first()
            
            if not mapping:
                raise HTTPException(status_code=404, detail="Mapping not found")
            
            return {
                "id": mapping.id,
                "email": mapping.account_email,
                "platform": mapping.account_type,
                "session_id": mapping.proxy_session_id,
                "proxy_host": mapping.proxy_host,
                "proxy_port": mapping.proxy_port,
                "assigned_ip": mapping.assigned_ip,
                "status": mapping.status,
                "created_at": mapping.created_at.isoformat() if mapping.created_at else None,
                "last_used_at": mapping.last_used_at.isoformat() if mapping.last_used_at else None,
                "use_count": mapping.use_count,
                "notes": mapping.notes
            }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get mapping: {e}")
        raise HTTPException(status_code=500, detail=str(e))
