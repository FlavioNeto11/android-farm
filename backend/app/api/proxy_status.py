"""Endpoint para verificar status do proxy"""
from fastapi import APIRouter
from datetime import datetime
import logging

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/proxy", tags=["proxy"])


@router.get("/status")
async def get_proxy_status():
    """Verificar status do proxy com layered fallback"""
    from app.modules.accounts.platforms.instagram.proxy_config import (
        load_proxy_from_env, get_masked_url, layered_proxy_fallback,
        ProxyAuthenticationError, ProxyConnectionError
    )
    
    proxy_config = load_proxy_from_env()
    
    if not proxy_config:
        return {
            "configured": False,
            "status": "disabled",
            "proxy_method": "none",
            "using_proxy": False,
            "message": "Proxy disabled (PROXY_ENABLED=false)",
            "last_check": datetime.now().isoformat()
        }
    
    try:
        result = layered_proxy_fallback(proxy_config)
        return {
            "configured": True,
            "host": proxy_config.host,
            "port": proxy_config.port,
            "proxy_method": result.method,
            "using_proxy": result.using_proxy,
            "ip": result.ip,
            "country": result.country,
            "status": "ok" if result.using_proxy else "fallback_direct",
            "message": f"Proxy method: {result.method}" + (f", IP: {result.ip}" if result.ip else ""),
            "last_check": datetime.now().isoformat()
        }
    except (ProxyAuthenticationError, ProxyConnectionError) as e:
        return {
            "configured": True,
            "host": proxy_config.host,
            "port": proxy_config.port,
            "proxy_method": "failed",
            "using_proxy": False,
            "status": "error",
            "error": str(e),
            "last_check": datetime.now().isoformat()
        }
