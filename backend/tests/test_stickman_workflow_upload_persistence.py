import os
import asyncio
import zipfile

os.environ["DATABASE_URL"] = "sqlite:///:memory:"

from io import BytesIO

from starlette.datastructures import UploadFile
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.database import Base
from app.models.system_config import SystemConfig
from app.services import stickman_workflow_assets
from app.services.stickman_workflow_assets import _normalize_manifest, list_material_libraries, save_material_libraries


def _session():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(bind=engine)
    return sessionmaker(bind=engine)()


def test_save_material_libraries_keeps_uploaded_package_fields_after_refresh(tmp_path):
    db = _session()
    package_dir = tmp_path / "library"
    package_dir.mkdir()
    manifest = package_dir / "materials.normalized.json"
    cover = package_dir / "cover.png"
    manifest.write_text("[]", encoding="utf-8")
    cover.write_bytes(b"png")

    save_material_libraries(db, [{
        "key": "partner_style",
        "name": "合作者风格库",
        "base_path": str(package_dir),
        "material_json_path": str(manifest),
        "cover_image_path": str(cover),
        "material_count": 18,
        "image_count": 18,
        "is_active": True,
        "is_visible": True,
        "source": "uploaded_package",
    }])

    refreshed = list_material_libraries(db)
    uploaded = next(item for item in refreshed if item["key"] == "partner_style")

    assert uploaded["base_path"] == str(package_dir)
    assert uploaded["material_json_path"] == str(manifest)
    assert uploaded["cover_image_path"] == str(cover)
    assert uploaded["material_count"] == 18
    assert uploaded["image_count"] == 18
    assert uploaded["is_active"] is True
    assert uploaded["is_visible"] is True


def test_normalize_manifest_accepts_utf8_bom_json(tmp_path):
    image = tmp_path / "scene.png"
    image.write_bytes(b"png")
    manifest = tmp_path / "material.json"
    manifest.write_text('[{"file_name":"scene.png","image_path":"scene.png"}]', encoding="utf-8-sig")

    normalized_path, material_count, image_count, cover_image = _normalize_manifest(tmp_path, manifest)

    assert normalized_path.exists()
    assert material_count == 1
    assert image_count == 1
    assert cover_image == image


def test_save_material_libraries_keeps_new_library_when_name_is_blank():
    db = _session()

    save_material_libraries(db, [{
        "key": "draft_style",
        "name": "",
        "is_active": True,
        "is_visible": True,
    }])

    refreshed = list_material_libraries(db)
    draft = next(item for item in refreshed if item["key"] == "draft_style")

    assert draft["name"] == "draft_style"
    assert draft["is_active"] is True
    assert draft["is_visible"] is True


def test_upload_package_accepts_generated_manifest_and_camel_case_paths(tmp_path, monkeypatch):
    upload_root = tmp_path / "uploads"
    monkeypatch.setattr(stickman_workflow_assets, "_upload_root", lambda: upload_root)

    buffer = BytesIO()
    with zipfile.ZipFile(buffer, "w") as archive:
        archive.writestr("materials.generated.json", '[{"fileName":"scene.png","imagePath":"scene.png","summaryLabel":"焦虑"}]')
        archive.writestr("scene.png", b"png")
    buffer.seek(0)
    upload = UploadFile(filename="library.zip", file=buffer)

    package_info = asyncio.run(stickman_workflow_assets.save_material_library_package(upload, library_key="generated_style"))

    assert package_info["material_count"] == 1
    assert package_info["image_count"] == 1
    assert package_info["material_json_path"].endswith("materials.normalized.json")
    assert package_info["cover_image_path"].endswith("scene.png")


def test_upload_package_rejects_oversized_zip_with_clear_error(tmp_path, monkeypatch):
    upload_root = tmp_path / "uploads"
    monkeypatch.setattr(stickman_workflow_assets, "_upload_root", lambda: upload_root)
    monkeypatch.setattr(stickman_workflow_assets, "MAX_PACKAGE_BYTES", 10)

    buffer = BytesIO(b"0" * 32)
    upload = UploadFile(filename="library.zip", file=buffer)

    try:
        asyncio.run(stickman_workflow_assets.save_material_library_package(upload, library_key="too_large"))
    except ValueError as exc:
        assert "压缩包不能超过" in str(exc)
    else:
        raise AssertionError("oversized package should be rejected")
