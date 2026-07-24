import os
import sys
import types

os.environ["DATABASE_URL"] = "sqlite:///:memory:"

dashscope_stub = types.ModuleType("dashscope")
dashscope_audio_stub = types.ModuleType("dashscope.audio")
dashscope_tts_stub = types.ModuleType("dashscope.audio.tts_v2")


class _SpeechSynthesizer:
    pass


dashscope_tts_stub.SpeechSynthesizer = _SpeechSynthesizer
sys.modules.setdefault("dashscope", dashscope_stub)
sys.modules.setdefault("dashscope.audio", dashscope_audio_stub)
sys.modules.setdefault("dashscope.audio.tts_v2", dashscope_tts_stub)
sys.modules.setdefault("edge_tts", types.ModuleType("edge_tts"))

from app.services import ai_video


def test_prepare_sc1_materials_uses_render_service_public_url(tmp_path, monkeypatch):
    source_dir = tmp_path / "source"
    source_dir.mkdir()
    (source_dir / "sample.png").write_bytes(b"fake image bytes")

    render_material_root = tmp_path / "render-public" / "sc1-materials"
    monkeypatch.setattr(ai_video, "SC1_MATERIAL_LIBRARY_PATH", source_dir)
    monkeypatch.setattr(ai_video, "SC1_MATERIAL_PUBLIC_BASE_URL", "http://127.0.0.1:18788/sc1-materials")

    service = ai_video.AiVideoService.__new__(ai_video.AiVideoService)
    service.render_material_root = render_material_root
    scenes = [{"assetImages": [{"fileName": "sample.png", "src": "/sc1-materials/sample.png"}]}]

    service._prepare_sc1_materials_for_render(scenes, "job_1")

    assert (render_material_root / "sample.png").exists()
    assert scenes[0]["assetImages"][0]["src"] == "http://127.0.0.1:18788/sc1-materials/sample.png"
