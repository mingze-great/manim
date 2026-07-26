from datetime import datetime

from sqlalchemy import Boolean, Column, DateTime, ForeignKey, Integer, String, Text

from app.database import Base


class PartnerProfile(Base):
    __tablename__ = "partner_profiles"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), unique=True, nullable=False, index=True)
    display_name = Column(String(80), nullable=False)
    commission_rate_bps = Column(Integer, default=3000, nullable=False)
    status = Column(String(20), default="active", nullable=False)
    settlement_info_json = Column(Text, nullable=True)
    notes = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class ReferralCode(Base):
    __tablename__ = "referral_codes"

    id = Column(Integer, primary_key=True, index=True)
    partner_id = Column(Integer, ForeignKey("partner_profiles.id"), nullable=False, index=True)
    code = Column(String(40), unique=True, nullable=False, index=True)
    channel_name = Column(String(80), nullable=True)
    status = Column(String(20), default="active", nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)


class InviteCode(Base):
    __tablename__ = "invite_codes"

    id = Column(Integer, primary_key=True, index=True)
    code = Column(String(64), unique=True, nullable=False, index=True)
    partner_id = Column(Integer, ForeignKey("partner_profiles.id"), nullable=True, index=True)
    plan_key = Column(String(40), nullable=False)
    material_mode = Column(String(20), default="material_only", nullable=False)
    quota_limit = Column(Integer, default=0, nullable=False)
    quota_period = Column(String(20), default="daily", nullable=False)
    max_video_seconds = Column(Integer, default=60, nullable=False)
    allowed_libraries_json = Column(Text, nullable=True)
    amount = Column(Integer, default=0, nullable=False)
    commission_rate_bps = Column(Integer, default=0, nullable=False)
    commission_amount = Column(Integer, default=0, nullable=False)
    max_uses = Column(Integer, default=1, nullable=False)
    used_count = Column(Integer, default=0, nullable=False)
    status = Column(String(20), default="active", nullable=False)
    expires_at = Column(DateTime, nullable=True)
    redeemed_by_user_id = Column(Integer, ForeignKey("users.id"), nullable=True, index=True)
    redeemed_at = Column(DateTime, nullable=True)
    created_by_user_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)


class CommissionLedger(Base):
    __tablename__ = "commission_ledgers"

    id = Column(Integer, primary_key=True, index=True)
    partner_id = Column(Integer, ForeignKey("partner_profiles.id"), nullable=False, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    order_id = Column(Integer, ForeignKey("orders.id"), nullable=True, index=True)
    invite_code_id = Column(Integer, ForeignKey("invite_codes.id"), nullable=True, index=True)
    amount = Column(Integer, default=0, nullable=False)
    commission_rate_bps = Column(Integer, default=0, nullable=False)
    commission_amount = Column(Integer, default=0, nullable=False)
    status = Column(String(20), default="pending", nullable=False)
    source = Column(String(30), default="order", nullable=False)
    notes = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
