from sqlalchemy import Column, Integer, Date
from app.database import Base


class DailyStatistics(Base):
    __tablename__ = "daily_statistics"
    
    id = Column(Integer, primary_key=True, index=True)
    date = Column(Date, unique=True, nullable=False)
    conversations_count = Column(Integer, default=0)
    api_calls_count = Column(Integer, default=0)
    videos_count = Column(Integer, default=0)
    projects_count = Column(Integer, default=0)
    active_users_count = Column(Integer, default=0)