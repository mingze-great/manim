from sqlalchemy import Column, Integer, String, Boolean, DateTime, Text
from sqlalchemy.orm import relationship
from datetime import datetime
from app.database import Base


class User(Base):
    __tablename__ = "users"
    
    id = Column(Integer, primary_key=True, index=True)
    username = Column(String(50), unique=True, index=True, nullable=False)
    email = Column(String(100), unique=True, index=True, nullable=False)
    hashed_password = Column(String(255), nullable=False)
    is_active = Column(Boolean, default=True)
    is_admin = Column(Boolean, default=False)
    is_approved = Column(Boolean, default=False, comment="是否审核通过")
    expires_at = Column(DateTime, nullable=True, comment="账号有效期")
    api_calls_count = Column(Integer, default=0, comment="API调用次数")
    videos_count = Column(Integer, default=0, comment="生成视频数量")
    last_active_at = Column(DateTime, nullable=True, comment="最后活跃时间")
    created_at = Column(DateTime, default=datetime.utcnow)
    
    orders = relationship("Order", back_populates="user")
    subscription = relationship("Subscription", back_populates="user", uselist=False)
    
    def is_expired(self):
        if self.expires_at is None:
            return False
        return datetime.utcnow() > self.expires_at
    
    def can_use(self):
        return self.is_approved and not self.is_expired()
    
    def to_dict(self):
        return {
            "id": self.id,
            "username": self.username,
            "email": self.email,
            "is_active": self.is_active,
            "is_admin": self.is_admin,
            "is_approved": self.is_approved,
            "expires_at": self.expires_at.isoformat() if self.expires_at else None,
            "is_expired": self.is_expired(),
            "can_use": self.can_use(),
            "api_calls_count": self.api_calls_count,
            "videos_count": self.videos_count,
            "last_active_at": self.last_active_at.isoformat() if self.last_active_at else None,
            "created_at": self.created_at.isoformat() if self.created_at else None
        }


class AuditLog(Base):
    __tablename__ = "audit_logs"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, nullable=True)
    username = Column(String(50), nullable=True)
    action = Column(String(100), nullable=False)
    resource = Column(String(100), nullable=True)
    resource_id = Column(Integer, nullable=True)
    details = Column(Text, nullable=True)
    ip_address = Column(String(50), nullable=True)
    user_agent = Column(String(500), nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    
    def to_dict(self):
        return {
            "id": self.id,
            "user_id": self.user_id,
            "username": self.username,
            "action": self.action,
            "resource": self.resource,
            "resource_id": self.resource_id,
            "details": self.details,
            "ip_address": self.ip_address,
            "user_agent": self.user_agent,
            "created_at": self.created_at.isoformat() if self.created_at else None
        }
