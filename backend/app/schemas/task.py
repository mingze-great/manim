from pydantic import BaseModel
from datetime import datetime
from typing import Optional


class TaskCreate(BaseModel):
    project_id: int
    template_id: Optional[int] = None


class TaskResponse(BaseModel):
    id: int
    project_id: int
    status: str
    progress: int
    video_url: Optional[str]
    error_message: Optional[str]
    log: Optional[str]
    started_at: Optional[datetime]
    completed_at: Optional[datetime]
    created_at: datetime
    
    class Config:
        from_attributes = True


class TaskStatusResponse(BaseModel):
    status: str
    progress: int
    video_url: Optional[str] = None
    error_message: Optional[str] = None
    log: Optional[str] = None


class FixCodeRequest(BaseModel):
    error_message: str
    current_code: str


class FixCodeResponse(BaseModel):
    success: bool
    fixed_code: Optional[str] = None
    fix_description: Optional[str] = None
    message: Optional[str] = None
