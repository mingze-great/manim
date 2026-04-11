import httpx
import uuid
from pathlib import Path
from typing import List
from app.config import get_settings
from app.utils.cos_storage import cos_storage

settings = get_settings()


class ImageGenService:
    def __init__(self):
        self.api_key = settings.STICKMAN_IMAGE_API_KEY or settings.DASHSCOPE_API_KEY
        self.base_url = settings.STICKMAN_IMAGE_BASE_URL
        self.model = settings.STICKMAN_IMAGE_MODEL or "qwen-image-2.0-pro"
        self.model_chain = [item.strip() for item in (settings.STICKMAN_IMAGE_MODELS or self.model).split(",") if item.strip()]
        if self.model and self.model not in self.model_chain:
            self.model_chain.insert(0, self.model)

    async def generate_image(self, prompt: str) -> tuple[str, str, str]:
        """生成单张图片"""
        last_error = None
        async with httpx.AsyncClient(timeout=120.0) as client:
            for model in self.model_chain:
                try:
                    response = await client.post(
                        self.base_url,
                        headers={
                            "Authorization": f"Bearer {self.api_key}",
                            "Content-Type": "application/json"
                        },
                        json={
                            "model": model,
                            "input": {
                                "messages": [
                                    {
                                        "role": "user",
                                        "content": [{"text": prompt}]
                                    }
                                ]
                            },
                            "parameters": {
                                "size": "1024*1024",
                                "watermark": False,
                                "prompt_extend": True
                            }
                        }
                    )
                    response.raise_for_status()
                    data = response.json()
                    image_url = self._extract_image_url(data)
                    if not image_url:
                        raise Exception(f"图片生成未返回有效的URL: {data}")
                    image_resp = await client.get(image_url)
                    image_resp.raise_for_status()
                    return self._save_image(image_resp.content)
                except Exception as exc:
                    last_error = exc
                    continue
        raise Exception(f"图片生成失败: {last_error}")

    def _extract_image_url(self, data: dict) -> str:
        output = data.get("output") or {}
        choices = output.get("choices") or []
        if choices:
            content = (choices[0].get("message") or {}).get("content") or []
            if content and isinstance(content[0], dict):
                return content[0].get("image") or content[0].get("url") or ""
        results = output.get("results") or []
        if results:
            return (results[0] or {}).get("url") or ""
        return ""

    def _save_image(self, content: bytes) -> tuple[str, str, str]:
        uploads_dir = Path(__file__).resolve().parents[2] / "uploads" / "article_images"
        uploads_dir.mkdir(parents=True, exist_ok=True)
        filename = f"article_{uuid.uuid4().hex[:12]}.png"
        file_path = uploads_dir / filename
        with open(file_path, "wb") as file:
            file.write(content)
        local_url = f"/api/article-images/{filename}"
        public_url = local_url
        storage = "local"
        if cos_storage.enabled:
            remote_key = f"articles/images/{filename}"
            uploaded_key = cos_storage.upload_image(content, remote_key, content_type='image/png')
            if uploaded_key:
                public_url = cos_storage.get_public_url(uploaded_key) or local_url
                storage = "cos"
        return local_url, public_url, storage
    
    async def generate_images_for_article(self, topic: str, content: str) -> List[dict]:
        """为文章生成配图"""
        images = []
        
        # 封面图
        try:
            cover_prompt = f"公众号文章封面图，主题：{topic}，简约商务风格，高质量，专业感"
            cover_local_url, cover_url, storage = await self.generate_image(cover_prompt)
            images.append({
                "url": cover_url,
                "local_url": cover_local_url,
                "position": 0,
                "anchor_paragraph": 0,
                "prompt": cover_prompt,
                "type": "cover",
                "storage": storage,
            })
        except Exception as e:
            print(f"[ImageGen] 封面图生成失败: {e}")
        
        paragraphs = [p.strip() for p in content.split("\n\n") if p.strip() and not p.startswith("#")]
        
        # 内容图1
        if len(paragraphs) >= 2:
            try:
                content_prompt = f"公众号文章配图，主题：{topic}，内容相关：{paragraphs[0][:50]}，简约商务风格"
                content_local_url, content_url, storage = await self.generate_image(content_prompt)
                images.append({
                    "url": content_url,
                    "local_url": content_local_url,
                    "position": 300,
                    "anchor_paragraph": 1,
                    "prompt": content_prompt,
                    "type": "content",
                    "storage": storage,
                })
            except Exception as e:
                print(f"[ImageGen] 内容图1生成失败: {e}")
        
        # 内容图2
        if len(paragraphs) >= 4:
            try:
                content_prompt2 = f"公众号文章配图，主题：{topic}，内容相关：{paragraphs[2][:50]}，简约商务风格"
                content_local_url2, content_url2, storage = await self.generate_image(content_prompt2)
                images.append({
                    "url": content_url2,
                    "local_url": content_local_url2,
                    "position": 600,
                    "anchor_paragraph": 3,
                    "prompt": content_prompt2,
                    "type": "content",
                    "storage": storage,
                })
            except Exception as e:
                print(f"[ImageGen] 内容图2生成失败: {e}")
        
        return images


image_gen_service = ImageGenService()
