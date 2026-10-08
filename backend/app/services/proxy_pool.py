import os
import json
import logging
from typing import Dict, Optional
from dataclasses import dataclass, asdict

logger = logging.getLogger(__name__)


@dataclass
class ProxyConfig:
    host: str
    port: int
    username: str
    password: str
    session_id: str = ""
    
    def get_url(self) -> str:
        import urllib.parse
        safe_user = urllib.parse.quote(self.username, safe="")
        safe_pass = urllib.parse.quote(self.password, safe="")
        return f"http://{safe_user}:{safe_pass}@{self.host}:{self.port}"
    
    def get_masked_url(self) -> str:
        return f"http://{self.username}:****@{self.host}:{self.port}"
    
    def get_session_url(self) -> str:
        import urllib.parse
        session_user = f"{self.username}-session-{self.session_id}"
        safe_user = urllib.parse.quote(session_user, safe="")
        safe_pass = urllib.parse.quote(self.password, safe="")
        return f"http://{safe_user}:{safe_pass}@{self.host}:{self.port}"


class ProxyPoolManager:
    _instance = None
    
    def __init__(self):
        self.session_map: Dict[str, ProxyConfig] = {}
        self.config = self._load_config()
        self._load_from_env()
    
    @classmethod
    def get_instance(cls) -> "ProxyPoolManager":
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance
    
    def _load_config(self) -> dict:
        config_path = os.path.join(os.path.dirname(__file__), "..", "..", "config", "proxy_pool.json")
        if os.path.exists(config_path):
            with open(config_path) as f:
                return json.load(f)
        return {
            "provider": "brightdata_isp",
            "base_credentials": {
                "host": os.getenv("PROXY_HOST", "brd.superproxy.io"),
                "port": int(os.getenv("PROXY_PORT", "44445")),
                "username": os.getenv("PROXY_USER", ""),
                "password": os.getenv("PROXY_PASS", "")
            },
            "session_prefix": "android_farm",
            "max_sessions_per_proxy": 5,
            "rotation_policy": "sticky"
        }
    
    def _load_from_env(self):
        if os.getenv("PROXY_ENABLED") == "true":
            base = self.config.get("base_credentials", {})
            if base.get("username"):
                logger.info(f"Proxy pool loaded: {base.get('host')}:{base.get('port')}")
    
    def get_proxy_for_session(self, session_id: str) -> ProxyConfig:
        if session_id in self.session_map:
            logger.info(f"Returning existing proxy for session: {session_id}")
            return self.session_map[session_id]
        
        base = self.config.get("base_credentials", {})
        proxy = ProxyConfig(
            host=base.get("host", "brd.superproxy.io"),
            port=int(base.get("port", 44445)),
            username=base.get("username", ""),
            password=base.get("password", ""),
            session_id=session_id
        )
        
        self.session_map[session_id] = proxy
        logger.info(f"Created new proxy mapping for session: {session_id}")
        return proxy
    
    def get_session_count(self) -> int:
        return len(self.session_map)
    
    def get_active_sessions(self) -> list:
        return list(self.session_map.keys())
    
    def remove_session(self, session_id: str):
        if session_id in self.session_map:
            del self.session_map[session_id]
            logger.info(f"Removed session: {session_id}")
