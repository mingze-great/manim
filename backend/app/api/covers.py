from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from pydantic import BaseModel
from typing import Optional, List
from app.database import get_db
from app.models.user import User
from app.models.cover import Cover
from app.models.cover_style import CoverStyle
from app.api.auth import get_current_user
from app.services.cover_generator import CoverGenerator
from datetime import datetime

router = APIRouter(prefix="/covers", tags=["covers"])


class CoverStyleResponse(BaseModel):
    id: int
    name: str
    description: Optional[str]
    base_prompt: str
    example_image_url: Optional[str]
    font_recommendation: Optional[str]
    color_recommendation: Optional[str]
    
    class Config:
        from_attributes = True


class CoverCreateRequest(BaseModel):
    style_id: Optional[int] = None
    title_line1: str
    title_line2: Optional[str] = None
    topic: str
    font_style: Optional[str] = "黑体"
    font_color: Optional[str] = "#333333"


class CoverResponse(BaseModel):
    id: int
    style_id: Optional[int]
    title_line1: str
    title_line2: Optional[str]
    topic: str
    font_style: Optional[str]
    font_color: Optional[str]
    image_url: Optional[str]
    local_url: Optional[str]
    created_at: datetime
    
    class Config:
        from_attributes = True


@router.get("/styles", response_model=List[CoverStyleResponse])
async def get_cover_styles(
    db: Session = Depends(get_db)
):
    styles = db.query(CoverStyle).filter(CoverStyle.is_active == True).all()
    return styles


@router.post("", response_model=CoverResponse)
async def create_cover(
    request: CoverCreateRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    generator = CoverGenerator(db)
    
    style = None
    if request.style_id:
        style = db.query(CoverStyle).filter(CoverStyle.id == request.style_id).first()
    
    result = await generator.generate_cover(
        user_id=current_user.id,
        topic=request.topic,
        title_line1=request.title_line1,
        title_line2=request.title_line2,
        style=style,
        font_style=request.font_style,
        font_color=request.font_color,
    )
    
    return result


@router.get("/{cover_id}", response_model=CoverResponse)
async def get_cover(
    cover_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    cover = db.query(Cover).filter(
        Cover.id == cover_id,
        Cover.user_id == current_user.id
    ).first()
    
    if not cover:
        raise HTTPException(status_code=404, detail="封面不存在")
    
    return cover


@router.post("/{cover_id}/regenerate", response_model=CoverResponse)
async def regenerate_cover(
    cover_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    cover = db.query(Cover).filter(
        Cover.id == cover_id,
        Cover.user_id == current_user.id
    ).first()
    
    if not cover:
        raise HTTPException(status_code=404, detail="封面不存在")
    
    generator = CoverGenerator(db)
    style = None
    if cover.style_id:
        style = db.query(CoverStyle).filter(CoverStyle.id == cover.style_id).first()
    
    result = await generator.generate_cover(
        user_id=current_user.id,
        topic=cover.topic,
        title_line1=cover.title_line1,
        title_line2=cover.title_line2,
        style=style,
        font_style=cover.font_style,
        font_color=cover.font_color,
        cover_id=cover_id,
    )
    
    return result


@router.get("/history", response_model=List[CoverResponse])
async def get_cover_history(
    limit: int = 20,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    covers = db.query(Cover).filter(
        Cover.user_id == current_user.id
    ).order_by(Cover.created_at.desc()).limit(limit).all()
    
    return covers