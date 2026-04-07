import json
import httpx
from typing import List
from app.config import get_settings
from app.utils.cos_storage import cos_storage

settings = get_settings()


class ImageGenService:
    def __init__(self):
        self.api_key = settings.IMAGE_API_KEY
        self.base_url = settings.IMAGE_BASE_URL
        self.model = settings.IMAGE_MODEL
    
    async def generate_image(self, prompt: str) -> str:
        """生成单张图片"""
        async with httpx.AsyncClient(timeout=60.0) as client:
            response = await client.post(
                self.base_url,
                headers={
                    "Authorization": f"Bearer {self.api_key}",
                    "Content-Type": "application/json"
                },
                json={
                    "model": self.model,
                    "input": {
                        "prompt": prompt
                    }
                }
            )
            
            if response.status_code != 200:
                raise Exception(f"图片生成失败: {response.text}")
            
            data = response.json()
            image_url = data["output"]["results"][0]["url"]
            
            cos_url = await cos_storage.upload_image_from_url(image_url, f"article_{hash(prompt)}.png")
            
            return cos_url
    
    async def generate_images_for_article(self, topic: str, content: str) -> List[dict]:
        """为文章生成配图"""
        images = []
        
        cover_prompt = f"公众号文章封面图，主题：{topic}，简约商务风格，高质量，专业感"
        cover_url = await self.generate_image(cover_prompt)
        images.append({
            "url": cover_url,
            "position": 0,
            "prompt": cover_prompt
        })
        
        paragraphs = [p.strip() for p in content.split("\n\n") if p.strip() and not p.startswith("#")]
        
        if len(paragraphs) >= 2:
            content_prompt = f"公众号文章配图，主题：{topic}，内容相关：{paragraphs[0][:50]}，简约商务风格"
            content_url = await self.generate_image(content_prompt)
            images.append({
                "url": content_url,
                "position": 300,
                "prompt": content_prompt
            })
        
        if len(paragraphs) >= 4:
            content_prompt2 = f"公众号文章配图，主题：{topic}，内容相关：{paragraphs[2][:50]}，简约商务风格"
            content_url2 = await self.generate_image(content_prompt2)
            images.append({
                "url": content_url2,
                "position": 600,
                "prompt": content_prompt2
            })
        
        return images


image_gen_service = ImageGenService()