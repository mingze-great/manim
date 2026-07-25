from __future__ import annotations

import json
import os
import re
import shutil
import uuid
import zipfile
from pathlib import Path
from typing import Optional

from fastapi import UploadFile
from sqlalchemy.orm import Session

from app.config import get_settings
from app.models.system_config import SystemConfig

STICKMAN_WORKFLOW_MATERIAL_LIBRARY_CONFIG_KEY = "stickman_workflow_material_libraries"


def _upload_root() -> Path:
    return Path(__file__).resolve().parents[2] / "uploads" / "stickman_workflow_material_libraries"


def _asset_dir() -> Path:
    target = _upload_root()
    target.mkdir(parents=True, exist_ok=True)
    return target


def material_library_asset_root() -> Path:
    return _asset_dir()


def _slug(text: str) -> str:
    cleaned = re.sub(r"[^0-9a-zA-Z\u4e00-\u9fff]+", "-", str(text or "").strip()).strip("-")
    return cleaned[:60] or uuid.uuid4().hex[:12]


def _default_sc1_base_path() -> str:
    settings = get_settings()
    configured = str(settings.STICKMAN_MATERIAL_SOURCE_DIR or "").strip()
    if configured:
        return configured
    if os.name == "nt":
        return r"E:\ai\火柴人工作流\outputs"
    return "/opt/manim_assets/sc1-outputs"


def _default_sc1_manifest_path(base_path: str) -> str:
    settings = get_settings()
    configured = str(settings.STICKMAN_MATERIAL_LIBRARY_PATH or "").strip()
    if configured:
        return configured
    return str(Path(base_path) / "material.json")


def default_material_library() -> dict:
    base_path = _default_sc1_base_path()
    return {
        "key": "sc1_outputs",
        "name": "SC1 火柴人素材库",
        "description": "默认心理学火柴人素材库",
        "is_active": True,
        "is_visible": True,
        "sort_order": 1,
        "base_path": base_path,
        "material_json_path": _default_sc1_manifest_path(base_path),
        "cover_image_path": "",
        "cover_image_url": "",
        "image_count": 0,
        "material_count": 0,
        "source": "configured_path",
    }


def normalize_material_library_items(items: list[dict]) -> list[dict]:
    normalized: list[dict] = []
    for index, raw in enumerate(items or [], start=1):
        if not isinstance(raw, dict):
            continue
        key = str(raw.get("key") or "").strip()
        name = str(raw.get("name") or "").strip() or key
        if not key:
            continue
        item = {
            "key": key,
            "name": name,
            "description": str(raw.get("description") or "").strip(),
            "is_active": bool(raw.get("is_active", True)),
            "is_visible": bool(raw.get("is_visible", True)),
            "sort_order": int(raw.get("sort_order") or index),
            "base_path": str(raw.get("base_path") or "").strip(),
            "material_json_path": str(raw.get("material_json_path") or "").strip(),
            "cover_image_path": str(raw.get("cover_image_path") or "").strip(),
            "cover_image_url": str(raw.get("cover_image_url") or "").strip(),
            "image_count": int(raw.get("image_count") or 0),
            "material_count": int(raw.get("material_count") or 0),
            "source": str(raw.get("source") or "uploaded_package").strip(),
        }
        normalized.append(item)
    normalized.sort(key=lambda item: (int(item.get("sort_order") or 0), item["name"]))
    return normalized


def _read_config(db: Session) -> list[dict]:
    config = db.query(SystemConfig).filter(SystemConfig.key == STICKMAN_WORKFLOW_MATERIAL_LIBRARY_CONFIG_KEY).first()
    if not config or not config.value:
        return []
    try:
        payload = json.loads(config.value)
    except Exception:
        return []
    return payload if isinstance(payload, list) else []


def _write_config(db: Session, value: list[dict]):
    serialized = json.dumps(value, ensure_ascii=False)
    config = db.query(SystemConfig).filter(SystemConfig.key == STICKMAN_WORKFLOW_MATERIAL_LIBRARY_CONFIG_KEY).first()
    if config:
        config.value = serialized
    else:
        db.add(SystemConfig(key=STICKMAN_WORKFLOW_MATERIAL_LIBRARY_CONFIG_KEY, value=serialized))
    db.commit()


def list_material_libraries(db: Session, active_only: bool = False, visible_only: bool = False) -> list[dict]:
    merged = {default_material_library()["key"]: default_material_library()}
    for item in normalize_material_library_items(_read_config(db)):
        merged[item["key"]] = item
    libraries = list(merged.values())
    libraries.sort(key=lambda item: (int(item.get("sort_order") or 0), item.get("name") or ""))
    if active_only:
        libraries = [item for item in libraries if item.get("is_active")]
    if visible_only:
        libraries = [item for item in libraries if item.get("is_visible")]
    return libraries


def save_material_libraries(db: Session, items: list[dict]) -> list[dict]:
    normalized = normalize_material_library_items(items)
    _write_config(db, normalized)
    return list_material_libraries(db)


def _asset_public_url(local_path: str = "", explicit_url: str = "", library_key: str = "") -> Optional[str]:
    image_path = str(local_path or "").strip()
    if not image_path:
        return explicit_url or None
    key = str(library_key or "").strip()
    if key:
        return f"/api/admin/stickman-workflow/assets/material-libraries/{key}/{Path(image_path).name}"
    return f"/api/admin/stickman-workflow/assets/material-libraries/{Path(image_path).name}"


def _public_payload(item: dict) -> dict:
    clone = dict(item)
    clone["image_url"] = _asset_public_url(
        str(clone.get("cover_image_path") or "").strip(),
        str(clone.get("cover_image_url") or "").strip(),
        str(clone.get("key") or "").strip(),
    )
    return clone


def public_material_libraries(db: Session) -> list[dict]:
    return [_public_payload(item) for item in list_material_libraries(db, active_only=True, visible_only=True)]


def resolve_material_library(db: Session, library_key: str) -> Optional[dict]:
    key = str(library_key or "sc1_outputs").strip() or "sc1_outputs"
    return next((item for item in list_material_libraries(db, active_only=True) if item.get("key") == key), None)


def find_material_library_asset(db: Session, filename: str, library_key: str = "") -> Optional[Path]:
    safe_name = Path(str(filename or "")).name
    for item in list_material_libraries(db):
        if library_key and item.get("key") != library_key:
            continue
        path = str(item.get("cover_image_path") or "").strip()
        if path and Path(path).name == safe_name and Path(path).exists():
            return Path(path)
    candidate = _asset_dir() / safe_name
    if candidate.exists():
        return candidate
    return None


def _safe_extract_zip(zip_path: Path, target_dir: Path):
    with zipfile.ZipFile(zip_path, "r") as archive:
        for member in archive.infolist():
            destination = (target_dir / member.filename).resolve()
            if not str(destination).startswith(str(target_dir.resolve())):
                raise ValueError("压缩包包含不安全路径")
        archive.extractall(target_dir)


def _resolve_image(package_dir: Path, raw_path: str, file_name: str) -> Optional[Path]:
    candidates: list[Path] = []
    if raw_path:
        raw = Path(raw_path)
        candidates.append(raw if raw.is_absolute() else package_dir / raw)
    if file_name:
        candidates.append(package_dir / file_name)
        candidates.extend(package_dir.rglob(Path(file_name).name))
    for candidate in candidates:
        if candidate.exists() and candidate.is_file():
            return candidate
    return None


def _normalize_manifest(package_dir: Path, manifest_path: Path) -> tuple[Path, int, int, Optional[Path]]:
    payload = json.loads(manifest_path.read_text(encoding="utf-8-sig"))
    if isinstance(payload, dict):
        payload = payload.get("materials") or payload.get("items") or payload.get("data") or []
    if not isinstance(payload, list) or not payload:
        raise ValueError("material.json 内容无效，必须是数组")
    normalized: list[dict] = []
    for raw in payload:
        if not isinstance(raw, dict):
            continue
        clone = dict(raw)
        file_name = str(clone.get("file_name") or clone.get("fileName") or clone.get("filename") or "").strip()
        raw_image_path = str(clone.get("image_path") or clone.get("imagePath") or clone.get("path") or "").strip()
        image_path = _resolve_image(package_dir, raw_image_path, file_name)
        if not image_path:
            continue
        clone["file_name"] = file_name or image_path.name
        clone["image_path"] = str(image_path)
        normalized.append(clone)
    if not normalized:
        raise ValueError("素材库里没有可用图片，请检查 material.json 与图片文件")
    normalized_path = package_dir / "materials.normalized.json"
    normalized_path.write_text(json.dumps(normalized, ensure_ascii=False, indent=2), encoding="utf-8")
    cover_image = Path(str(normalized[0].get("image_path") or ""))
    image_count = len({str(item.get("image_path") or "") for item in normalized})
    return normalized_path, len(normalized), image_count, cover_image if cover_image.exists() else None


async def save_material_library_package(file: UploadFile, *, library_key: str) -> dict:
    suffix = Path(file.filename or "material_library.zip").suffix.lower()
    if suffix != ".zip":
        raise ValueError("仅支持 zip 素材库")
    content = await file.read()
    if not content:
        raise ValueError("压缩包为空")
    package_dir = _asset_dir() / f"{_slug(library_key)}_{uuid.uuid4().hex[:10]}"
    package_dir.mkdir(parents=True, exist_ok=True)
    zip_path = package_dir / "package.zip"
    zip_path.write_bytes(content)
    try:
        _safe_extract_zip(zip_path, package_dir)
    except Exception as exc:
        shutil.rmtree(package_dir, ignore_errors=True)
        raise ValueError(f"压缩包解压失败: {exc}") from exc
    finally:
        if zip_path.exists():
            zip_path.unlink()

    manifest_candidates = (
        list(package_dir.rglob("material.json"))
        + list(package_dir.rglob("materials.json"))
        + list(package_dir.rglob("materials.generated.json"))
        + list(package_dir.rglob("materials.normalized.json"))
    )
    manifest_path = manifest_candidates[0] if manifest_candidates else None
    if not manifest_path:
        shutil.rmtree(package_dir, ignore_errors=True)
        raise ValueError("压缩包内缺少 material.json、materials.json 或 materials.generated.json")
    try:
        normalized_manifest_path, material_count, image_count, cover_image = _normalize_manifest(package_dir, manifest_path)
    except Exception as exc:
        shutil.rmtree(package_dir, ignore_errors=True)
        raise ValueError(str(exc)) from exc
    return {
        "base_path": str(package_dir),
        "material_json_path": str(normalized_manifest_path),
        "cover_image_path": str(cover_image) if cover_image else "",
        "cover_image_url": "",
        "material_count": material_count,
        "image_count": image_count,
        "source": "uploaded_package",
    }
