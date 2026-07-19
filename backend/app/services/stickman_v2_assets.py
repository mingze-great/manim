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
from PIL import Image, ImageDraw, ImageFilter, ImageFont, ImageStat
from sqlalchemy.orm import Session

from app.models.system_config import SystemConfig
OPENING_STYLE_CONFIG_KEY = "stickman_v2_opening_styles"
BACKGROUND_TEMPLATE_CONFIG_KEY = "stickman_v2_background_templates"
SCENE_STYLE_LIBRARY_CONFIG_KEY = "stickman_v2_scene_style_libraries"


def _upload_root() -> Path:
    return Path(__file__).resolve().parents[2] / "uploads" / "stickman_v2_admin_assets"


def asset_dir(kind: str) -> Path:
    target = _upload_root() / kind
    target.mkdir(parents=True, exist_ok=True)
    return target


def _scene_style_library_root() -> Path:
    target = _upload_root() / "scene_style_libraries"
    target.mkdir(parents=True, exist_ok=True)
    return target


def _read_config(db: Session, key: str) -> list[dict]:
    config = db.query(SystemConfig).filter(SystemConfig.key == key).first()
    if not config or not config.value:
        return []
    try:
        payload = json.loads(config.value)
    except Exception:
        return []
    return payload if isinstance(payload, list) else []


def _write_config(db: Session, key: str, value: list[dict]):
    config = db.query(SystemConfig).filter(SystemConfig.key == key).first()
    serialized = json.dumps(value, ensure_ascii=False)
    if config:
        config.value = serialized
    else:
        db.add(SystemConfig(key=key, value=serialized))
    db.commit()


def _slug(text: str) -> str:
    cleaned = re.sub(r"[^0-9a-zA-Z\u4e00-\u9fff]+", "-", str(text or "").strip()).strip("-")
    return cleaned[:60] or uuid.uuid4().hex[:12]


def _normalize_items(items: list[dict], *, kind: str) -> list[dict]:
    normalized: list[dict] = []
    for index, raw in enumerate(items or [], start=1):
        if not isinstance(raw, dict):
            continue
        key = str(raw.get("key") or _slug(raw.get("name") or f"{kind}-{index}")).strip()
        name = str(raw.get("name") or key).strip()
        if not key or not name:
            continue
        item = {
            "key": key,
            "name": name,
            "description": str(raw.get("description") or "").strip(),
            "is_active": bool(raw.get("is_active", True)),
            "sort_order": int(raw.get("sort_order") or index),
        }
        if kind == "opening_styles":
            item["prompt"] = str(raw.get("prompt") or "").strip()
            item["sample_image_path"] = str(raw.get("sample_image_path") or "").strip()
            item["sample_image_url"] = str(raw.get("sample_image_url") or "").strip()
        elif kind == "background_templates":
            item["background_image_path"] = str(raw.get("background_image_path") or "").strip()
            item["background_image_url"] = str(raw.get("background_image_url") or "").strip()
        else:
            item["is_visible"] = bool(raw.get("is_visible", True))
            item["package_dir"] = str(raw.get("package_dir") or "").strip()
            item["material_json_path"] = str(raw.get("material_json_path") or "").strip()
            item["cover_image_path"] = str(raw.get("cover_image_path") or "").strip()
            item["cover_image_url"] = str(raw.get("cover_image_url") or "").strip()
            item["image_count"] = int(raw.get("image_count") or 0)
            item["material_count"] = int(raw.get("material_count") or 0)
        normalized.append(item)
    normalized.sort(key=lambda item: (int(item.get("sort_order") or 0), item["name"]))
    return normalized


def list_opening_styles(db: Session, active_only: bool = False) -> list[dict]:
    items = _normalize_items(_read_config(db, OPENING_STYLE_CONFIG_KEY), kind="opening_styles")
    if active_only:
        items = [item for item in items if item.get("is_active")]
    return items


def save_opening_styles(db: Session, items: list[dict]) -> list[dict]:
    normalized = _normalize_items(items, kind="opening_styles")
    _write_config(db, OPENING_STYLE_CONFIG_KEY, normalized)
    return normalized


def list_background_templates(db: Session, active_only: bool = False) -> list[dict]:
    items = _normalize_items(_read_config(db, BACKGROUND_TEMPLATE_CONFIG_KEY), kind="background_templates")
    if active_only:
        items = [item for item in items if item.get("is_active")]
    return items


def save_background_templates(db: Session, items: list[dict]) -> list[dict]:
    normalized = _normalize_items(items, kind="background_templates")
    _write_config(db, BACKGROUND_TEMPLATE_CONFIG_KEY, normalized)
    return normalized


def list_scene_style_libraries(db: Session, active_only: bool = False, visible_only: bool = False) -> list[dict]:
    items = _normalize_items(_read_config(db, SCENE_STYLE_LIBRARY_CONFIG_KEY), kind="scene_style_libraries")
    if active_only:
        items = [item for item in items if item.get("is_active")]
    if visible_only:
        items = [item for item in items if item.get("is_visible")]
    return items


def save_scene_style_libraries(db: Session, items: list[dict]) -> list[dict]:
    normalized = _normalize_items(items, kind="scene_style_libraries")
    _write_config(db, SCENE_STYLE_LIBRARY_CONFIG_KEY, normalized)
    return normalized


def _asset_public_url(*, kind: str, local_path: str = "", explicit_url: str = "") -> Optional[str]:
    image_path = str(local_path or "").strip()
    if not image_path:
        return explicit_url or None
    return f"/api/projects/stickman/v2-assets/{kind}/{Path(image_path).name}"


async def save_asset_upload(file: UploadFile, *, kind: str, item_key: str) -> dict:
    suffix = Path(file.filename or "asset.png").suffix.lower()
    if suffix not in {".png", ".jpg", ".jpeg", ".webp"}:
        raise ValueError("仅支持 png/jpg/jpeg/webp 图片")
    target_dir = asset_dir(kind)
    target_path = target_dir / f"{_slug(item_key)}_{uuid.uuid4().hex[:10]}{suffix}"
    content = await file.read()
    if not content:
        raise ValueError("图片文件为空")
    target_path.write_bytes(content)
    return {"path": str(target_path), "image_url": ""}


def _item_public_payload(item: dict, *, kind: str) -> dict:
    payload = dict(item)
    if kind == "opening_styles":
        image_path_key = "sample_image_path"
        image_url_key = "sample_image_url"
    elif kind == "background_templates":
        image_path_key = "background_image_path"
        image_url_key = "background_image_url"
    else:
        image_path_key = "cover_image_path"
        image_url_key = "cover_image_url"
    payload["image_url"] = _asset_public_url(
        kind=kind,
        local_path=str(payload.get(image_path_key) or "").strip(),
        explicit_url=str(payload.get(image_url_key) or "").strip(),
    )
    return payload


def public_opening_styles(db: Session) -> list[dict]:
    return [_item_public_payload(item, kind="opening_styles") for item in list_opening_styles(db, active_only=True)]


def public_background_templates(db: Session) -> list[dict]:
    return [_item_public_payload(item, kind="background_templates") for item in list_background_templates(db, active_only=True)]


def public_scene_style_libraries(db: Session) -> list[dict]:
    return [_item_public_payload(item, kind="scene_style_libraries") for item in list_scene_style_libraries(db, active_only=True, visible_only=True)]


def get_background_template(db: Session, template_key: str) -> Optional[dict]:
    key = str(template_key or "").strip()
    if not key:
        return None
    return next((item for item in list_background_templates(db, active_only=True) if item.get("key") == key), None)


def find_asset_file(db: Session, kind: str, filename: str) -> Optional[Path]:
    if kind == "opening_styles":
        source = list_opening_styles(db)
        key = "sample_image_path"
    elif kind == "background_templates":
        source = list_background_templates(db)
        key = "background_image_path"
    else:
        source = list_scene_style_libraries(db)
        key = "cover_image_path"
    for item in source:
        path = str(item.get(key) or "").strip()
        if path and Path(path).name == filename and Path(path).exists():
            return Path(path)
    candidate = asset_dir(kind) / filename
    if candidate.exists():
        return candidate
    return None


def _resolve_scene_library_image(package_dir: Path, raw_path: str, file_name: str) -> Optional[Path]:
    candidate_values = []
    if raw_path:
        raw_candidate = Path(raw_path)
        candidate_values.append(raw_candidate if raw_candidate.is_absolute() else package_dir / raw_candidate)
    if file_name:
        file_candidate = package_dir / file_name
        candidate_values.append(file_candidate)
        basename = Path(file_name).name
        if basename:
            candidate_values.extend(package_dir.rglob(basename))
    seen = set()
    for candidate in candidate_values:
        resolved = Path(candidate)
        key = str(resolved)
        if key in seen:
            continue
        seen.add(key)
        if resolved.exists() and resolved.is_file():
            return resolved
    return None


def _scene_library_cover_image(package_dir: Path, entries: list[dict]) -> Optional[Path]:
    for entry in entries:
        image_path = _resolve_scene_library_image(package_dir, str(entry.get("image_path") or "").strip(), str(entry.get("file_name") or "").strip())
        if image_path:
            return image_path
    for pattern in ("*.png", "*.jpg", "*.jpeg", "*.webp"):
        first = next(iter(sorted(package_dir.rglob(pattern))), None)
        if first:
            return first
    return None


def _normalize_scene_library_manifest(package_dir: Path, manifest_path: Path) -> tuple[Path, int, int, Optional[Path]]:
    payload = json.loads(manifest_path.read_text(encoding="utf-8"))
    if not isinstance(payload, list) or not payload:
        raise ValueError("material.json 内容无效，必须是数组")
    normalized_entries = []
    for entry in payload:
        if not isinstance(entry, dict):
            continue
        clone = dict(entry)
        file_name = str(clone.get("file_name") or "").strip()
        raw_image_path = str(clone.get("image_path") or "").strip()
        image_path = _resolve_scene_library_image(package_dir, raw_image_path, file_name)
        if not image_path:
            continue
        clone["file_name"] = file_name or image_path.name
        clone["image_path"] = str(image_path)
        normalized_entries.append(clone)
    if not normalized_entries:
        raise ValueError("场景图风格包里没有可用图片，请检查 material.json 与图片文件是否对应")
    normalized_manifest_path = package_dir / "materials.normalized.json"
    normalized_manifest_path.write_text(json.dumps(normalized_entries, ensure_ascii=False, indent=2), encoding="utf-8")
    cover_image = _scene_library_cover_image(package_dir, normalized_entries)
    image_count = len({str(item.get("image_path") or "") for item in normalized_entries if str(item.get("image_path") or "").strip()})
    return normalized_manifest_path, len(normalized_entries), image_count, cover_image


async def save_scene_style_library_package(file: UploadFile, *, item_key: str) -> dict:
    suffix = Path(file.filename or "scene_style_library.zip").suffix.lower()
    if suffix != ".zip":
        raise ValueError("仅支持 zip 压缩包")
    content = await file.read()
    if not content:
        raise ValueError("压缩包为空")

    package_dir = _scene_style_library_root() / f"{_slug(item_key)}_{uuid.uuid4().hex[:10]}"
    package_dir.mkdir(parents=True, exist_ok=True)
    zip_path = package_dir / "package.zip"
    zip_path.write_bytes(content)
    try:
        with zipfile.ZipFile(zip_path, "r") as archive:
            archive.extractall(package_dir)
    except Exception as exc:
        shutil.rmtree(package_dir, ignore_errors=True)
        raise ValueError(f"压缩包解压失败: {exc}") from exc
    finally:
        if zip_path.exists():
            zip_path.unlink()

    manifest_path = next((path for path in [package_dir / "material.json", package_dir / "materials.json"] if path.exists()), None)
    if not manifest_path:
        manifest_candidates = list(package_dir.rglob("material.json")) + list(package_dir.rglob("materials.json"))
        manifest_path = manifest_candidates[0] if manifest_candidates else None
    if not manifest_path:
        shutil.rmtree(package_dir, ignore_errors=True)
        raise ValueError("压缩包内缺少 material.json 或 materials.json")

    try:
        normalized_manifest_path, material_count, image_count, cover_image = _normalize_scene_library_manifest(package_dir, manifest_path)
    except Exception as exc:
        shutil.rmtree(package_dir, ignore_errors=True)
        raise ValueError(str(exc)) from exc

    return {
        "package_dir": str(package_dir),
        "material_json_path": str(normalized_manifest_path),
        "cover_image_path": str(cover_image) if cover_image else "",
        "cover_image_url": "",
        "material_count": material_count,
        "image_count": image_count,
    }


def resolve_generation_assets(db: Session, generation_flags: dict, project_background_image_path: Optional[str], project_style_reference_image_path: Optional[str], project_style_reference_notes: Optional[str]):
    flags = dict(generation_flags or {})
    selected_style_key = str(flags.get("opening_style_key") or "").strip()
    selected_background_key = str(flags.get("background_template_key") or "").strip()
    selected_scene_style_key = str(flags.get("scene_style_library_key") or "").strip()
    selected_style = next((item for item in list_opening_styles(db, active_only=True) if item.get("key") == selected_style_key), None)
    selected_background = next((item for item in list_background_templates(db, active_only=True) if item.get("key") == selected_background_key), None)
    selected_scene_style = next((item for item in list_scene_style_libraries(db, active_only=True) if item.get("key") == selected_scene_style_key), None)

    style_image_path = str(selected_style.get("sample_image_path") or "").strip() if selected_style else str(project_style_reference_image_path or "").strip()
    style_notes = str(project_style_reference_notes or "").strip()
    if selected_style:
        style_prompt = str(selected_style.get("prompt") or "").strip()
        style_desc = str(selected_style.get("description") or "").strip()
        merged = "\n".join(part for part in [style_prompt, style_desc, style_notes] if part)
        style_notes = merged.strip()

    uploaded_background_path = str(project_background_image_path or "").strip()
    template_background_path = str(selected_background.get("background_image_path") or "").strip() if selected_background else ""
    background_image_path = uploaded_background_path or template_background_path
    return {
        "background_image_path": background_image_path or None,
        "style_reference_image_path": style_image_path or None,
        "style_reference_notes": style_notes or None,
        "opening_style_name": str(selected_style.get("name") or "").strip() if selected_style else None,
        "background_template_name": str(selected_background.get("name") or "").strip() if selected_background else None,
        "scene_style_library": selected_scene_style,
        "scene_style_library_name": str(selected_scene_style.get("name") or "").strip() if selected_scene_style else None,
    }


def _background_output_dir() -> Path:
    target = Path(__file__).resolve().parents[2] / "uploads" / "background_images"
    target.mkdir(parents=True, exist_ok=True)
    return target


def _background_font_candidates() -> list[str]:
    if os.name == "nt":
        return [r"C:\Windows\Fonts\msyhbd.ttc", r"C:\Windows\Fonts\msyh.ttc", r"C:\Windows\Fonts\simhei.ttf"]
    return [
        "/usr/share/fonts/truetype/noto/NotoSansCJK-Bold.ttc",
        "/usr/share/fonts/opentype/noto/NotoSansCJK-Bold.ttc",
        "/usr/share/fonts/truetype/wqy/wqy-zenhei.ttc",
        "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
    ]


def _load_background_font(size: int):
    for candidate in _background_font_candidates():
        if candidate and Path(candidate).exists():
            try:
                return ImageFont.truetype(candidate, size=size)
            except Exception:
                continue
    return ImageFont.load_default()


def _normalize_theme_title(text: str) -> str:
    clean = re.sub(r"\s+", " ", str(text or "").strip())
    return clean[:28] or "主题内容"


def _wrap_theme_title(draw: ImageDraw.ImageDraw, text: str, font, max_width: int) -> list[str]:
    chars = list(text)
    lines: list[str] = []
    current = ""
    for char in chars:
        candidate = f"{current}{char}"
        bbox = draw.textbbox((0, 0), candidate, font=font)
        if current and (bbox[2] - bbox[0]) > max_width:
            lines.append(current)
            current = char
        else:
            current = candidate
    if current:
        lines.append(current)
    return lines[:2] or [text]


def render_project_background_from_template(template_path: str, theme_text: str, project_id: int) -> str:
    source = Path(str(template_path or "").strip())
    if not source.exists():
        raise ValueError("背景模板图不存在")

    title = _normalize_theme_title(theme_text)
    output_path = _background_output_dir() / f"project_{project_id}_template_{uuid.uuid4().hex[:12]}.png"

    with Image.open(source).convert("RGBA") as image:
        canvas = image.copy()
        draw = ImageDraw.Draw(canvas)
        width, height = canvas.size

        panel_left = int(width * 0.055)
        panel_top = int(height * 0.06)
        panel_width = int(width * 0.34)
        panel_height = int(height * 0.16)
        panel_box = (panel_left, panel_top, panel_left + panel_width, panel_top + panel_height)

        panel_sample = image.crop(panel_box).convert("RGB")
        stat = ImageStat.Stat(panel_sample)
        fill_rgb = tuple(int(channel) for channel in stat.median[:3]) if panel_sample.size[0] and panel_sample.size[1] else (255, 255, 255)
        draw.rectangle(panel_box, fill=(*fill_rgb, 255))

        font = _load_background_font(max(30, int(height * 0.036)))
        lines = _wrap_theme_title(draw, title, font, int(panel_width * 0.84))
        text_x = panel_left + int(panel_width * 0.08)
        text_y = panel_top + int(panel_height * 0.16)
        line_gap = max(10, int(height * 0.01))
        for index, line in enumerate(lines):
            bbox = draw.textbbox((0, 0), line, font=font)
            line_height = bbox[3] - bbox[1]
            y = text_y + index * (line_height + line_gap)
            draw.text(
                (text_x, y),
                line,
                font=font,
                fill=(33, 37, 41, 255),
                stroke_width=2,
                stroke_fill=(255, 255, 255, 180),
            )

        canvas.convert("RGB").save(output_path, format="PNG")
    return str(output_path)


def normalize_scene_overlay_image(source_path: str, target_path: str, max_size: int = 800):
    from PIL import Image

    image = Image.open(source_path).convert("RGBA")
    canvas = Image.new("RGBA", (max_size, max_size), (0, 0, 0, 0))
    image.thumbnail((int(max_size * 0.96), int(max_size * 0.96)), Image.Resampling.LANCZOS)
    x = (max_size - image.width) // 2
    y = (max_size - image.height) // 2
    canvas.alpha_composite(image, (x, y))
    canvas.save(target_path, format="PNG")
