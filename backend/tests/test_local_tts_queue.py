import sys
import types
import wave

from fastapi import FastAPI
from fastapi.testclient import TestClient


dashscope_stub = types.ModuleType("dashscope")
dashscope_tts_stub = types.ModuleType("dashscope.audio.tts_v2")
dashscope_tts_stub.SpeechSynthesizer = type("SpeechSynthesizer", (), {})
sys.modules.setdefault("dashscope", dashscope_stub)
sys.modules.setdefault("dashscope.audio", types.ModuleType("dashscope.audio"))
sys.modules.setdefault("dashscope.audio.tts_v2", dashscope_tts_stub)
sys.modules.setdefault("edge_tts", types.ModuleType("edge_tts"))

from app.api import local_tts
from app.services.local_tts_queue import LocalTTSQueue


def _wav_bytes() -> bytes:
    import io

    buffer = io.BytesIO()
    with wave.open(buffer, "wb") as wav:
        wav.setnchannels(1)
        wav.setsampwidth(2)
        wav.setframerate(22050)
        wav.writeframes(b"\x01\x00" * 22050)
    return buffer.getvalue()


def test_local_tts_worker_claims_and_completes_audio(tmp_path, monkeypatch):
    monkeypatch.setenv("LOCAL_TTS_WORKER_TOKEN", "test-token")
    monkeypatch.setenv("LOCAL_TTS_QUEUE_ROOT", str(tmp_path / "queue"))

    queue = LocalTTSQueue(tmp_path / "queue", token="test-token")
    request = queue.create_request(text="先别急着证明自己", voice="dayun_manbo", job_id="42", scene_index=0)

    app = FastAPI()
    app.include_router(local_tts.router, prefix="/api")
    client = TestClient(app)

    claimed = client.post("/api/local-tts/claim", headers={"Authorization": "Bearer test-token"})
    assert claimed.status_code == 200
    assert claimed.json()["request"]["requestId"] == request["requestId"]

    completed = client.post(
        f"/api/local-tts/{request['requestId']}/complete",
        headers={"Authorization": "Bearer test-token"},
        files={"file": ("scene.wav", _wav_bytes(), "audio/wav")},
    )
    assert completed.status_code == 200
    assert completed.json()["status"] == "completed"
    assert queue.wait_for_audio(request["requestId"], 2).exists()


def test_local_tts_worker_rejects_bad_token(tmp_path, monkeypatch):
    monkeypatch.setenv("LOCAL_TTS_WORKER_TOKEN", "test-token")
    monkeypatch.setenv("LOCAL_TTS_QUEUE_ROOT", str(tmp_path / "queue"))

    app = FastAPI()
    app.include_router(local_tts.router, prefix="/api")
    client = TestClient(app)

    response = client.post("/api/local-tts/claim", headers={"Authorization": "Bearer wrong-token"})
    assert response.status_code == 401


def test_local_tts_worker_does_not_reclaim_active_lease(tmp_path, monkeypatch):
    monkeypatch.setenv("LOCAL_TTS_WORKER_TOKEN", "test-token")
    monkeypatch.setenv("LOCAL_TTS_QUEUE_ROOT", str(tmp_path / "queue"))

    queue = LocalTTSQueue(tmp_path / "queue", token="test-token")
    request = queue.create_request(text="先别急着证明自己", voice="dayun_manbo", job_id="42", scene_index=0)

    first = queue.claim_next()
    second = queue.claim_next()

    assert first and first["requestId"] == request["requestId"]
    assert second is None


def test_local_tts_worker_fail_does_not_overwrite_completed_audio(tmp_path, monkeypatch):
    monkeypatch.setenv("LOCAL_TTS_WORKER_TOKEN", "test-token")
    monkeypatch.setenv("LOCAL_TTS_QUEUE_ROOT", str(tmp_path / "queue"))

    queue = LocalTTSQueue(tmp_path / "queue", token="test-token")
    request = queue.create_request(text="先别急着证明自己", voice="dayun_manbo", job_id="42", scene_index=0)
    queue.request_dir(request["requestId"]).mkdir(parents=True, exist_ok=True)
    completed_path = queue.request_dir(request["requestId"]) / "completed.wav"
    completed_path.write_bytes(_wav_bytes())
    payload = queue._read_payload(request["requestId"]) or {}
    payload["status"] = "completed"
    queue._write_payload(request["requestId"], payload)

    result = queue.fail_request(request["requestId"], "late failure")
    stored = queue._read_payload(request["requestId"])

    assert result["status"] == "completed"
    assert stored["status"] == "completed"
