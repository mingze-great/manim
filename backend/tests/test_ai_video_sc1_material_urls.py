import os
import json
import subprocess
import sys
import types
import wave

import pytest

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

    assert (render_material_root / "job_1" / "sample.png").exists()
    assert scenes[0]["assetImages"][0]["src"] == "http://127.0.0.1:18788/sc1-materials/job_1/sample.png"


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

    assert (render_material_root / "job_2" / "selected.png").exists()
    assert scenes[0]["assetImages"][0]["src"] == "http://127.0.0.1:18788/sc1-materials/job_2/selected.png"


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


def test_prepare_sc1_materials_rejects_missing_scene_image(tmp_path, monkeypatch):
    source_dir = tmp_path / "source"
    source_dir.mkdir()
    monkeypatch.setattr(ai_video, "SC1_MATERIAL_LIBRARY_PATH", source_dir)

    service = ai_video.AiVideoService.__new__(ai_video.AiVideoService)
    service.render_material_root = tmp_path / "render-public" / "sc1-materials"
    scenes = [{"assetImages": [{"fileName": "missing.png", "src": "/sc1-materials/missing.png"}]}]

    with pytest.raises(RuntimeError, match="missing.png"):
        service._prepare_sc1_materials_for_render(scenes, "job_missing")


def test_prepare_sc1_materials_namespaces_same_filename_per_job(tmp_path):
    first_root = tmp_path / "first"
    second_root = tmp_path / "second"
    first_root.mkdir()
    second_root.mkdir()
    (first_root / "1.png").write_bytes(b"first")
    (second_root / "1.png").write_bytes(b"second")

    service = ai_video.AiVideoService.__new__(ai_video.AiVideoService)
    service.render_material_root = tmp_path / "render-public" / "sc1-materials"
    first_scenes = [{"assetImages": [{"fileName": "1.png", "src": "/sc1-materials/1.png"}]}]
    second_scenes = [{"assetImages": [{"fileName": "1.png", "src": "/sc1-materials/1.png"}]}]

    first_stage = service._prepare_sc1_materials_for_render(
        first_scenes,
        "job_1",
        {"materialLibraryPath": str(first_root)},
    )
    second_stage = service._prepare_sc1_materials_for_render(
        second_scenes,
        "job_2",
        {"materialLibraryPath": str(second_root)},
    )

    assert first_stage != second_stage
    assert first_scenes[0]["assetImages"][0]["src"].endswith("/job_1/1.png")
    assert second_scenes[0]["assetImages"][0]["src"].endswith("/job_2/1.png")
    assert (first_stage / "1.png").read_bytes() == b"first"
    assert (second_stage / "1.png").read_bytes() == b"second"


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


def test_ai_image_mode_prefers_local_backend_url_for_render(monkeypatch):
    service = ai_video.AiVideoService.__new__(ai_video.AiVideoService)
    service.backend_public_url = "http://127.0.0.1:8004"
    service._sc1_material_cache = (None, [])
    service._media_for_scene = lambda *_args, **_kwargs: []
    service._infer_scene_count = lambda *_args, **_kwargs: 1

    async def fake_generate_image(prompt):
        return (
            "/api/article-images/local.png",
            "https://example-cos.test/articles/images/public.png",
            "cos",
        )

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
    assert asset["src"] == "http://127.0.0.1:8004/api/article-images/local.png"


def test_ai_image_mode_fails_clearly_when_realtime_generation_fails(monkeypatch):
    service = ai_video.AiVideoService.__new__(ai_video.AiVideoService)
    service.backend_public_url = "http://127.0.0.1:8004"
    service._sc1_material_cache = (None, [])
    service._media_for_scene = lambda *_args, **_kwargs: []
    service._infer_scene_count = lambda *_args, **_kwargs: 1

    async def fake_generate_image(_prompt, reference_images=None):
        raise RuntimeError("apikey error")

    fake_service = types.SimpleNamespace(generate_image=fake_generate_image)
    monkeypatch.setattr(ai_video, "image_gen_service", fake_service, raising=False)

    with pytest.raises(RuntimeError, match="实时生图失败"):
        service._build_scenes(
            "你越想证明自己，越容易在关系里内耗。",
            {"prompt": "关系内耗", "imageMode": "ai_image", "useMaterialLibrary": False},
            "knowledge_ip_stickman",
            "sc1_stickman",
            "medium",
        )


def test_ai_image_mode_times_out_clearly_when_realtime_generation_hangs(monkeypatch):
    service = ai_video.AiVideoService.__new__(ai_video.AiVideoService)
    service.backend_public_url = "http://127.0.0.1:8004"
    service._sc1_material_cache = (None, [])
    service._media_for_scene = lambda *_args, **_kwargs: []
    service._infer_scene_count = lambda *_args, **_kwargs: 1
    monkeypatch.setenv("STICKMAN_IMAGE_TIMEOUT_SECONDS", "1")

    async def fake_generate_image(_prompt, reference_images=None):
        import asyncio

        await asyncio.sleep(2)
        return "/api/article-images/too-late.png", "/api/article-images/too-late.png", "local"

    fake_service = types.SimpleNamespace(generate_image=fake_generate_image)
    monkeypatch.setattr(ai_video, "image_gen_service", fake_service, raising=False)

    with pytest.raises(RuntimeError, match="图片生成超时"):
        service._build_scenes(
            "你越想证明自己，越容易在关系里内耗。",
            {"prompt": "关系内耗", "imageMode": "ai_image", "useMaterialLibrary": False},
            "knowledge_ip_stickman",
            "sc1_stickman",
            "medium",
        )


def test_hybrid_image_mode_can_fallback_when_realtime_generation_fails(tmp_path, monkeypatch):
    material_root = tmp_path / "materials"
    material_root.mkdir()
    (material_root / "1.png").write_bytes(b"fallback-material")

    service = ai_video.AiVideoService.__new__(ai_video.AiVideoService)
    service.backend_public_url = "http://127.0.0.1:8004"
    service.render_material_root = tmp_path / "render" / "sc1-materials"
    service._sc1_material_cache = (None, [])
    service._media_for_scene = lambda *_args, **_kwargs: []
    service._infer_scene_count = lambda *_args, **_kwargs: 1

    async def fake_generate_image(_prompt, reference_images=None):
        raise RuntimeError("apikey error")

    fake_service = types.SimpleNamespace(generate_image=fake_generate_image)
    monkeypatch.setattr(ai_video, "image_gen_service", fake_service, raising=False)

    scenes = service._build_scenes(
        "你越想证明自己，越容易在关系里内耗。",
        {
            "prompt": "关系内耗",
            "imageMode": "hybrid",
            "useMaterialLibrary": True,
            "materialLibraryPath": str(material_root),
        },
        "knowledge_ip_stickman",
        "sc1_stickman",
        "medium",
    )

    asset = scenes[0]["visual"]["assetImages"][0]
    assert asset.get("generated") is not True
    assert "/sc1-materials/" in asset["src"]


def test_ai_image_mode_generates_per_user_script_semantic_scene(monkeypatch):
    service = ai_video.AiVideoService.__new__(ai_video.AiVideoService)
    service.backend_public_url = "http://127.0.0.1:8004"
    service._sc1_material_cache = (None, [])
    service._media_for_scene = lambda *_args, **_kwargs: []

    calls = []

    async def fake_generate_image(prompt):
        calls.append(prompt)
        return f"/api/article-images/generated-{len(calls)}.png", f"/api/article-images/generated-{len(calls)}.png", "local"

    fake_service = types.SimpleNamespace(generate_image=fake_generate_image)
    monkeypatch.setattr(ai_video, "image_gen_service", fake_service, raising=False)

    script = "第一句。第二句。第三句。第四句。第五句。第六句。第七句。第八句。"
    scenes = service._build_scenes(
        script,
        {"prompt": "关系内耗", "imageMode": "ai_image", "useMaterialLibrary": False},
        "knowledge_ip_stickman",
        "sc1_stickman",
        "medium",
        script_source="user",
    )

    assert len(scenes) == 4
    assert len(calls) == 4
    assert len({scene["visual"]["assetImages"][0]["src"] for scene in scenes}) == 4


def test_ai_image_mode_expands_generated_target_duration_into_segment_images(monkeypatch):
    service = ai_video.AiVideoService.__new__(ai_video.AiVideoService)
    service.backend_public_url = "http://127.0.0.1:8004"
    service._sc1_material_cache = (None, [])
    service._media_for_scene = lambda *_args, **_kwargs: []

    calls = []

    async def fake_generate_image(prompt):
        calls.append(prompt)
        return f"/api/article-images/segment-{len(calls)}.png", f"/api/article-images/segment-{len(calls)}.png", "local"

    fake_service = types.SimpleNamespace(generate_image=fake_generate_image)
    monkeypatch.setattr(ai_video, "image_gen_service", fake_service, raising=False)

    scenes = service._build_scenes(
        "关系内耗",
        {"prompt": "关系内耗", "targetSeconds": 60, "imageMode": "ai_image", "useMaterialLibrary": False},
        "knowledge_ip_stickman",
        "sc1_stickman",
        "medium",
        script_source="generated",
    )

    assert len(scenes) >= 8
    assert len(calls) == len(scenes)
    assert len({scene["visual"]["assetImages"][0]["src"] for scene in scenes}) == len(scenes)
    assert all("当前语义分段" in prompt for prompt in calls)


def test_ai_image_mode_sends_material_reference_image_for_style(tmp_path, monkeypatch):
    material_root = tmp_path / "xiaonvsheng"
    material_root.mkdir()
    (material_root / "1.png").write_bytes(b"reference-image-bytes")
    manifest = material_root / "materials.json"
    manifest.write_text(json.dumps([{"fileName": "1.png"}], ensure_ascii=False), encoding="utf-8")

    service = ai_video.AiVideoService.__new__(ai_video.AiVideoService)
    service.backend_public_url = "http://127.0.0.1:8004"
    service._sc1_material_cache = (None, [])
    service._media_for_scene = lambda *_args, **_kwargs: []

    reference_payloads = []

    async def fake_generate_image(prompt, reference_images=None):
        reference_payloads.append(reference_images or [])
        return "/api/article-images/generated-style.png", "/api/article-images/generated-style.png", "local"

    fake_service = types.SimpleNamespace(generate_image=fake_generate_image)
    monkeypatch.setattr(ai_video, "image_gen_service", fake_service, raising=False)

    scenes = service._build_scenes(
        "你越想证明自己，越容易在关系里内耗。",
        {
            "prompt": "关系内耗",
            "materialLibrary": "小女生",
            "materialLibraryName": "小女生",
            "materialLibraryPath": str(material_root),
            "materialLibraryManifest": str(manifest),
            "imageMode": "ai_image",
            "useMaterialLibrary": False,
        },
        "knowledge_ip_stickman",
        "sc1_stickman",
        "medium",
        script_source="user",
    )

    assert scenes[0]["visual"]["assetImages"][0]["generated"] is True
    assert reference_payloads
    assert reference_payloads[0][0].startswith("data:image/png;base64,")


def test_sc1_generated_image_prompt_uses_material_library_style():
    service = ai_video.AiVideoService.__new__(ai_video.AiVideoService)

    prompt = service._sc1_generated_image_prompt({"prompt": "关系内耗"}, "你总是把沉默理解成否定", 1)

    assert "小女生、sucai2、大叔、outputs" in prompt
    assert "纯白或近白背景" in prompt
    assert "少量线条道具" in prompt
    assert "不要文字" in prompt


def test_user_script_split_preserves_all_sentences_when_scene_count_is_smaller():
    service = ai_video.AiVideoService.__new__(ai_video.AiVideoService)
    script = "第一句。第二句。第三句。第四句。第五句。第六句。"

    chunks = service._split_script(
        script,
        scene_count=3,
        content_type="knowledge_ip_stickman",
        allow_prompt_expansion=False,
    )

    joined = "".join(chunks)
    for sentence in ["第一句", "第二句", "第三句", "第四句", "第五句", "第六句"]:
        assert sentence in joined
    assert len(chunks) == 3
    assert all(chunk.count("。") <= 3 for chunk in chunks)


def test_dayun_manbo_tts_prefers_qwen_manbo_server_tts(tmp_path, monkeypatch):
    service = ai_video.AiVideoService.__new__(ai_video.AiVideoService)
    service.render_audio_root = tmp_path / "render-audio"
    service.render_service_url = "http://127.0.0.1:18787"
    service.cosyvoice_sample_rate = 22050
    service.qwen_manbo_voice = "qwen-manbo-voice"
    service._append_log = lambda *_args, **_kwargs: None
    service._resolve_cosyvoice_voice = lambda _voice: "中文女"
    service._resolve_edge_tts_voice = lambda _voice: "zh-CN-XiaoxiaoNeural"
    service._resolve_dashscope_voice = lambda _voice: "longanhuan"
    service.local_tts_allow_safe_fallback = False

    qwen_calls = []

    def qwen_tts(text, output_path):
        qwen_calls.append(text)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        with wave.open(str(output_path), "wb") as wav:
            wav.setnchannels(1)
            wav.setsampwidth(2)
            wav.setframerate(22050)
            wav.writeframes(b"\x01\x00" * 22050)
        return 1.0

    monkeypatch.setattr(service, "_generate_qwen_manbo_audio", qwen_tts)
    monkeypatch.setattr(
        service,
        "_generate_local_tts_worker_audio",
        lambda *_args, **_kwargs: (_ for _ in ()).throw(AssertionError("local worker should not run when Qwen works")),
    )

    project_json = {"scenes": [{"voiceText": "先别急着证明自己", "duration": 1.2}]}
    audio_scenes = service._generate_cosyvoice_audio(
        project_json,
        tmp_path / "job_42",
        None,
        {"voiceProvider": "dayun_manbo", "voiceId": "dayun_manbo"},
    )

    assert qwen_calls == ["先别急着证明自己"]
    assert audio_scenes[0]["provider"] == "qwen_manbo"
    assert project_json["voice"]["speaker"] == "qwen-manbo-voice"
    assert (tmp_path / "job_42" / "audio" / "scene-01.wav").exists()


def test_dayun_manbo_tts_falls_back_to_local_worker_when_qwen_unavailable(tmp_path, monkeypatch):
    service = ai_video.AiVideoService.__new__(ai_video.AiVideoService)
    service.render_audio_root = tmp_path / "render-audio"
    service.render_service_url = "http://127.0.0.1:18787"
    service.cosyvoice_sample_rate = 22050
    service._append_log = lambda *_args, **_kwargs: None
    service._resolve_cosyvoice_voice = lambda _voice: "中文女"
    service._resolve_edge_tts_voice = lambda _voice: "zh-CN-XiaoxiaoNeural"
    service._resolve_dashscope_voice = lambda _voice: "longanhuan"
    service.local_tts_allow_safe_fallback = False

    local_worker_calls = []

    monkeypatch.setattr(
        service,
        "_generate_qwen_manbo_audio",
        lambda *_args, **_kwargs: (_ for _ in ()).throw(RuntimeError("qwen unavailable")),
    )

    def local_worker(text, output_path, voice, **kwargs):
        local_worker_calls.append((text, voice, kwargs["scene_index"], kwargs.get("cue_index")))
        output_path.parent.mkdir(parents=True, exist_ok=True)
        with wave.open(str(output_path), "wb") as wav:
            wav.setnchannels(1)
            wav.setsampwidth(2)
            wav.setframerate(22050)
            wav.writeframes(b"\x01\x00" * 22050)
        return 1.0

    monkeypatch.setattr(service, "_generate_local_tts_worker_audio", local_worker)
    monkeypatch.setattr(
        service,
        "_generate_dayun_manbo_audio",
        lambda *_args, **_kwargs: (_ for _ in ()).throw(AssertionError("Dayun HTTP should not run for Manbo one-click jobs")),
    )
    monkeypatch.setattr(
        service,
        "_generate_dashscope_cosyvoice_audio",
        lambda *_args, **_kwargs: (_ for _ in ()).throw(AssertionError("DashScope should not run when local worker works")),
    )
    monkeypatch.setattr(
        service,
        "_generate_edge_tts_audio",
        lambda *_args, **_kwargs: (_ for _ in ()).throw(AssertionError("Edge TTS should not run when local worker works")),
    )
    monkeypatch.setattr(
        service,
        "_generate_open_source_cosyvoice_audio",
        lambda *_args, **_kwargs: (_ for _ in ()).throw(AssertionError("server local CosyVoice should not run")),
    )

    project_json = {"scenes": [{"voiceText": "先别急着证明自己", "duration": 1.2}]}
    audio_scenes = service._generate_cosyvoice_audio(
        project_json,
        tmp_path / "job_42",
        None,
        {"voiceProvider": "dayun_manbo", "voiceId": "dayun_manbo"},
    )

    assert local_worker_calls == [("先别急着证明自己", "dayun_manbo", 0, None)]
    assert audio_scenes[0]["provider"] == "local_tts_worker"
    assert audio_scenes[0]["src"] == "http://127.0.0.1:18787/generated-audio/job_42/scene-01.wav"
    assert (tmp_path / "job_42" / "audio" / "scene-01.wav").exists()


def test_dayun_manbo_tts_worker_failure_does_not_start_server_cosyvoice(tmp_path, monkeypatch):
    service = ai_video.AiVideoService.__new__(ai_video.AiVideoService)
    service.render_audio_root = tmp_path / "render-audio"
    service.render_service_url = "http://127.0.0.1:18787"
    service.cosyvoice_sample_rate = 22050
    service._append_log = lambda *_args, **_kwargs: None
    service._resolve_cosyvoice_voice = lambda _voice: "中文女"
    service._resolve_edge_tts_voice = lambda _voice: "zh-CN-XiaoxiaoNeural"
    service._resolve_dashscope_voice = lambda _voice: "longanhuan"
    service.local_tts_allow_safe_fallback = False

    monkeypatch.setattr(
        service,
        "_generate_qwen_manbo_audio",
        lambda *_args, **_kwargs: (_ for _ in ()).throw(RuntimeError("qwen unavailable")),
    )
    monkeypatch.setattr(
        service,
        "_generate_local_tts_worker_audio",
        lambda *_args, **_kwargs: (_ for _ in ()).throw(RuntimeError("worker offline")),
    )
    monkeypatch.setattr(
        service,
        "_generate_open_source_cosyvoice_audio",
        lambda *_args, **_kwargs: (_ for _ in ()).throw(AssertionError("server local CosyVoice should not run")),
    )

    with pytest.raises(RuntimeError, match="worker offline"):
        service._generate_cosyvoice_audio(
            {"scenes": [{"voiceText": "先别急着证明自己", "duration": 1.2}]},
            tmp_path / "job_42",
            None,
            {"voiceProvider": "dayun_manbo", "voiceId": "dayun_manbo"},
        )


def test_safe_tts_fallback_uses_local_cosyvoice_only_after_edge_tts_failure(tmp_path, monkeypatch):
    service = ai_video.AiVideoService.__new__(ai_video.AiVideoService)
    service._resolve_edge_tts_voice = lambda _voice: "zh-CN-XiaoxiaoNeural"
    service._resolve_cosyvoice_voice = lambda _voice: "中文女"
    service._resolve_dashscope_voice = lambda _voice: "longanhuan"
    service.allow_server_local_cosyvoice = True

    calls = []
    monkeypatch.setattr(service, "_generate_dashscope_cosyvoice_audio", lambda *_args, **_kwargs: (_ for _ in ()).throw(RuntimeError("dashscope unavailable")))
    monkeypatch.setattr(service, "_generate_edge_tts_audio", lambda *_args, **_kwargs: (_ for _ in ()).throw(RuntimeError("edge unavailable")))
    monkeypatch.setattr(service, "_generate_external_simple_tts_audio", lambda *_args, **_kwargs: (_ for _ in ()).throw(RuntimeError("external unavailable")))

    def fallback_open_source(text, voice, output_path):
        calls.append((text, voice))
        output_path.write_bytes(b"fake")
        return 1.5

    monkeypatch.setattr(service, "_generate_open_source_cosyvoice_audio", fallback_open_source)

    seconds, provider, voice = service._generate_safe_tts_fallback_audio("先别急着证明自己", tmp_path / "scene.wav", "中文女")

    assert seconds == 1.5
    assert provider == "open_source_cosyvoice"
    assert voice == "中文女"
    assert calls == [("先别急着证明自己", "中文女")]


def test_safe_tts_fallback_uses_external_tts_before_local_cosyvoice(tmp_path, monkeypatch):
    service = ai_video.AiVideoService.__new__(ai_video.AiVideoService)
    service._resolve_edge_tts_voice = lambda _voice: "zh-CN-XiaoxiaoNeural"
    service._resolve_cosyvoice_voice = lambda _voice: "中文女"
    service._resolve_dashscope_voice = lambda _voice: "longanhuan"
    service.allow_server_local_cosyvoice = False

    calls = []
    monkeypatch.setattr(service, "_generate_dashscope_cosyvoice_audio", lambda *_args, **_kwargs: (_ for _ in ()).throw(RuntimeError("dashscope unavailable")))
    monkeypatch.setattr(service, "_generate_edge_tts_audio", lambda *_args, **_kwargs: (_ for _ in ()).throw(RuntimeError("edge unavailable")))

    def fallback_external(text, output_path):
        calls.append(text)
        output_path.write_bytes(b"fake")
        return 1.25

    monkeypatch.setattr(service, "_generate_external_simple_tts_audio", fallback_external)
    monkeypatch.setattr(
        service,
        "_generate_open_source_cosyvoice_audio",
        lambda *_args, **_kwargs: (_ for _ in ()).throw(AssertionError("local CosyVoice should not run when Google TTS works")),
    )

    seconds, provider, voice = service._generate_safe_tts_fallback_audio("先别急着证明自己", tmp_path / "scene.wav", "中文女")

    assert seconds == 1.25
    assert provider == "external_simple_tts"
    assert voice == "zh-CN"
    assert calls == ["先别急着证明自己"]


def test_safe_tts_fallback_does_not_call_server_local_cosyvoice_by_default(tmp_path, monkeypatch):
    service = ai_video.AiVideoService.__new__(ai_video.AiVideoService)
    service._resolve_edge_tts_voice = lambda _voice: "zh-CN-XiaoxiaoNeural"
    service._resolve_cosyvoice_voice = lambda _voice: "中文女"
    service._resolve_dashscope_voice = lambda _voice: "longanhuan"
    service.allow_server_local_cosyvoice = False

    monkeypatch.setattr(service, "_generate_dashscope_cosyvoice_audio", lambda *_args, **_kwargs: (_ for _ in ()).throw(RuntimeError("dashscope unavailable")))
    monkeypatch.setattr(service, "_generate_edge_tts_audio", lambda *_args, **_kwargs: (_ for _ in ()).throw(RuntimeError("edge unavailable")))
    monkeypatch.setattr(service, "_generate_external_simple_tts_audio", lambda *_args, **_kwargs: (_ for _ in ()).throw(RuntimeError("external unavailable")))
    monkeypatch.setattr(
        service,
        "_generate_open_source_cosyvoice_audio",
        lambda *_args, **_kwargs: (_ for _ in ()).throw(AssertionError("server local CosyVoice should not run by default")),
    )

    with pytest.raises(RuntimeError, match="server local CosyVoice is disabled"):
        service._generate_safe_tts_fallback_audio("先别急着证明自己", tmp_path / "scene.wav", "中文女")


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
    monkeypatch.setattr(ai_video.requests, "get", lambda *_args, **_kwargs: types.SimpleNamespace(status_code=200))
    monkeypatch.setattr(ai_video.urllib.request, "urlopen", lambda *_args, **_kwargs: (_ for _ in ()).throw(RuntimeError("sft unavailable")))
    monkeypatch.setattr(service, "_prepare_cosyvoice_prompt_audio", lambda path: path)
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


def test_open_source_cosyvoice_rejects_implausibly_short_partial_pcm(tmp_path, monkeypatch):
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
    monkeypatch.setattr(ai_video.requests, "get", lambda *_args, **_kwargs: types.SimpleNamespace(status_code=200))
    monkeypatch.setattr(ai_video.urllib.request, "urlopen", lambda *_args, **_kwargs: (_ for _ in ()).throw(RuntimeError("sft unavailable")))
    monkeypatch.setattr(service, "_prepare_cosyvoice_prompt_audio", lambda path: path)

    def fake_run(command, **_kwargs):
        output_path = command[command.index("-o") + 1]
        with open(output_path, "wb") as file:
            file.write((1000).to_bytes(2, "little", signed=True) * 2000)
        return subprocess.CompletedProcess(command, 28, stdout="", stderr="Operation timed out")

    monkeypatch.setattr(ai_video.subprocess, "run", fake_run)

    with pytest.raises(RuntimeError, match="CosyVoice"):
        service._generate_open_source_cosyvoice_audio("来挑战一下你的脑洞", "中文女", tmp_path / "scene.wav")


def test_open_source_cosyvoice_health_failure_prevents_local_tts_call(tmp_path, monkeypatch):
    service = ai_video.AiVideoService.__new__(ai_video.AiVideoService)
    service.cosyvoice_url = "http://127.0.0.1:50000"
    service.cosyvoice_timeout = 180
    service.cosyvoice_sample_rate = 22050

    monkeypatch.setattr(ai_video.requests, "get", lambda *_args, **_kwargs: (_ for _ in ()).throw(RuntimeError("connection refused")))
    monkeypatch.setattr(ai_video.urllib.request, "urlopen", lambda *_args, **_kwargs: (_ for _ in ()).throw(AssertionError("SFT request should not run")))
    monkeypatch.setattr(ai_video.subprocess, "run", lambda *_args, **_kwargs: (_ for _ in ()).throw(AssertionError("zero-shot curl should not run")))

    with pytest.raises(RuntimeError, match="not healthy"):
        service._generate_open_source_cosyvoice_audio("先别急着证明自己", "中文女", tmp_path / "scene.wav")


def test_sc1_material_paths_falls_back_when_configured_manifest_is_missing(tmp_path):
    service = ai_video.AiVideoService.__new__(ai_video.AiVideoService)
    root = tmp_path / "materials"
    root.mkdir()
    generated_manifest = root / "materials.generated.json"
    generated_manifest.write_text("[]", encoding="utf-8")

    material_root, manifest_path = service._sc1_material_paths(
        {
            "materialLibraryPath": str(root),
            "materialLibraryManifest": str(root / "material.json"),
        }
    )

    assert material_root == root.resolve()
    assert manifest_path == generated_manifest.resolve()


def test_build_srt_contains_every_caption_cue_with_absolute_timing():
    service = ai_video.AiVideoService.__new__(ai_video.AiVideoService)
    scenes = [
        {
            "duration": 2.0,
            "subtitleText": "不应只显示这一句",
            "segments": [{"captionCues": [
                {"text": "第一句", "startFrame": 0, "endFrame": 30},
                {"text": "第二句", "startFrame": 30, "endFrame": 60},
            ]}],
        },
        {
            "duration": 1.0,
            "segments": [{"captionCues": [
                {"text": "第三句", "startFrame": 0, "endFrame": 30},
            ]}],
        },
    ]

    srt = service._build_srt(scenes)

    assert "第一句" in srt
    assert "第二句" in srt
    assert "第三句" in srt
    assert "00:00:01,000 --> 00:00:02,000" in srt
    assert "00:00:02,000 --> 00:00:03,000" in srt
    assert srt.count("-->") == 3


def test_sc1_summary_labels_are_unique_across_the_video(monkeypatch):
    service = ai_video.AiVideoService.__new__(ai_video.AiVideoService)
    service._sc1_material_cache = (None, [])
    service._infer_scene_count = lambda *_args, **_kwargs: 2
    monkeypatch.setattr(service, "_media_for_scene", lambda *_args, **_kwargs: {})

    scenes = service._build_scenes(
        "别急着下结论，先看清关系。别急着下结论，先看清关系。",
        {"sceneCount": 2, "scriptSource": "user", "imageMode": "material_only"},
        "knowledge_ip_stickman",
        "sc1_stickman",
        "medium",
        script_source="user",
    )
    labels = [
        cue["summaryLabel"]
        for scene in scenes
        for segment in scene["segments"]
        for cue in segment["captionCues"]
    ]

    assert labels
    assert len(labels) == len(set(labels))
    assert all(2 <= len(label) <= 4 for label in labels)


def test_sc1_summary_labels_remain_unique_for_twenty_four_repeated_cues():
    service = ai_video.AiVideoService.__new__(ai_video.AiVideoService)
    used = set()

    for index in range(24):
        label = service._sc1_make_unique_label("反复内耗", index, used)
        assert label not in used
        assert 2 <= len(label) <= 4
        used.add(label)

    assert len(used) == 24


def test_sc1_summary_label_does_not_fall_back_to_arbitrary_script_slice():
    service = ai_video.AiVideoService.__new__(ai_video.AiVideoService)
    used = {"被戳中", "别慌", "看清", "松绑", "稳住", "破防", "醒醒", "自救", "释怀"}

    label = service._sc1_make_unique_label("你不需要为所有人的情绪负责", 0, used)

    assert label not in {"你不需要", "不需要为", "需要为所", "要为所有", "为所有人", "所有人的"}
    assert label in {"情绪", "责任", "负责", "觉察", "转念", "清醒", "破局", "重启", "自省", "看见"} or len(label) == 4


def test_sc1_summary_label_prefers_keywords_from_current_caption():
    service = ai_video.AiVideoService.__new__(ai_video.AiVideoService)
    used = {"看清", "稳住", "松绑", "警报", "边界", "内耗"}

    label = service._sc1_make_unique_label("把对象和后果分开看", 4, used)

    assert label in {"对象", "后果", "分开", "分开看"}


def test_sc1_summary_label_uses_strong_keyword_from_current_caption():
    service = ai_video.AiVideoService.__new__(ai_video.AiVideoService)

    label = service._sc1_make_unique_label(
        "别总是在别人的情绪里寻找自己的价值，爱你的人不会让你长期患得患失，而真正爱自己的人，也不会为了留住一个人，慢慢丢掉自己",
        0,
        set(),
    )

    assert label in {"价值", "爱己", "患失", "留住", "丢掉"}
    assert label != "情绪"


def test_sc1_caption_cues_split_long_caption_into_short_lines():
    service = ai_video.AiVideoService.__new__(ai_video.AiVideoService)

    cues = service._split_sc1_caption_cues(
        "别总是在别人的情绪里寻找自己的价值，爱你的人不会让你长期患得患失，而真正爱自己的人，也不会为了留住一个人，慢慢丢掉自己"
    )

    assert len(cues) == 3
    assert all(len(cue) <= 18 for cue in cues)
    assert cues[0] == "别总是在别人的情绪里寻找自己的价值"


def test_sc1_caption_cues_drop_sentence_number_prefixes():
    service = ai_video.AiVideoService.__new__(ai_video.AiVideoService)

    cues = service._split_sc1_caption_cues("第二句，不要把别人的情绪都揽到自己身上。")

    assert cues == ["不要把别人的情绪都揽到自己身上"]


def test_sc1_video_emits_english_subtitles_for_each_caption_cue(monkeypatch):
    service = ai_video.AiVideoService.__new__(ai_video.AiVideoService)
    service._sc1_material_cache = (None, [])
    service._infer_scene_count = lambda *_args, **_kwargs: 1
    monkeypatch.setattr(service, "_media_for_scene", lambda *_args, **_kwargs: {})
    monkeypatch.setattr(service, "_sc1_material_images_for_scene", lambda *_args, **_kwargs: [])

    scenes = service._build_scenes(
        "Keep the Chinese captions only.",
        {"sceneCount": 1, "scriptSource": "user", "imageMode": "material_only"},
        "knowledge_ip_stickman",
        "sc1_stickman",
        "medium",
        script_source="user",
    )

    assert scenes[0]["englishText"]
    for segment in scenes[0]["segments"]:
        assert segment["englishText"]
        assert all(cue["englishText"] for cue in segment["captionCues"])
