import asyncio
import os

os.environ["DATABASE_URL"] = "sqlite:///:memory:"

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.api import admin
from app.api.auth import get_password_hash
from app.database import Base
from app.models.partner import PartnerProfile, ReferralCode
from app.models.user import User


def _session():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(bind=engine)
    return sessionmaker(bind=engine)()


def _user(username: str, *, is_admin: bool = False, role: str = "user") -> User:
    return User(
        username=username,
        email=f"{username}@example.test",
        phone=None,
        hashed_password=get_password_hash("pass1234"),
        is_active=True,
        is_approved=True,
        is_admin=is_admin,
        role=role,
    )


def test_admin_can_enable_partner_from_user_detail():
    db = _session()
    admin_user = _user("admin", is_admin=True, role="admin")
    target = _user("creator")
    db.add_all([admin_user, target])
    db.commit()
    db.refresh(target)

    payload = admin.UserPartnerProfileUpdate(
        enabled=True,
        display_name="创作者渠道",
        commission_rate_bps=2500,
        status="active",
    )
    response = asyncio.run(admin.update_user_partner_profile(target.id, payload, db, admin_user))

    partner = db.query(PartnerProfile).filter(PartnerProfile.user_id == target.id).first()
    referral = db.query(ReferralCode).filter(ReferralCode.partner_id == partner.id).first()

    assert response["enabled"] is True
    assert response["display_name"] == "创作者渠道"
    assert response["commission_rate_bps"] == 2500
    assert response["referral_code"] == referral.code
    assert partner.status == "active"
    assert target.role == "partner"


def test_admin_can_disable_partner_from_user_detail():
    db = _session()
    admin_user = _user("admin", is_admin=True, role="admin")
    target = _user("creator", role="partner")
    db.add_all([admin_user, target])
    db.commit()
    db.refresh(target)
    partner = PartnerProfile(user_id=target.id, display_name="旧渠道", commission_rate_bps=3000, status="active")
    db.add(partner)
    db.commit()

    payload = admin.UserPartnerProfileUpdate(enabled=False)
    response = asyncio.run(admin.update_user_partner_profile(target.id, payload, db, admin_user))

    db.refresh(target)
    db.refresh(partner)

    assert response["enabled"] is False
    assert response["status"] == "inactive"
    assert partner.status == "inactive"
    assert target.role == "user"
