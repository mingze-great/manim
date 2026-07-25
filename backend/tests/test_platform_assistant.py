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

from fastapi import FastAPI
from fastapi.testclient import TestClient


def test_assistant_retrieval_hits_stickman_and_invite_topics():
    from app.services.platform_assistant import PlatformAssistantKnowledgeBase

    kb = PlatformAssistantKnowledgeBase(
        entries=[
            {
                "title": "火柴人工作流",
                "source": "specs/sc1-stickman-workflow-spec.md",
                "content": "用户进入 /stickman-workflow 输入标题，选择素材库、声音和时长，生成心理学火柴人成片。",
                "route": "/stickman-workflow",
            },
            {
                "title": "邀请码兑换",
                "source": "rules/payment.md",
                "content": "用户在个人中心输入邀请码或兑换码即可开通套餐。",
                "route": "/profile",
            },
        ]
    )

    hits = kb.search("我怎么生成心理学火柴人视频，并且用邀请码开通", page_path="/stickman-workflow")

    assert [hit["title"] for hit in hits[:2]] == ["火柴人工作流", "邀请码兑换"]
    assert hits[0]["route"] == "/stickman-workflow"


def test_assistant_prompt_sanitizes_sensitive_paths_and_secrets():
    from app.services.platform_assistant import PlatformAssistantService

    service = PlatformAssistantService(
        knowledge_base=types.SimpleNamespace(
            search=lambda *_args, **_kwargs: [
                {
                    "title": "部署状态",
                    "source": "PROJECT_STATE.md",
                    "content": "SSH root@152.136.218.74 部署在 /opt/manim-v2-3004-snapshot，API key sk-secret。",
                    "route": "",
                }
            ]
        )
    )

    prompt = service.build_messages("服务器怎么部署", page_path="/admin")[1]["content"]

    assert "root@" not in prompt
    assert "/opt/" not in prompt
    assert "sk-secret" not in prompt
    assert "敏感信息已隐藏" in prompt


def test_platform_assistant_api_requires_login_and_returns_answer(monkeypatch):
    from app.api import platform_assistant
    from app.api.auth import get_current_user

    app = FastAPI()
    app.include_router(platform_assistant.router, prefix="/api")
    client = TestClient(app)

    unauthenticated = client.post("/api/platform-assistant/chat", json={"message": "怎么生成火柴人视频"})
    assert unauthenticated.status_code == 401

    class _User:
        username = "demo"
        is_admin = False
        role = "user"

    async def fake_current_user():
        return _User()

    class _Assistant:
        async def answer(self, message, page_path="", module=""):
            return {
                "answer": f"去火柴人工作流：{message}",
                "suggestedActions": [{"label": "去火柴人工作流", "route": "/stickman-workflow"}],
                "sources": [{"title": "火柴人工作流", "source": "specs/sc1-stickman-workflow-spec.md"}],
            }

    monkeypatch.setattr(platform_assistant, "assistant_service", _Assistant())
    app.dependency_overrides[get_current_user] = fake_current_user

    response = client.post("/api/platform-assistant/chat", json={"message": "怎么生成火柴人视频", "pagePath": "/stickman-workflow"})

    assert response.status_code == 200
    data = response.json()
    assert "火柴人工作流" in data["answer"]
    assert data["suggestedActions"][0]["route"] == "/stickman-workflow"
