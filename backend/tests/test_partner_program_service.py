import os

os.environ["DATABASE_URL"] = "sqlite:///:memory:"

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
