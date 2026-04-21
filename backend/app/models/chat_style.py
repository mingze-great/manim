from sqlalchemy import Column, Integer, String, Text, Boolean, DateTime
from sqlalchemy.sql import func
from app.database import Base


class ChatStyle(Base):
    __tablename__ = "chat_styles"
    
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(50), nullable=False, unique=True)
    code = Column(String(30), nullable=False, unique=True)
    description = Column(Text)
    system_prompt_zh = Column(Text, nullable=False)
    system_prompt_en = Column(Text)
    is_default = Column(Boolean, default=False)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())
    
    def to_dict(self):
        return {
            "id": self.id,
            "name": self.name,
            "code": self.code,
            "description": self.description,
            "system_prompt_zh": self.system_prompt_zh,
            "system_prompt_en": self.system_prompt_en,
            "is_default": self.is_default,
            "is_active": self.is_active,
        }