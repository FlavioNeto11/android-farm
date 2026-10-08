from abc import ABC, abstractmethod
from typing import Optional, Dict
from dataclasses import dataclass
import logging
import asyncio

from app.modules.browsers.domain.browser_profile import BrowserContext
from app.models import Account, Credential

logger = logging.getLogger(__name__)


@dataclass
class PersonaData:
    """Dados da persona para criação de conta"""
    profile_id: str
    display_name: Optional[str] = None
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    email: Optional[str] = None
    birth_date: Optional[str] = None
    gender: Optional[str] = None
    locale: Optional[str] = None
    username: Optional[str] = None
    summary: Optional[str] = None


@dataclass
class AccountResult:
    """Resultado da criação de conta"""
    success: bool
    handle: Optional[str] = None
    login_identifier: Optional[str] = None
    password: Optional[str] = None
    credential_ref: Optional[str] = None
    error_message: Optional[str] = None
    verification_needed: bool = False


class PlatformProvider(ABC):
    """Interface abstrata para provedores de plataformas"""

    @abstractmethod
    async def create_account(
        self,
        persona_data: PersonaData,
        proxy_host: Optional[str] = None,
        proxy_port: Optional[int] = None,
        proxy_username: Optional[str] = None,
        proxy_password: Optional[str] = None,
        timeout: int = 60
    ) -> AccountResult:
        """
        Criar conta na plataforma.

        Args:
            persona_data: Dados da persona
            proxy_host: Host do proxy (opcional)
            proxy_port: Porta do proxy
            proxy_username: Usuário do proxy
            proxy_password: Senha do proxy
            timeout: Tempo máximo em segundos

        Returns:
            Resultado da criação
        """
        pass

    @abstractmethod
    def get_platform_name(self) -> str:
        """Retornar nome da plataforma"""
        pass

    @abstractmethod
    def get_signup_url(self) -> str:
        """Retornar URL de signup"""
        pass

    @abstractmethod
    def get_config(self) -> Dict:
        """Retornar configurações da plataforma"""
        pass

    async def validate_account(self, handle: str, password: str, context: BrowserContext) -> bool:
        """
        Validar se conta foi criada com sucesso.
        (Implementação opcional, por plataforma ou genérica)
        """
        return True

    def needs_verification(self) -> bool:
        """Retornar se plataforma precisa de verificação"""
        return True
