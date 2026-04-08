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
    
    requirement = request.requirement if request else None
    
    async def event_generator():
        try:
            full_content = ""
            title = ""
            
            async for chunk in service.generate_outline_stream(
                article.topic, 
                article.category, 
                requirement
            ):
                full_content += chunk
                # 发送SSE事件
                yield f"data: {json.dumps({'content': chunk}, ensure_ascii=False)}\n\n"
            
            # 提取标题
            title = service.extract_title(full_content)
            
            # 更新数据库
            article.outline = full_content
            article.title = title
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
    
    # 如果没有大纲，先生成
    if not article.outline:
        from app.services.article_gen import ArticleGenService
        gen_service = ArticleGenService(db)
        result = await gen_service.generate_outline(article.topic, article.category)
        article.outline = result["outline"]
        article.title = result["title"]
        db.commit()
    
    requirement = request.requirement if request else None
    
    async def event_generator():
        try:
            full_content = ""
            
            async for chunk in service.generate_content_stream(
                article.topic,
                article.outline,
                article.category,
                requirement
            ):
                full_content += chunk
                # 发送SSE事件
                yield f"data: {json.dumps({'content': chunk}, ensure_ascii=False)}\n\n"
            
            # 更新数据库
            word_count = len(full_content.replace("\n", "").replace(" ", ""))
            article.content_text = full_content
            article.word_count = word_count
            article.status = "draft"
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