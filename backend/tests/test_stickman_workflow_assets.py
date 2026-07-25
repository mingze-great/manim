from app.services.stickman_workflow_assets import _asset_public_url, normalize_material_library_items


def test_normalize_material_library_items_keeps_default_sc1():
    items = normalize_material_library_items([
        {
            "key": "sc1_outputs",
            "name": "SC1 火柴人素材库",
            "base_path": "/opt/manim_assets/sc1-outputs",
            "is_active": True,
        }
    ])
    assert items[0]["key"] == "sc1_outputs"
    assert items[0]["base_path"] == "/opt/manim_assets/sc1-outputs"
    assert items[0]["is_active"] is True


def test_normalize_material_library_items_rejects_blank_key():
    items = normalize_material_library_items([{"key": "", "name": ""}])
    assert items == []


def test_material_library_cover_url_is_namespaced_by_library_key():
    url = _asset_public_url("/tmp/generated/1.png", "", "therapy_style")

    assert url == "/api/admin/stickman-workflow/assets/material-libraries/therapy_style/1.png"
