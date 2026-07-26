from __future__ import annotations

import math
import re
from datetime import datetime
from typing import Optional

ENDING_PAUSE_SECONDS = 0.25
MID_PAUSE_SECONDS = 0.12
LINE_PAUSE_SECONDS = 0.35
DEFAULT_CHARS_PER_SECOND = 4.6


def _current_marker(period: str) -> str:
    now = datetime.utcnow()
    return now.strftime("%Y-%m") if period == "monthly" else now.date().isoformat()


def _reset_period_counter(permission: dict, *, used_key: str, marker_key: str, period: str) -> None:
    marker = _current_marker(period)
    if not permission.get(marker_key) and int(permission.get(used_key) or 0) > 0:
        permission[marker_key] = marker
        return
    if permission.get(marker_key) != marker:
        permission[used_key] = 0
        permission[marker_key] = marker


def _minutes(seconds: int) -> int:
    return max(1, int(math.ceil(max(int(seconds or 0), 1) / 60)))


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


def validate_stickman_quota(permission: dict, requested_seconds: int) -> None:
    if not permission.get("enabled", False):
        raise ValueError("当前账号暂未开通火柴人成片")
    seconds = max(1, int(requested_seconds or 1))
    max_video_seconds = int(permission.get("max_video_seconds") or 60)
    if seconds > max_video_seconds:
        raise ValueError(f"单条视频不能超过 {max_video_seconds} 秒")

    quota_mode = str(permission.get("quota_mode") or "period")
    if quota_mode == "count_package":
        total_limit = int(permission.get("total_video_limit") or permission.get("daily_limit") or 0)
        used_total = int(permission.get("used_total_videos") or 0)
        if total_limit > 0 and used_total >= total_limit:
            raise ValueError("视频次数已用完")
        return

    period = str(permission.get("period") or "monthly")
    _reset_period_counter(permission, used_key="used_today", marker_key="last_reset_date", period=period)
    video_limit = int(permission.get("daily_limit") or 0)
    used_videos = int(permission.get("used_today") or 0)
    if video_limit > 0 and used_videos >= video_limit:
        raise ValueError("当前周期视频数量已用完")

    requested_minutes = _minutes(seconds)
    daily_minutes_limit = int(permission.get("daily_minutes_limit") or 0)
    if daily_minutes_limit > 0:
        _reset_period_counter(permission, used_key="used_daily_minutes", marker_key="daily_minutes_marker", period="daily")
        remaining = daily_minutes_limit - int(permission.get("used_daily_minutes") or 0)
        if requested_minutes > remaining:
            raise ValueError(f"每日剩余分钟不足，剩余 {max(remaining, 0)} 分钟")

    monthly_minutes_limit = int(permission.get("monthly_minutes_limit") or 0)
    if monthly_minutes_limit > 0:
        _reset_period_counter(permission, used_key="used_monthly_minutes", marker_key="monthly_minutes_marker", period="monthly")
        remaining = monthly_minutes_limit - int(permission.get("used_monthly_minutes") or 0)
        if requested_minutes > remaining:
            raise ValueError(f"本月剩余分钟不足，剩余 {max(remaining, 0)} 分钟")


def consume_stickman_quota(permission: dict, requested_seconds: int) -> dict:
    seconds = max(1, int(requested_seconds or 1))
    requested_minutes = _minutes(seconds)
    quota_mode = str(permission.get("quota_mode") or "period")

    if quota_mode == "count_package":
        permission["used_total_videos"] = int(permission.get("used_total_videos") or 0) + 1
        permission["used_total_minutes"] = int(permission.get("used_total_minutes") or 0) + requested_minutes
        return permission

    period = str(permission.get("period") or "monthly")
    _reset_period_counter(permission, used_key="used_today", marker_key="last_reset_date", period=period)
    permission["used_today"] = int(permission.get("used_today") or 0) + 1

    if int(permission.get("daily_minutes_limit") or 0) > 0:
        _reset_period_counter(permission, used_key="used_daily_minutes", marker_key="daily_minutes_marker", period="daily")
        permission["used_daily_minutes"] = int(permission.get("used_daily_minutes") or 0) + requested_minutes
    if int(permission.get("monthly_minutes_limit") or 0) > 0:
        _reset_period_counter(permission, used_key="used_monthly_minutes", marker_key="monthly_minutes_marker", period="monthly")
        permission["used_monthly_minutes"] = int(permission.get("used_monthly_minutes") or 0) + requested_minutes
    return permission
