import os

os.environ["DATABASE_URL"] = "sqlite:///:memory:"

from app.services.stickman_workflow_plans import normalize_stickman_workflow_plans, permission_from_plan


def test_count_package_plan_uses_total_video_limit_without_calendar_expiry():
    permission = permission_from_plan(
        {
            "quota_mode": "count_package",
            "daily_limit": 0,
            "total_video_limit": 40,
            "max_video_seconds": 300,
            "material_mode": "ai_image",
            "allowed_libraries": ["sc1_outputs"],
        }
    )

    assert permission["quota_mode"] == "count_package"
    assert permission["daily_limit"] == 0
    assert permission["total_video_limit"] == 40
    assert permission["period"] == "lifetime"
    assert permission["unlimited_time"] is True
    assert permission["max_video_seconds"] == 300
    assert permission["material_mode"] == "ai_image"


def test_normalize_count_package_treats_legacy_daily_limit_as_total_limit():
    plans = normalize_stickman_workflow_plans(
        [
            {
                "key": "legacy_count",
                "name": "40条包",
                "quota_mode": "count_package",
                "daily_limit": 40,
                "total_video_limit": 0,
                "max_video_seconds": 300,
            }
        ]
    )

    assert plans[0]["daily_limit"] == 0
    assert plans[0]["total_video_limit"] == 40
