import asyncio
import os

os.environ["DATABASE_URL"] = "sqlite:///:memory:"

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.api.auth import authenticate_user, get_current_partner_user, get_password_hash
from app.database import Base
from app.models.partner import PartnerProfile
from app.models.user import User


def _session():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(bind=engine)
    return sessionmaker(bind=engine)()


def _user(username: str, phone: str | None, password: str = "pass123", **kwargs) -> User:
    return User(
        username=username,
        email=f"{username}@example.test",
        phone=phone,
        hashed_password=get_password_hash(password),
        is_active=kwargs.pop("is_active", True),
        is_approved=kwargs.pop("is_approved", True),
        is_admin=kwargs.pop("is_admin", False),
        role=kwargs.pop("role", "user"),
        **kwargs,
    )


def test_authenticate_user_accepts_unique_phone_identifier():
    db = _session()
    db.add(_user("phone_login_user", "13800001111"))
    db.commit()

    user, error = authenticate_user(db, "13800001111", "pass123")

    assert error is None
    assert user.username == "phone_login_user"


def test_authenticate_user_rejects_duplicate_phone_identifier():
    db = _session()
    db.add_all([
        _user("dup_phone_a", "13800002222"),
        _user("dup_phone_b", "13800002222"),
    ])
    db.commit()

    user, error = authenticate_user(db, "13800002222", "pass123")

    assert user is None
    assert "手机号绑定了多个账号" in error


def test_admin_is_not_treated_as_partner_user():
    admin = _user("admin_user", "13800003333", is_admin=True, role="user")

    try:
        asyncio.run(get_current_partner_user(admin))
    except Exception as exc:
        assert getattr(exc, "status_code", None) == 403
    else:
        raise AssertionError("admin should not pass partner-only dependency")


def test_partner_user_can_access_partner_dependency():
    partner = _user("partner_user", "13800004444", role="partner")

    result = asyncio.run(get_current_partner_user(partner))

    assert result is partner

