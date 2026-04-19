from sqlalchemy import Column, Integer, String, Text, Boolean, DateTime
from datetime import datetime
from app.database import Base


class VideoTopicCategory(Base):
    __tablename__ = "video_topic_categories"
    
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(50), unique=True, nullable=False)
    icon = Column(String(100))
    description = Column(Text)
    example_topics = Column(Text)
    topic_generation_prompt = Column(Text)
    system_prompt = Column(Text)
    is_active = Column(Boolean, default=True)
    skip_chat = Column(Boolean, default=False, comment="跳过对话，直接生成脚本")
    sort_order = Column(Integer, default=0)
    created_at = Column(DateTime, default=datetime.utcnow)