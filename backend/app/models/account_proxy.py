from sqlalchemy import Column, String, DateTime, Integer, Text
from datetime import datetime
from app.models import Base


class AccountProxyMapping(Base):
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
