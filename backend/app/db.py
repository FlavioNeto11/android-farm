from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, Session
from sqlalchemy.pool import StaticPool
from contextlib import contextmanager
from typing import Generator

from app.models import Base
import logging

logger = logging.getLogger(__name__)


class Database:
    """Gerenciador de banco de dados"""

    def __init__(self, url: str):
        self.url = url
        self.engine = None
        self.session_factory = None

    def init_connections(self):
        """Inicializar conexões"""
        engine_kwargs = {
            "echo": False,
            "connect_args": {"check_same_thread": False} if self.url.startswith("sqlite") else {}
        }

        if self.url.startswith("sqlite"):
            engine_kwargs.update({
                "poolclass": StaticPool,
            })
            # Use sync SQLite driver
            if self.url.startswith("sqlite+aiosqlite"):
                self.url = self.url.replace("sqlite+aiosqlite", "sqlite")

        self.engine = create_engine(self.url, **engine_kwargs)
        self.session_factory = sessionmaker(
            bind=self.engine,
            autocommit=False,
            autoflush=False,
            expire_on_commit=False
        )

        Base.metadata.create_all(bind=self.engine)
        logger.info(f"Database initialized with URL: {self.url}")


_global_db = None


def init_db(config_url: str):
    """Inicializar banco de dados global"""
    global _global_db
    _global_db = Database(config_url)
    _global_db.init_connections()


def get_db_session() -> Session:
    """Retornar sessão para uso sync"""
    if not _global_db:
        raise RuntimeError("Database not initialized. Call init_db() first.")

    return _global_db.session_factory()


@contextmanager
def get_db_context() -> Generator[Session, None, None]:
    """Context manager para sessão de banco"""
    session = get_db_session()
    try:
        yield session
        session.commit()
    except Exception as e:
        session.rollback()
        raise e
    finally:
        session.close()


def seed_platform_configs():
    """Sementear configurações de plataformas se não existirem"""
    from app.models import PlatformConfig

    session = get_db_session()

    try:
        outlook = session.query(PlatformConfig).filter_by(platform="outlook").first()
        instagram = session.query(PlatformConfig).filter_by(platform="instagram").first()

        if not outlook:
            outlook = PlatformConfig(
                platform="outlook",
                enabled=True,
                signup_url="https://signup.live.com",
                account_age_days=365,
                timeout=60,
                requires_phone=False,
                requires_verification=True
            )
            session.add(outlook)

        if not instagram:
            instagram = PlatformConfig(
                platform="instagram",
                enabled=True,
                signup_url="https://www.instagram.com/accounts/emailsignup/",
                account_age_days=365,
                timeout=90,
                requires_phone=True,
                requires_verification=True
            )
            session.add(instagram)

        session.commit()
        logger.info("Platform configs seeded")

    except Exception as e:
        session.rollback()
        logger.error(f"Error seeding platform configs: {e}")
        raise
    finally:
        session.close()
