from sqlalchemy import Column, Integer, String, Boolean, DateTime, ForeignKey
from sqlalchemy.orm import relationship
from datetime import datetime
from app.database import Base


class UserModulePermission(Base):
    __tablename__ = "user_module_permissions"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    module_key = Column(String(20), nullable=False)
    enabled = Column(Boolean, default=True)
    quota_limit = Column(Integer, default=0)
    quota_used = Column(Integer, default=0)
    period = Column(String(20), default="daily")
    last_reset_at = Column(DateTime, nullable=True)
    expires_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    user = relationship("User", back_populates="module_permission_records")
    
    def check_and_reset_quota(self):
        now = datetime.utcnow()
        should_reset = False
        
        if self.period == "monthly":
            current_month = now.strftime("%Y-%m")
            if self.last_reset_at:
                last_month = self.last_reset_at.strftime("%Y-%m")
                if last_month != current_month:
                    should_reset = True
            else:
                should_reset = True
        else:
            today = now.date()
            if self.last_reset_at:
                last_date = self.last_reset_at.date()
                if last_date != today:
                    should_reset = True
            else:
                should_reset = True
        
        if should_reset:
            self.quota_used = 0
            self.last_reset_at = now
        
        return should_reset
    
    def can_use(self):
        if not self.enabled:
            return False, "该模块未开通"
        
        if self.expires_at and datetime.utcnow() > self.expires_at:
            return False, "该模块已过期"
        
        self.check_and_reset_quota()
        
        if self.quota_limit > 0 and self.quota_used >= self.quota_limit:
            period_label = "本月" if self.period == "monthly" else "今日"
            return False, f"{period_label}配额已用完"
        
        return True, None
    
    def increment_usage(self):
        self.check_and_reset_quota()
        self.quota_used += 1
        self.updated_at = datetime.utcnow()
    
    def to_dict(self):
        return {
            "id": self.id,
            "user_id": self.user_id,
            "module_key": self.module_key,
            "enabled": self.enabled,
            "quota_limit": self.quota_limit,
            "quota_used": self.quota_used,
            "period": self.period,
            "last_reset_at": self.last_reset_at.isoformat() if self.last_reset_at else None,
            "expires_at": self.expires_at.isoformat() if self.expires_at else None,
        }
