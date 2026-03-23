from sqlalchemy import Column, Integer, String, Text, DateTime, ForeignKey, Enum
from datetime import datetime
from app.database import Base
import enum


class ProjectStatus(str, enum.Enum):
    DRAFT = "draft"
    CHATTING = "chatting"
    PENDING = "pending"
    RENDERING = "rendering"
    COMPLETED = "completed"
    FAILED = "failed"


class Project(Base):
    __tablename__ = "projects"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    title = Column(String(200), nullable=False)
    theme = Column(Text, nullable=False)
    final_script = Column(Text, nullable=True)
    manim_code = Column(Text, nullable=True)
    custom_code = Column(Text, nullable=True)  # 用户自定义参考代码
    status = Column(String(20), default=ProjectStatus.DRAFT.value)
    template_id = Column(Integer, ForeignKey("templates.id"), nullable=True)
    video_url = Column(String(500), nullable=True)
    video_created_at = Column(DateTime, nullable=True, comment="视频创建时间，用于定时清理")
    error_message = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class Conversation(Base):
    __tablename__ = "conversations"
    
    id = Column(Integer, primary_key=True, index=True)
    project_id = Column(Integer, ForeignKey("projects.id"), nullable=False)
    role = Column(String(10), nullable=False)
    content = Column(Text, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)
