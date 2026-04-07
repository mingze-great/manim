from typing import List
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.user import User
from app.models.article import Article
from app.api.auth import get_current_user
from app.schemas.article import (
    ArticleCreate,
    ArticleUpdate,
    ArticleResponse,
    UsageResponse
)
from app.services.article_gen import ArticleGenService
from app.services.image_gen import image_gen_service

router = APIRouter(prefix="/articles", tags=["articles"])


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
        outline=article_data.outline
    )
    
    return ArticleResponse.from_orm(article)


@router.post("/{article_id}/generate-outline")
async def generate_outline(
    article_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    service = ArticleGenService(db)
    
    article = service.get_article(article_id)
    if not article or article.user_id != current_user.id:
        raise HTTPException(status_code=404, detail="文章不存在")
    
    outline = await service.generate_outline(article.topic)
    
    article = await service.update_article(article_id, outline=outline)
    
    return {"outline": outline}


@router.post("/{article_id}/generate-content")
async def generate_content(
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
    
    result = await service.generate_content(article.topic, article.outline)
    
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
    
    images = await image_gen_service.generate_images_for_article(
        article.topic,
        article.content_text
    )
    
    article = await service.update_article(article_id, images=images)
    
    return {"images": images}


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