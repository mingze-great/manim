from pydantic import BaseModel
from typing import Optional, List


class VideoTopicCategoryBase(BaseModel):
    name: str
    icon: str
    description: Optional[str] = None
    example_topics: List[str] = []
    topic_generation_prompt: Optional[str] = None
    system_prompt: Optional[str] = None
    is_active: bool = True
    sort_order: int = 0


class VideoTopicCategoryCreate(VideoTopicCategoryBase):
    pass


class VideoTopicCategoryUpdate(BaseModel):
    name: Optional[str] = None
    icon: Optional[str] = None
    description: Optional[str] = None
    example_topics: Optional[List[str]] = None
    topic_generation_prompt: Optional[str] = None
    system_prompt: Optional[str] = None
    is_active: Optional[bool] = None
    sort_order: Optional[int] = None


class VideoTopicCategoryResponse(VideoTopicCategoryBase):
    id: int
    
    class Config:
        from_attributes = True


class GenerateTopicRequest(BaseModel):
    category: str
    keyword: Optional[str] = None


class GenerateTopicResponse(BaseModel):
    topics: List[str]