from typing import Optional, List
from datetime import datetime, timedelta
from fastapi import APIRouter, Depends, HTTPException, Query, Request
from sqlalchemy.orm import Session
from sqlalchemy import func
import json

from app.database import get_db
from app.models.article_category import ArticleCategory
from app.models.user import User, AuditLog
from app.models.project import Project
from app.models.article import Article
from app.models.task import Task
from app.schemas.article import ArticleCategoryCreate, ArticleCategoryUpdate
from app.schemas.user import UserResponse, UserUpdate, UserStats, AuditLogResponse, SystemStats, UserDetail, ProjectStatus, RecentProject, TaskLog, TokenUsageItem, TokenUsageResponse
from app.api.auth import get_current_user, get_current_admin_user
from app.config import get_settings
import psutil

router = APIRouter(prefix="/admin", tags=["admin"])
settings = get_settings()

MODULE_KEYS = ["visual", "stickman", "article"]


def _normalize_module_permissions(payload: dict, user: User) -> dict:
    permissions = user.get_module_permissions()
    for module_key in MODULE_KEYS:
        if module_key in payload and isinstance(payload[module_key], dict):
            current = permissions.get(module_key, {})
            current.update({
                "enabled": bool(payload[module_key].get("enabled", current.get("enabled", False))),
                "daily_limit": int(payload[module_key].get("daily_limit", current.get("daily_limit", 0)) or 0),
                "used_today": int(payload[module_key].get("used_today", current.get("used_today", 0)) or 0),
                "last_reset_date": payload[module_key].get("last_reset_date", current.get("last_reset_date")),
                "period": payload[module_key].get("period", current.get("period", "daily")),
            })
            permissions[module_key] = current
    return permissions


def _sync_permissions_to_db(db, user: User, permissions: dict):
    from app.models.user_module_permission import UserModulePermission
    for module_key in MODULE_KEYS:
        perm_data = permissions.get(module_key, {})
        record = db.query(UserModulePermission).filter(
            UserModulePermission.user_id == user.id,
            UserModulePermission.module_key == module_key
        ).first()
        
        if not record:
            record = UserModulePermission(
                user_id=user.id,
                module_key=module_key,
                enabled=perm_data.get("enabled", True),
                quota_limit=perm_data.get("daily_limit", 0),
                quota_used=perm_data.get("used_today", 0),
                period=perm_data.get("period", "daily"),
            )
            db.add(record)
        else:
            record.enabled = perm_data.get("enabled", record.enabled)
            record.quota_limit = perm_data.get("daily_limit", record.quota_limit)
            record.quota_used = perm_data.get("used_today", record.quota_used)
            record.period = perm_data.get("period", record.period)
    
    db.commit()
def _count_admin_users(users: list[User]) -> int:
    return sum(1 for user in users if bool(user.is_admin))


@router.get("/available-models")
async def get_available_models(
    current_user: User = Depends(get_current_user)
):
    """获取可用模型列表（已废弃，返回空列表）"""
    return {"models": []}


@router.get("/article-categories")
async def list_article_categories(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_admin_user)
):
    categories = db.query(ArticleCategory).order_by(ArticleCategory.sort_order).all()
    return [{
        "id": c.id,
        "name": c.name,
        "icon": c.icon,
        "system_prompt": c.system_prompt,
        "example_topics": c.example_topics,
        "image_prompt_template": c.image_prompt_template,
        "is_active": c.is_active,
        "sort_order": c.sort_order,
    } for c in categories]


@router.post("/article-categories")
async def create_article_category(
    data: ArticleCategoryCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_admin_user)
):
    existing = db.query(ArticleCategory).filter(ArticleCategory.name == data.name).first()
    if existing:
        raise HTTPException(status_code=400, detail="方向名称已存在")

    category = ArticleCategory(
        name=data.name,
        icon=data.icon,
        system_prompt=data.system_prompt,
        example_topics=json.dumps(data.example_topics, ensure_ascii=False),
        image_prompt_template=data.image_prompt_template,
        is_active=True,
        sort_order=0,
    )
    db.add(category)
    db.commit()
    db.refresh(category)
    return {"message": "创建成功", "id": category.id}


@router.put("/article-categories/{category_id}")
async def update_article_category(
    category_id: int,
    data: ArticleCategoryUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_admin_user)
):
    category = db.query(ArticleCategory).filter(ArticleCategory.id == category_id).first()
    if not category:
        raise HTTPException(status_code=404, detail="方向不存在")

    update_dict = data.model_dump(exclude_unset=True)
    for key, value in update_dict.items():
        if key == "example_topics" and value is not None:
            value = json.dumps(value, ensure_ascii=False)
        setattr(category, key, value)
    db.commit()
    return {"message": "更新成功"}


@router.delete("/article-categories/{category_id}")
async def delete_article_category(
    category_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_admin_user)
):
    category = db.query(ArticleCategory).filter(ArticleCategory.id == category_id).first()
    if not category:
        raise HTTPException(status_code=404, detail="方向不存在")
    db.delete(category)
    db.commit()
    return {"message": "删除成功"}


@router.get("/users", response_model=List[UserResponse])
async def list_users(
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=100),
    search: Optional[str] = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_admin_user)
):
    query = db.query(User)
    
    if search:
        query = query.filter(
            (User.username.contains(search)) | 
            (User.email.contains(search))
        )
    
    users = query.order_by(User.created_at.desc()).offset(skip).limit(limit).all()
    return users


@router.get("/users/count")
async def count_users(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_admin_user)
):
    total = db.query(User).count()
    active = db.query(User).filter(User.is_active == True).count()
    return {"total": total, "active": active}


@router.get("/users/{user_id}", response_model=UserResponse)
async def get_user(
    user_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_admin_user)
):
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="用户不存在")
    return user


@router.get("/users/{user_id}/stats", response_model=UserStats)
async def get_user_stats(
    user_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_admin_user)
):
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="用户不存在")

    total_projects = db.query(Project).filter(Project.user_id == user_id).count()
    total_articles = db.query(Article).filter(Article.user_id == user_id).count()
    total_articles = db.query(Article).filter(Article.user_id == user_id).count()
    total_articles = db.query(Article).filter(Article.user_id == user_id).count()
    total_articles = db.query(Article).filter(Article.user_id == user_id).count()
    total_articles = db.query(Article).filter(Article.user_id == user_id).count()
    total_tasks = db.query(Task).filter(Task.project_id.in_(
        db.query(Project.id).filter(Project.user_id == user_id)
    )).count()
    completed_tasks = db.query(Task).filter(
        Task.project_id.in_(
            db.query(Project.id).filter(Project.user_id == user_id)
        ),
        Task.status == "completed"
    ).count()
    failed_tasks = db.query(Task).filter(
        Task.project_id.in_(
            db.query(Project.id).filter(Project.user_id == user_id)
        ),
        Task.status == "failed"
    ).count()
    
    return {
        "total_projects": total_projects,
        "total_tasks": total_tasks,
        "completed_tasks": completed_tasks,
        "failed_tasks": failed_tasks
    }


@router.get("/users/{user_id}/detail", response_model=UserDetail)
async def get_user_detail(
    user_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_admin_user)
):
    """获取用户详情（完整统计+最近任务日志）"""
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="用户不存在")

    total_projects = db.query(Project).filter(Project.user_id == user_id).count()
    total_articles = db.query(Article).filter(Article.user_id == user_id).count()
    
    def get_status_text(status: str) -> str:
        status_map = {
            "chatting": "对话中",
            "code_generating": "生成代码中",
            "code_generated": "代码生成完成",
            "processing": "渲染中",
            "completed": "视频生成成功",
            "failed": "生成失败"
        }
        return status_map.get(status, status)
    
    current_status = None
    recent_projects = []
    recent_articles = []
    latest_task = None
    
    projects = db.query(Project).filter(
        Project.user_id == user_id
    ).order_by(Project.created_at.desc()).limit(3).all()
    
    for proj in projects:
        task = db.query(Task).filter(Task.project_id == proj.id).first()
        
        status = proj.status or "chatting"
        if task and task.status == "processing":
            status = "processing"
        elif task and task.status == "completed":
            status = "completed"
        elif task and task.status == "failed":
            status = "failed"
        
        recent_projects.append({
            "id": proj.id,
            "title": proj.title or f"项目-{proj.id}",
            "status": status,
            "status_text": get_status_text(status),
            "created_at": proj.created_at,
            "has_video": bool(task and task.video_url) if task else False,
            "error_message": task.error_message if task else None
        })
        
        if not current_status or status in ["processing", "code_generating", "chatting"]:
            current_status = {
                "project_id": proj.id,
                "project_title": proj.title or f"项目-{proj.id}",
                "status": status,
                "status_text": get_status_text(status),
                "updated_at": proj.updated_at
            }
    
    latest_task_query = db.query(Task).join(
        Project, Task.project_id == Project.id
    ).filter(Project.user_id == user_id).order_by(Task.created_at.desc()).first()
    
    if latest_task_query:
        proj = db.query(Project).filter(Project.id == latest_task_query.project_id).first()
        latest_task = {
            "project_id": latest_task_query.project_id,
            "project_title": proj.title if proj else f"项目-{latest_task_query.project_id}",
            "status": latest_task_query.status,
            "error_message": latest_task_query.error_message,
            "log": latest_task_query.log,
            "created_at": latest_task_query.created_at
        }

    articles = db.query(Article).filter(Article.user_id == user_id).order_by(Article.created_at.desc()).limit(3).all()
    for article in articles:
        recent_articles.append({
            "id": article.id,
            "title": article.title or article.topic,
            "status": article.status or "draft",
            "status_text": "已排版" if article.content_html else "草稿中",
            "created_at": article.created_at,
            "has_video": False,
            "error_message": None,
        })

    permissions = user.get_module_permissions()
    module_usage = {
        "visual": permissions.get("visual", {}),
        "stickman": permissions.get("stickman", {}),
        "article": permissions.get("article", {}),
    }
    
    return {
        "id": user.id,
        "username": user.username,
        "email": user.email,
        "is_active": user.is_active,
        "is_admin": user.is_admin,
        "is_approved": user.is_approved,
        "expires_at": user.expires_at,
        "created_at": user.created_at,
        "last_active_at": user.last_active_at,
        "total_projects": total_projects,
        "total_articles": total_articles,
        "videos_count": user.videos_count or 0,
        "token_usage": user.token_usage or 0,
        "module_permissions": permissions,
        "module_usage": module_usage,
        "current_status": current_status,
        "recent_projects": recent_projects,
        "recent_articles": recent_articles,
        "latest_task": latest_task
    }


@router.put("/users/{user_id}")
async def update_user(
    user_id: int,
    user_update: UserUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_admin_user),
    request: Request = None
):
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="用户不存在")
    
    if user_update.is_active is not None:
        user.is_active = user_update.is_active
    if user_update.is_admin is not None:
        user.is_admin = user_update.is_admin
    if user_update.module_permissions is not None:
        user.set_module_permissions(_normalize_module_permissions(user_update.module_permissions, user))
    
    db.commit()
    db.refresh(user)
    
    from app.api.auth import log_audit
    log_audit(db, current_user.id, current_user.username, "USER_UPDATE", 
              resource="user", resource_id=user_id,
              details=f"更新用户: {user.username}", request=request)
    
    return user


@router.put("/users/{user_id}/module-permissions")
async def update_user_module_permissions(
    user_id: int,
    payload: dict,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_admin_user),
    request: Request = None,
):
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="用户不存在")
    if user.is_admin:
        raise HTTPException(status_code=400, detail="管理员账号默认无限制，请勿修改模块权限")

    permissions = _normalize_module_permissions(payload, user)
    user.set_module_permissions(permissions)
    db.commit()
    db.refresh(user)

    from app.api.auth import log_audit
    log_audit(db, current_user.id, current_user.username, "USER_MODULE_PERMISSION_UPDATE",
              resource="user", resource_id=user_id,
              details=f"更新用户 {user.username} 模块权限", request=request)
    return {"message": "模块权限已更新", "module_permissions": permissions}


@router.post("/users/module-permissions/batch")
async def batch_update_user_module_permissions(
    payload: dict,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_admin_user),
    request: Request = None,
):
    user_ids = payload.get("user_ids") or []
    updates = payload.get("module_permissions") or {}
    if not user_ids:
        raise HTTPException(status_code=400, detail="请选择用户")

    users = db.query(User).filter(User.id.in_(user_ids)).all()
    skipped_admins = _count_admin_users(users)
    updated_count = 0
    for user in users:
        if user.is_admin:
            continue
        permissions = _normalize_module_permissions(updates, user)
        user.set_module_permissions(permissions)
        updated_count += 1
    db.commit()

    from app.api.auth import log_audit
    log_audit(db, current_user.id, current_user.username, "USER_MODULE_PERMISSION_BATCH_UPDATE",
              resource="user", resource_id=None,
              details=f"批量更新 {updated_count} 个用户模块权限，跳过管理员 {skipped_admins} 个", request=request)
    return {"message": f"已更新 {updated_count} 个用户的模块权限，跳过管理员 {skipped_admins} 个", "updated_count": updated_count, "skipped_admins": skipped_admins}


@router.delete("/users/{user_id}")
async def delete_user(
    user_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_admin_user),
    request: Request = None
):
    if user_id == current_user.id:
        raise HTTPException(status_code=400, detail="不能删除自己")
    
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="用户不存在")
    
    db.query(Project).filter(Project.user_id == user_id).delete()
    db.delete(user)
    db.commit()
    
    from app.api.auth import log_audit
    log_audit(db, current_user.id, current_user.username, "USER_DELETE", 
              resource="user", resource_id=user_id,
              details=f"删除用户: {user.username}", request=request)
    
    return {"message": "用户已删除"}


@router.get("/audit-logs", response_model=List[AuditLogResponse])
async def list_audit_logs(
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=100),
    user_id: Optional[int] = None,
    action: Optional[str] = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_admin_user)
):
    query = db.query(AuditLog)
    
    if user_id:
        query = query.filter(AuditLog.user_id == user_id)
    if action:
        query = query.filter(AuditLog.action.contains(action))
    
    logs = query.order_by(AuditLog.created_at.desc()).offset(skip).limit(limit).all()
    return logs


@router.get("/stats", response_model=SystemStats)
async def get_system_stats(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_admin_user)
):
    total_users = db.query(User).count()
    active_users = db.query(User).filter(User.is_active == True).count()
    total_projects = db.query(Project).count()
    total_videos = db.query(Task).filter(Task.status == "completed").count()
    
    today_start = datetime.utcnow().replace(hour=0, minute=0, second=0, microsecond=0)
    api_calls_today = db.query(AuditLog).filter(
        AuditLog.created_at >= today_start,
        AuditLog.action.in_(["LOGIN_SUCCESS", "USER_REGISTER", "PROJECT_CREATE", "TASK_GENERATE"])
    ).count()
    
    return {
        "total_users": total_users,
        "active_users": active_users,
        "total_projects": total_projects,
        "total_videos": total_videos,
        "api_calls_today": api_calls_today,
        "cpu_usage": psutil.cpu_percent(),
        "memory_usage": psutil.virtual_memory().percent,
        "disk_usage": psutil.disk_usage('/').percent
    }


@router.post("/users/{user_id}/toggle-active")
async def toggle_user_active(
    user_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_admin_user),
    request: Request = None
):
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="用户不存在")
    if user_id == current_user.id:
        raise HTTPException(status_code=400, detail="不能修改自己的状态")
    
    user.is_active = not user.is_active
    db.commit()
    
    from app.api.auth import log_audit
    action = "USER_ENABLE" if user.is_active else "USER_DISABLE"
    action_text = "启用" if user.is_active else "禁用"
    log_audit(db, current_user.id, current_user.username, action, 
              resource="user", resource_id=user_id,
              details=f"{action_text}用户: {user.username}", request=request)
    
    return {"message": f"用户已{action_text}", "is_active": user.is_active}


@router.post("/users/{user_id}/set-video-limit")
async def set_user_video_limit(
    user_id: int,
    limit: int = Query(..., ge=5, le=20),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_admin_user),
    request: Request = None
):
    """设置用户每日视频配额"""
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="用户不存在")
    
    user.daily_video_limit = limit
    permissions = user.get_module_permissions()
    permissions.setdefault("visual", {}).update({"daily_limit": limit, "enabled": True})
    user.set_module_permissions(permissions)
    db.commit()
    
    from app.api.auth import log_audit
    log_audit(db, current_user.id, current_user.username, "SET_VIDEO_LIMIT",
              resource="user", resource_id=user_id,
              details=f"设置用户 {user.username} 每日视频配额为 {limit}",
              request=request)
    
    return {"message": "配额已更新", "daily_video_limit": limit}


@router.post("/users/{user_id}/reset-password")
async def reset_user_password(
    user_id: int,
    password: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_admin_user),
    request: Request = None
):
    """重置用户密码"""
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="用户不存在")
    
    if len(password) < 8:
        raise HTTPException(status_code=400, detail="密码至少8位")
    
    from passlib.context import CryptContext
    pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
    user.hashed_password = pwd_context.hash(password)
    
    db.commit()
    
    from app.api.auth import log_audit
    log_audit(db, current_user.id, current_user.username, "PASSWORD_RESET",
              resource="user", resource_id=user_id,
              details=f"重置用户密码: {user.username}",
              request=request)
    
    return {"message": "密码重置成功"}


@router.post("/users/{user_id}/approve")
async def approve_user(
    user_id: int,
    days_valid: int = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_admin_user),
    request: Request = None
):
    """审核通过用户，可设置有效期"""
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="用户不存在")
    
    user.is_approved = True
    if days_valid:
        user.expires_at = datetime.utcnow() + timedelta(days=days_valid)
    
    db.commit()
    
    from app.api.auth import log_audit
    log_audit(db, current_user.id, current_user.username, "USER_APPROVED", 
              resource="user", resource_id=user_id,
              details=f"审核通过用户: {user.username}, 有效期: {days_valid}天" if days_valid else f"审核通过用户: {user.username}",
              request=request)
    
    return {"message": "用户已审核通过", "expires_at": user.expires_at}


@router.post("/users/{user_id}/reject")
async def reject_user(
    user_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_admin_user),
    request: Request = None
):
    """拒绝用户"""
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="用户不存在")
    
    user.is_approved = False
    db.commit()
    
    from app.api.auth import log_audit
    log_audit(db, current_user.id, current_user.username, "USER_REJECTED", 
              resource="user", resource_id=user_id,
              details=f"拒绝用户: {user.username}", request=request)
    
    return {"message": "用户已拒绝"}


@router.post("/users/{user_id}/extend")
async def extend_user(
    user_id: int,
    days: float = Query(30, ge=0.00347, le=365),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_admin_user),
    request: Request = None
):
    """延长用户有效期"""
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="用户不存在")
    
    now = datetime.utcnow()
    delta_seconds = days * 24 * 60 * 60
    user.expires_at = now + timedelta(seconds=delta_seconds)
    
    user.is_approved = True
    db.commit()
    
    from app.api.auth import log_audit
    log_audit(db, current_user.id, current_user.username, "USER_EXTENDED", 
              resource="user", resource_id=user_id,
              details=f"延长用户有效期: {user.username} +{days}天, 新到期: {user.expires_at}",
              request=request)
    
    return {"message": f"已延长{days}天", "expires_at": user.expires_at.strftime('%Y-%m-%d %H:%M:%S') if user.expires_at else None}


@router.get("/pending-users", response_model=List[UserResponse])
async def list_pending_users(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_admin_user)
):
    """获取待审核用户列表"""
    users = db.query(User).filter(User.is_approved == False).order_by(User.created_at.desc()).all()
    return users


@router.get("/user-stats")
async def get_all_user_stats(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_admin_user)
):
    """获取所有用户统计信息"""
    users = db.query(User).order_by(User.last_active_at.desc().nullslast()).all()
    result = []
    for user in users:
        total_projects = db.query(Project).filter(Project.user_id == user.id).count()
        result.append({
            "id": user.id,
            "username": user.username,
            "email": user.email,
            "is_active": user.is_active,
            "is_approved": user.is_approved,
            "expires_at": user.expires_at.isoformat() if user.expires_at else None,
            "api_calls_count": user.api_calls_count or 0,
            "videos_count": user.videos_count or 0,
            "last_active_at": user.last_active_at.isoformat() if user.last_active_at else None,
            "total_projects": total_projects,
            "created_at": user.created_at.isoformat() if user.created_at else None
        })
    return result


@router.get("/statistics/overview")
async def get_statistics_overview(
    period: str = Query("day", regex="^(day|week|month)$"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_admin_user)
):
    """获取统计概览"""
    from datetime import date, timedelta
    from app.models.statistics import DailyStatistics
    from sqlalchemy import func as sql_func
    
    today = date.today()
    
    if period == "day":
        start_date = today
    elif period == "week":
        start_date = today - timedelta(days=7)
    else:
        start_date = today - timedelta(days=30)
    
    stats = db.query(DailyStatistics).filter(
        DailyStatistics.date >= start_date
    ).all()
    
    total_conversations = sum(s.conversations_count or 0 for s in stats)
    total_api_calls = sum(s.api_calls_count or 0 for s in stats)
    total_videos = sum(s.videos_count or 0 for s in stats)
    total_projects = sum(s.projects_count or 0 for s in stats)
    
    active_users = db.query(User).filter(
        User.last_active_at >= datetime.utcnow() - timedelta(days=1 if period == "day" else 7 if period == "week" else 30)
    ).count()
    
    return {
        "conversations_count": total_conversations,
        "api_calls_count": total_api_calls,
        "videos_count": total_videos,
        "projects_count": total_projects,
        "active_users": active_users
    }


@router.get("/statistics/trend")
async def get_statistics_trend(
    period: str = Query("day", regex="^(day|week|month)$"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_admin_user)
):
    """获取趋势数据"""
    from datetime import date, timedelta
    from app.models.statistics import DailyStatistics
    
    today = date.today()
    
    if period == "day":
        days = 7
    elif period == "week":
        days = 28
    else:
        days = 30
    
    start_date = today - timedelta(days=days)
    
    stats = db.query(DailyStatistics).filter(
        DailyStatistics.date >= start_date
    ).order_by(DailyStatistics.date).all()
    
    stats_map = {s.date: s for s in stats}
    
    result = []
    for i in range(days + 1):
        d = start_date + timedelta(days=i)
        s = stats_map.get(d)
        result.append({
            "date": d.isoformat(),
            "conversations_count": s.conversations_count if s else 0,
            "api_calls_count": s.api_calls_count if s else 0,
            "videos_count": s.videos_count if s else 0,
            "projects_count": s.projects_count if s else 0
        })
    
    return result


def update_daily_statistics():
    """更新每日统计数据（定时任务调用）"""
    from datetime import date
    from sqlalchemy import func
    from app.models import DailyStatistics, Conversation
    from app.database import SessionLocal
    
    db = SessionLocal()
    try:
        today = date.today()
        
        existing = db.query(DailyStatistics).filter(DailyStatistics.date == today).first()
        if not existing:
            existing = DailyStatistics(date=today)
            db.add(existing)
        
        existing.conversations_count = db.query(Conversation).filter(
            Conversation.created_at >= datetime.combine(today, datetime.min.time()),
            Conversation.created_at < datetime.combine(today + timedelta(days=1), datetime.min.time())
        ).count()
        
        existing.videos_count = db.query(Task).filter(
            Task.status == "completed",
            Task.created_at >= datetime.combine(today, datetime.min.time()),
            Task.created_at < datetime.combine(today + timedelta(days=1), datetime.min.time())
        ).count()
        
        existing.projects_count = db.query(Project).filter(
            Project.created_at >= datetime.combine(today, datetime.min.time()),
            Project.created_at < datetime.combine(today + timedelta(days=1), datetime.min.time())
        ).count()
        
        existing.active_users_count = db.query(User).filter(
            User.last_active_at >= datetime.combine(today, datetime.min.time())
        ).count()
        
        total_api_calls = db.query(User).filter(
            User.last_active_at >= datetime.combine(today, datetime.min.time())
        ).with_entities(func.sum(User.api_calls_count)).scalar() or 0
        
        existing.api_calls_count = total_api_calls
        
        db.commit()
        print(f"[Statistics] Updated daily statistics for {today}")
        
    except Exception as e:
        print(f"[Statistics Error] Failed to update: {e}")
        db.rollback()
    finally:
        db.close()


@router.get("/token-usage", response_model=TokenUsageResponse)
async def get_token_usage(
    period: str = Query("day", regex="^(day|week|month)$"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_admin_user)
):
    """获取 Token 使用统计（按总量排序）"""
    from datetime import datetime, timedelta
    
    now = datetime.utcnow()
    if period == "day":
        start_time = now - timedelta(days=1)
    elif period == "week":
        start_time = now - timedelta(weeks=1)
    else:
        start_time = now - timedelta(days=30)
    
    users = db.query(User).filter(
        ((User.chat_token_usage > 0) | (User.code_token_usage > 0)),
        # User.last_active_at >= start_time  # 已移除，因为字段为空
    ).all()
    
    result = []
    sorted_users = sorted(users, key=lambda x: (x.chat_token_usage or 0) + (x.code_token_usage or 0), reverse=True)
    
    for i, user in enumerate(sorted_users):
        chat_tokens = user.chat_token_usage or 0
        code_tokens = user.code_token_usage or 0
        result.append({
            "id": user.id,
            "username": user.username,
            "chat_token_usage": chat_tokens,
            "code_token_usage": code_tokens,
            "total_token_usage": chat_tokens + code_tokens,
            "rank": i + 1
        })
    
    return {
        "users": result,
        "total_chat_tokens": sum(u["chat_token_usage"] for u in result),
        "total_code_tokens": sum(u["code_token_usage"] for u in result),
        "total_tokens": sum(u["total_token_usage"] for u in result)
    }


@router.get("/module-stats")
async def get_module_stats(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_admin_user)
):
    today = datetime.utcnow().date()
    tomorrow = today + timedelta(days=1)

    def build(total: int, today_count: int, success: int, failed: int):
        return {
            "total": total,
            "today": today_count,
            "success": success,
            "failed": failed,
            "success_rate": round((success / total) * 100, 1) if total else 0.0,
        }

    visual_total = db.query(Project).filter(Project.module_type == "manim").count()
    visual_today = db.query(Project).filter(Project.module_type == "manim", Project.created_at >= today, Project.created_at < tomorrow).count()
    visual_success = db.query(Project).filter(Project.module_type == "manim", Project.status == "completed").count()
    visual_failed = db.query(Project).filter(Project.module_type == "manim", Project.status == "failed").count()

    stickman_total = db.query(Project).filter(Project.module_type == "stickman").count()
    stickman_today = db.query(Project).filter(Project.module_type == "stickman", Project.created_at >= today, Project.created_at < tomorrow).count()
    stickman_success = db.query(Project).filter(Project.module_type == "stickman", Project.status == "completed").count()
    stickman_failed = db.query(Project).filter(Project.module_type == "stickman", Project.status == "failed").count()

    article_total = db.query(Article).count()
    article_today = db.query(Article).filter(Article.created_at >= today, Article.created_at < tomorrow).count()
    article_success = db.query(Article).filter(Article.content_html.isnot(None)).count()
    article_failed = db.query(Article).filter(Article.status == "failed").count()

    return {
        "visual": build(visual_total, visual_today, visual_success, visual_failed),
        "stickman": build(stickman_total, stickman_today, stickman_success, stickman_failed),
        "article": build(article_total, article_today, article_success, article_failed),
    }


# ============ 视频主题方向管理 ============

@router.get("/video-topic-categories")
async def list_video_topic_categories(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_admin_user)
):
    """获取所有视频主题方向"""
    from app.models.video_topic_category import VideoTopicCategory
    
    categories = db.query(VideoTopicCategory).order_by(
        VideoTopicCategory.sort_order
    ).all()
    
    return [{
        "id": c.id,
        "name": c.name,
        "icon": c.icon,
        "description": c.description,
        "example_topics": json.loads(c.example_topics) if c.example_topics else [],
        "topic_generation_prompt": c.topic_generation_prompt,
        "system_prompt": c.system_prompt,
        "is_active": c.is_active,
        "sort_order": c.sort_order,
        "created_at": c.created_at.isoformat() if c.created_at else None
    } for c in categories]


@router.post("/video-topic-categories")
async def create_video_topic_category(
    name: str,
    icon: str,
    description: str = "",
    example_topics: List[str] = [],
    topic_generation_prompt: str = "",
    system_prompt: str = "",
    is_active: bool = True,
    sort_order: int = 0,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_admin_user)
):
    """创建视频主题方向"""
    from app.models.video_topic_category import VideoTopicCategory
    
    existing = db.query(VideoTopicCategory).filter(
        VideoTopicCategory.name == name
    ).first()
    
    if existing:
        raise HTTPException(status_code=400, detail="方向名称已存在")
    
    category = VideoTopicCategory(
        name=name,
        icon=icon,
        description=description,
        example_topics=json.dumps(example_topics, ensure_ascii=False),
        topic_generation_prompt=topic_generation_prompt,
        system_prompt=system_prompt,
        is_active=is_active,
        sort_order=sort_order
    )
    
    db.add(category)
    db.commit()
    db.refresh(category)
    
    return {
        "message": "创建成功",
        "id": category.id
    }


@router.put("/video-topic-categories/{category_id}")
async def update_video_topic_category(
    category_id: int,
    name: str = None,
    icon: str = None,
    description: str = None,
    example_topics: List[str] = None,
    topic_generation_prompt: str = None,
    system_prompt: str = None,
    is_active: bool = None,
    sort_order: int = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_admin_user)
):
    """更新视频主题方向"""
    from app.models.video_topic_category import VideoTopicCategory
    
    category = db.query(VideoTopicCategory).filter(
        VideoTopicCategory.id == category_id
    ).first()
    
    if not category:
        raise HTTPException(status_code=404, detail="方向不存在")
    
    if name is not None:
        existing = db.query(VideoTopicCategory).filter(
            VideoTopicCategory.name == name,
            VideoTopicCategory.id != category_id
        ).first()
        if existing:
            raise HTTPException(status_code=400, detail="方向名称已存在")
        category.name = name
    
    if icon is not None:
        category.icon = icon
    if description is not None:
        category.description = description
    if example_topics is not None:
        category.example_topics = json.dumps(example_topics, ensure_ascii=False)
    if topic_generation_prompt is not None:
        category.topic_generation_prompt = topic_generation_prompt
    if system_prompt is not None:
        category.system_prompt = system_prompt
    if is_active is not None:
        category.is_active = is_active
    if sort_order is not None:
        category.sort_order = sort_order
    
    db.commit()
    
    return {"message": "更新成功"}


@router.delete("/video-topic-categories/{category_id}")
async def delete_video_topic_category(
    category_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_admin_user)
):
    """删除视频主题方向"""
    from app.models.video_topic_category import VideoTopicCategory
    
    category = db.query(VideoTopicCategory).filter(
        VideoTopicCategory.id == category_id
    ).first()
    
    if not category:
        raise HTTPException(status_code=404, detail="方向不存在")
    
    db.delete(category)
    db.commit()
    
    return {"message": "删除成功"}


# ============ 系统配置管理 ============

@router.get("/system-config/{key}")
async def get_system_config(
    key: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_admin_user)
):
    """获取系统配置"""
    from app.models.system_config import SystemConfig
    
    config = db.query(SystemConfig).filter(SystemConfig.key == key).first()
    
    if not config:
        return {"key": key, "value": ""}
    
    return {"key": config.key, "value": config.value}


@router.post("/system-config/{key}")
async def set_system_config(
    key: str,
    data: dict,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_admin_user)
):
    """设置系统配置"""
    from app.models.system_config import SystemConfig
    
    value = data.get("value", "")
    
    config = db.query(SystemConfig).filter(SystemConfig.key == key).first()
    
    if config:
        config.value = value
    else:
        config = SystemConfig(key=key, value=value)
        db.add(config)
    
    db.commit()
    
    return {"message": "配置保存成功"}
