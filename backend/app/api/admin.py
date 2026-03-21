from typing import Optional, List
from datetime import datetime, timedelta
from fastapi import APIRouter, Depends, HTTPException, Query, Request
from sqlalchemy.orm import Session
from sqlalchemy import func

from app.database import get_db
from app.models.user import User, AuditLog
from app.models.project import Project
from app.models.task import Task
from app.schemas.user import UserResponse, UserUpdate, UserStats, AuditLogResponse, SystemStats
from app.api.auth import get_current_user, get_current_admin_user
import psutil

router = APIRouter(prefix="/admin", tags=["admin"])


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
    
    db.commit()
    db.refresh(user)
    
    from app.api.auth import log_audit
    log_audit(db, current_user.id, current_user.username, "USER_UPDATE", 
              resource="user", resource_id=user_id,
              details=f"更新用户: {user.username}", request=request)
    
    return user


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
    days: int = Query(30, ge=1, le=365),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_admin_user),
    request: Request = None
):
    """延长用户有效期"""
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="用户不存在")
    
    now = datetime.utcnow()
    if user.expires_at and user.expires_at > now:
        user.expires_at = user.expires_at + timedelta(days=days)
    else:
        user.expires_at = now + timedelta(days=days)
    
    user.is_approved = True
    db.commit()
    
    from app.api.auth import log_audit
    log_audit(db, current_user.id, current_user.username, "USER_EXTENDED", 
              resource="user", resource_id=user_id,
              details=f"延长用户有效期: {user.username} +{days}天, 新到期: {user.expires_at}",
              request=request)
    
    return {"message": f"已延长{days}天", "expires_at": user.expires_at}


@router.get("/pending-users", response_model=List[UserResponse])
async def list_pending_users(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_admin_user)
):
    """获取待审核用户列表"""
    users = db.query(User).filter(User.is_approved == False).order_by(User.created_at.desc()).all()
    return users


@router.get("/invitation-codes")
async def list_invitation_codes(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_admin_user)
):
    """获取邀请码列表"""
    from app.models.invitation import InvitationCode
    codes = db.query(InvitationCode).order_by(InvitationCode.created_at.desc()).all()
    return [{"id": c.id, "code": c.code, "is_used": c.is_used, "used_by": c.used_by, 
             "used_at": c.used_at, "created_at": c.created_at, "expires_at": c.expires_at} for c in codes]
