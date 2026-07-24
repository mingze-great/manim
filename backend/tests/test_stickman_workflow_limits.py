from app.services.stickman_workflow_limits import estimate_script_duration_seconds, validate_script_duration_request


def test_estimate_script_duration_seconds_counts_chinese_text_and_pauses():
    seconds = estimate_script_duration_seconds("你总是想太多，因为你把别人的情绪，当成了自己的责任。")
    assert 6 <= seconds <= 12


def test_validate_script_duration_request_rejects_custom_script_with_target_seconds():
    import pytest
    with pytest.raises(ValueError, match="自定义文案和目标时长不能同时选择"):
        validate_script_duration_request(custom_script="一段文案", target_seconds=30)
