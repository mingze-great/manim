from __future__ import annotations

import secrets
import string
from datetime import datetime, timedelta
from typing import Optional
import json

from sqlalchemy.orm import Session

from app.models.partner import CommissionLedger, InviteCode, PartnerProfile, ReferralCode
from app.models.subscription import Order, SUBSCRIPTION_PLANS, Subscription
from app.models.user import User
from app.models.user_module_permission import UserModulePermission


def normalize_invite_code(code: str) -> str:
    return str(code or "").strip().upper()


def generate_invite_code(prefix: str = "SC1", length: int = 8) -> str:
    alphabet = string.ascii_uppercase + string.digits
    token = "".join(secrets.choice(alphabet) for _ in range(length))
    return f"{normalize_invite_code(prefix)}-{token}"


def estimate_commission_amount(amount: int, commission_rate_bps: int) -> int:
    return int(int(amount or 0) * int(commission_rate_bps or 0) / 10000)


def get_partner_profile_for_user(db: Session, user: User) -> Optional[PartnerProfile]:
    if not user:
        return None
    return db.query(PartnerProfile).filter(PartnerProfile.user_id == user.id).first()


def get_partner_by_referral_code(db: Session, code: str) -> Optional[PartnerProfile]:
    normalized = normalize_invite_code(code)
    if not normalized:
        return None
    referral = (
        db.query(ReferralCode)
        .filter(ReferralCode.code == normalized, ReferralCode.status == "active")
        .first()
    )
    if not referral:
        return None
    return db.query(PartnerProfile).filter(PartnerProfile.id == referral.partner_id, PartnerProfile.status == "active").first()


def ensure_referral_code(db: Session, partner: PartnerProfile, channel_name: str = "默认渠道") -> ReferralCode:
    existing = db.query(ReferralCode).filter(ReferralCode.partner_id == partner.id, ReferralCode.status == "active").first()
    if existing:
        return existing
    base = normalize_invite_code(partner.display_name)[:8] or f"P{partner.id}"
    code = base
    suffix = 1
    while db.query(ReferralCode).filter(ReferralCode.code == code).first():
        suffix += 1
        code = f"{base}{suffix}"
    referral = ReferralCode(partner_id=partner.id, code=code, channel_name=channel_name, status="active")
    db.add(referral)
    db.flush()
    return referral


def upsert_module_permission(
    db: Session,
    user: User,
    module_key: str,
    *,
    enabled: bool,
    quota_limit: int,
    period: str,
    expires_at: Optional[datetime],
) -> UserModulePermission:
    record = (
        db.query(UserModulePermission)
        .filter(UserModulePermission.user_id == user.id, UserModulePermission.module_key == module_key)
        .first()
    )
    if not record:
        record = UserModulePermission(user_id=user.id, module_key=module_key)
        db.add(record)
    record.enabled = enabled
    record.quota_limit = int(quota_limit or 0)
    record.period = period or "daily"
    record.expires_at = expires_at
    return record


def _update_user_permission_json(user: User, module_key: str, extras: dict) -> None:
    permissions = user.get_module_permissions()
    current = permissions.get(module_key) or {}
    current.update(extras)
    permissions[module_key] = current
    user.set_module_permissions(permissions)


def stickman_entitlement_from_user(user: User) -> dict:
    permission = user.get_module_permission("stickman_v2") if user else {}
    material_mode = str(permission.get("material_mode") or "material_only").strip() or "material_only"
    if material_mode not in {"material_only", "ai_image", "hybrid"}:
        material_mode = "material_only"
    try:
        max_video_seconds = int(permission.get("max_video_seconds") or 60)
    except Exception:
        max_video_seconds = 60
    allowed_libraries = permission.get("allowed_libraries")
    if isinstance(allowed_libraries, str):
        try:
            allowed_libraries = json.loads(allowed_libraries)
        except Exception:
            allowed_libraries = []
    if not isinstance(allowed_libraries, list):
        allowed_libraries = []
    return {
        "material_mode": material_mode,
        "can_use_ai_images": material_mode in {"ai_image", "hybrid"},
        "max_video_seconds": max(15, min(300, max_video_seconds)),
        "allowed_libraries": [str(item).strip() for item in allowed_libraries if str(item).strip()],
    }


def apply_invite_code_to_user(db: Session, user: User, raw_code: str) -> InviteCode:
    code = normalize_invite_code(raw_code)
    invite = db.query(InviteCode).filter(InviteCode.code == code).first()
    if not invite or invite.status != "active":
        raise ValueError("兑换码无效")
    if invite.expires_at and invite.expires_at < datetime.utcnow():
        raise ValueError("兑换码已过期")
    if invite.max_uses > 0 and invite.used_count >= invite.max_uses:
        raise ValueError("兑换码已被使用")

    plan_config = SUBSCRIPTION_PLANS.get(invite.plan_key, SUBSCRIPTION_PLANS["basic"])
    expires_at = datetime.utcnow() + timedelta(days=30)
    subscription = db.query(Subscription).filter(Subscription.user_id == user.id).first()
    if not subscription:
        subscription = Subscription(user_id=user.id)
        db.add(subscription)
    subscription.plan = invite.plan_key
    subscription.daily_quota = int(plan_config.get("daily_quota") or invite.quota_limit or 0)
    subscription.max_projects = int(plan_config.get("max_projects") or 0)
    subscription.expires_at = expires_at
    subscription.is_active = 1

    user.is_approved = True
    user.expires_at = expires_at
    if invite.partner_id:
        user.referred_by_partner_id = invite.partner_id
        referral = db.query(ReferralCode).filter(ReferralCode.partner_id == invite.partner_id, ReferralCode.status == "active").first()
        user.referral_code = referral.code if referral else None

    upsert_module_permission(
        db,
        user,
        "stickman_v2",
        enabled=True,
        quota_limit=invite.quota_limit,
        period=invite.quota_period,
        expires_at=expires_at,
    )
    allowed_libraries: list[str] = []
    if invite.allowed_libraries_json:
        try:
            raw_libraries = json.loads(invite.allowed_libraries_json)
            if isinstance(raw_libraries, list):
                allowed_libraries = [str(item).strip() for item in raw_libraries if str(item).strip()]
        except Exception:
            allowed_libraries = []
    _update_user_permission_json(
        user,
        "stickman_v2",
        {
            "material_mode": invite.material_mode or "material_only",
            "max_video_seconds": int(invite.max_video_seconds or 60),
            "allowed_libraries": allowed_libraries,
        },
    )

    invite.used_count += 1
    invite.redeemed_by_user_id = user.id
    invite.redeemed_at = datetime.utcnow()
    if invite.max_uses > 0 and invite.used_count >= invite.max_uses:
        invite.status = "used"

    if invite.partner_id:
        db.add(CommissionLedger(
            partner_id=invite.partner_id,
            user_id=user.id,
            invite_code_id=invite.id,
            amount=0,
            commission_rate_bps=0,
            commission_amount=0,
            status="tracked",
            source="invite_code",
            notes=f"兑换码开通套餐 {invite.plan_key}",
        ))
    db.commit()
    db.refresh(invite)
    return invite


def record_commission_for_order(db: Session, order: Order) -> Optional[CommissionLedger]:
    if not order or order.commission_status in {"pending", "settled"}:
        return None
    user = db.query(User).filter(User.id == order.user_id).first()
    partner_id = order.partner_id or (user.referred_by_partner_id if user else None)
    if not partner_id:
        order.commission_status = "none"
        db.commit()
        return None
    partner = db.query(PartnerProfile).filter(PartnerProfile.id == partner_id, PartnerProfile.status == "active").first()
    if not partner:
        order.commission_status = "none"
        db.commit()
        return None
    commission_amount = estimate_commission_amount(order.amount, partner.commission_rate_bps)
    order.partner_id = partner.id
    order.referral_code = order.referral_code or (user.referral_code if user else None)
    order.commission_amount = commission_amount
    order.commission_status = "pending"
    ledger = CommissionLedger(
        partner_id=partner.id,
        user_id=order.user_id,
        order_id=order.id,
        amount=order.amount,
        commission_rate_bps=partner.commission_rate_bps,
        commission_amount=commission_amount,
        status="pending",
        source="order",
    )
    db.add(ledger)
    db.commit()
    db.refresh(ledger)
    return ledger
