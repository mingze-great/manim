from __future__ import annotations

import math
import re
from typing import Optional

ENDING_PAUSE_SECONDS = 0.25
MID_PAUSE_SECONDS = 0.12
LINE_PAUSE_SECONDS = 0.35
DEFAULT_CHARS_PER_SECOND = 4.6


def estimate_script_duration_seconds(script: str, speed_factor: float = 1.0) -> int:
    text = str(script or "").strip()
    if not text:
        return 0
    chinese_chars = len(re.findall(r"[\u4e00-\u9fff]", text))
    latin_words = len(re.findall(r"[A-Za-z0-9]+", text))
    readable_units = chinese_chars + int(latin_words * 1.8)
    speed = max(0.5, min(2.0, float(speed_factor or 1.0)))
    spoken_seconds = readable_units / (DEFAULT_CHARS_PER_SECOND * speed)
    mid_pauses = len(re.findall(r"[，、,；;：:]", text)) * MID_PAUSE_SECONDS
    ending_pauses = len(re.findall(r"[。！？.!?]", text)) * ENDING_PAUSE_SECONDS
    line_pauses = text.count("\n") * LINE_PAUSE_SECONDS
    return max(1, int(math.ceil(spoken_seconds + mid_pauses + ending_pauses + line_pauses)))


def validate_script_duration_request(custom_script: Optional[str] = None, target_seconds: Optional[int] = None, max_video_seconds: int = 60) -> int:
    clean_script = str(custom_script or "").strip()
    requested_seconds = int(target_seconds or 0)
    if clean_script and requested_seconds > 0:
        raise ValueError("自定义文案和目标时长不能同时选择")
    if requested_seconds < 0:
        raise ValueError("目标时长无效")
    if requested_seconds and requested_seconds > int(max_video_seconds or 60):
        raise ValueError(f"目标时长不能超过 {int(max_video_seconds or 60)} 秒")
    if clean_script:
        estimated = estimate_script_duration_seconds(clean_script)
        if estimated > int(max_video_seconds or 60):
            raise ValueError(f"自定义文案预计 {estimated} 秒，超过当前上限 {int(max_video_seconds or 60)} 秒")
        return estimated
    return requested_seconds


def validate_image_mode(image_mode: str, can_use_ai_images: bool) -> str:
    normalized = str(image_mode or "material_only").strip() or "material_only"
    if normalized not in {"material_only", "ai_image", "hybrid"}:
        raise ValueError("图片模式无效")
    if normalized != "material_only" and not can_use_ai_images:
        raise ValueError("当前套餐不支持实时生成场景图")
    return normalized
