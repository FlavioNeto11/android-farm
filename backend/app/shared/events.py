"""Eventos do sistema de farm de contas"""
from enum import Enum
from typing import Optional
from dataclasses import dataclass
from datetime import datetime
import uuid


class EventType(str, Enum):
    """Tipos de eventos"""
    ACCOUNT_CREATED = "account.created"
    ACCOUNT_FAILED = "account.failed"
    CREDENTIAL_AUTHORED = "credential.authored"
    ACCOUNT_ASSIGNED = "account.assigned"
    PROXY_USED = "proxy.used"
    TASK_COMPLETED = "task.completed"


@dataclass
class AccountCreatedEvent:
    """Evento quando conta é criada"""
    event_type: EventType = EventType.ACCOUNT_CREATED
    event_id: str = None
    timestamp: datetime = None
    account_id: str = None
    platform: str = None
    handle: Optional[str] = None
    profile_id: Optional[str] = None


@dataclass
class AccountFailedEvent:
    """Evento quando criação de conta falha"""
    event_type: EventType = EventType.ACCOUNT_FAILED
    event_id: str = None
    timestamp: datetime = None
    account_id: str = None
    platform: str = None
    profile_id: Optional[str] = None
    error_message: str = None
    retry_count: int = 0


@dataclass
class CredentialAuthoredEvent:
    """Evento quando credencial é escrita"""
    event_type: EventType = EventType.CREDENTIAL_AUTHORED
    event_id: str = None
    timestamp: datetime = None
    account_id: str = None
    profile_id: Optional[str] = None
    consent_by: Optional[str] = None


@dataclass
class AccountAssignedEvent:
    """Evento quando conta é atribuída a persona"""
    event_type: EventType = EventType.ACCOUNT_ASSIGNED
    event_id: str = None
    timestamp: datetime = None
    account_id: str = None
    profile_id: str = None
    platform: str = None


@dataclass
class ProxyUsedEvent:
    """Evento quando proxy é usado"""
    event_type: EventType = EventType.PROXY_USED
    event_id: str = None
    timestamp: datetime = None
    proxy_id: str = None
    proxy_host: str = None
    country: Optional[str] = None


def create_event(account_id: str, event_type: EventType, **kwargs):
    """Fábrica para criar eventos"""
    if event_type == EventType.ACCOUNT_CREATED:
        return AccountCreatedEvent(
            event_id=str(uuid.uuid4()),
            timestamp=datetime.utcnow(),
            account_id=account_id,
            **kwargs
        )
    elif event_type == EventType.ACCOUNT_FAILED:
        return AccountFailedEvent(
            event_id=str(uuid.uuid4()),
            timestamp=datetime.utcnow(),
            account_id=account_id,
            **kwargs
        )
    elif event_type == EventType.CREDENTIAL_AUTHORED:
        return CredentialAuthoredEvent(
            event_id=str(uuid.uuid4()),
            timestamp=datetime.utcnow(),
            account_id=account_id,
            **kwargs
        )
    elif event_type == EventType.ACCOUNT_ASSIGNED:
        return AccountAssignedEvent(
            event_id=str(uuid.uuid4()),
            timestamp=datetime.utcnow(),
            account_id=account_id,
            **kwargs
        )
    elif event_type == EventType.PROXY_USED:
        return ProxyUsedEvent(
            event_id=str(uuid.uuid4()),
            timestamp=datetime.utcnow(),
            proxy_id=kwargs.get("proxy_id"),
            proxy_host=kwargs.get("proxy_host"),
            country=kwargs.get("country")
        )
    else:
        raise ValueError(f"Unknown event type: {event_type}")
