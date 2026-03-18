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
    custom_code: Optional[str] = None  # 用户自定义参考代码
    status: Optional[str] = None
    template_id: Optional[int] = None


class ProjectResponse(ProjectBase):
    id: int
    user_id: int
    final_script: Optional[str]
    manim_code: Optional[str]
    custom_code: Optional[str]  # 用户自定义参考代码
    status: str
    template_id: Optional[int]
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
