from pydantic import BaseModel
from datetime import datetime
from typing import Optional


class TemplateBase(BaseModel):
    name: str
    description: Optional[str] = None
    category: Optional[str] = None
    code: str
    thumbnail: Optional[str] = None


class TemplateCreate(TemplateBase):
    is_system: bool = False


class TemplateUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    category: Optional[str] = None
    code: Optional[str] = None
    thumbnail: Optional[str] = None


class TemplateResponse(TemplateBase):
    id: int
    is_system: bool
    user_id: Optional[int]
    usage_count: int
    created_at: datetime
    
    class Config:
        from_attributes = True


class TemplateListResponse(BaseModel):
    system_templates: list[TemplateResponse]
    user_templates: list[TemplateResponse]
