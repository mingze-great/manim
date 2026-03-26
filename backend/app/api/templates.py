from typing import Annotated, Optional
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.user import User
from app.models.template import Template
from app.schemas.template import TemplateCreate, TemplateResponse, TemplateListResponse, TemplateUpdate
from app.api.auth import get_current_user

router = APIRouter(prefix="/templates", tags=["templates"])


@router.get("", response_model=TemplateListResponse)
def get_templates(
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[Session, Depends(get_db)],
    skip: int = Query(0, ge=0),
    limit: int = Query(10, ge=1, le=100),
    category: Optional[str] = Query(None),
):
    current_user_obj = current_user
    
    # 获取当前用户权限并执行查询
    user_is_admin = bool(current_user_obj.is_admin)
    current_user_id = current_user_obj.id
    
    # 获取系统模板
    if user_is_admin:
        # 管理员能看到所有系统模板
        system_query_result = db.query(Template).filter(
            Template.is_active.is_(True),
            Template.is_system.is_(True)
        ).offset(skip).limit(limit).all()
    else:
        # 普通用户只能看到 is_visible=True 或 NULL 的系统模板
        system_query_result = db.query(Template).filter(
            Template.is_active.is_(True),
            Template.is_system.is_(True),
            (Template.is_visible.is_(True) | Template.is_visible.is_(None))
        ).offset(skip).limit(limit).all()
    
    # 获取用户模板
    if user_is_admin:
        # 管理员能看到所有非系统模板
        user_query_result = db.query(Template).filter(
            Template.is_active.is_(True),
            Template.is_system.is_(False)
        ).offset(skip).limit(limit).all()
    else:
        # 普通用户只能看到自己创建的模板
        user_query_result = db.query(Template).filter(
            Template.is_active.is_(True),
            Template.user_id == current_user_id
        ).offset(skip).limit(limit).all()
    
    # 将换 SQLAlchemy 模型为 Pydantic 响应模型
    system_responses = [TemplateResponse.model_validate(t) for t in system_query_result]
    user_responses = [TemplateResponse.model_validate(t) for t in user_query_result]
    
    return TemplateListResponse(
        system_templates=system_responses,
        user_templates=user_responses
    )


@router.get("/{template_id}", response_model=TemplateResponse)
def get_template(
    template_id: int,
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[Session, Depends(get_db)]
):
    template_model = db.query(Template).filter(Template.id == template_id, Template.is_active.is_(True)).first()
    if not template_model:
        raise HTTPException(status_code=404, detail="Template not found")
    
    # 获取当前用户的权限数据
    current_user_obj = current_user
    is_current_admin = bool(current_user_obj.is_admin)  # 转换为 Python bool 类型
    current_user_id = current_user_obj.id
    
    # 获取模板的相关数据
    template_data = db.query(Template).filter(
        Template.id == template_id,
        Template.is_active.is_(True)
    ).first()
    
    if not template_data:
        raise HTTPException(status_code=404, detail="Template not found")
    
    # 获取权限值
    template_is_system_value = bool(template_data.is_system)  # 转换为Python bool
    template_user_id = template_data.user_id
    
    # 如果不是系统模板且不是当前用户创建的，且当前用户不是管理员
    template_not_system = not template_is_system_value
    template_not_current_user = template_user_id != current_user_id  
    user_not_admin = not is_current_admin
    
    if template_not_system and template_not_current_user and user_not_admin:
        raise HTTPException(status_code=404, detail="Template not found")
    
    # 通过SQLAlchemy ORM属性增加使用次数
    template_db_obj = db.query(Template).filter(
        Template.id == template_id,
        Template.is_active.is_(True)
    ).first()
    
    # 安全地获取当前使用次数并计算新次数（使用属性名称和默认值）
    current_usage_count = template_db_obj.usage_count if template_db_obj.usage_count is not None else 0
    template_db_obj.usage_count = current_usage_count + 1  # type: ignore
    db.commit()
    
    return TemplateResponse.model_validate(template_db_obj)


@router.post("", response_model=TemplateResponse)
def create_template(
    template: TemplateCreate,
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[Session, Depends(get_db)]
):
    current_user_obj = current_user
    user_is_admin_value = bool(current_user_obj.is_admin)  # 转换为 Python bool类型
    template_is_system_bool = bool(template.is_system)  # 转换为 Python bool类型
    
    # 普通用户不能创建系统模板
    if template_is_system_bool and not user_is_admin_value:
        raise HTTPException(status_code=403, detail="Only administrators can create system templates")
    
    current_user_id = current_user_obj.id
    new_template = Template(
        name=template.name,
        description=template.description,
        category=template.category,
        code=template.code,
        thumbnail=template.thumbnail,
        prompt=template.prompt,
        is_system=template_is_system_bool,
        user_id=current_user_id if not template_is_system_bool else None,
        is_active=True,
        is_visible=True
    )
    db.add(new_template)
    db.commit()
    db.refresh(new_template)
    return TemplateResponse.model_validate(new_template)


@router.put("/{template_id}", response_model=TemplateResponse)
def update_template(
    template_id: int,
    update_data: TemplateUpdate,
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[Session, Depends(get_db)]
):
    template = db.query(Template).filter(
        Template.id == template_id
    ).first()
    
    if not template:
        raise HTTPException(status_code=404, detail="Template not found")
    
    # 获取权限信息
    current_user_obj = current_user
    current_user_id = current_user_obj.id
    current_is_admin_value = bool(current_user_obj.is_admin)  # 转换为 Python bool类型
    
    is_template_system_value = bool(template.is_system)  # 转换为 Python bool类型
    template_owner_id = template.user_id
    
    # 通过普通变量判断权限 - 避免直接使用SQLAlchemy的布尔字段进行判断
    template_owned_by_user = template_owner_id == current_user_id
    
    # 转换为python变量再进行比较检查权限
    is_not_admin_and_not_owner = not current_is_admin_value and not template_owned_by_user
    is_not_admin_and_system_template = not current_is_admin_value and is_template_system_value
    
    # 检查是否可以修改模板
    if is_not_admin_and_system_template or is_not_admin_and_not_owner:
        if is_template_system_value:
            raise HTTPException(status_code=403, detail="Cannot modify system template")
        if template_owner_id != current_user_id:
            raise HTTPException(status_code=403, detail="Not authorized")
    
    update_data_dict = update_data.model_dump(exclude_unset=True)
    for field, value in update_data_dict.items():
        if value is not None:
            setattr(template, field, value)
    
    db.commit()
    db.refresh(template)
    return TemplateResponse.model_validate(template)


@router.delete("/{template_id}")
def delete_template(
    template_id: int,
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[Session, Depends(get_db)]
):
    template = db.query(Template).filter(
        Template.id == template_id
    ).first()
    
    if not template:
        raise HTTPException(status_code=404, detail="Template not found")
    
    # 获取当前用户信息并转换为python原生类型避免SQLAlchemy列类型判断
    current_user_obj = current_user
    template_is_system_value = bool(template.is_system)  # 转换为 Python 类型
    template_user_id_value = template.user_id  # 获取用户ID
    current_user_id_value = current_user_obj.id  # 获取当前用户ID
    current_is_admin_value = bool(current_user_obj.is_admin)  # 转换为 Python 类型
    
    # 检查权限：
    # 1. 管理员可以删除任何模板
    # 2. 普通用户可以删除自己的非系统模板
    admin_can_delete = current_is_admin_value
    user_can_delete = not template_is_system_value and template_user_id_value == current_user_id_value
    
    can_delete = admin_can_delete or user_can_delete
    
    if not can_delete:
        if template_is_system_value:
            raise HTTPException(status_code=403, detail="Cannot delete system template")
        else:
            raise HTTPException(status_code=403, detail="Not authorized")
    
    # 设置为非激活状态（软删除）
    template.is_active = False  # type: ignore
    db.commit()
    return {"message": "Template deleted"}
