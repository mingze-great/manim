from app.services.partner_program import estimate_commission_amount, normalize_invite_code


def test_normalize_invite_code_uppercases_and_strips():
    assert normalize_invite_code(" ab-12 ") == "AB-12"


def test_estimate_commission_amount_uses_basis_points():
    assert estimate_commission_amount(19900, 3000) == 5970
