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
    category = Column(String(50), nullable=True)  # 视频主题方向
    module_type = Column(String(20), default="manim", nullable=False)
    storyboard_count = Column(Integer, default=3, nullable=False)
    aspect_ratio = Column(String(10), default="16:9", nullable=False)
    generation_mode = Column(String(20), default="one_click", nullable=False)
    voice_source = Column(String(20), default="ai", nullable=False)
    voice_file_path = Column(String(500), nullable=True)
    voice_duration = Column(Integer, nullable=True)
    tts_provider = Column(String(30), default="dashscope_cosyvoice", nullable=False)
    tts_voice = Column(String(80), default="longshuo_v3", nullable=False)
    tts_rate = Column(String(20), default="+0%", nullable=False)
    style_reference_image_path = Column(String(500), nullable=True)
    style_reference_notes = Column(Text, nullable=True)
    style_reference_profile = Column(Text, nullable=True)
    preview_image_asset_json = Column(Text, nullable=True)
    preview_regen_count = Column(Integer, default=0, nullable=False)
    storyboard_json = Column(Text, nullable=True)
    image_assets_json = Column(Text, nullable=True)
    generation_flags = Column(Text, nullable=True)
    quota_consumed = Column(Integer, default=0, nullable=False)
    final_script = Column(Text, nullable=True)
    manim_code = Column(Text, nullable=True)
    custom_code = Column(Text, nullable=True)  # 用户自定义参考代码
    status = Column(String(20), default=ProjectStatus.DRAFT.value)
    template_id = Column(Integer, ForeignKey("templates.id"), nullable=True)
    video_url = Column(String(500), nullable=True)
    video_created_at = Column(DateTime, nullable=True, comment="视频创建时间，用于定时清理")
    error_message = Column(Text, nullable=True)
    render_fail_count = Column(Integer, default=0, comment="渲染失败次数")
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class Conversation(Base):
    __tablename__ = "conversations"
    
    id = Column(Integer, primary_key=True, index=True)
    project_id = Column(Integer, ForeignKey("projects.id"), nullable=False)
    role = Column(String(10), nullable=False)
    content = Column(Text, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)
