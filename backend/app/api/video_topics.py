from typing import List
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
import json
import re

from app.database import get_db
from app.models.video_topic_category import VideoTopicCategory
from app.schemas.video_topic import (
    VideoTopicCategoryResponse,
    GenerateTopicRequest,
    GenerateTopicResponse
)
from app.utils.llm_factory import LLMFactory

router = APIRouter(prefix="/video-topics", tags=["video-topics"])


@router.get("/categories", response_model=List[dict])
async def get_video_topic_categories(
    db: Session = Depends(get_db)
):
    """获取所有视频主题方向"""
    categories = db.query(VideoTopicCategory).filter(
        VideoTopicCategory.is_active == True
    ).order_by(VideoTopicCategory.sort_order).all()
    
    return [{
        "id": c.id,
        "name": c.name,
        "icon": c.icon,
        "description": c.description,
        "example_topics": json.loads(c.example_topics) if c.example_topics else []
    } for c in categories]


@router.post("/generate", response_model=GenerateTopicResponse)
async def generate_topic_from_prompt(
    request: GenerateTopicRequest,
    db: Session = Depends(get_db)
):
    """AI生成主题"""
    category = db.query(VideoTopicCategory).filter(
        VideoTopicCategory.name == request.category
    ).first()
    
    if not category:
        raise HTTPException(status_code=404, detail="方向不存在")
    
    client = LLMFactory.get_client()
    
    prompt = f"""根据以下信息生成5个热门视频主题：

方向：{category.name}
描述：{category.description or '无'}
关键词：{request.keyword or '无'}
生成提示：{category.topic_generation_prompt or '生成该方向的热门主题'}

要求：
1. 每个主题10-20字
2. 简洁吸引人
3. 符合该方向的风格

直接输出主题列表，格式如下：
1. [主题1]
2. [主题2]
3. [主题3]
4. [主题4]
5. [主题5]"""

    response = await client.chat(
        messages=[{"role": "user", "content": prompt}],
        model=LLMFactory.get_chat_model(),
        temperature=0.8
    )
    
    topics = []
    lines = response.strip().split('\n')
    for line in lines:
        match = re.match(r'^\d+\.\s*(.+)', line.strip())
        if match:
            topic = match.group(1).strip()
            if topic and len(topic) > 0:
                topics.append(topic)
    
    return {"topics": topics}