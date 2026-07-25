import os
import sys
import types

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

from app.api import stickman_workflow
from app.services.stickman_workflow_limits import estimate_script_duration_seconds, validate_script_duration_request


def test_estimate_script_duration_seconds_counts_chinese_text_and_pauses():
    seconds = estimate_script_duration_seconds("你总是想太多，因为你把别人的情绪，当成了自己的责任。")
    assert 6 <= seconds <= 12


def test_validate_script_duration_request_rejects_custom_script_with_target_seconds():
    with pytest.raises(ValueError, match="自定义文案和目标时长不能同时选择"):
        validate_script_duration_request(custom_script="一段文案", target_seconds=30)


def test_material_library_entitlement_rejects_unallowed_library():
    with pytest.raises(HTTPException) as exc:
        stickman_workflow._ensure_material_library_allowed(
            {"key": "premium_sc1"},
            {"allowed_libraries": ["sc1_outputs"]},
        )
    assert exc.value.status_code == 400
    assert "素材库" in exc.value.detail


def test_material_library_entitlement_allows_empty_scope():
    stickman_workflow._ensure_material_library_allowed(
        {"key": "premium_sc1"},
        {"allowed_libraries": []},
    )
