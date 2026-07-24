from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.api.auth import get_current_partner_user
from app.database import get_db
from app.models.partner import CommissionLedger, InviteCode, PartnerProfile
from app.models.subscription import Order
from app.models.user import User
from app.services.partner_program import generate_invite_code, get_partner_profile_for_user

router = APIRouter(prefix="/partner", tags=["partner"])


class PartnerInviteCodeCreate(BaseModel):
    plan_key: str = "basic"
    quota_limit: int = 30
    quota_period: str = "daily"
    max_video_seconds: int = 60
    max_uses: int = 1


def _require_partner_profile(db: Session, user: User) -> PartnerProfile:
    profile = get_partner_profile_for_user(db, user)
    if not profile and user.is_admin:
        profile = db.query(PartnerProfile).first()
    if not profile:
        raise HTTPException(status_code=403, detail="当前账号不是合作者")
    return profile


@router.get("/profile")
def get_partner_profile(
    db: Annotated[Session, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_partner_user)],
):
    profile = _require_partner_profile(db, current_user)
    return {
        "id": profile.id,
        "display_name": profile.display_name,
        "commission_rate_bps": profile.commission_rate_bps,
        "status": profile.status,
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


@router.post("/invite-codes")
def create_partner_invite_code(
    payload: PartnerInviteCodeCreate,
    db: Annotated[Session, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_partner_user)],
):
    profile = _require_partner_profile(db, current_user)
    code = generate_invite_code("SC1")
    while db.query(InviteCode).filter(InviteCode.code == code).first():
        code = generate_invite_code("SC1")
    invite = InviteCode(
        code=code,
        partner_id=profile.id,
        plan_key=payload.plan_key,
        quota_limit=payload.quota_limit,
        quota_period=payload.quota_period,
        max_video_seconds=payload.max_video_seconds,
        max_uses=payload.max_uses,
        created_by_user_id=current_user.id,
    )
    db.add(invite)
    db.commit()
    db.refresh(invite)
    return {"code": invite.code, "plan_key": invite.plan_key, "status": invite.status}
