from sqlalchemy import Column, String, Enum, DateTime, Text, ForeignKey, Index, Integer, Boolean
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship
from datetime import datetime
from enum import Enum as PyEnum
import uuid

Base = declarative_base()


class AccountStatus(str, PyEnum):
    """Status de uma conta"""
    creating = "creating"
    ready = "ready"
    failed = "failed"
    blocked = "blocked"


class CredentialStatus(str, PyEnum):
    """Status de credencial"""
    active = "active"
    invalid = "invalid"


class ProxyStatus(str, PyEnum):
    """Status de proxy"""
    active = "active"
    exhausted = "exhausted"
    blocked = "blocked"


class Account(Base):
    """Modelo de conta"""
    __tablename__ = "accounts"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    platform = Column(String(50), nullable=False, index=True)
    handle = Column(String(255), nullable=True)
    status = Column(Enum(AccountStatus), nullable=False, default=AccountStatus.creating)

    # Persona relationship
    profile_id = Column(String(36), ForeignKey("personas.id"), nullable=True)

    # Metadata
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)
    error_message = Column(Text, nullable=True)
    proxy_used = Column(String(255), nullable=True)  # IP do proxy usado

    # Relationship
    credential = relationship("Credential", back_populates="account", uselist=False, cascade="all, delete-orphan")

    __table_args__ = (
        Index("ix_accounts_status", "status"),
        Index("ix_accounts_profile_id", "profile_id"),
    )

    def __repr__(self):
        return f"<Account(id='{self.id}', platform='{self.platform}', status='{self.status}', handle='{self.handle}')>"


class Credential(Base):
    """Modelo de credencial"""
    __tablename__ = "credentials"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    account_id = Column(String(36), ForeignKey("accounts.id", ondelete="CASCADE"), unique=True, nullable=False)
    login_identifier = Column(String(255), nullable=False)
    secret_ref = Column(String(255), nullable=False)  # Reference para segredo criptografado
    status = Column(Enum(CredentialStatus), nullable=False, default=CredentialStatus.active)

    # Consent
    consent_at = Column(DateTime, nullable=True)
    consent_by = Column(String(100), nullable=True)

    # Attempts
    failed_attempts = Column(Integer, default=0)
    blocked_until = Column(DateTime, nullable=True)

    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)
    last_used_at = Column(DateTime, nullable=True)

    # Relationship
    account = relationship("Account", back_populates="credential")

    def __repr__(self):
        return f"<Credential(id='{self.id}', account_id='{self.account_id}', login_identifier='{self.login_identifier}', status='{self.status}')>"


class Proxy(Base):
    """Modelo de proxy"""
    __tablename__ = "proxies"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    host = Column(String(255), nullable=False)
    port = Column(Integer, nullable=False)
    username = Column(String(255), nullable=True)
    password_ref = Column(String(255), nullable=True)  # Reference para senha
    status = Column(Enum(ProxyStatus), nullable=False, default=ProxyStatus.active)

    # Attributes
    country = Column(String(50), nullable=True)  # country code ou cidade
    ssl = Column(String(10), default="true", nullable=False)  # true/false
    level = Column(String(10), default="free", nullable=False)  # free/standard/pro

    # Statistics
    used_count = Column(Integer, default=0)
    failed_count = Column(Integer, default=0)

    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)
    last_used_at = Column(DateTime, nullable=True)

    def __repr__(self):
        return f"<Proxy(id='{self.id}', host='{self.host}:{self.port}', status='{self.status}', country='{self.country}')>"


class Persona(Base):
    """Modelo de persona para referência"""
    __tablename__ = "personas"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))

    # Identity
    username = Column(String(100), nullable=True, index=True)
    display_name = Column(String(100), nullable=True)
    first_name = Column(String(100), nullable=True)
    last_name = Column(String(100), nullable=True)
    email = Column(String(255), nullable=True)

    # Metadata
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    def __repr__(self):
        return f"<Persona(id='{self.id}', username='{self.username}', display_name='{self.display_name}')>"


class PlatformConfig(Base):
    """Configuração de cada plataforma"""
    __tablename__ = "platform_configs"

    platform = Column(String(50), primary_key=True)  # outlook, instagram
    enabled = Column(Boolean, default=True, nullable=False)

    # URLs and settings
    signup_url = Column(String(500), nullable=False)
    account_age_days = Column(Integer, default=365, nullable=False)  # Account age em dias

    # Timeout (seconds)
    timeout = Column(Integer, default=60, nullable=False)

    # Config JSON (extra settings per platform)
    config = Column(Text, nullable=True)  # JSON string

    # Creation settings
    requires_phone = Column(Boolean, default=False, nullable=False)
    requires_verification = Column(Boolean, default=True, nullable=False)

    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    def __repr__(self):
        return f"<PlatformConfig(platform='{self.platform}', enabled={self.enabled})>"


class AccountProxyMapping(Base):
    """Mapeamento de conta com proxy para consistência de IP"""
    __tablename__ = "account_proxy_mappings"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    account_email = Column(String(255), unique=True, nullable=False, index=True)
    account_type = Column(String(50))
    proxy_session_id = Column(String(100), nullable=False, index=True)
    proxy_host = Column(String(100))
    proxy_port = Column(Integer)
    proxy_user = Column(String(255))
    proxy_pass = Column(String(255))
    assigned_ip = Column(String(50))
    created_at = Column(DateTime, default=datetime.utcnow)
    last_used_at = Column(DateTime)
    use_count = Column(Integer, default=0)
    status = Column(String(50), default="active")
    notes = Column(Text)

    def __repr__(self):
        return f"<AccountProxyMapping(email='{self.account_email}', session='{self.proxy_session_id}', ip='{self.assigned_ip}')>"
