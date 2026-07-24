import os
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
