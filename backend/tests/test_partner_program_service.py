import os

os.environ["DATABASE_URL"] = "sqlite:///:memory:"

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.api import partner
from app.database import Base
from app.models.partner import InviteCode, PartnerProfile
from app.models.user import User
from app.services.partner_program import estimate_commission_amount, normalize_invite_code, stickman_entitlement_from_user
from app.services.stickman_workflow_plans import permission_from_plan


def test_normalize_invite_code_uppercases_and_strips():
    assert normalize_invite_code(" ab-12 ") == "AB-12"


def test_estimate_commission_amount_uses_basis_points():
    assert estimate_commission_amount(19900, 3000) == 5970


def test_stickman_entitlement_reads_material_scope_and_limits():
    class UserStub:
        def get_module_permission(self, module_key):
            assert module_key == "stickman_v2"
            return {
                "material_mode": "hybrid",
                "max_video_seconds": 120,
                "allowed_libraries": '["sc1_outputs", "premium_sc1"]',
            }

    entitlement = stickman_entitlement_from_user(UserStub())

    assert entitlement["can_use_ai_images"] is True
    assert entitlement["max_video_seconds"] == 120
    assert entitlement["allowed_libraries"] == ["sc1_outputs", "premium_sc1"]
    assert entitlement["visible_image_modes"] == ["material_only", "ai_image"]
    assert entitlement["can_choose_image_mode"] is True


def test_stickman_entitlement_limits_visible_modes_to_one_mode():
    class UserStub:
        def get_module_permission(self, module_key):
            assert module_key == "stickman_v2"
            return {
                "material_mode": "ai_image",
                "visible_image_modes": ["ai_image"],
            }

    entitlement = stickman_entitlement_from_user(UserStub())

    assert entitlement["material_mode"] == "ai_image"
    assert entitlement["visible_image_modes"] == ["ai_image"]
    assert entitlement["can_choose_image_mode"] is False


def test_stickman_count_package_plan_maps_to_unlimited_time_permission():
    permission = permission_from_plan({
        "quota_mode": "count_package",
        "daily_limit": 40,
        "total_video_limit": 40,
        "max_video_seconds": 300,
        "material_mode": "ai_image",
        "allowed_libraries": ["sc1_outputs"],
    })

    assert permission["quota_mode"] == "count_package"
    assert permission["total_video_limit"] == 40
    assert permission["unlimited_time"] is True
    assert permission["max_video_seconds"] == 300
    assert permission["material_mode"] == "ai_image"


def test_partner_invite_inherits_single_visible_image_mode_even_if_payload_requests_ai():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(bind=engine)
    db = sessionmaker(bind=engine)()
    user = User(
        id=1,
        username="partner_user",
        email="partner@example.test",
        hashed_password="x",
        is_active=True,
        is_approved=True,
        role="partner",
    )
    user.set_module_permissions({
        "stickman_v2": {
            "enabled": True,
            "material_mode": "material_only",
            "visible_image_modes": ["material_only"],
            "max_video_seconds": 300,
        }
    })
    db.add(user)
    db.add(PartnerProfile(user_id=1, display_name="渠道", commission_rate_bps=3000, status="active"))
    db.commit()

    response = partner.create_partner_invite_code(
        partner.PartnerInviteCodeCreate(
            plan_key="custom_single",
            material_mode="ai_image",
            quota_limit=1,
            max_video_seconds=60,
            amount=1000,
        ),
        db,
        user,
    )

    invite = db.query(InviteCode).filter(InviteCode.code == response["code"]).first()
    assert invite.material_mode == "material_only"
    assert response["material_mode"] == "material_only"
