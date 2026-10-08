"""Endpoint para verificar status do proxy"""
from fastapi import APIRouter
from datetime import datetime
import logging

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/proxy", tags=["proxy"])


@router.get("/status")
async def get_proxy_status():
    """Verificar status do proxy configurado"""
    from app.modules.accounts.platforms.instagram.proxy_config import (
        load_proxy_from_env, get_masked_url, validate_proxy_connection,
        diagnose_proxy_error, ProxyAuthenticationError, ProxyConnectionError
    )
    
    proxy_config = load_proxy_from_env()
    
    if not proxy_config:
        return {
            "configured": False,
            "status": "disabled",
            "message": "Proxy disabled (PROXY_ENABLED=false)",
            "last_check": datetime.now().isoformat()
        }
    
    result = {
        "configured": True,
        "host": proxy_config.host,
        "port": proxy_config.port,
        "username": proxy_config.username,
        "status": "unknown",
        "last_check": datetime.now().isoformat()
    }
    
    try:
        validate_proxy_connection(proxy_config)
        result["status"] = "ok"
        result["message"] = "Proxy connection successful"
    except (ProxyAuthenticationError, ProxyConnectionError) as e:
        result["status"] = "error"
        result["error"] = {
            "code": "AUTH_FAILED" if isinstance(e, ProxyAuthenticationError) else "CONNECTION_FAILED",
            "message": str(e),
            "action_required": diagnose_proxy_error(e)
        }
        result["fallback_active"] = True
    
    return result
