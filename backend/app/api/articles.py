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
    GenerateContentRequest,
    RewriteOutlineSectionRequest,
    RewriteContentSectionRequest,
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


@router.post("/meta/generate-topics")
async def generate_article_topics(
    payload: dict,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    service = ArticleGenService(db)
    category = payload.get("category") or "生活"
    keyword = payload.get("keyword") or ""
    topics = await service.generate_topic_suggestions(str(category), str(keyword))
    return {"topics": topics}


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
    allowed, reason = current_user.can_use_module("article")
    if not allowed:
        raise HTTPException(status_code=403, detail=reason or "当前账号未开通公众号文章模块")
    
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
    if not getattr(article, 'quota_consumed', 0):
        usage = await service.check_daily_limit(current_user.id)
        if usage["remaining"] == 0:
            raise HTTPException(status_code=429, detail="本月公众号文章使用次数已达上限")
    if not getattr(article, 'quota_consumed', 0):
        usage = await service.check_daily_limit(current_user.id)
        if usage["remaining"] == 0:
            raise HTTPException(status_code=429, detail="本月公众号文章使用次数已达上限")

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
    if not getattr(article, 'quota_consumed', 0):
        usage = await service.check_daily_limit(current_user.id)
        if usage["remaining"] == 0:
            raise HTTPException(status_code=429, detail="本月公众号文章使用次数已达上限")

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
    if not getattr(article, 'quota_consumed', 0):
        await service.increment_usage(current_user.id)
        article = await service.update_article(article_id, quota_consumed=1)

    return {
        "title": result["title"],
        "content": result["content"],
        "word_count": result["word_count"]
    }


@router.post("/{article_id}/generate-draft", response_model=ArticleResponse)
async def generate_draft(
    article_id: int,
    request: GenerateContentRequest = None,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    service = ArticleGenService(db)
    article = service.get_article(article_id)
    if not article or article.user_id != current_user.id:
        raise HTTPException(status_code=404, detail="文章不存在")
    if not getattr(article, 'quota_consumed', 0):
        usage = await service.check_daily_limit(current_user.id)
        if usage["remaining"] == 0:
            raise HTTPException(status_code=429, detail="本月公众号文章使用次数已达上限")

    updated = await service.generate_draft(article_id, request.requirement if request else None)
    if not getattr(updated, 'quota_consumed', 0):
        await service.increment_usage(current_user.id)
        updated = await service.update_article(article_id, quota_consumed=1)
    return ArticleResponse.from_orm(updated)


@router.post("/{article_id}/rewrite-outline-section")
async def rewrite_outline_section(
    article_id: int,
    request: RewriteOutlineSectionRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    service = ArticleGenService(db)
    article = service.get_article(article_id)
    if not article or article.user_id != current_user.id:
        raise HTTPException(status_code=404, detail="文章不存在")

    rewritten = await service.rewrite_outline_section(
        topic=article.topic,
        category=article.category or "生活",
        current_outline=article.outline or "",
        section_text=request.section_text,
        requirement=request.requirement,
    )
    return {"section_text": rewritten}


@router.post("/{article_id}/rewrite-content-section")
async def rewrite_content_section(
    article_id: int,
    request: RewriteContentSectionRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    service = ArticleGenService(db)
    article = service.get_article(article_id)
    if not article or article.user_id != current_user.id:
        raise HTTPException(status_code=404, detail="文章不存在")

    rewritten = await service.rewrite_content_section(
        topic=article.topic,
        category=article.category or "生活",
        article_title=request.article_title or article.title or article.topic,
        current_outline=article.outline or "",
        section_text=request.section_text,
        requirement=request.requirement,
    )
    return {"section_text": rewritten}


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
            image_local_url, image_url, storage = await image_gen_service.generate_image(img_info["prompt"])
            print(f"[ImageGen] 第{idx+1}张图片生成成功")
            return {
                "success": True,
                "index": idx,
                "image": {
                    "url": image_url,
                    "local_url": image_local_url,
                    "position": img_info["position"],
                    "anchor_paragraph": img_info.get("anchor_paragraph"),
                    "prompt": img_info["prompt"],
                    "type": img_info.get("type", "content"),
                    "storage": storage,
                    "related_text": img_info.get("related_text"),
                    "scene_subject": img_info.get("scene_subject"),
                    "scene_action": img_info.get("scene_action"),
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
        new_local_url, new_url, storage = await image_gen_service.generate_image(old_image["prompt"])
        
        images[image_index]["url"] = new_url
        images[image_index]["local_url"] = new_local_url
        images[image_index]["storage"] = storage
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
        if not getattr(article, 'quota_consumed', 0):
            await service.increment_usage(current_user.id)
            article = await service.update_article(article_id, quota_consumed=1)
    
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
