import asyncio
from typing import List
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from pydantic import BaseModel

from app.database import get_db
from app.models.user import User
from app.models.article import Article
from app.models.favorite_topic import FavoriteTopic
from app.api.auth import get_current_user
from app.schemas.article import (
    ArticleCreate,
    ArticleUpdate,
    ArticleResponse,
    UsageResponse,
    CategoryResponse,
    GenerateOutlineRequest,
    GenerateContentRequest
)
from app.services.article_gen import ArticleGenService
from app.services.image_gen import image_gen_service
from app.article_prompts import ARTICLE_CATEGORIES


class FavoriteTopicCreate(BaseModel):
    topic: str
    category: str = "生活"


class FavoriteTopicResponse(BaseModel):
    id: int
    topic: str
    category: str
    
    class Config:
        from_attributes = True

router = APIRouter(prefix="/articles", tags=["articles"])


@router.get("/meta/categories", response_model=List[CategoryResponse])
async def get_categories():
    """获取创作方向列表"""
    categories = []
    for name, data in ARTICLE_CATEGORIES.items():
        categories.append(CategoryResponse(
            name=name,
            icon=data["icon"],
            example_topics=data["example_topics"]
        ))
    return categories


@router.get("/usage", response_model=UsageResponse)
async def get_usage(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    service = ArticleGenService(db)
    usage = await service.check_daily_limit(current_user.id)
    return UsageResponse(**usage)


@router.post("", response_model=ArticleResponse)
async def create_article(
    article_data: ArticleCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    service = ArticleGenService(db)
    
    usage = await service.check_daily_limit(current_user.id)
    if usage["remaining"] <= 0:
        raise HTTPException(status_code=429, detail="今日使用次数已达上限")
    
    article = await service.create_article(
        user_id=current_user.id,
        topic=article_data.topic,
        category=article_data.category,
        outline=article_data.outline
    )
    
    return ArticleResponse.from_orm(article)


@router.post("/{article_id}/generate-outline")
async def generate_outline(
    article_id: int,
    request: GenerateOutlineRequest = None,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    service = ArticleGenService(db)

    article = service.get_article(article_id)
    if not article or article.user_id != current_user.id:
        raise HTTPException(status_code=404, detail="文章不存在")

    requirement = request.requirement if request else None
    result = await service.generate_outline(article.topic, article.category, requirement)

    article = await service.update_article(
        article_id,
        outline=result["outline"],
        title=result["title"]
    )

    return {
        "outline": result["outline"],
        "title": result["title"]
    }


@router.post("/{article_id}/generate-content")
async def generate_content(
    article_id: int,
    request: GenerateContentRequest = None,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    service = ArticleGenService(db)

    article = service.get_article(article_id)
    if not article or article.user_id != current_user.id:
        raise HTTPException(status_code=404, detail="文章不存在")

    if not article.outline:
        outline_result = await service.generate_outline(article.topic, article.category)
        article = await service.update_article(
            article_id,
            outline=outline_result["outline"],
            title=outline_result["title"]
        )

    requirement = request.requirement if request else None
    result = await service.generate_content(article.topic, article.outline, article.category, requirement)

    article = await service.update_article(
        article_id,
        title=result["title"],
        content_text=result["content"],
        word_count=result["word_count"],
        status="draft"
    )

    return {
        "title": result["title"],
        "content": result["content"],
        "word_count": result["word_count"]
    }


@router.post("/{article_id}/generate-images")
async def generate_images(
    article_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    service = ArticleGenService(db)
    
    article = service.get_article(article_id)
    if not article or article.user_id != current_user.id:
        raise HTTPException(status_code=404, detail="文章不存在")
    
    if not article.content_text:
        raise HTTPException(status_code=400, detail="请先生成文章内容")
    
    smart_images = await service.generate_smart_images(
        article.content_text,
        article.topic,
        article.category or "生活"
    )
    
    print(f"[ImageGen] 需要生成 {len(smart_images)} 张配图")
    
    # 并发生成所有图片
    async def generate_single_image(idx: int, img_info: dict):
        try:
            print(f"[ImageGen] 开始生成第{idx+1}张图片: {img_info['prompt'][:50]}...")
            image_url = await image_gen_service.generate_image(img_info["prompt"])
            print(f"[ImageGen] 第{idx+1}张图片生成成功")
            return {
                "success": True,
                "index": idx,
                "image": {
                    "url": image_url,
                    "position": img_info["position"],
                    "prompt": img_info["prompt"],
                    "type": img_info.get("type", "content")
                }
            }
        except Exception as e:
            import logging
            logging.error(f"[ImageGen] 第{idx+1}张图片生成失败: {e}", exc_info=True)
            return {
                "success": False,
                "index": idx,
                "error": str(e)
            }
    
    # 使用asyncio.gather并发生成
    tasks = [generate_single_image(i, img_info) for i, img_info in enumerate(smart_images)]
    results = await asyncio.gather(*tasks)
    
    # 按顺序收集成功的图片
    generated_images = []
    for result in sorted(results, key=lambda x: x["index"]):
        if result["success"]:
            generated_images.append(result["image"])
    
    success_count = len(generated_images)
    total_count = len(smart_images)
    print(f"[ImageGen] 配图生成完成，成功{success_count}/{total_count}张")
    
    article = await service.update_article(article_id, images=generated_images)
    
    return {
        "images": generated_images,
        "total": total_count,
        "success": success_count,
        "failed": total_count - success_count
    }


@router.post("/{article_id}/regenerate-image/{image_index}")
async def regenerate_single_image(
    article_id: int,
    image_index: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """重新生成单张图片"""
    service = ArticleGenService(db)
    
    article = service.get_article(article_id)
    if not article or article.user_id != current_user.id:
        raise HTTPException(status_code=404, detail="文章不存在")
    
    import json
    images = article.images
    if isinstance(images, str):
        images = json.loads(images)
    
    if not images or image_index < 0 or image_index >= len(images):
        raise HTTPException(status_code=400, detail="图片索引无效")
    
    old_image = images[image_index]
    
    try:
        print(f"[ImageGen] 重新生成第{image_index+1}张图片...")
        new_url = await image_gen_service.generate_image(old_image["prompt"])
        
        images[image_index]["url"] = new_url
        article = await service.update_article(article_id, images=images)
        
        print(f"[ImageGen] 第{image_index+1}张图片重新生成成功")
        return {
            "message": "图片重新生成成功",
            "image": images[image_index]
        }
    except Exception as e:
        import logging
        logging.error(f"[ImageGen] 图片重新生成失败: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"图片生成失败: {str(e)}")


@router.put("/{article_id}/images")
async def update_article_images(
    article_id: int,
    images: List[dict],
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """更新文章图片（支持排序和删除）"""
    service = ArticleGenService(db)
    
    article = service.get_article(article_id)
    if not article or article.user_id != current_user.id:
        raise HTTPException(status_code=404, detail="文章不存在")
    
    article = await service.update_article(article_id, images=images)
    
    return {
        "message": "图片更新成功",
        "images": images
    }


@router.delete("/{article_id}/images/{image_index}")
async def delete_article_image(
    article_id: int,
    image_index: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """删除单张图片"""
    service = ArticleGenService(db)
    
    article = service.get_article(article_id)
    if not article or article.user_id != current_user.id:
        raise HTTPException(status_code=404, detail="文章不存在")
    
    import json
    images = article.images
    if isinstance(images, str):
        images = json.loads(images)
    
    if not images or image_index < 0 or image_index >= len(images):
        raise HTTPException(status_code=400, detail="图片索引无效")
    
    deleted_image = images.pop(image_index)
    article = await service.update_article(article_id, images=images)
    
    return {
        "message": "图片删除成功",
        "images": images
    }


@router.post("/{article_id}/generate-html")
async def generate_html(
    article_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    service = ArticleGenService(db)
    
    article = service.get_article(article_id)
    if not article or article.user_id != current_user.id:
        raise HTTPException(status_code=404, detail="文章不存在")
    
    if not article.content_text:
        raise HTTPException(status_code=400, detail="请先生成文章内容")
    
    html = service.convert_to_html(
        article.title or "公众号文章",
        article.content_text,
        article.images or []
    )
    
    article = await service.update_article(
        article_id,
        content_html=html,
        status="completed"
    )
    
    await service.increment_usage(current_user.id)
    
    return {"html": html}


@router.post("/{article_id}/generate-all")
async def generate_all(
    article_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    service = ArticleGenService(db)
    
    article = service.get_article(article_id)
    if not article or article.user_id != current_user.id:
        raise HTTPException(status_code=404, detail="文章不存在")
    
    if not article.outline:
        outline = await service.generate_outline(article.topic)
        article = await service.update_article(article_id, outline=outline)
    
    if not article.content_text:
        result = await service.generate_content(article.topic, article.outline)
        article = await service.update_article(
            article_id,
            title=result["title"],
            content_text=result["content"],
            word_count=result["word_count"]
        )
    
    if not article.images:
        images = await image_gen_service.generate_images_for_article(
            article.topic,
            article.content_text
        )
        article = await service.update_article(article_id, images=images)
    
    html = service.convert_to_html(
        article.title or "公众号文章",
        article.content_text,
        article.images or []
    )
    
    article = await service.update_article(
        article_id,
        content_html=html,
        status="completed"
    )
    
    await service.increment_usage(current_user.id)
    
    return ArticleResponse.from_orm(article)


@router.get("", response_model=List[ArticleResponse])
async def list_articles(
    limit: int = 10,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    service = ArticleGenService(db)
    articles = service.get_user_articles(current_user.id, limit)
    return [ArticleResponse.from_orm(article) for article in articles]


@router.get("/{article_id}", response_model=ArticleResponse)
async def get_article(
    article_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    service = ArticleGenService(db)
    article = service.get_article(article_id)
    
    if not article or article.user_id != current_user.id:
        raise HTTPException(status_code=404, detail="文章不存在")
    
    return ArticleResponse.from_orm(article)


@router.put("/{article_id}", response_model=ArticleResponse)
async def update_article(
    article_id: int,
    update_data: ArticleUpdate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    service = ArticleGenService(db)
    
    article = service.get_article(article_id)
    if not article or article.user_id != current_user.id:
        raise HTTPException(status_code=404, detail="文章不存在")
    
    update_dict = update_data.dict(exclude_unset=True)
    article = await service.update_article(article_id, **update_dict)
    
    return ArticleResponse.from_orm(article)


@router.delete("/{article_id}")
async def delete_article(
    article_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    service = ArticleGenService(db)
    
    article = service.get_article(article_id)
    if not article or article.user_id != current_user.id:
        raise HTTPException(status_code=404, detail="文章不存在")
    
    success = service.delete_article(article_id)
    
    if success:
        return {"message": "删除成功"}
    else:
        raise HTTPException(status_code=500, detail="删除失败")


# ==================== 收藏主题管理 ====================

@router.post("/favorites", response_model=FavoriteTopicResponse)
async def add_favorite_topic(
    data: FavoriteTopicCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """添加收藏主题"""
    existing = db.query(FavoriteTopic).filter(
        FavoriteTopic.user_id == current_user.id,
        FavoriteTopic.topic == data.topic
    ).first()
    
    if existing:
        raise HTTPException(status_code=400, detail="该主题已收藏")
    
    favorite = FavoriteTopic(
        user_id=current_user.id,
        topic=data.topic,
        category=data.category
    )
    db.add(favorite)
    db.commit()
    db.refresh(favorite)
    
    return favorite


@router.get("/favorites", response_model=List[FavoriteTopicResponse])
async def list_favorite_topics(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """获取收藏主题列表"""
    favorites = db.query(FavoriteTopic).filter(
        FavoriteTopic.user_id == current_user.id
    ).order_by(FavoriteTopic.created_at.desc()).all()
    
    return favorites


@router.delete("/favorites/{favorite_id}")
async def delete_favorite_topic(
    favorite_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """删除收藏主题"""
    favorite = db.query(FavoriteTopic).filter(
        FavoriteTopic.id == favorite_id,
        FavoriteTopic.user_id == current_user.id
    ).first()
    
    if not favorite:
        raise HTTPException(status_code=404, detail="收藏主题不存在")
    
    db.delete(favorite)
    db.commit()
    
    return {"message": "删除成功"}