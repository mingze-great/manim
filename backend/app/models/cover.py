from sqlalchemy import Column, Integer, String, Boolean, DateTime, Text, ForeignKey
from sqlalchemy.orm import relationship
from datetime import datetime
from app.database import Base


class Cover(Base):
    __tablename__ = "covers"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    style_id = Column(Integer, ForeignKey("cover_styles.id"), nullable=True)
    title_line1 = Column(String(100), nullable=False, comment="第一行标题")
    title_line2 = Column(String(100), nullable=True, comment="第二行标题")
    topic = Column(String(200), nullable=False, comment="封面主题")
    font_style = Column(String(50), nullable=True, default="黑体", comment="字体样式")
    font_color = Column(String(20), nullable=True, default="#333333", comment="字体颜色")
    image_url = Column(String(500), nullable=True, comment="云端图片URL")
    local_url = Column(String(500), nullable=True, comment="本地图片URL")
    storage = Column(String(20), nullable=True, default="local", comment="存储方式")
    created_at = Column(DateTime, default=datetime.utcnow)
    
    user = relationship("User", backref="covers")
    style = relationship("CoverStyle", backref="covers")