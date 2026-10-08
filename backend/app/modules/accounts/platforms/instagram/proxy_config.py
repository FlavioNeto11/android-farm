import os
from dataclasses import dataclass
from typing import Optional
import logging
import urllib.parse
import time

logger = logging.getLogger(__name__)


class ProxyAuthenticationError(Exception):
    """Credenciais inválidas ou expiradas"""
    pass


class ProxyConnectionError(Exception):
    """Proxy não responde"""
    pass


class ProxyRateLimitError(Exception):
    """Proxy bloqueado pelo target"""
    pass


@dataclass
class ProxyConfig:
    host: str
    port: int
    username: str
    password: str


def load_proxy_from_env() -> Optional[ProxyConfig]:
    enabled = os.getenv("PROXY_ENABLED", "false").lower() == "true"
    if not enabled:
        logger.info("Proxy disabled (PROXY_ENABLED=false)")
        return None
    
    host = os.getenv("PROXY_HOST")
    port_str = os.getenv("PROXY_PORT")
    username = os.getenv("PROXY_USER")
    password = os.getenv("PROXY_PASS")
    
    if not all([host, port_str, username, password]):
        logger.warning("Proxy enabled but missing credentials")
        return None
    
    try:
        port = int(port_str)
    except ValueError:
        logger.error(f"Invalid PROXY_PORT: {port_str}")
        return None
    
    return ProxyConfig(host=host, port=port, username=username, password=password)


def get_proxy_url(config: ProxyConfig) -> str:
    safe_user = urllib.parse.quote(config.username, safe="")
    safe_pass = urllib.parse.quote(config.password, safe="")
    return f"http://{safe_user}:{safe_pass}@{config.host}:{config.port}"


def get_masked_url(config: ProxyConfig) -> str:
    return f"http://{config.username}:****@{config.host}:{config.port}"


def diagnose_proxy_error(error: Exception) -> str:
    error_str = str(error).lower()
    if "403" in error_str or "forbidden" in error_str:
        return (
            "Proxy returned 403 Forbidden. Credenciais expiradas ou inválidas. "
            "Acesse https://brightdata.com/cp/zones e verifique se a zona está ativa. "
            "Renove as credenciais e atualize PROXY_USER/PROXY_PASS no .env"
        )
    elif "407" in error_str:
        return "Proxy requires authentication. Verifique PROXY_USER e PROXY_PASS no .env"
    elif "502" in error_str or "bad gateway" in error_str:
        return "Erro no servidor proxy. Tente novamente em alguns minutos"
    elif "timeout" in error_str or "timed out" in error_str:
        return "Proxy não responde. Verifique conexão de rede e se o Bright Data está acessível"
    elif "tunnel" in error_str:
        return (
            "Tunnel connection failed. Verifique se o proxy está configurado corretamente. "
            "Para Bright Data ISP, use brd.superproxy.io:44445"
        )
    else:
        return f"Erro desconhecido: {error}"


def validate_proxy_connection(config: ProxyConfig) -> bool:
    max_retries = 3
    base_delay = 2
    
    for attempt in range(max_retries):
        try:
            import httpx
            proxy_url = get_proxy_url(config)
            
            with httpx.Client(proxy=proxy_url, timeout=15) as client:
                resp = client.get("https://geo.brdtest.com/welcome.txt")
                
                if resp.status_code == 403:
                    raise ProxyAuthenticationError(
                        "Proxy returned 403 Forbidden. "
                        "Credentials may be expired or invalid. "
                        "Check Bright Data dashboard and renew proxy."
                    )
                elif resp.status_code == 407:
                    raise ProxyAuthenticationError("Proxy requires authentication (407)")
                elif resp.status_code == 502:
                    raise ProxyConnectionError("Bad Gateway (502)")
                elif resp.status_code == 200:
                    ip = resp.text.strip()[:50]
                    logger.info(f"Proxy connection successful: IP={ip}")
                    return True
                else:
                    raise ProxyConnectionError(f"Unexpected status: {resp.status_code}")
                    
        except (ProxyAuthenticationError, ProxyRateLimitError):
            raise
        except httpx.ProxyError as e:
            error_str = str(e).lower()
            if "403" in error_str or "forbidden" in error_str:
                raise ProxyAuthenticationError(str(e))
            elif "407" in error_str:
                raise ProxyAuthenticationError(str(e))
            elif attempt < max_retries - 1:
                delay = base_delay * (attempt + 1)
                logger.warning(f"Proxy attempt {attempt + 1} failed, retrying in {delay}s: {e}")
                time.sleep(delay)
            else:
                raise ProxyConnectionError(f"Proxy connection failed after {max_retries} attempts: {e}")
        except Exception as e:
            if attempt < max_retries - 1:
                delay = base_delay * (attempt + 1)
                logger.warning(f"Proxy attempt {attempt + 1} failed, retrying in {delay}s: {e}")
                time.sleep(delay)
            else:
                raise ProxyConnectionError(f"Proxy connection failed: {e}")
    
    return False
