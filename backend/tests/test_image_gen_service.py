import os
import sys
import types
import asyncio

os.environ["DATABASE_URL"] = "sqlite:///:memory:"


class _CosStorage:
    enabled = False


cos_module = types.ModuleType("app.utils.cos_storage")
cos_module.cos_storage = _CosStorage()
sys.modules.setdefault("app.utils.cos_storage", cos_module)

from app.services.image_gen import ImageGenService


class _FakeResponse:
    def __init__(self, payload=None, content=b"image-bytes"):
        self._payload = payload or {}
        self.content = content

    def raise_for_status(self):
        return None

    def json(self):
        return self._payload


class _FakeClient:
    requests = []

    def __init__(self, *args, **kwargs):
        pass

    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc, tb):
        return False

    async def post(self, url, headers=None, json=None):
        self.requests.append({"url": url, "headers": headers, "json": json})
        return _FakeResponse({"data": [{"url": "https://example.test/generated.png"}]})

    async def get(self, url):
        self.requests.append({"get": url})
        return _FakeResponse(content=b"downloaded-image")


def test_generate_image_uses_gpt_image_generate_payload(monkeypatch):
    from app.services import image_gen

    _FakeClient.requests = []
    monkeypatch.setattr(image_gen.httpx, "AsyncClient", _FakeClient)

    service = ImageGenService.__new__(ImageGenService)
    service.api_key = "test-key"
    service.base_url = "https://v1/api/generate"
    service.model = "gpt-image-2"
    service.model_chain = ["gpt-image-2"]
    service.image_size = "1024x1024"
    service.reply_type = "json"
    service._save_image = lambda content: ("/api/article-images/test.png", "/api/article-images/test.png", "local")

    result = asyncio.run(service.generate_image("生成一张心理学火柴人场景图"))

    request = _FakeClient.requests[0]
    assert request["url"] == "https://v1/api/generate"
    assert request["headers"]["Authorization"] == "Bearer test-key"
    assert request["json"] == {
        "model": "gpt-image-2",
        "prompt": "生成一张心理学火柴人场景图",
        "images": [],
        "aspectRatio": "1024x1024",
        "replyType": "json",
    }
    assert _FakeClient.requests[1]["get"] == "https://example.test/generated.png"
    assert result == ("/api/article-images/test.png", "/api/article-images/test.png", "local")
