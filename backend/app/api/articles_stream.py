from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session
import json

from app.database import get_db
from app.models.user import User
from app.api.auth import get_current_user
from app.schemas.article import GenerateOutlineRequest, GenerateContentRequest
from app.services.article_gen_stream import ArticleGenStreamService

router = APIRouter(prefix="/articles-stream", tags=["articles-stream"])


@router.post("/{article_id}/generate-outline-stream")
async def generate_outline_stream(
    article_id: int,
    request: GenerateOutlineRequest = None,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """流式生成文章大纲"""
    service = ArticleGenStreamService(db)
    
    # 验证文章权限
    from app.models.article import Article
    article = db.query(Article).filter(Article.id == article_id).first()
    if not article or article.user_id != current_user.id:
        raise HTTPException(status_code=404, detail="文章不存在")
    if not getattr(article, 'quota_consumed', 0):
        from app.services.article_gen import ArticleGenService
        usage_check = ArticleGenService(db)
        usage = await usage_check.check_daily_limit(current_user.id)
        if usage["remaining"] == 0:
            raise HTTPException(status_code=429, detail="本月公众号文章使用次数已达上限")
    article_topic = str(article.topic)
    article_category = str(article.category or '生活')
    
    requirement = request.requirement if request else None
    
    async def event_generator():
        try:
            full_content = ""
            title = ""
            
            async for chunk in service.generate_outline_stream(
                article_topic,
                article_category,
                requirement
            ):
                full_content += chunk
                cleaned_full = service.clean_generated_text(full_content)
                yield f"data: {json.dumps({'content': chunk, 'full_content': cleaned_full, 'char_count': len(cleaned_full.replace(chr(10), '').replace(' ', ''))}, ensure_ascii=False)}\n\n"
            
            # 提取标题
            full_content = service.clean_generated_text(full_content)
            title = service.extract_title(full_content)
            
            # 更新数据库
            article_local = db.query(Article).filter(Article.id == article_id).first()
            if article_local:
                article_local.outline = full_content
                article_local.title = title
                db.commit()
            
            # 发送完成事件
            yield f"data: {json.dumps({'done': True, 'title': title}, ensure_ascii=False)}\n\n"
            
        except Exception as e:
            yield f"data: {json.dumps({'error': str(e)}, ensure_ascii=False)}\n\n"
    
    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no"
        }
    )


@router.post("/{article_id}/generate-content-stream")
async def generate_content_stream(
    article_id: int,
    request: GenerateContentRequest = None,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """流式生成文章内容"""
    service = ArticleGenStreamService(db)
    
    # 验证文章权限
    from app.models.article import Article
    article = db.query(Article).filter(Article.id == article_id).first()
    if not article or article.user_id != current_user.id:
        raise HTTPException(status_code=404, detail="文章不存在")
    if not getattr(article, 'quota_consumed', 0):
        from app.services.article_gen import ArticleGenService
        usage_check = ArticleGenService(db)
        usage = await usage_check.check_daily_limit(current_user.id)
        if usage["remaining"] == 0:
            raise HTTPException(status_code=429, detail="本月公众号文章使用次数已达上限")
    article_topic = str(article.topic)
    article_category = str(article.category or '生活')
    article_outline = str(article.outline or '')
    
    # 如果没有大纲，先生成
    if not article.outline:
        from app.services.article_gen import ArticleGenService
        gen_service = ArticleGenService(db)
        result = await gen_service.generate_outline(article_topic, article_category)
        article.outline = result["outline"]
        article.title = result["title"]
        db.commit()
        article_outline = result["outline"]
    
    requirement = request.requirement if request else None
    
    async def event_generator():
        try:
            full_content = ""
            
            async for chunk in service.generate_content_stream(
                article_topic,
                article_outline,
                article_category,
                requirement
            ):
                full_content += chunk
                cleaned_full = service.clean_generated_text(full_content)
                yield f"data: {json.dumps({'content': chunk, 'full_content': cleaned_full, 'char_count': len(cleaned_full.replace(chr(10), '').replace(' ', ''))}, ensure_ascii=False)}\n\n"
            
            # 更新数据库
            full_content = service.clean_generated_text(full_content)
            word_count = len(full_content.replace("\n", "").replace(" ", ""))
            article_local = db.query(Article).filter(Article.id == article_id).first()
            if article_local:
                article_local.content_text = full_content
                article_local.word_count = word_count
                article_local.status = "draft"
                if not getattr(article_local, 'quota_consumed', 0):
                    from app.services.article_gen import ArticleGenService
                    usage_check = ArticleGenService(db)
                    await usage_check.increment_usage(current_user.id)
                    article_local.quota_consumed = 1
                db.commit()
            
            # 发送完成事件
            yield f"data: {json.dumps({'done': True, 'word_count': word_count}, ensure_ascii=False)}\n\n"
            
        except Exception as e:
            yield f"data: {json.dumps({'error': str(e)}, ensure_ascii=False)}\n\n"
    
    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no"
        }
    )
