from pydantic import BaseModel
from typing import Optional, List
from datetime import datetime


class ArticleBase(BaseModel):
    topic: str
    outline: Optional[str] = None


class ArticleCreate(ArticleBase):
    pass


class ArticleUpdate(BaseModel):
    title: Optional[str] = None
    content_text: Optional[str] = None
    outline: Optional[str] = None


class ImageInfo(BaseModel):
    url: str
    position: int
    prompt: str


class ArticleResponse(BaseModel):
    id: int
    user_id: int
    title: Optional[str]
    topic: str
    outline: Optional[str]
    content_html: Optional[str]
    content_text: Optional[str]
    images: Optional[List[ImageInfo]]
    status: str
    word_count: int
    created_at: datetime
    updated_at: datetime
    
    class Config:
        from_attributes = True


class UsageResponse(BaseModel):
    used_today: int
    limit: int
    remaining: int
    reset_time: str