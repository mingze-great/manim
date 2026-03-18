from typing import Annotated, List
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.user import User
from app.models.template import Template
from app.schemas.template import TemplateCreate, TemplateResponse, TemplateListResponse
from app.api.auth import get_current_user

router = APIRouter(prefix="/templates", tags=["templates"])


@router.get("", response_model=TemplateListResponse)
def get_templates(
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[Session, Depends(get_db)]
):
    system_templates = db.query(Template).filter(Template.is_system == True).all()
    user_templates = db.query(Template).filter(
        Template.user_id == current_user.id
    ).all()
    
    return TemplateListResponse(
        system_templates=system_templates,
        user_templates=user_templates
    )


@router.get("/{template_id}", response_model=TemplateResponse)
def get_template(
    template_id: int,
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[Session, Depends(get_db)]
):
    template = db.query(Template).filter(Template.id == template_id).first()
    if not template:
        raise HTTPException(status_code=404, detail="Template not found")
    
    if not template.is_system and template.user_id != current_user.id:
        raise HTTPException(status_code=404, detail="Template not found")
    
    return template


@router.post("", response_model=TemplateResponse)
def create_template(
    template: TemplateCreate,
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[Session, Depends(get_db)]
):
    new_template = Template(
        name=template.name,
        description=template.description,
        category=template.category,
        code=template.code,
        thumbnail=template.thumbnail,
        is_system=False,
        user_id=current_user.id
    )
    db.add(new_template)
    db.commit()
    db.refresh(new_template)
    return new_template


@router.delete("/{template_id}")
def delete_template(
    template_id: int,
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[Session, Depends(get_db)]
):
    template = db.query(Template).filter(
        Template.id == template_id,
        Template.is_system == False,
        Template.user_id == current_user.id
    ).first()
    
    if not template:
        raise HTTPException(status_code=404, detail="Template not found or cannot be deleted")
    
    db.delete(template)
    db.commit()
    return {"message": "Template deleted"}
