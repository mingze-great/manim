from sqlalchemy import Column, Integer, String, Boolean, DateTime, Text, Date
from sqlalchemy.orm import relationship
from datetime import datetime
import json
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
    token_usage = Column(Integer, default=0, comment="Token使用量")
    chat_token_usage = Column(Integer, default=0, comment="对话Token使用量")
    code_token_usage = Column(Integer, default=0, comment="代码生成Token使用量")
    daily_video_count = Column(Integer, default=0, comment="当日视频生成数量")
    daily_video_limit = Column(Integer, default=5, comment="每日视频配额限制(5-20)")
    module_permissions_json = Column(Text, nullable=True, comment="模块权限与配额配置")
    custom_voices_json = Column(Text, nullable=True, comment="用户自定义音色库")
    last_video_date = Column(Date, nullable=True, comment="最后生成视频日期")
    last_active_at = Column(DateTime, nullable=True, comment="最后活跃时间")
    created_at = Column(DateTime, default=datetime.utcnow)
    
    orders = relationship("Order", back_populates="user")
    subscription = relationship("Subscription", back_populates="user", uselist=False)
    module_permission_records = relationship("UserModulePermission", back_populates="user", cascade="all, delete-orphan")
    
    def is_expired(self):
        if self.expires_at is None:
            return False
        return datetime.utcnow() > self.expires_at
    
    def can_use(self):
        return self.is_approved and not self.is_expired()

    def get_default_module_permissions(self):
        return {
            "visual": {"enabled": True, "daily_limit": self.daily_video_limit or 5, "used_today": 0, "last_reset_date": None, "period": "daily"},
            "stickman": {"enabled": True, "daily_limit": 2, "used_today": 0, "last_reset_date": None, "period": "monthly"},
            "article": {"enabled": True, "daily_limit": 2, "used_today": 0, "last_reset_date": None, "period": "monthly"},
        }

    def get_module_permissions(self):
        if self.is_admin:
            return {
                "visual": {"enabled": True, "daily_limit": -1, "used_today": 0, "last_reset_date": None, "period": "daily"},
                "stickman": {"enabled": True, "daily_limit": -1, "used_today": 0, "last_reset_date": None, "period": "monthly"},
                "article": {"enabled": True, "daily_limit": -1, "used_today": 0, "last_reset_date": None, "period": "monthly"},
            }
        permissions = self.get_default_module_permissions()
        if self.module_permissions_json:
            try:
                stored = json.loads(self.module_permissions_json)
                if isinstance(stored, dict):
                    for key, value in stored.items():
                        if key in permissions and isinstance(value, dict):
                            permissions[key].update(value)
            except Exception:
                pass
        return permissions

    def set_module_permissions(self, permissions: dict):
        self.module_permissions_json = json.dumps(permissions, ensure_ascii=False)

    def get_custom_voices(self):
        if not self.custom_voices_json:
            return []
        try:
            data = json.loads(self.custom_voices_json)
            return data if isinstance(data, list) else []
        except Exception:
            return []

    def add_custom_voice(self, voice: dict):
        voices = self.get_custom_voices()
        voices = [item for item in voices if item.get('voice_id') != voice.get('voice_id')]
        voices.append(voice)
        self.custom_voices_json = json.dumps(voices, ensure_ascii=False)

    @property
    def module_permissions(self):
        return self.get_module_permissions()

    def get_module_permission(self, module_key: str):
        permissions = self.get_module_permissions()
        permission = permissions.get(module_key, {"enabled": False, "daily_limit": 0, "used_today": 0, "last_reset_date": None, "period": "daily"})
        period = permission.get("period") or ("monthly" if module_key in {"stickman", "article"} else "daily")
        current_marker = datetime.utcnow().strftime('%Y-%m') if period == 'monthly' else datetime.utcnow().date().isoformat()
        if permission.get("last_reset_date") != current_marker:
            permission["used_today"] = 0
            permission["last_reset_date"] = current_marker
            permissions[module_key] = permission
            self.set_module_permissions(permissions)
        return permission

    def can_use_module(self, module_key: str):
        if self.is_admin:
            return True, None
        if not self.can_use():
            return False, "账号当前不可用"
        permission = self.get_module_permission(module_key)
        if not permission.get("enabled", False):
            return False, "当前账号未开通此模块"
        limit = int(permission.get("daily_limit", 0) or 0)
        used_today = int(permission.get("used_today", 0) or 0)
        if limit > 0 and used_today >= limit:
            period_label = "本月" if permission.get("period") == "monthly" else "今日"
            return False, f"{period_label}{module_key}模块使用次数已达上限"
        return True, None

    def increment_module_usage(self, module_key: str):
        if self.is_admin:
            return
        permissions = self.get_module_permissions()
        permission = permissions.get(module_key, {"enabled": True, "daily_limit": 0, "used_today": 0, "last_reset_date": None, "period": "daily"})
        period = permission.get("period") or ("monthly" if module_key in {"stickman", "article"} else "daily")
        marker = datetime.utcnow().strftime('%Y-%m') if period == 'monthly' else datetime.utcnow().date().isoformat()
        if permission.get("last_reset_date") != marker:
            permission["used_today"] = 0
        permission["used_today"] = int(permission.get("used_today", 0) or 0) + 1
        permission["last_reset_date"] = marker
        permissions[module_key] = permission
        self.set_module_permissions(permissions)
    
    def get_module_permission_record(self, db, module_key: str):
        from app.models.user_module_permission import UserModulePermission
        record = db.query(UserModulePermission).filter(
            UserModulePermission.user_id == self.id,
            UserModulePermission.module_key == module_key
        ).first()
        return record
    
    def can_use_module_new(self, db, module_key: str):
        if self.is_admin:
            return True, None
        if not self.can_use():
            return False, "账号当前不可用"
        
        record = self.get_module_permission_record(db, module_key)
        if not record:
            return self.can_use_module(module_key)
        
        return record.can_use()
    
    def increment_module_usage_new(self, db, module_key: str):
        if self.is_admin:
            return
        record = self.get_module_permission_record(db, module_key)
        if record:
            record.increment_usage()
        else:
            self.increment_module_usage(module_key)
    
    def get_all_module_permissions_dict(self, db):
        from app.models.user_module_permission import UserModulePermission
        records = db.query(UserModulePermission).filter(
            UserModulePermission.user_id == self.id
        ).all()
        
        result = {}
        module_keys = ["visual", "stickman", "article"]
        for key in module_keys:
            record = None
            for r in records:
                if r.module_key == key:
                    record = r
                    break
            
            if record:
                record.check_and_reset_quota()
                result[key] = {
                    "enabled": record.enabled,
                    "daily_limit": record.quota_limit,
                    "used_today": record.quota_used,
                    "period": record.period,
                    "expires_at": record.expires_at.isoformat() if record.expires_at else None,
                }
            else:
                default_perm = self.get_module_permission(key)
                result[key] = default_perm
        
        return result
    
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
            "module_permissions": self.get_module_permissions(),
            "custom_voices": self.get_custom_voices(),
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
