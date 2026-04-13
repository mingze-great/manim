from sqlalchemy import Column, Integer, String, Boolean, DateTime, Text
from datetime import datetime
from app.database import Base


class CoverStyle(Base):
    __tablename__ = "cover_styles"
    
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(50), nullable=False, comment="风格名称")
    description = Column(Text, nullable=True, comment="风格描述")
    base_prompt = Column(Text, nullable=False, comment="封面母prompt，支持{topic}占位符")
    example_image_url = Column(String(500), nullable=True, comment="示例图片URL")
    font_recommendation = Column(String(200), nullable=True, default="黑体", comment="推荐字体")
    color_recommendation = Column(String(200), nullable=True, default="#333333", comment="推荐颜色")
    is_active = Column(Boolean, default=True, comment="是否启用")
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)