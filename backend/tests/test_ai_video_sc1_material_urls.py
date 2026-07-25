import os
import json
import subprocess
import sys
import types
import wave

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


def test_sc1_material_selection_uses_job_material_manifest(tmp_path, monkeypatch):
    selected_root = tmp_path / "selected-library"
    selected_root.mkdir()
    manifest = selected_root / "materials.json"
    manifest.write_text(
        json.dumps(
            [
                {
                    "file_name": "selected.png",
                    "primary_subject": "关系证明",
                    "emotion_primary": "内耗",
                    "storyboard_roles": ["hook", "problem"],
                    "search_keywords": ["证明", "关系", "内耗"],
                }
            ],
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )
    (selected_root / "selected.png").write_bytes(b"selected image bytes")

    fallback_root = tmp_path / "fallback-library"
    fallback_root.mkdir()
    (fallback_root / "materials.json").write_text("[]", encoding="utf-8")
    monkeypatch.setattr(ai_video, "SC1_MATERIAL_LIBRARY_PATH", fallback_root)

    service = ai_video.AiVideoService.__new__(ai_video.AiVideoService)
    service._sc1_material_cache = (None, [])

    images = service._sc1_material_images_for_scene(
        {
            "prompt": "为什么你越想证明自己越容易内耗",
            "materialLibraryPath": str(selected_root),
            "materialLibraryManifest": str(manifest),
        },
        "你越想证明自己，越容易在关系里内耗",
        0,
    )

    assert images[0]["fileName"] == "selected.png"


def test_prepare_sc1_materials_uses_job_material_root(tmp_path, monkeypatch):
    selected_root = tmp_path / "selected-library"
    selected_root.mkdir()
    (selected_root / "selected.png").write_bytes(b"selected image bytes")

    fallback_root = tmp_path / "fallback-library"
    fallback_root.mkdir()
    monkeypatch.setattr(ai_video, "SC1_MATERIAL_LIBRARY_PATH", fallback_root)
    monkeypatch.setattr(ai_video, "SC1_MATERIAL_PUBLIC_BASE_URL", "http://127.0.0.1:18788/sc1-materials")

    render_material_root = tmp_path / "render-public" / "sc1-materials"
    service = ai_video.AiVideoService.__new__(ai_video.AiVideoService)
    service.render_material_root = render_material_root
    scenes = [{"assetImages": [{"fileName": "selected.png"}]}]

    service._prepare_sc1_materials_for_render(
        scenes,
        "job_2",
        {"materialLibraryPath": str(selected_root)},
    )

    assert (render_material_root / "selected.png").exists()
    assert scenes[0]["assetImages"][0]["src"] == "http://127.0.0.1:18788/sc1-materials/selected.png"


def test_prepare_sc1_materials_keeps_generated_http_images(tmp_path, monkeypatch):
    fallback_root = tmp_path / "fallback-library"
    fallback_root.mkdir()
    monkeypatch.setattr(ai_video, "SC1_MATERIAL_LIBRARY_PATH", fallback_root)

    render_material_root = tmp_path / "render-public" / "sc1-materials"
    service = ai_video.AiVideoService.__new__(ai_video.AiVideoService)
    service.render_material_root = render_material_root
    scenes = [{"assetImages": [{"src": "http://127.0.0.1:8004/api/article-images/generated.png", "generated": True}]}]

    service._prepare_sc1_materials_for_render(scenes, "job_3", {})

    assert scenes[0]["assetImages"][0]["src"] == "http://127.0.0.1:8004/api/article-images/generated.png"


def test_ai_image_mode_generates_scene_asset(monkeypatch):
    service = ai_video.AiVideoService.__new__(ai_video.AiVideoService)
    service.backend_public_url = "http://127.0.0.1:8004"
    service._sc1_material_cache = (None, [])
    service._media_for_scene = lambda *_args, **_kwargs: []
    service._infer_scene_count = lambda *_args, **_kwargs: 1

    calls = []

    async def fake_generate_image(prompt):
        calls.append(prompt)
        return "/api/article-images/generated.png", "/api/article-images/generated.png", "local"

    fake_service = types.SimpleNamespace(generate_image=fake_generate_image)
    monkeypatch.setattr(ai_video, "image_gen_service", fake_service, raising=False)

    scenes = service._build_scenes(
        "你越想证明自己，越容易在关系里内耗。",
        {"prompt": "关系内耗", "imageMode": "ai_image", "useMaterialLibrary": False},
        "knowledge_ip_stickman",
        "sc1_stickman",
        "medium",
    )

    asset = scenes[0]["visual"]["assetImages"][0]
    assert calls
    assert "SC1心理学火柴人" in calls[0]
    assert asset["generated"] is True
    assert asset["src"] == "http://127.0.0.1:8004/api/article-images/generated.png"
    assert asset["slot"] == "center"


def test_dayun_manbo_tts_rate_limit_falls_back_to_open_source_cosyvoice(tmp_path, monkeypatch):
    service = ai_video.AiVideoService.__new__(ai_video.AiVideoService)
    service.render_audio_root = tmp_path / "render-audio"
    service.render_service_url = "http://127.0.0.1:18787"
    service.cosyvoice_sample_rate = 22050
    service._append_log = lambda *_args, **_kwargs: None
    service._resolve_cosyvoice_voice = lambda _voice: "中文女"

    def fail_dayun(_text, _output_path):
        raise RuntimeError("Dayun Manbo TTS request failed: HTTP Error 429: Too Many Requests")

    fallback_calls = []

    def fallback_open_source(text, _voice, output_path):
        fallback_calls.append((text, _voice))
        output_path.parent.mkdir(parents=True, exist_ok=True)
        with wave.open(str(output_path), "wb") as wav:
            wav.setnchannels(1)
            wav.setsampwidth(2)
            wav.setframerate(22050)
            wav.writeframes(b"\x01\x00" * 22050)
        return 1.0

    monkeypatch.setattr(service, "_generate_dayun_manbo_audio", fail_dayun)
    monkeypatch.setattr(service, "_generate_open_source_cosyvoice_audio", fallback_open_source)

    project_json = {"scenes": [{"voiceText": "先别急着证明自己", "duration": 1.2}]}
    audio_scenes = service._generate_cosyvoice_audio(
        project_json,
        tmp_path / "job_42",
        None,
        {"voiceProvider": "dayun_manbo", "voiceId": "dayun_manbo"},
    )

    assert fallback_calls == [("先别急着证明自己", "中文女")]
    assert audio_scenes[0]["provider"] == "open_source_cosyvoice"
    assert audio_scenes[0]["src"] == "http://127.0.0.1:18787/generated-audio/job_42/scene-01.wav"
    assert (tmp_path / "job_42" / "audio" / "scene-01.wav").exists()


def test_open_source_cosyvoice_accepts_valid_pcm_when_stream_times_out(tmp_path, monkeypatch):
    service = ai_video.AiVideoService.__new__(ai_video.AiVideoService)
    service.cosyvoice_url = "http://127.0.0.1:50000"
    service.cosyvoice_timeout = 180
    service.cosyvoice_sample_rate = 22050

    prompt = tmp_path / "prompt.wav"
    with wave.open(str(prompt), "wb") as wav:
        wav.setnchannels(1)
        wav.setsampwidth(2)
        wav.setframerate(22050)
        wav.writeframes(b"\x01\x00" * 22050)
    monkeypatch.setenv("SC1_COSYVOICE_PROMPT_WAV", str(prompt))
    monkeypatch.setattr(ai_video.urllib.request, "urlopen", lambda *_args, **_kwargs: (_ for _ in ()).throw(RuntimeError("sft unavailable")))
    monkeypatch.setattr(ai_video.requests, "post", lambda *_args, **_kwargs: (_ for _ in ()).throw(AssertionError("requests fallback should not be used")))

    calls = []

    def fake_run(command, **_kwargs):
        calls.append(command)
        output_path = command[command.index("-o") + 1]
        with open(output_path, "wb") as file:
            file.write((1000).to_bytes(2, "little", signed=True) * 22050)
        return subprocess.CompletedProcess(command, 28, stdout="", stderr="Operation timed out")

    monkeypatch.setattr(ai_video.subprocess, "run", fake_run)

    output_path = tmp_path / "scene.wav"
    seconds = service._generate_open_source_cosyvoice_audio("先别急着证明自己", "中文女", output_path)

    assert round(seconds, 2) == 1.0
    assert output_path.exists()
    assert calls
    assert "--max-time" in calls[0]
    assert "75" in calls[0]
