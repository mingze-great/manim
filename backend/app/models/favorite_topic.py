from sqlalchemy import Column, Integer, String, DateTime, ForeignKey
from sqlalchemy.orm import relationship
from datetime import datetime
from app.database import Base


class FavoriteTopic(Base):
    __tablename__ = "favorite_topics"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    topic = Column(String(500), nullable=False)
    category = Column(String(50))
    created_at = Column(DateTime, default=datetime.utcnow)
    
    user = relationship("User", backref="favorite_topics")