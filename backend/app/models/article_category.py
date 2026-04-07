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
    is_active = Column(Boolean, default=True)
    sort_order = Column(Integer, default=0)
    created_at = Column(DateTime, default=datetime.utcnow)