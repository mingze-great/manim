from app.models.partner import CommissionLedger, InviteCode, PartnerProfile, ReferralCode
from app.models.subscription import Order
from app.models.user import User


def test_partner_models_importable():
    assert PartnerProfile.__tablename__ == "partner_profiles"
    assert ReferralCode.__tablename__ == "referral_codes"
    assert InviteCode.__tablename__ == "invite_codes"
    assert CommissionLedger.__tablename__ == "commission_ledgers"
    assert hasattr(User, "role")
    assert hasattr(Order, "commission_status")
