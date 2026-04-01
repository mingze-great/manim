from sqlalchemy import Column, Integer, String, Text, Boolean, DateTime, ForeignKey
from datetime import datetime
from app.database import Base


class Template(Base):
    __tablename__ = "templates"
    
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(200), nullable=False)
    description = Column(Text, nullable=True)
    category = Column(String(50), nullable=True)
    code = Column(Text, nullable=False)
    prompt = Column(Text, nullable=True)
    thumbnail = Column(String(500), nullable=True)
    example_video_url = Column(String(500), nullable=True, comment="示例视频URL")
    is_system = Column(Boolean, default=False)
    is_visible = Column(Boolean, default=True, comment="是否对用户可见")
    user_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    usage_count = Column(Integer, default=0)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
