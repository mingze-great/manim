import os
import sys
import types
import inspect
import wave
from types import SimpleNamespace

os.environ["DATABASE_URL"] = "sqlite:///:memory:"

dashscope_stub = types.ModuleType("dashscope")
dashscope_audio_stub = types.ModuleType("dashscope.audio")
dashscope_tts_stub = types.ModuleType("dashscope.audio.tts_v2")


class _SpeechSynthesizer:
    pass


dashscope_tts_stub.SpeechSynthesizer = _SpeechSynthesizer
sys.modules.setdefault("dashscope", dashscope_stub)
sys.modules.setdefault("dashscope.audio", dashscope_audio_stub)
sys.modules.setdefault("dashscope.audio.tts_v2", dashscope_tts_stub)
sys.modules.setdefault("edge_tts", types.ModuleType("edge_tts"))

import pytest
from fastapi import HTTPException
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.api import stickman_workflow
from app.database import Base
from app.models.ai_video import AiVideoJob, AiVideoProject
from app.services.stickman_workflow_limits import (
    consume_stickman_quota,
    estimate_script_duration_seconds,
    validate_script_duration_request,
    validate_stickman_quota,
)
from app.services.stickman_workflow_plans import normalize_stickman_workflow_plans, permission_from_plan


def test_estimate_script_duration_seconds_counts_chinese_text_and_pauses():
    seconds = estimate_script_duration_seconds("你总是想太多，因为你把别人的情绪，当成了自己的责任。")
    assert 6 <= seconds <= 12


def test_validate_script_duration_request_rejects_custom_script_with_target_seconds():
    with pytest.raises(ValueError, match="自定义文案和目标时长不能同时选择"):
        validate_script_duration_request(custom_script="一段文案", target_seconds=30)


def test_material_library_entitlement_rejects_unallowed_library_when_enforced():
    with pytest.raises(HTTPException) as exc:
        stickman_workflow._ensure_material_library_allowed(
            {"key": "premium_sc1"},
            {"allowed_libraries": ["sc1_outputs"], "enforce_allowed_libraries": True},
        )
    assert exc.value.status_code == 400
    assert "素材库" in exc.value.detail


def test_material_library_entitlement_allows_empty_scope():
    stickman_workflow._ensure_material_library_allowed(
        {"key": "premium_sc1"},
        {"allowed_libraries": []},
    )


def test_material_library_entitlement_does_not_hide_visible_styles_by_default():
    stickman_workflow._ensure_material_library_allowed(
        {"key": "premium_sc1"},
        {"allowed_libraries": ["sc1_outputs"]},
    )


def test_duration_estimate_returns_plan_limit_and_allowed_state():
    response = stickman_workflow.estimate_stickman_script_duration(
        stickman_workflow.StickmanWorkflowDurationEstimateRequest(
            script="你不需要为所有人的情绪负责。先分清对象，再承担属于自己的后果。",
        ),
        current_user=SimpleNamespace(is_admin=True),
    )

    assert response["estimatedSeconds"] > 0
    assert response["maxVideoSeconds"] == 300
    assert response["allowed"] is True


def test_admin_creation_permission_keeps_300_second_limit():
    user = SimpleNamespace(
        is_admin=True,
        get_module_permissions=lambda: {"stickman_v2": {"enabled": True, "daily_limit": -1, "used_today": 0}},
    )

    permission = stickman_workflow._stickman_permission_for_user(user)

    assert permission["max_video_seconds"] == 300
    validate_stickman_quota(permission, requested_seconds=300)


def test_duration_estimate_request_accepts_script_longer_than_1200_chars():
    payload = stickman_workflow.StickmanWorkflowDurationEstimateRequest(script="你" * 1500)

    assert len(payload.script) == 1500


def test_stickman_config_exposes_allowed_image_modes_for_admin(monkeypatch):
    monkeypatch.setattr(stickman_workflow, "_visible_libraries_for_user", lambda db, user: [])

    response = stickman_workflow.get_stickman_workflow_config(db=None, current_user=SimpleNamespace(is_admin=True))

    assert response["capabilities"]["visibleImageModes"] == ["material_only", "ai_image"]
    assert response["capabilities"]["canChooseImageMode"] is True


def test_stickman_job_history_lists_only_current_users_workflow_jobs(monkeypatch):
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(bind=engine)
    db = sessionmaker(bind=engine)()
    db.add_all([
        AiVideoProject(id=1, user_id=1, title="我的火柴人", video_type="knowledge_ip_stickman"),
        AiVideoProject(id=2, user_id=1, title="其他模块", video_type="knowledge_visualization"),
        AiVideoProject(id=3, user_id=2, title="别人火柴人", video_type="knowledge_ip_stickman"),
    ])
    db.add_all([
        AiVideoJob(
            id=1,
            project_id=1,
            user_id=1,
            status="completed",
            progress=100,
            stage="completed",
            input_payload='{"workflowSource":"standalone_stickman_workflow"}',
            output_url="/api/ai-video/files/1/output/video.mp4",
        ),
        AiVideoJob(
            id=2,
            project_id=2,
            user_id=1,
            status="completed",
            progress=100,
            stage="completed",
            input_payload='{"workflowSource":"other"}',
            output_url="/api/ai-video/files/2/output/video.mp4",
        ),
        AiVideoJob(
            id=3,
            project_id=3,
            user_id=2,
            status="completed",
            progress=100,
            stage="completed",
            input_payload='{"workflowSource":"standalone_stickman_workflow"}',
            output_url="/api/ai-video/files/3/output/video.mp4",
        ),
    ])
    db.commit()
    monkeypatch.setattr(stickman_workflow.service, "reconcile_stale_job", lambda db, job: job)

    response = stickman_workflow.list_stickman_jobs(db=db, current_user=SimpleNamespace(id=1, is_admin=False))

    assert [item.jobId for item in response] == ["job_1"]


def test_period_card_can_limit_daily_videos_and_monthly_minutes():
    permission = {
        "enabled": True,
        "quota_mode": "period",
        "period": "monthly",
        "daily_limit": 5,
        "used_today": 1,
        "monthly_minutes_limit": 10,
        "used_monthly_minutes": 8,
        "max_video_seconds": 300,
    }

    validate_stickman_quota(permission, requested_seconds=120)

    with pytest.raises(ValueError, match="剩余分钟"):
        validate_stickman_quota(permission, requested_seconds=181)


def test_count_package_limits_total_videos_without_calendar_expiry():
    permission = {
        "enabled": True,
        "quota_mode": "count_package",
        "total_video_limit": 40,
        "used_total_videos": 39,
        "max_video_seconds": 300,
        "unlimited_time": True,
    }

    validate_stickman_quota(permission, requested_seconds=300)
    consume_stickman_quota(permission, requested_seconds=300)

    assert permission["used_total_videos"] == 40
    with pytest.raises(ValueError, match="视频次数"):
        validate_stickman_quota(permission, requested_seconds=60)


def test_stickman_plan_normalization_keeps_month_and_count_cards_exclusive():
    plans = normalize_stickman_workflow_plans([
        {"key": "monthly", "quota_mode": "period", "daily_limit": 3, "max_video_minutes": 5},
        {"key": "count", "quota_mode": "count_package", "daily_limit": 9, "total_video_limit": 40, "max_video_minutes": 5},
    ])
    monthly = next(item for item in plans if item["key"] == "monthly")
    count = next(item for item in plans if item["key"] == "count")

    assert monthly["daily_limit"] == 3
    assert monthly["daily_minutes_limit"] == 15
    assert monthly["monthly_minutes_limit"] == 450
    assert monthly["total_video_limit"] == 0
    assert permission_from_plan(monthly)["period"] == "daily"

    assert count["daily_limit"] == 0
    assert count["total_video_limit"] == 40
    assert count["daily_minutes_limit"] == 0
    assert permission_from_plan(count)["period"] == "lifetime"


def test_stickman_quota_rejects_single_video_over_limit():
    with pytest.raises(ValueError, match="单条视频不能超过"):
        validate_stickman_quota(
            {"enabled": True, "quota_mode": "count_package", "max_video_seconds": 300},
            requested_seconds=301,
        )


def test_material_generation_asset_endpoint_requires_admin_dependency():
    from app.api import admin
    from app.api.auth import get_current_admin_user

    parameter = inspect.signature(admin.get_material_library_generation_asset).parameters["current_user"]

    assert parameter.default.dependency is get_current_admin_user


def test_config_exposes_scene_styles_as_user_facing_material_library_alias(monkeypatch):
    monkeypatch.setattr(
        stickman_workflow,
        "_visible_libraries_for_user",
        lambda db, user: [
            {
                "key": "warm_style",
                "name": "温暖陪伴",
                "description": "柔和心理场景",
                "image_url": "/api/example.png",
            }
        ],
    )

    response = stickman_workflow.get_stickman_workflow_config(db=None, current_user=SimpleNamespace(is_admin=True))

    assert response["sceneStyles"][0]["key"] == "warm_style"
    assert response["sceneStyles"][0]["sampleImageUrl"] == "/api/example.png"


def test_voice_preview_cache_is_limited_to_five_seconds(tmp_path):
    source = tmp_path / "sample.wav"
    sample_rate = 16000
    with wave.open(str(source), "wb") as wav_file:
        wav_file.setnchannels(1)
        wav_file.setsampwidth(2)
        wav_file.setframerate(sample_rate)
        wav_file.writeframes(b"\x00\x00" * sample_rate * 7)

    preview = stickman_workflow._five_second_voice_preview(source)
    try:
        with wave.open(str(preview), "rb") as wav_file:
            duration_ms = int(wav_file.getnframes() / wav_file.getframerate() * 1000)
        assert 4800 <= duration_ms <= 5200
        assert preview.suffix == ".wav"
    finally:
        preview.unlink(missing_ok=True)
