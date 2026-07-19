from sqlalchemy import Column, Integer, String, Text, Boolean, DateTime
from datetime import datetime
from app.database import Base


class ArticleCategory(Base):
    __tablename__ = "article_categories"
    
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(50), unique=True, nullable=False)
    icon = Column(String(100))
    system_prompt = Column(Text, nullable=False)
    example_topics = Column(Text)
    image_prompt_template = Column(Text)
    
    # 新增视觉风格字段
    visual_style = Column(String(200))  # 视觉风格关键词
    emotion_tone = Column(String(200))  # 情绪基调
    color_palette = Column(String(200))  # 色彩方案
    
    is_active = Column(Boolean, default=True)
    sort_order = Column(Integer, default=0)
    created_at = Column(DateTime, default=datetime.utcnow)