import os
import sys
import types

os.environ["DATABASE_URL"] = "sqlite:///:memory:"

dashscope_stub = types.ModuleType("dashscope")
dashscope_audio_stub = types.ModuleType("dashscope.audio")
dashscope_tts_stub = types.ModuleType("dashscope.audio.tts_v2")
dashscope_tts_stub.SpeechSynthesizer = type("SpeechSynthesizer", (), {})
sys.modules.setdefault("dashscope", dashscope_stub)
sys.modules.setdefault("dashscope.audio", dashscope_audio_stub)
sys.modules.setdefault("dashscope.audio.tts_v2", dashscope_tts_stub)
sys.modules.setdefault("edge_tts", types.ModuleType("edge_tts"))

from app.services.ai_video import AiVideoService


def test_user_script_build_scenes_preserves_every_sentence(monkeypatch):
    service = AiVideoService.__new__(AiVideoService)
    service._sc1_material_cache = (None, [])
    monkeypatch.setattr(service, "_media_for_scene", lambda *_args, **_kwargs: {})
    monkeypatch.setattr(service, "_sc1_material_images_for_scene", lambda *_args, **_kwargs: [])
    script = "第一句。第二句。第三句。第四句。第五句。第六句。第七句。第八句。第九句。第十句。"

    scenes = service._build_scenes(
        script,
        {"sceneCount": 3, "scriptSource": "user", "imageMode": "material_only"},
        "knowledge_ip_stickman",
        "sc1_stickman",
        "medium",
        script_source="user",
    )

    joined = "".join(scene["voiceText"] for scene in scenes)
    for sentence in ["第一句", "第二句", "第三句", "第四句", "第五句", "第六句", "第七句", "第八句", "第九句", "第十句"]:
        assert sentence in joined
    assert len(scenes) == 4
    assert all(scene["voiceText"].count("。") <= 3 for scene in scenes)
