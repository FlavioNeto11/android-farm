from pydantic import BaseModel
from typing import Optional
from datetime import datetime


class AccountImportRequest(BaseModel):
    email: str
    platform: str
    proxy_session_id: str
    proxy_host: Optional[str] = None
    proxy_port: Optional[int] = None
    proxy_user: Optional[str] = None
    proxy_pass: Optional[str] = None
    created_at: Optional[str] = None
    handle: Optional[str] = None
    password: Optional[str] = None
    notes: Optional[str] = None
