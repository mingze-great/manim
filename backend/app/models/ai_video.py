from datetime import datetime

from sqlalchemy import Column, DateTime, ForeignKey, Integer, String, Text

from app.database import Base


class AiVideoProject(Base):
    __tablename__ = "ai_video_projects"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    title = Column(String(200), nullable=False)
    video_type = Column(String(50), default="knowledge_visualization", nullable=False)
    aspect_ratio = Column(String(10), default="16:9", nullable=False)
    current_version_id = Column(Integer, nullable=True)
    status = Column(String(30), default="draft", nullable=False)
    cover_url = Column(String(500), nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class AiVideoJob(Base):
    __tablename__ = "ai_video_jobs"

    id = Column(Integer, primary_key=True, index=True)
    project_id = Column(Integer, ForeignKey("ai_video_projects.id"), nullable=False, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    job_type = Column(String(50), default="generate", nullable=False)
    status = Column(String(30), default="pending", nullable=False)
    progress = Column(Integer, default=0, nullable=False)
    stage = Column(String(50), default="pending", nullable=False)
    input_payload = Column(Text, nullable=True)
    output_url = Column(String(500), nullable=True)
    cover_url = Column(String(500), nullable=True)
    error_message = Column(Text, nullable=True)
    log_path = Column(String(500), nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    completed_at = Column(DateTime, nullable=True)


class AiVideoVersion(Base):
    __tablename__ = "ai_video_versions"

    id = Column(Integer, primary_key=True, index=True)
    project_id = Column(Integer, ForeignKey("ai_video_projects.id"), nullable=False, index=True)
    version_no = Column(Integer, default=1, nullable=False)
    project_json = Column(Text, nullable=False)
    output_url = Column(String(500), nullable=True)
    cover_url = Column(String(500), nullable=True)
    change_summary = Column(Text, nullable=True)
    created_by = Column(Integer, ForeignKey("users.id"), nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)


class AiVideoAsset(Base):
    __tablename__ = "ai_video_assets"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    project_id = Column(Integer, ForeignKey("ai_video_projects.id"), nullable=True, index=True)
    asset_type = Column(String(50), nullable=False)
    file_url = Column(String(500), nullable=False)
    metadata_json = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)


class AiVideoBrandKit(Base):
    __tablename__ = "ai_video_brand_kits"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    name = Column(String(120), nullable=False)
    logo_url = Column(String(500), nullable=True)
    colors = Column(Text, nullable=True)
    fonts = Column(Text, nullable=True)
    voice_config = Column(Text, nullable=True)
    subtitle_style = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
