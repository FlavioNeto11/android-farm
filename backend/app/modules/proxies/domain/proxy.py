from sqlalchemy.orm import Session
from sqlalchemy import select, update
from typing import Optional
from datetime import datetime, timedelta
import logging

from app.models import Proxy, ProxyStatus

logger = logging.getLogger(__name__)


class ProxyPool:
    """Gerenciador de pool de proxies"""

    def __init__(self, pool_size: int, rotation_strategy: str = "round_robin"):
        self.pool_size = pool_size
        self.rotation_strategy = rotation_strategy
        self.used_count = 0

    def get_available_proxy(self, db: Session) -> Optional[Proxy]:
        """
        Selecionar proxy disponível do pool.

        Returns:
            Proxy do banco ou None
        """
        # Retirar proxy da lista disponível
        query = (
            select(Proxy)
            .where(Proxy.status == ProxyStatus.active)
            .where(Proxy.failed_count < 5)  # Limite de falhas
            .order_by(Proxy.used_count.asc())
            .limit(1)
        )

        proxy = db.execute(query).scalar_one_or_none()

        if proxy:
            # Atualizar estatísticas
            proxy.used_count += 1
            proxy.last_used_at = datetime.utcnow()
            db.commit()
            logger.info(f"Selected proxy: {proxy.id} - {proxy.host}:{proxy.port}")
            return proxy

        logger.warning("No available proxy found")
        return None

    def mark_proxy_failed(self, proxy_id: str, db: Session):
        """Marcar proxy como falhado"""
        proxy = db.get(Proxy, proxy_id)
        if proxy:
            proxy.status = ProxyStatus.exhausted
            proxy.failed_count += 1
            proxy.last_used_at = datetime.utcnow()
            db.commit()

            if proxy.failed_count >= 5:
                logger.warning(f"Proxy {proxy_id} marked as exhausted (failed {proxy.failed_count} times)")


class ProxyManager:
    """Gerenciador de proxies completo"""

    def __init__(self, pool_size: int, rotation_strategy: str):
        self.pool = ProxyPool(pool_size, rotation_strategy)

    def get_proxy(self, db: Session) -> Optional[Proxy]:
        """Obter proxy disponível"""
        return self.pool.get_available_proxy(db)

    def add_proxy(self, db: Session, proxy_dict: dict) -> Proxy:
        """Adicionar proxy ao banco"""
        new_proxy = Proxy(
            host=proxy_dict["host"],
            port=proxy_dict["port"],
            username=proxy_dict.get("username"),
            password_ref=proxy_dict.get("password"),
            country=proxy_dict.get("country"),
            level=proxy_dict.get("level", "free")
        )

        db.add(new_proxy)
        db.commit()
        db.refresh(new_proxy)

        logger.info(f"Added proxy: {new_proxy.host}:{new_proxy.port}")
        return new_proxy

    def update_proxy_status(self, db: Session, proxy_id: str, status: ProxyStatus):
        """Atualizar status de proxy"""
        stmt = update(Proxy).where(Proxy.id == proxy_id).values(status=status)
        db.execute(stmt)
        db.commit()
        logger.info(f"Updated proxy {proxy_id} status to {status}")

    def validate_proxy(
        self,
        db: Session,
        proxy_id: str
    ) -> bool:
        """
        Validar se proxy está acessível.
        (Para expansão futura - test de conexão real)
        """
        return True


# Global proxy manager
proxy_manager = None


def init_proxy_manager(pool_size: int, rotation_strategy: str):
    """Inicializar proxy manager global"""
    global proxy_manager
    proxy_manager = ProxyManager(pool_size, rotation_strategy)
    logger.info("Proxy manager initialized")


def get_proxy_manager() -> ProxyManager:
    """Obter proxy manager global"""
    if proxy_manager is None:
        raise RuntimeError("Proxy manager not initialized. Call init_proxy_manager() first.")
    return proxy_manager
