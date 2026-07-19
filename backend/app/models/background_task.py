from sqlalchemy import Column, Integer, String, Text, DateTime, ForeignKey, JSON
from datetime import datetime
from app.database import Base


class BackgroundTask(Base):
    __tablename__ = "background_tasks"
    
    id = Column(Integer, primary_key=True, index=True)
    task_type = Column(String(50), nullable=False)
    project_id = Column(Integer, ForeignKey("projects.id"), nullable=False)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    
    status = Column(String(20), default="pending")
    progress = Column(Integer, default=0)
    message = Column(Text, nullable=True)
    
    input_params = Column(JSON, nullable=True)
    result = Column(Text, nullable=True)
    error = Column(Text, nullable=True)
    
    created_at = Column(DateTime, default=datetime.utcnow)
    started_at = Column(DateTime, nullable=True)
    completed_at = Column(DateTime, nullable=True)