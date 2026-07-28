import json
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.api.auth import get_current_partner_user
from app.database import get_db
from app.models.partner import CommissionLedger, InviteCode, PartnerProfile
from app.models.subscription import Order
from app.models.user import User
from app.services.notifications import notify_admin_event
from app.services.partner_program import ensure_referral_code, estimate_commission_amount, generate_invite_code, get_partner_profile_for_user, stickman_entitlement_from_user
from app.services.stickman_workflow_plans import find_partner_stickman_sales_plan, list_partner_stickman_sales_plans

router = APIRouter(prefix="/partner", tags=["partner"])


class PartnerInviteCodeCreate(BaseModel):
    plan_key: str = "basic"
    quota_limit: int | None = None
    quota_period: str = "daily"
    max_video_seconds: int | None = None
    max_uses: int = 1
    allowed_libraries: list[str] = []
    amount: int = 0
    material_mode: str | None = None


def _require_partner_profile(db: Session, user: User) -> PartnerProfile:
    profile = get_partner_profile_for_user(db, user)
    if not profile:
        raise HTTPException(status_code=403, detail="当前账号不是合作者")
    return profile


@router.get("/profile")
def get_partner_profile(
    db: Annotated[Session, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_partner_user)],
):
    profile = _require_partner_profile(db, current_user)
    referral = ensure_referral_code(db, profile)
    db.commit()
    return {
        "id": profile.id,
        "display_name": profile.display_name,
        "commission_rate_bps": profile.commission_rate_bps,
        "status": profile.status,
        "referral_code": referral.code,
        "stickman_entitlement": stickman_entitlement_from_user(current_user),
    }


@router.get("/referrals")
def list_partner_referrals(
    db: Annotated[Session, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_partner_user)],
):
    profile = _require_partner_profile(db, current_user)
    users = db.query(User).filter(User.referred_by_partner_id == profile.id).order_by(User.created_at.desc()).limit(200).all()
    return [
        {
            "id": user.id,
            "username": user.username,
            "phone": user.phone,
            "is_approved": user.is_approved,
            "created_at": user.created_at.isoformat() if user.created_at else None,
        }
        for user in users
    ]


@router.get("/orders")
def list_partner_orders(
    db: Annotated[Session, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_partner_user)],
):
    profile = _require_partner_profile(db, current_user)
    orders = db.query(Order).filter(Order.partner_id == profile.id).order_by(Order.created_at.desc()).limit(200).all()
    return [
        {
            "order_id": order.order_id,
            "plan": order.plan,
            "amount": order.amount,
            "status": order.status,
            "commission_amount": order.commission_amount,
            "commission_status": order.commission_status,
            "created_at": order.created_at.isoformat() if order.created_at else None,
        }
        for order in orders
    ]


@router.get("/commissions")
def list_partner_commissions(
    db: Annotated[Session, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_partner_user)],
):
    profile = _require_partner_profile(db, current_user)
    rows = db.query(CommissionLedger).filter(CommissionLedger.partner_id == profile.id).order_by(CommissionLedger.created_at.desc()).limit(200).all()
    return [
        {
            "id": row.id,
            "user_id": row.user_id,
            "amount": row.amount,
            "commission_amount": row.commission_amount,
            "status": row.status,
            "source": row.source,
            "created_at": row.created_at.isoformat() if row.created_at else None,
        }
        for row in rows
    ]


@router.get("/stickman-plans")
def list_partner_stickman_plans(
    db: Annotated[Session, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_partner_user)],
):
    _require_partner_profile(db, current_user)
    return {"plans": list_partner_stickman_sales_plans(db), "entitlement": stickman_entitlement_from_user(current_user)}


@router.post("/invite-codes")
def create_partner_invite_code(
    payload: PartnerInviteCodeCreate,
    db: Annotated[Session, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_partner_user)],
):
    profile = _require_partner_profile(db, current_user)
    entitlement = stickman_entitlement_from_user(current_user)
    plan = find_partner_stickman_sales_plan(db, payload.plan_key)
    if not plan:
        raise HTTPException(status_code=400, detail="合作者只能选择 399、599、799 三档火柴人套餐")
    allowed_libraries = [str(item).strip() for item in (payload.allowed_libraries or plan.get("allowed_libraries") or []) if str(item).strip()] or ["sc1_outputs"]
    amount = int(payload.amount or plan.get("amount") or 0)
    commission_amount = estimate_commission_amount(amount, profile.commission_rate_bps)
    quota_limit = int(payload.quota_limit if payload.quota_limit is not None else (plan.get("daily_limit") or plan.get("total_video_limit") or 0))
    max_video_seconds = int(payload.max_video_seconds if payload.max_video_seconds is not None else (plan.get("max_video_seconds") or 300))
    visible_modes = [str(item).strip() for item in entitlement.get("visible_image_modes") or ["material_only"] if str(item).strip()]
    requested_mode = str(payload.material_mode or plan.get("material_mode") or entitlement.get("material_mode") or "material_only").strip()
    if requested_mode == "hybrid":
        requested_mode = "material_only"
    if entitlement.get("can_choose_image_mode"):
        if requested_mode not in visible_modes:
            raise HTTPException(status_code=400, detail="当前合作者不支持给用户开通该图片模式")
        material_mode = requested_mode
    else:
        material_mode = str(entitlement.get("material_mode") or visible_modes[0] or "material_only")
    code = generate_invite_code("SC1")
    while db.query(InviteCode).filter(InviteCode.code == code).first():
        code = generate_invite_code("SC1")
    invite = InviteCode(
        code=code,
        partner_id=profile.id,
        plan_key=payload.plan_key,
        material_mode=material_mode,
        quota_limit=quota_limit,
        quota_period=payload.quota_period,
        max_video_seconds=max_video_seconds,
        allowed_libraries_json=json.dumps(allowed_libraries, ensure_ascii=False),
        amount=amount,
        commission_rate_bps=profile.commission_rate_bps,
        commission_amount=commission_amount,
        max_uses=payload.max_uses,
        created_by_user_id=current_user.id,
    )
    db.add(invite)
    db.commit()
    db.refresh(invite)
    notify_admin_event(
        "合作者生成兑换码",
        f"合作者 {profile.display_name} 生成兑换码 {invite.code}，套餐 {invite.plan_key}，金额 {invite.amount / 100:.2f} 元，预计佣金 {invite.commission_amount / 100:.2f} 元。",
    )
    return {
        "code": invite.code,
        "plan_key": invite.plan_key,
        "material_mode": invite.material_mode,
        "allowed_libraries": json.loads(invite.allowed_libraries_json or "[]"),
        "amount": invite.amount,
        "commission_rate_bps": invite.commission_rate_bps,
        "commission_amount": invite.commission_amount,
        "status": invite.status,
    }
