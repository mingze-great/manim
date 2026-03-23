from sqlalchemy import Column, Integer, String, Text, Boolean, DateTime, ForeignKey
from datetime import datetime
from app.database import Base


class Template(Base):
    __tablename__ = "templates"
    
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(200), nullable=False)  # 增加长度
    description = Column(Text, nullable=True)
    category = Column(String(50), nullable=True)
    code = Column(Text, nullable=False)
    thumbnail = Column(String(500), nullable=True)
    is_system = Column(Boolean, default=False)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    usage_count = Column(Integer, default=0)
    is_active = Column(Boolean, default=True)  # 添加激活状态
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)  # 添加更新时间
