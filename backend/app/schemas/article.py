from pydantic import BaseModel, field_validator
from typing import Optional, List, Any
from datetime import datetime
import json


class ArticleBase(BaseModel):
    topic: str
    category: str = "生活"
    outline: Optional[str] = None


class ArticleCreate(ArticleBase):
    pass


class ArticleUpdate(BaseModel):
    title: Optional[str] = None
    content_text: Optional[str] = None
    outline: Optional[str] = None
    category: Optional[str] = None


class ImageInfo(BaseModel):
    url: str
    position: int
    prompt: str


class ArticleResponse(BaseModel):
    id: int
    user_id: int
    category: str
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
    
    @field_validator('images', mode='before')
    @classmethod
    def parse_images(cls, v: Any) -> Optional[List[dict]]:
        if isinstance(v, str):
            try:
                return json.loads(v)
            except:
                return None
        return v
    
    class Config:
        from_attributes = True


class UsageResponse(BaseModel):
    used_today: int
    limit: int
    remaining: int
    reset_time: str


class CategoryResponse(BaseModel):
    name: str
    icon: str
    example_topics: List[str]