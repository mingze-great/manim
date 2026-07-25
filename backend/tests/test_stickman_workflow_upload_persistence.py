import os

os.environ["DATABASE_URL"] = "sqlite:///:memory:"

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.database import Base
from app.models.system_config import SystemConfig
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
