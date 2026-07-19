from sqlalchemy import Column, Integer, Date, DateTime, ForeignKey
from datetime import datetime
from app.database import Base


class UserDailyUsage(Base):
    __tablename__ = "user_daily_usage"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    usage_date = Column(Date, nullable=False)
    article_count = Column(Integer, default=0)
    created_at = Column(DateTime, default=datetime.utcnow)