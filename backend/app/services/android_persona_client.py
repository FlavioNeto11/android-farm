import os
import httpx
from typing import List, Dict, Optional
import time
import logging

logger = logging.getLogger(__name__)


class AndroidPersonaClient:
    def __init__(self):
        self.base_url = os.getenv("ANDROID_API_URL", "http://127.0.0.1:8000")
        self.timeout = 5.0
        self._cache: Dict[str, tuple] = {}
        self._cache_ttl = 60

    def _get_cached(self, key: str) -> Optional[any]:
        if key in self._cache:
            data, timestamp = self._cache[key]
            if time.time() - timestamp < self._cache_ttl:
                return data
        return None

    def _set_cached(self, key: str, data):
        self._cache[key] = (data, time.time())

    async def list_personas(self) -> List[Dict]:
        cached = self._get_cached("list_personas")
        if cached is not None:
            return cached

        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.get(f"{self.base_url}/api/personas")
                response.raise_for_status()
                personas = response.json()
                self._set_cached("list_personas", personas)
                return personas
        except Exception as e:
            logger.warning(f"Error fetching personas from android: {e}")
            fallback = self._get_cached("list_personas")
            return fallback if fallback is not None else []

    async def get_persona(self, persona_id: str) -> Optional[Dict]:
        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.get(f"{self.base_url}/api/personas/{persona_id}")
                response.raise_for_status()
                return response.json()
        except Exception as e:
            logger.warning(f"Error fetching persona {persona_id}: {e}")
            return None

    async def get_persona_image_url(self, persona_id: str, image_id: str = "primary") -> str:
        return f"{self.base_url}/api/personas/{persona_id}/images/{image_id}"


android_client = AndroidPersonaClient()
