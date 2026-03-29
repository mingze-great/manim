from pydantic import BaseModel, EmailStr, field_validator, Field
from datetime import datetime
from typing import Optional
import re


class UserBase(BaseModel):
    username: str
    email: EmailStr


class UserCreate(UserBase):
    password: str = Field(..., min_length=8, max_length=50)
    
    @field_validator('password')
    @classmethod
    def validate_password(cls, v):
        if not re.search(r'[A-Za-z]', v):
            raise ValueError('密码必须包含字母')
        if not re.search(r'\d', v):
            raise ValueError('密码必须包含数字')
        return v


class UserLogin(BaseModel):
    username: str
    password: str


class UserResponse(UserBase):
    id: int
    is_active: bool
    is_admin: bool = False
    is_approved: bool = True
    expires_at: Optional[datetime] = None
    api_calls_count: int = 0
    videos_count: int = 0
    last_active_at: Optional[datetime] = None
    created_at: datetime
    
    class Config:
        from_attributes = True


class Token(BaseModel):
    access_token: str
    token_type: str


class TokenData(BaseModel):
    username: Optional[str] = None


class UserUpdate(BaseModel):
    is_active: Optional[bool] = None
    is_admin: Optional[bool] = None


class UserStats(BaseModel):
    total_projects: int
    total_tasks: int
    completed_tasks: int
    failed_tasks: int


class AuditLogResponse(BaseModel):
    id: int
    user_id: Optional[int]
    username: Optional[str]
    action: str
    resource: Optional[str]
    resource_id: Optional[int]
    details: Optional[str]
    ip_address: Optional[str]
    created_at: datetime
    
    class Config:
        from_attributes = True


class SystemStats(BaseModel):
    total_users: int
    active_users: int
    total_projects: int
    total_videos: int
    api_calls_today: int
    cpu_usage: float = 0.0
    memory_usage: float = 0.0
    disk_usage: float = 0.0


class ProjectStatus(BaseModel):
    project_id: int
    project_title: str
    status: str
    status_text: str
    updated_at: Optional[datetime] = None


class RecentProject(BaseModel):
    id: int
    title: str
    status: str
    status_text: str
    created_at: datetime
    has_video: bool = False
    error_message: Optional[str] = None


class TaskLog(BaseModel):
    project_id: int
    project_title: str
    status: str
    error_message: Optional[str] = None
    log: Optional[str] = None
    created_at: Optional[datetime] = None


class UserDetail(BaseModel):
    id: int
    username: str
    email: str
    is_active: bool
    is_admin: bool = False
    is_approved: bool = True
    expires_at: Optional[datetime] = None
    created_at: datetime
    last_active_at: Optional[datetime] = None
    
    total_projects: int = 0
    videos_count: int = 0
    token_usage: int = 0
    
    current_status: Optional[ProjectStatus] = None
    recent_projects: list[RecentProject] = []
    latest_task: Optional[TaskLog] = None


class TokenUsageItem(BaseModel):
    id: int
    username: str
    chat_token_usage: int
    code_token_usage: int
    total_token_usage: int
    rank: int


class TokenUsageResponse(BaseModel):
    users: list[TokenUsageItem]
    total_chat_tokens: int
    total_code_tokens: int
    total_tokens: int
