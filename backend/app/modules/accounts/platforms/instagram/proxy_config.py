import os
from dataclasses import dataclass, field
from typing import Optional, Literal
import logging
import urllib.parse
import time
import httpx

logger = logging.getLogger(__name__)


ProxyMethod = Literal["native", "system_env", "direct"]


class ProxyAuthenticationError(Exception):
    pass


class ProxyConnectionError(Exception):
    pass


class ProxyRateLimitError(Exception):
    pass


@dataclass
class ProxyConfig:
    host: str
    port: int
    username: str
    password: str


@dataclass
class ProxyResult:
    method: ProxyMethod
    using_proxy: bool
    ip: str = ""
    country: str = ""
    error: str = ""


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
        return "Proxy returned 403 Forbidden. Credenciais expiradas ou inválidas."
    elif "407" in error_str:
        return "Proxy requires authentication. Verifique PROXY_USER e PROXY_PASS."
    elif "502" in error_str or "bad gateway" in error_str:
        return "Erro no servidor proxy. Tente novamente em alguns minutos."
    elif "timeout" in error_str or "timed out" in error_str:
        return "Proxy não responde."
    elif "tunnel" in error_str:
        return "Tunnel connection failed. Verifique configuração do proxy."
    else:
        return f"Erro desconhecido: {error}"


def _test_proxy_url(proxy_url: Optional[str], test_url: str = "https://geo.brdtest.com/welcome.txt") -> ProxyResult:
    """Test a proxy URL and return result. Returns direct if proxy_url is None."""
    try:
        client_kwargs = {"timeout": 15}
        if proxy_url:
            client_kwargs["proxy"] = proxy_url
        
        with httpx.Client(**client_kwargs) as client:
            resp = client.get(test_url)
            
            if resp.status_code == 200:
                body = resp.text.strip()
                ip = body[:50]
                country = ""
                if "IP=" in body:
                    parts = body.split("IP=")
                    if len(parts) > 1:
                        ip = parts[1].split()[0][:50]
                return ProxyResult(
                    method="native" if proxy_url else "direct",
                    using_proxy=proxy_url is not None,
                    ip=ip,
                    country=country,
                )
            elif resp.status_code == 403:
                raise ProxyAuthenticationError("Proxy returned 403 Forbidden")
            elif resp.status_code == 407:
                raise ProxyAuthenticationError("Proxy requires authentication (407)")
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
        raise ProxyConnectionError(str(e))
    except Exception as e:
        raise ProxyConnectionError(str(e))


def layered_proxy_fallback(config: Optional[ProxyConfig]) -> ProxyResult:
    """
    Try proxy in layered fallback:
    Layer A: native (playwright proxy via httpx test)
    Layer B: system_env (set HTTP_PROXY/HTTPS_PROXY env vars)
    Layer C: direct (no proxy)
    
    Only accepts a layer if geo.brdtest.com returns status 200.
    """
    if not config:
        logger.info("No proxy config → direct mode")
        try:
            result = _test_proxy_url(None)
            result.method = "direct"
            result.using_proxy = False
            return result
        except Exception as e:
            return ProxyResult(method="direct", using_proxy=False, error=str(e))
    
    proxy_url = get_proxy_url(config)
    
    # Layer A: Native proxy
    logger.info("Proxy Layer A: Testing native proxy...")
    try:
        result = _test_proxy_url(proxy_url)
        result.method = "native"
        result.using_proxy = True
        logger.info(f"Proxy Layer A SUCCESS: method=native, ip={result.ip}")
        return result
    except (ProxyAuthenticationError, ProxyRateLimitError) as e:
        logger.warning(f"Proxy Layer A auth failed: {e} → trying Layer B")
    except ProxyConnectionError as e:
        logger.warning(f"Proxy Layer A failed: {e} → trying Layer B")
    
    # Layer B: System environment proxy
    logger.info("Proxy Layer B: Testing via system environment variables...")
    old_http = os.environ.get("HTTP_PROXY")
    old_https = os.environ.get("HTTPS_PROXY")
    old_http_lower = os.environ.get("http_proxy")
    old_https_lower = os.environ.get("https_proxy")
    
    try:
        os.environ["HTTP_PROXY"] = proxy_url
        os.environ["HTTPS_PROXY"] = proxy_url
        os.environ["http_proxy"] = proxy_url
        os.environ["https_proxy"] = proxy_url
        
        result = _test_proxy_url(None)
        result.method = "system_env"
        result.using_proxy = True
        logger.info(f"Proxy Layer B SUCCESS: method=system_env, ip={result.ip}")
        return result
    except (ProxyAuthenticationError, ProxyRateLimitError) as e:
        logger.warning(f"Proxy Layer B auth failed: {e} → trying Layer C")
    except ProxyConnectionError as e:
        logger.warning(f"Proxy Layer B failed: {e} → trying Layer C")
    finally:
        if old_http is not None:
            os.environ["HTTP_PROXY"] = old_http
        else:
            os.environ.pop("HTTP_PROXY", None)
        if old_https is not None:
            os.environ["HTTPS_PROXY"] = old_https
        else:
            os.environ.pop("HTTPS_PROXY", None)
        if old_http_lower is not None:
            os.environ["http_proxy"] = old_http_lower
        else:
            os.environ.pop("http_proxy", None)
        if old_https_lower is not None:
            os.environ["https_proxy"] = old_https_lower
        else:
            os.environ.pop("https_proxy", None)
    
    # Layer C: Direct (no proxy)
    logger.warning("Proxy Layer C: All proxy layers failed → falling back to direct (checkpoint expected)")
    try:
        result = _test_proxy_url(None)
        result.method = "direct"
        result.using_proxy = False
        result.error = "All proxy layers failed, using direct connection"
        logger.info(f"Proxy Layer C: direct mode, ip={result.ip}")
        return result
    except Exception as e:
        return ProxyResult(method="direct", using_proxy=False, error=str(e))
