from app.services.stickman_workflow_assets import normalize_material_library_items


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
