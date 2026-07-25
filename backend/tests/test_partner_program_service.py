import os

os.environ["DATABASE_URL"] = "sqlite:///:memory:"

from app.services.partner_program import estimate_commission_amount, normalize_invite_code, stickman_entitlement_from_user


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
