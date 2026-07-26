from __future__ import annotations

import json

from sqlalchemy.orm import Session

from app.models.system_config import SystemConfig

CONFIG_KEY = "stickman_workflow_plans"


def default_stickman_workflow_plans() -> list[dict]:
    return [
        {
            "key": "monthly_basic",
            "name": "素材月卡",
            "description": "适合稳定日更的素材库模式",
            "quota_mode": "period",
            "daily_limit": 3,
            "daily_minutes_limit": 0,
            "monthly_minutes_limit": 90,
            "total_video_limit": 0,
            "max_video_seconds": 60,
            "material_mode": "material_only",
            "allowed_libraries": ["sc1_outputs"],
            "amount": 9900,
            "is_active": True,
            "sort_order": 1,
        },
        {
            "key": "count_40x5m",
            "name": "40条不限时包",
            "description": "40个视频，每个视频5分钟以内，不限制自然有效期",
            "quota_mode": "count_package",
            "daily_limit": 0,
            "daily_minutes_limit": 0,
            "monthly_minutes_limit": 0,
            "total_video_limit": 40,
            "max_video_seconds": 300,
            "material_mode": "material_only",
            "allowed_libraries": ["sc1_outputs"],
            "amount": 19900,
            "is_active": True,
            "sort_order": 2,
        },
    ]


def _safe_int(value: object, default: int = 0) -> int:
    try:
        return int(value if value is not None else default)
    except (TypeError, ValueError):
        return default


def _normalize_plan(raw: dict, index: int) -> dict:
    key = str(raw.get("key") or "").strip() or f"plan_{index}"
    quota_mode = str(raw.get("quota_mode") or "period").strip()
    if quota_mode not in {"period", "count_package"}:
        quota_mode = "period"
    material_mode = str(raw.get("material_mode") or "material_only").strip()
    if material_mode not in {"material_only", "ai_image", "hybrid"}:
        material_mode = "material_only"
    libraries = raw.get("allowed_libraries") or []
    if isinstance(libraries, str):
        try:
            libraries = json.loads(libraries)
        except Exception:
            libraries = []
    if not isinstance(libraries, list):
        libraries = []
    total_video_limit = max(0, _safe_int(raw.get("total_video_limit")))
    daily_limit = max(0, _safe_int(raw.get("daily_limit")))
    if quota_mode == "count_package" and total_video_limit == 0:
        total_video_limit = daily_limit
        daily_limit = 0
    return {
        "key": key,
        "name": str(raw.get("name") or key).strip(),
        "description": str(raw.get("description") or "").strip(),
        "quota_mode": quota_mode,
        "daily_limit": daily_limit,
        "daily_minutes_limit": max(0, _safe_int(raw.get("daily_minutes_limit"))),
        "monthly_minutes_limit": max(0, _safe_int(raw.get("monthly_minutes_limit"))),
        "total_video_limit": total_video_limit,
        "max_video_seconds": max(15, min(1800, _safe_int(raw.get("max_video_seconds"), 60))),
        "material_mode": material_mode,
        "allowed_libraries": [str(item).strip() for item in libraries if str(item).strip()],
        "amount": max(0, _safe_int(raw.get("amount"))),
        "is_active": bool(raw.get("is_active", True)),
        "sort_order": _safe_int(raw.get("sort_order"), index),
    }


def normalize_stickman_workflow_plans(items: list[dict]) -> list[dict]:
    plans = [_normalize_plan(item, index) for index, item in enumerate(items or [], start=1) if isinstance(item, dict)]
    plans.sort(key=lambda item: (int(item.get("sort_order") or 0), item.get("name") or ""))
    return plans


def list_stickman_workflow_plans(db: Session, active_only: bool = False) -> list[dict]:
    config = db.query(SystemConfig).filter(SystemConfig.key == CONFIG_KEY).first()
    payload = None
    if config and config.value:
        try:
            payload = json.loads(config.value)
        except Exception:
            payload = None
    plans = normalize_stickman_workflow_plans(payload if isinstance(payload, list) else default_stickman_workflow_plans())
    if active_only:
        plans = [plan for plan in plans if plan.get("is_active")]
    return plans


def save_stickman_workflow_plans(db: Session, items: list[dict]) -> list[dict]:
    plans = normalize_stickman_workflow_plans(items)
    serialized = json.dumps(plans, ensure_ascii=False)
    config = db.query(SystemConfig).filter(SystemConfig.key == CONFIG_KEY).first()
    if config:
        config.value = serialized
    else:
        db.add(SystemConfig(key=CONFIG_KEY, value=serialized))
    db.commit()
    return list_stickman_workflow_plans(db)


def find_stickman_workflow_plan(db: Session, key: str) -> dict | None:
    plan_key = str(key or "").strip()
    return next((plan for plan in list_stickman_workflow_plans(db, active_only=True) if plan.get("key") == plan_key), None)


def permission_from_plan(plan: dict) -> dict:
    quota_mode = str(plan.get("quota_mode") or "period")
    material_mode = plan.get("material_mode") or "material_only"
    permission = {
        "enabled": True,
        "quota_mode": quota_mode,
        "daily_limit": 0 if quota_mode == "count_package" else int(plan.get("daily_limit") or 0),
        "period": "lifetime" if quota_mode == "count_package" else "monthly",
        "max_video_seconds": int(plan.get("max_video_seconds") or 60),
        "material_mode": "material_only" if material_mode == "hybrid" else material_mode,
        "visible_image_modes": ["material_only", "ai_image"] if material_mode == "hybrid" else [material_mode],
        "allowed_libraries": plan.get("allowed_libraries") or [],
    }
    if quota_mode == "count_package":
        permission.update(
            {
                "total_video_limit": int(plan.get("total_video_limit") or plan.get("daily_limit") or 0),
                "used_total_videos": 0,
                "unlimited_time": True,
            }
        )
    else:
        permission.update(
            {
                "daily_minutes_limit": int(plan.get("daily_minutes_limit") or 0),
                "monthly_minutes_limit": int(plan.get("monthly_minutes_limit") or 0),
            }
        )
    return permission
