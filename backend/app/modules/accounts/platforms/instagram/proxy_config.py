import os
from dataclasses import dataclass
from typing import Optional
import logging
import urllib.parse

logger = logging.getLogger(__name__)


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


def validate_proxy_connection(config: ProxyConfig) -> bool:
    try:
        import httpx
        proxy_url = get_proxy_url(config)
        with httpx.Client(proxy=proxy_url, timeout=10) as client:
            resp = client.get("https://geo.brdtest.com/welcome.txt")
            if resp.status_code == 200:
                ip = resp.text.strip()[:50]
                logger.info(f"Proxy connection successful: IP={ip}")
                return True
            else:
                logger.error(f"Proxy returned status {resp.status_code}")
                return False
    except Exception as e:
        logger.error(f"Proxy connection failed: {e}")
        return False
