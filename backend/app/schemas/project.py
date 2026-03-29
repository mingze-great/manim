from pydantic import BaseModel
from datetime import datetime
from typing import Optional, List


class ProjectBase(BaseModel):
    title: str
    theme: str


class ProjectCreate(ProjectBase):
    pass


class ProjectUpdate(BaseModel):
    title: Optional[str] = None
    theme: Optional[str] = None
    final_script: Optional[str] = None
    manim_code: Optional[str] = None
    custom_code: Optional[str] = None
    status: Optional[str] = None
    template_id: Optional[int] = None
    video_url: Optional[str] = None
    error_message: Optional[str] = None


class ProjectResponse(ProjectBase):
    id: int
    user_id: int
    final_script: Optional[str]
    manim_code: Optional[str]
    custom_code: Optional[str]
    status: str
    template_id: Optional[int]
    video_url: Optional[str]
    error_message: Optional[str]
    render_fail_count: int = 0
    created_at: datetime
    updated_at: datetime
    
    class Config:
        from_attributes = True


class ConversationCreate(BaseModel):
    content: str


class ConversationResponse(BaseModel):
    id: int
    project_id: int
    role: str
    content: str
    created_at: datetime
    
    class Config:
        from_attributes = True
