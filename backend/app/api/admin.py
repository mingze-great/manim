from typing import Optional, List
from datetime import datetime, timedelta
from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException, Query, Request, UploadFile, File, Form
from fastapi.responses import FileResponse
from pydantic import BaseModel
from sqlalchemy.orm import Session
from sqlalchemy import func
import json
import re

from app.database import get_db
from app.models.article_category import ArticleCategory
from app.models.user import User, AuditLog
from app.models.project import Project, Conversation
from app.models.article import Article
from app.models.task import Task
from app.models.subscription import Order, Subscription
from app.models.partner import CommissionLedger, InviteCode, PartnerProfile, ReferralCode
from app.models.favorite_topic import FavoriteTopic
from app.models.material_library_generation import MaterialLibraryGeneration
from app.models.user_module_permission import UserModulePermission
from app.schemas.article import ArticleCategoryCreate, ArticleCategoryUpdate
from app.schemas.user import UserResponse, UserUpdate, UserStats, AuditLogResponse, SystemStats, UserDetail, ProjectStatus, RecentProject, TaskLog, TokenUsageItem, TokenUsageResponse
from app.api.auth import get_current_user, get_current_admin_user
from app.config import get_settings
from app.services.notifications import notify_admin_event
from app.services.partner_program import ensure_referral_code, generate_invite_code
from app.services.stickman_workflow_assets import (
    find_material_library_asset,
    list_material_libraries,
    save_material_libraries,
    save_material_library_package,
    material_library_asset_root,
)
from app.services.partner_program import estimate_commission_amount
from app.services.stickman_workflow_plans import (
    find_stickman_workflow_plan,
    list_stickman_workflow_plans,
    save_stickman_workflow_plans,
)
from app.tasks.celery_tasks import generate_material_library_celery
import psutil
from app.services.stickman_v2_assets import (
    save_background_templates,
    save_opening_styles,
    save_scene_style_libraries,
    save_asset_upload,
    save_scene_style_library_package,
    list_opening_styles,
    list_background_templates,
    list_scene_style_libraries,
    find_asset_file,
)


def _with_image_urls(items: list[dict], kind: str):
    if kind == "opening_styles":
        key = "sample_image_path"
        url_key = "sample_image_url"
    elif kind == "background_templates":
        key = "background_image_path"
        url_key = "background_image_url"
    else:
        key = "cover_image_path"
        url_key = "cover_image_url"
    payload = []
    for item in items:
        clone = dict(item)
        image_path = str(clone.get(key) or "").strip()
        explicit_url = str(clone.get(url_key) or "").strip()
        clone["image_url"] = f"/api/admin/stickman-v2/assets/{kind}/{Path(image_path).name}" if image_path else (explicit_url or None)
        payload.append(clone)
    return payload


def _with_workflow_library_urls(items: list[dict]):
    payload = []
    for item in items:
        clone = dict(item)
        image_path = str(clone.get("cover_image_path") or "").strip()
        explicit_url = str(clone.get("cover_image_url") or "").strip()
        library_key = str(clone.get("key") or "").strip()
        clone["image_url"] = f"/api/admin/stickman-workflow/assets/material-libraries/{library_key}/{Path(image_path).name}" if image_path else (explicit_url or None)
        payload.append(clone)
    return payload

router = APIRouter(prefix="/admin", tags=["admin"])
settings = get_settings()

MODULE_KEYS = ["visual", "stickman_legacy", "stickman_v2", "explainer", "article"]


class PartnerCreateRequest(BaseModel):
    user_id: int
    display_name: str
    commission_rate_bps: int = 3000


class UserPartnerProfileUpdate(BaseModel):
    enabled: bool
    display_name: Optional[str] = None
    commission_rate_bps: Optional[int] = None
    status: Optional[str] = None


class InviteCodeCreateRequest(BaseModel):
    partner_id: Optional[int] = None
    plan_key: str = "basic"
    material_mode: Optional[str] = None
    quota_limit: Optional[int] = None
    quota_period: str = "daily"
    max_video_seconds: Optional[int] = None
    max_uses: int = 1
    allowed_libraries: List[str] = []
    amount: int = 0
    quota_mode: Optional[str] = None
    daily_minutes_limit: Optional[int] = None
    monthly_minutes_limit: Optional[int] = None
    total_video_limit: Optional[int] = None


class StickmanWorkflowPlanSaveRequest(BaseModel):
    plans: List[dict]


def _normalize_module_permissions(payload: dict, user: User) -> dict:
    permissions = user.get_module_permissions()
    extra_permission_fields = {
        "quota_mode",
        "max_video_seconds",
        "daily_video_limit",
        "daily_minutes_limit",
        "monthly_minutes_limit",
        "total_video_limit",
        "used_total_videos",
        "used_total_minutes",
        "used_daily_minutes",
        "used_monthly_minutes",
        "daily_minutes_marker",
        "monthly_minutes_marker",
        "unlimited_time",
        "material_mode",
        "allowed_libraries",
    }
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
            for field in extra_permission_fields:
                if field in payload[module_key]:
                    current[field] = payload[module_key].get(field)
            permissions[module_key] = current
    visual_permission = permissions.get("visual") or {}
    if visual_permission.get("daily_limit") is not None:
        try:
            user.daily_video_limit = int(visual_permission.get("daily_limit") or 0)
        except Exception:
            pass
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
                quota_limit=perm_data.get("total_video_limit" if perm_data.get("quota_mode") == "count_package" else "daily_limit", 0),
                quota_used=perm_data.get("used_total_videos" if perm_data.get("quota_mode") == "count_package" else "used_today", 0),
                period=perm_data.get("period", "lifetime" if perm_data.get("quota_mode") == "count_package" else "daily"),
            )
            db.add(record)
        else:
            record.enabled = perm_data.get("enabled", record.enabled)
            record.quota_limit = perm_data.get("total_video_limit" if perm_data.get("quota_mode") == "count_package" else "daily_limit", record.quota_limit)
            record.quota_used = perm_data.get("used_total_videos" if perm_data.get("quota_mode") == "count_package" else "used_today", record.quota_used)
            record.period = perm_data.get("period", "lifetime" if perm_data.get("quota_mode") == "count_package" else record.period)
    
    db.flush()


def _frontend_version_payload(value: str):
    frontend_version = str(value or "legacy")
    if frontend_version not in ["legacy", "v2"]:
        raise HTTPException(status_code=400, detail="frontend_version 只能是 legacy 或 v2")
    return frontend_version


def _normalize_visual_limit(limit: int):
    normalized = int(limit or 0)
    if normalized < 1 or normalized > 999:
        raise HTTPException(status_code=400, detail="每日限额范围需在 1 到 999 之间")
    return normalized
def _count_admin_users(users: list[User]) -> int:
    return sum(1 for user in users if bool(user.is_admin))


def _partner_profile_payload(db: Session, user: User) -> dict:
    partner = db.query(PartnerProfile).filter(PartnerProfile.user_id == user.id).first()
    if not partner:
        return {"enabled": False, "user_id": user.id}
    referral = db.query(ReferralCode).filter(
        ReferralCode.partner_id == partner.id,
        ReferralCode.status == "active",
    ).order_by(ReferralCode.created_at.desc()).first()
    return {
        "enabled": partner.status == "active" and user.role == "partner",
        "id": partner.id,
        "user_id": user.id,
        "display_name": partner.display_name,
        "commission_rate_bps": partner.commission_rate_bps,
        "status": partner.status,
        "referral_code": referral.code if referral else None,
        "created_at": partner.created_at.isoformat() if partner.created_at else None,
        "updated_at": partner.updated_at.isoformat() if partner.updated_at else None,
    }


@router.get("/partners")
async def list_partners(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_admin_user),
):
    partners = db.query(PartnerProfile).order_by(PartnerProfile.created_at.desc()).all()
    return [
        {
            "id": partner.id,
            "user_id": partner.user_id,
            "display_name": partner.display_name,
            "commission_rate_bps": partner.commission_rate_bps,
            "status": partner.status,
            "created_at": partner.created_at.isoformat() if partner.created_at else None,
        }
        for partner in partners
    ]


@router.post("/partners")
async def create_partner(
    payload: PartnerCreateRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_admin_user),
):
    user = db.query(User).filter(User.id == payload.user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="用户不存在")
    partner = db.query(PartnerProfile).filter(PartnerProfile.user_id == user.id).first()
    if not partner:
        partner = PartnerProfile(
            user_id=user.id,
            display_name=payload.display_name.strip() or user.username,
            commission_rate_bps=payload.commission_rate_bps,
            status="active",
        )
        db.add(partner)
        db.flush()
    else:
        partner.display_name = payload.display_name.strip() or partner.display_name
        partner.commission_rate_bps = payload.commission_rate_bps
        partner.status = "active"
    user.role = "partner"
    user.is_approved = True
    referral = ensure_referral_code(db, partner)
    db.commit()
    return {
        "id": partner.id,
        "user_id": user.id,
        "display_name": partner.display_name,
        "commission_rate_bps": partner.commission_rate_bps,
        "referral_code": referral.code,
    }


@router.get("/referrals")
async def list_referrals(
    partner_id: Optional[int] = Query(None),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_admin_user),
):
    query = db.query(User).filter(User.referred_by_partner_id.isnot(None))
    if partner_id:
        query = query.filter(User.referred_by_partner_id == partner_id)
    users = query.order_by(User.created_at.desc()).limit(500).all()
    return [
        {
            "id": user.id,
            "username": user.username,
            "phone": user.phone,
            "partner_id": user.referred_by_partner_id,
            "referral_code": user.referral_code,
            "is_approved": user.is_approved,
            "created_at": user.created_at.isoformat() if user.created_at else None,
        }
        for user in users
    ]


@router.get("/commissions")
async def list_commissions(
    partner_id: Optional[int] = Query(None),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_admin_user),
):
    query = db.query(CommissionLedger)
    if partner_id:
        query = query.filter(CommissionLedger.partner_id == partner_id)
    rows = query.order_by(CommissionLedger.created_at.desc()).limit(500).all()
    return [
        {
            "id": row.id,
            "partner_id": row.partner_id,
            "user_id": row.user_id,
            "order_id": row.order_id,
            "amount": row.amount,
            "commission_amount": row.commission_amount,
            "status": row.status,
            "source": row.source,
            "created_at": row.created_at.isoformat() if row.created_at else None,
        }
        for row in rows
    ]


@router.post("/invite-codes")
async def create_invite_code(
    payload: InviteCodeCreateRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_admin_user),
):
    plan = find_stickman_workflow_plan(db, payload.plan_key) or {}
    if payload.partner_id:
        partner = db.query(PartnerProfile).filter(PartnerProfile.id == payload.partner_id).first()
        if not partner:
            raise HTTPException(status_code=404, detail="合作者不存在")
        commission_rate_bps = int(partner.commission_rate_bps or 0)
    else:
        commission_rate_bps = 0
    amount = int(payload.amount or plan.get("amount") or 0)
    commission_amount = estimate_commission_amount(amount, commission_rate_bps)
    material_mode = payload.material_mode or plan.get("material_mode") or "material_only"
    quota_limit = int(payload.quota_limit if payload.quota_limit is not None else (plan.get("daily_limit") or plan.get("total_video_limit") or 0))
    max_video_seconds = int(payload.max_video_seconds or plan.get("max_video_seconds") or 60)
    allowed_libraries = payload.allowed_libraries or plan.get("allowed_libraries") or []
    code = generate_invite_code("SC1")
    while db.query(InviteCode).filter(InviteCode.code == code).first():
        code = generate_invite_code("SC1")
    invite = InviteCode(
        code=code,
        partner_id=payload.partner_id,
        plan_key=payload.plan_key,
        material_mode=material_mode,
        quota_limit=quota_limit,
        quota_period=payload.quota_period,
        max_video_seconds=max_video_seconds,
        allowed_libraries_json=json.dumps(
            [str(item).strip() for item in allowed_libraries if str(item).strip()],
            ensure_ascii=False,
        ) if allowed_libraries else None,
        amount=amount,
        commission_rate_bps=commission_rate_bps,
        commission_amount=commission_amount,
        max_uses=payload.max_uses,
        created_by_user_id=current_user.id,
    )
    db.add(invite)
    db.commit()
    db.refresh(invite)
    notify_admin_event(
        "后台生成兑换码",
        f"管理员 {current_user.username} 生成兑换码 {invite.code}，绑定合作者 {invite.partner_id or '无'}，套餐 {invite.plan_key}，金额 {invite.amount / 100:.2f} 元，预计佣金 {invite.commission_amount / 100:.2f} 元。",
    )
    return {
        "id": invite.id,
        "code": invite.code,
        "partner_id": invite.partner_id,
        "plan_key": invite.plan_key,
        "material_mode": invite.material_mode,
        "allowed_libraries": json.loads(invite.allowed_libraries_json or "[]"),
        "amount": invite.amount,
        "commission_rate_bps": invite.commission_rate_bps,
        "commission_amount": invite.commission_amount,
        "status": invite.status,
    }


@router.get("/stickman-workflow/plans")
async def get_stickman_workflow_plans(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_admin_user),
):
    return {"plans": list_stickman_workflow_plans(db)}


@router.post("/stickman-workflow/plans")
async def set_stickman_workflow_plans(
    payload: StickmanWorkflowPlanSaveRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_admin_user),
):
    return {"plans": save_stickman_workflow_plans(db, payload.plans)}


@router.get("/stickman-workflow/material-libraries")
async def get_stickman_workflow_material_libraries(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_admin_user),
):
    return {"libraries": _with_workflow_library_urls(list_material_libraries(db))}


@router.post("/stickman-workflow/material-libraries")
async def set_stickman_workflow_material_libraries(
    payload: dict,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_admin_user),
):
    libraries = payload.get("libraries") or []
    return {"libraries": _with_workflow_library_urls(save_material_libraries(db, libraries))}


@router.post("/stickman-workflow/material-libraries/{library_key}/package")
async def upload_stickman_workflow_material_library_package(
    library_key: str,
    file: UploadFile = File(...),
    name: Optional[str] = Form(None),
    description: Optional[str] = Form(None),
    sort_order: Optional[int] = Form(None),
    is_active: bool = Form(True),
    is_visible: bool = Form(True),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_admin_user),
):
    library_key = str(library_key or "").strip()
    if not library_key:
        raise HTTPException(status_code=400, detail="素材库 key 不能为空")
    libraries = list_material_libraries(db)
    index = next((i for i, item in enumerate(libraries) if item.get("key") == library_key), -1)
    if index < 0:
        libraries.append({
            "key": library_key,
            "name": str(name or library_key).strip() or library_key,
            "description": str(description or "").strip(),
            "sort_order": int(sort_order or len(libraries) + 1),
            "is_active": bool(is_active),
            "is_visible": bool(is_visible),
            "source": "uploaded_package",
        })
        index = len(libraries) - 1
    else:
        libraries[index]["name"] = str(name or libraries[index].get("name") or library_key).strip() or library_key
        libraries[index]["description"] = str(description if description is not None else libraries[index].get("description") or "").strip()
        libraries[index]["sort_order"] = int(sort_order or libraries[index].get("sort_order") or index + 1)
        libraries[index]["is_active"] = bool(is_active)
        libraries[index]["is_visible"] = bool(is_visible)
    if index < 0:
        raise HTTPException(status_code=404, detail="火柴人工作流素材库不存在")
    try:
        package_info = await save_material_library_package(file, library_key=library_key)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    libraries[index].update(package_info)
    saved = save_material_libraries(db, libraries)
    current = next((item for item in saved if item.get("key") == library_key), None) or libraries[index]
    return {
        "message": "火柴人工作流素材库已上传",
        "library": _with_workflow_library_urls([current])[0],
        "libraries": _with_workflow_library_urls(saved),
        "image_url": f"/api/admin/stickman-workflow/assets/material-libraries/{library_key}/{Path(current.get('cover_image_path') or '').name}" if current.get("cover_image_path") else (current.get("cover_image_url") or None),
        "image_count": int(current.get("image_count") or 0),
        "material_count": int(current.get("material_count") or 0),
    }


@router.get("/stickman-workflow/assets/material-libraries/{filename}")
async def get_stickman_workflow_material_library_asset(
    filename: str,
    db: Session = Depends(get_db),
):
    asset_path = find_material_library_asset(db, filename)
    if not asset_path or not asset_path.exists():
        raise HTTPException(status_code=404, detail="资源不存在")
    return FileResponse(asset_path)


@router.get("/stickman-workflow/assets/material-libraries/{library_key}/{filename}")
async def get_namespaced_stickman_workflow_material_library_asset(
    library_key: str,
    filename: str,
    db: Session = Depends(get_db),
):
    asset_path = find_material_library_asset(db, filename, library_key=library_key)
    if not asset_path or not asset_path.exists():
        raise HTTPException(status_code=404, detail="资源不存在")
    return FileResponse(asset_path)


def _material_generation_payload(generation: MaterialLibraryGeneration) -> dict:
    try:
        sample_names = json.loads(generation.sample_images_json or "[]")
    except Exception:
        sample_names = []
    return {
        "id": generation.id,
        "library_key": generation.library_key,
        "library_name": generation.library_name,
        "target_count": generation.target_count,
        "status": generation.status,
        "progress": generation.progress,
        "message": generation.message,
        "error": generation.error,
        "sample_images": [
            f"/api/admin/stickman-workflow/material-libraries/generations/{generation.id}/assets/{Path(name).name}"
            for name in sample_names
        ],
        "manifest_path": generation.manifest_path if generation.status == "completed" else None,
    }


@router.post("/stickman-workflow/material-libraries/generations/samples")
async def create_material_library_samples(
    library_key: str = Form(...),
    library_name: str = Form(...),
    target_count: int = Form(100),
    reference_image: UploadFile = File(...),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_admin_user),
):
    clean_key = str(library_key or "").strip().lower()
    clean_name = str(library_name or "").strip()
    if not re.fullmatch(r"[a-z0-9][a-z0-9_-]{1,79}", clean_key):
        raise HTTPException(status_code=400, detail="素材库 Key 仅支持小写字母、数字、下划线和短横线")
    if not clean_name:
        raise HTTPException(status_code=400, detail="请输入素材库名称")
    if target_count < 6 or target_count > 120:
        raise HTTPException(status_code=400, detail="素材数量必须在 6-120 张之间")
    suffix = Path(reference_image.filename or "reference.png").suffix.lower()
    if suffix not in {".png", ".jpg", ".jpeg", ".webp"}:
        raise HTTPException(status_code=400, detail="参考图仅支持 png、jpg、jpeg、webp")
    content = await reference_image.read()
    if not content or len(content) > 10 * 1024 * 1024:
        raise HTTPException(status_code=400, detail="参考图不能为空且不能超过 10MB")

    generation = MaterialLibraryGeneration(
        user_id=current_user.id,
        library_key=clean_key,
        library_name=clean_name,
        target_count=target_count,
        status="sample_pending",
        progress=0,
        message="样图任务已创建",
        reference_image_path="pending",
        output_dir="pending",
    )
    db.add(generation)
    db.flush()
    output_dir = material_library_asset_root() / f"generated_{generation.id}_{clean_key}"
    output_dir.mkdir(parents=True, exist_ok=True)
    reference_path = output_dir / f"reference{'.jpg' if suffix == '.jpeg' else suffix}"
    reference_path.write_bytes(content)
    generation.output_dir = str(output_dir)
    generation.reference_image_path = str(reference_path)
    db.commit()
    db.refresh(generation)
    generate_material_library_celery.delay(generation.id, "samples")
    return _material_generation_payload(generation)


@router.get("/stickman-workflow/material-libraries/generations/{generation_id}")
async def get_material_library_generation(
    generation_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_admin_user),
):
    generation = db.query(MaterialLibraryGeneration).filter(MaterialLibraryGeneration.id == generation_id).first()
    if not generation:
        raise HTTPException(status_code=404, detail="素材库生成任务不存在")
    return _material_generation_payload(generation)


@router.post("/stickman-workflow/material-libraries/generations/{generation_id}/confirm")
async def confirm_material_library_generation(
    generation_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_admin_user),
):
    generation = db.query(MaterialLibraryGeneration).filter(MaterialLibraryGeneration.id == generation_id).first()
    if not generation:
        raise HTTPException(status_code=404, detail="素材库生成任务不存在")
    if generation.status != "samples_ready":
        raise HTTPException(status_code=400, detail="样图尚未生成完成或已经确认")
    generation.status = "batch_pending"
    generation.message = "已确认样图，等待批量生成"
    db.commit()
    generate_material_library_celery.delay(generation.id, "batch")
    return _material_generation_payload(generation)


@router.post("/stickman-workflow/material-libraries/generations/{generation_id}/regenerate-samples")
async def regenerate_material_library_samples(
    generation_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_admin_user),
):
    generation = db.query(MaterialLibraryGeneration).filter(MaterialLibraryGeneration.id == generation_id).first()
    if not generation:
        raise HTTPException(status_code=404, detail="素材库生成任务不存在")
    if generation.status not in {"samples_ready", "failed"}:
        raise HTTPException(status_code=400, detail="当前状态不能重新生成样图")
    for name in ("1.png", "2.png"):
        (Path(generation.output_dir).resolve() / name).unlink(missing_ok=True)
    generation.status = "sample_pending"
    generation.progress = 0
    generation.error = None
    generation.message = "等待重新生成样图"
    db.commit()
    generate_material_library_celery.delay(generation.id, "samples")
    return _material_generation_payload(generation)


@router.get("/stickman-workflow/material-libraries/generations/{generation_id}/assets/{filename}")
async def get_material_library_generation_asset(
    generation_id: int,
    filename: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_admin_user),
):
    generation = db.query(MaterialLibraryGeneration).filter(MaterialLibraryGeneration.id == generation_id).first()
    if not generation:
        raise HTTPException(status_code=404, detail="素材库生成任务不存在")
    try:
        sample_names = {Path(name).name for name in json.loads(generation.sample_images_json or "[]")}
    except Exception:
        sample_names = set()
    if Path(filename).name not in sample_names:
        raise HTTPException(status_code=404, detail="样图不存在")
    output_dir = Path(generation.output_dir).resolve()
    asset_path = (output_dir / Path(filename).name).resolve()
    if asset_path.parent != output_dir or not asset_path.exists() or not asset_path.is_file():
        raise HTTPException(status_code=404, detail="样图不存在")
    return FileResponse(asset_path)


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
            (User.email.contains(search)) |
            (User.phone.contains(search))
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
            "code_generating": "生成脚本中",
            "code_generated": "脚本生成完成",
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
        "stickman_legacy": permissions.get("stickman_legacy", {}),
        "stickman_v2": permissions.get("stickman_v2", {}),
        "explainer": permissions.get("explainer", {}),
        "article": permissions.get("article", {}),
    }
    
    return {
        "id": user.id,
        "username": user.username,
        "email": user.email,
        "phone": user.phone,
        "is_active": user.is_active,
        "is_admin": user.is_admin,
        "frontend_version": user.frontend_version or "legacy",
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
        "latest_task": latest_task,
        "partner_profile": _partner_profile_payload(db, user),
    }


@router.get("/users/{user_id}/partner-profile")
async def get_user_partner_profile(
    user_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_admin_user),
):
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="用户不存在")
    return _partner_profile_payload(db, user)


@router.put("/users/{user_id}/partner-profile")
async def update_user_partner_profile(
    user_id: int,
    payload: UserPartnerProfileUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_admin_user),
):
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="用户不存在")
    if user.is_admin:
        raise HTTPException(status_code=400, detail="管理员账号不能设置为合作者")

    partner = db.query(PartnerProfile).filter(PartnerProfile.user_id == user.id).first()
    if payload.enabled:
        status = str(payload.status or "active").strip() or "active"
        if status not in {"active", "inactive"}:
            raise HTTPException(status_code=400, detail="合作者状态只能是 active 或 inactive")
        if not partner:
            partner = PartnerProfile(
                user_id=user.id,
                display_name=(payload.display_name or user.username).strip() or user.username,
                commission_rate_bps=int(payload.commission_rate_bps if payload.commission_rate_bps is not None else 3000),
                status=status,
            )
            db.add(partner)
            db.flush()
        else:
            if payload.display_name is not None:
                partner.display_name = payload.display_name.strip() or user.username
            if payload.commission_rate_bps is not None:
                partner.commission_rate_bps = int(payload.commission_rate_bps)
            partner.status = status
        if partner.commission_rate_bps < 0 or partner.commission_rate_bps > 10000:
            raise HTTPException(status_code=400, detail="佣金比例需在 0 到 10000 基点之间")
        user.role = "partner" if status == "active" else "user"
        user.is_approved = True
        ensure_referral_code(db, partner)
    else:
        if partner:
            partner.status = "inactive"
        user.role = "user"

    db.commit()
    db.refresh(user)
    return _partner_profile_payload(db, user)


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
        target_is_admin = bool(user_update.is_admin)
        if not target_is_admin and user.is_admin:
            if user.id == current_user.id:
                raise HTTPException(status_code=400, detail="???????????????????")
            admin_count = db.query(func.count(User.id)).filter(User.is_admin == True).scalar() or 0
            if admin_count <= 1:
                raise HTTPException(status_code=400, detail="???????????????")
        user.is_admin = target_is_admin
        if target_is_admin:
            user.is_approved = True
    if user_update.frontend_version is not None:
        user.frontend_version = _frontend_version_payload(user_update.frontend_version)
    if user_update.module_permissions is not None:
        permissions = _normalize_module_permissions(user_update.module_permissions, user)
        user.set_module_permissions(permissions)
        _sync_permissions_to_db(db, user, permissions)
    
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
    _sync_permissions_to_db(db, user, permissions)
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
        _sync_permissions_to_db(db, user, permissions)
        updated_count += 1
    db.commit()

    from app.api.auth import log_audit
    log_audit(db, current_user.id, current_user.username, "USER_MODULE_PERMISSION_BATCH_UPDATE",
              resource="user", resource_id=None,
              details=f"批量更新 {updated_count} 个用户模块权限，跳过管理员 {skipped_admins} 个", request=request)
    return {"message": f"已更新 {updated_count} 个用户的模块权限，跳过管理员 {skipped_admins} 个", "updated_count": updated_count, "skipped_admins": skipped_admins}


@router.post("/users/frontend-version/batch")
async def batch_update_user_frontend_version(
    payload: dict,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_admin_user),
    request: Request = None,
):
    user_ids = payload.get("user_ids") or []
    if not user_ids:
        raise HTTPException(status_code=400, detail="请选择用户")
    frontend_version = _frontend_version_payload(payload.get("frontend_version"))

    users = db.query(User).filter(User.id.in_(user_ids)).all()
    skipped_admins = _count_admin_users(users)
    updated_count = 0
    for user in users:
        if user.is_admin:
            continue
        user.frontend_version = frontend_version
        updated_count += 1
    db.commit()

    from app.api.auth import log_audit
    log_audit(
        db,
        current_user.id,
        current_user.username,
        "USER_FRONTEND_VERSION_BATCH_UPDATE",
        resource="user",
        resource_id=None,
        details=f"批量切换 {updated_count} 个用户前端版本为 {frontend_version}，跳过管理员 {skipped_admins} 个",
        request=request,
    )
    return {"message": f"已切换 {updated_count} 个用户的前端版本，跳过管理员 {skipped_admins} 个", "updated_count": updated_count, "skipped_admins": skipped_admins}


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
    
    project_ids = [p.id for p in db.query(Project.id).filter(Project.user_id == user_id).all()]
    
    if project_ids:
        db.query(Task).filter(Task.project_id.in_(project_ids)).delete(synchronize_session=False)
        db.query(Conversation).filter(Conversation.project_id.in_(project_ids)).delete(synchronize_session=False)
    
    db.query(Project).filter(Project.user_id == user_id).delete(synchronize_session=False)
    
    db.query(Article).filter(Article.user_id == user_id).delete(synchronize_session=False)
    db.query(UserModulePermission).filter(UserModulePermission.user_id == user_id).delete(synchronize_session=False)
    db.query(Order).filter(Order.user_id == user_id).delete(synchronize_session=False)
    db.query(Subscription).filter(Subscription.user_id == user_id).delete(synchronize_session=False)
    db.query(FavoriteTopic).filter(FavoriteTopic.user_id == user_id).delete(synchronize_session=False)
    
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
    
    normalized_limit = _normalize_visual_limit(limit)
    user.daily_video_limit = normalized_limit
    permissions = user.get_module_permissions()
    permissions.setdefault("visual", {}).update({"daily_limit": normalized_limit, "enabled": True})
    user.set_module_permissions(permissions)
    _sync_permissions_to_db(db, user, permissions)
    db.commit()
    
    from app.api.auth import log_audit
    log_audit(db, current_user.id, current_user.username, "SET_VIDEO_LIMIT",
              resource="user", resource_id=user_id,
              details=f"设置用户 {user.username} 每日思维可视化配额为 {normalized_limit}",
              request=request)
    
    return {"message": "配额已更新", "daily_video_limit": normalized_limit, "module_permissions": permissions}


@router.post("/users/visual-limit/batch")
async def batch_set_visual_limit(
    payload: dict,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_admin_user),
    request: Request = None,
):
    user_ids = payload.get("user_ids") or []
    if not user_ids:
        raise HTTPException(status_code=400, detail="请选择用户")
    normalized_limit = _normalize_visual_limit(payload.get("daily_limit"))

    users = db.query(User).filter(User.id.in_(user_ids)).all()
    skipped_admins = _count_admin_users(users)
    updated_count = 0
    for user in users:
        if user.is_admin:
            continue
        permissions = user.get_module_permissions()
        permissions.setdefault("visual", {}).update({"daily_limit": normalized_limit, "enabled": True})
        user.daily_video_limit = normalized_limit
        user.set_module_permissions(permissions)
        _sync_permissions_to_db(db, user, permissions)
        updated_count += 1
    db.commit()

    from app.api.auth import log_audit
    log_audit(
        db,
        current_user.id,
        current_user.username,
        "USER_VISUAL_LIMIT_BATCH_UPDATE",
        resource="user",
        resource_id=None,
        details=f"批量设置 {updated_count} 个用户每日思维可视化配额为 {normalized_limit}，跳过管理员 {skipped_admins} 个",
        request=request,
    )
    return {"message": f"已设置 {updated_count} 个用户的每日思维可视化配额，跳过管理员 {skipped_admins} 个", "updated_count": updated_count, "skipped_admins": skipped_admins, "daily_limit": normalized_limit}


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
            "phone": user.phone,
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

    explainer_total = db.query(Project).filter(Project.module_type == "explainer").count()
    explainer_today = db.query(Project).filter(Project.module_type == "explainer", Project.created_at >= today, Project.created_at < tomorrow).count()
    explainer_success = db.query(Project).filter(Project.module_type == "explainer", Project.status == "completed").count()
    explainer_failed = db.query(Project).filter(Project.module_type == "explainer", Project.status == "failed").count()

    article_total = db.query(Article).count()
    article_today = db.query(Article).filter(Article.created_at >= today, Article.created_at < tomorrow).count()
    article_success = db.query(Article).filter(Article.content_html.isnot(None)).count()
    article_failed = db.query(Article).filter(Article.status == "failed").count()

    return {
        "visual": build(visual_total, visual_today, visual_success, visual_failed),
        "stickman": build(stickman_total, stickman_today, stickman_success, stickman_failed),
        "explainer": build(explainer_total, explainer_today, explainer_success, explainer_failed),
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


@router.get("/stickman-v2/opening-styles")
async def get_stickman_v2_opening_styles(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_admin_user)
): 
    return {"styles": _with_image_urls(list_opening_styles(db), "opening_styles")}


@router.post("/stickman-v2/opening-styles")
async def set_stickman_v2_opening_styles(
    payload: dict,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_admin_user)
):
    styles = payload.get("styles") or []
    return {"styles": _with_image_urls(save_opening_styles(db, styles), "opening_styles")}


@router.post("/stickman-v2/opening-styles/{style_key}/sample-image")
async def upload_stickman_v2_opening_style_image(
    style_key: str,
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_admin_user)
):
    styles = list_opening_styles(db)
    index = next((i for i, item in enumerate(styles) if item.get("key") == style_key), -1)
    if index < 0:
        raise HTTPException(status_code=404, detail="风格不存在")
    try:
        upload = await save_asset_upload(file, kind="opening_styles", item_key=style_key)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    styles[index]["sample_image_path"] = upload["path"]
    styles[index]["sample_image_url"] = upload.get("image_url") or ""
    save_opening_styles(db, styles)
    return {"message": "样例图已上传", "image_url": f"/api/admin/stickman-v2/assets/opening_styles/{Path(upload['path']).name}"}


@router.get("/stickman-v2/background-templates")
async def get_stickman_v2_background_templates(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_admin_user)
): 
    return {"templates": _with_image_urls(list_background_templates(db), "background_templates")}


@router.post("/stickman-v2/background-templates")
async def set_stickman_v2_background_templates(
    payload: dict,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_admin_user)
):
    templates = payload.get("templates") or []
    return {"templates": _with_image_urls(save_background_templates(db, templates), "background_templates")}


@router.post("/stickman-v2/background-templates/{template_key}/image")
async def upload_stickman_v2_background_template_image(
    template_key: str,
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_admin_user)
):
    templates = list_background_templates(db)
    index = next((i for i, item in enumerate(templates) if item.get("key") == template_key), -1)
    if index < 0:
        raise HTTPException(status_code=404, detail="背景模板不存在")
    try:
        upload = await save_asset_upload(file, kind="background_templates", item_key=template_key)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    templates[index]["background_image_path"] = upload["path"]
    templates[index]["background_image_url"] = upload.get("image_url") or ""
    save_background_templates(db, templates)
    return {"message": "背景图已上传", "image_url": f"/api/admin/stickman-v2/assets/background_templates/{Path(upload['path']).name}"}


@router.get("/stickman-v2/scene-style-libraries")
async def get_stickman_v2_scene_style_libraries(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_admin_user)
):
    return {"libraries": _with_image_urls(list_scene_style_libraries(db), "scene_style_libraries")}


@router.post("/stickman-v2/scene-style-libraries")
async def set_stickman_v2_scene_style_libraries(
    payload: dict,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_admin_user)
):
    libraries = payload.get("libraries") or []
    return {"libraries": _with_image_urls(save_scene_style_libraries(db, libraries), "scene_style_libraries")}


@router.post("/stickman-v2/scene-style-libraries/{library_key}/package")
async def upload_stickman_v2_scene_style_library_package(
    library_key: str,
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_admin_user)
):
    libraries = list_scene_style_libraries(db)
    index = next((i for i, item in enumerate(libraries) if item.get("key") == library_key), -1)
    if index < 0:
        raise HTTPException(status_code=404, detail="场景图风格不存在")
    try:
        package_info = await save_scene_style_library_package(file, item_key=library_key)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    libraries[index].update(package_info)
    saved = save_scene_style_libraries(db, libraries)
    current = next((item for item in saved if item.get("key") == library_key), None) or libraries[index]
    return {
        "message": "场景图风格包已上传",
        "image_url": f"/api/admin/stickman-v2/assets/scene_style_libraries/{Path(current.get('cover_image_path') or '').name}" if current.get("cover_image_path") else (current.get("cover_image_url") or None),
        "image_count": int(current.get("image_count") or 0),
        "material_count": int(current.get("material_count") or 0),
    }


@router.get("/stickman-v2/assets/{kind}/{filename}")
async def get_stickman_v2_admin_asset(
    kind: str,
    filename: str,
    db: Session = Depends(get_db),
):
    if kind not in {"opening_styles", "background_templates", "scene_style_libraries"}:
        raise HTTPException(status_code=404, detail="资源不存在")
    asset_path = find_asset_file(db, kind, filename)
    if not asset_path or not asset_path.exists():
        raise HTTPException(status_code=404, detail="资源不存在")
    return FileResponse(asset_path)
