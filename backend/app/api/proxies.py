"""Rotas de gerenciamento de proxies"""
from fastapi import APIRouter, HTTPException, status
from typing import List, Optional
import logging

from app.db import get_db_context
from app.modules.proxies.domain.proxy import get_proxy_manager
from app.models import Proxy, ProxyStatus

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/proxies", tags=["proxies"])


@router.get("")
async def list_proxies():
    """Listar todos os proxies do pool"""
    with get_db_context() as db:
        proxies = db.query(Proxy).order_by(Proxy.created_at.desc()).all()

        return [
            {
                "id": p.id,
                "host": p.host,
                "port": p.port,
                "status": p.status.value,
                "country": p.country,
                "used_count": p.used_count,
            }
            for p in proxies
        ]


@router.post("", status_code=status.HTTP_201_CREATED)
async def add_proxy(
    host: str,
    port: int,
    username: Optional[str] = None,
    country: Optional[str] = None
):
    """Adicionar proxy ao pool"""
    try:
        with get_db_context() as db:
            proxy_manager = get_proxy_manager()
            new_proxy = proxy_manager.add_proxy(db, {
                "host": host,
                "port": port,
                "username": username,
                "country": country,
            })

            return {
                "id": new_proxy.id,
                "host": new_proxy.host,
                "port": new_proxy.port,
                "status": new_proxy.status.value,
                "country": new_proxy.country,
            }

    except Exception as e:
        logger.error(f"Failed to add proxy: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )


@router.delete("/{proxy_id}")
async def delete_proxy(proxy_id: str):
    """Remover proxy do pool"""
    with get_db_context() as db:
        proxy = db.get(Proxy, proxy_id)
        if not proxy:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Proxy not found"
            )

        db.delete(proxy)
        db.commit()

        return {
            "message": "Proxy removed successfully",
            "proxy_id": proxy_id
        }


@router.get("/active-count")
async def active_proxy_count():
    """Contar proxies ativos no pool"""
    with get_db_context() as db:
        from sqlalchemy import func

        active_count = db.query(func.count(Proxy.id)).filter(
            Proxy.status == ProxyStatus.active
        ).scalar()

        total_count = db.query(func.count(Proxy.id)).scalar()

        return {
            "active_proxies": active_count or 0,
            "total_proxies": total_count or 0
        }
