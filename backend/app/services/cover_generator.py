import os
import uuid
import requests
from pathlib import Path
from typing import Optional
from datetime import datetime
from sqlalchemy.orm import Session
from PIL import Image, ImageDraw, ImageFont
from app.models.cover import Cover
from app.models.cover_style import CoverStyle
from app.models.user import User
from app.config import get_settings
from app.utils.encryption import decrypt_api_key

settings = get_settings()


class CoverGenerator:
    def __init__(self, db: Session):
        self.db = db
        self.image_api_key = settings.DASHSCOPE_API_KEY
        self.image_base_url = settings.IMAGE_BASE_URL
    
    def _get_user_image_api_key(self, user_id: int) -> Optional[str]:
        user = self.db.query(User).filter(User.id == user_id).first()
        if user and user.image_use_custom and user.image_api_key_encrypted:
            return decrypt_api_key(user.image_api_key_encrypted)
        return None
    
    async def generate_cover(
        self,
        user_id: int,
        topic: str,
        title_line1: str,
        title_line2: Optional[str] = None,
        style: Optional[CoverStyle] = None,
        font_style: Optional[str] = "黑体",
        font_color: Optional[str] = "#333333",
        cover_id: Optional[int] = None,
    ) -> Cover:
        # 生成图片 prompt
        if style:
            prompt = style.base_prompt.replace("{topic}", topic)
        else:
            prompt = f"公众号封面，主题：{topic}，简约商务风格，专业感，高质量，无文字，9:16比例"
        
        # 获取用户自定义 API key（如果有）
        user_api_key = self._get_user_image_api_key(user_id)
        api_key = user_api_key or self.image_api_key
        
        # 生成图片
        image_url, local_path = await self._generate_image(prompt, api_key)
        
        # 在图片上添加文字标题
        if local_path and os.path.exists(local_path):
            final_path = self._add_text_to_image(
                local_path,
                title_line1,
                title_line2,
                font_style,
                font_color,
            )
        
        # 保存到数据库
        if cover_id:
            cover = self.db.query(Cover).filter(Cover.id == cover_id).first()
            if cover:
                cover.image_url = image_url
                cover.local_url = final_path or local_path
                cover.updated_at = datetime.utcnow()
        else:
            cover = Cover(
                user_id=user_id,
                style_id=style.id if style else None,
                title_line1=title_line1,
                title_line2=title_line2,
                topic=topic,
                font_style=font_style,
                font_color=font_color,
                image_url=image_url,
                local_url=final_path or local_path,
            )
            self.db.add(cover)
        
        self.db.commit()
        self.db.refresh(cover)
        return cover
    
    async def _generate_image(self, prompt: str, api_key: str) -> tuple[str, str]:
        # 调用图片生成 API
        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {api_key}",
        }
        
        payload = {
            "model": "qwen-image-2.0-pro",
            "input": {
                "prompt": prompt,
                "size": "720*1280",  # 9:16
                "n": 1,
            },
        }
        
        response = requests.post(
            self.image_base_url,
            headers=headers,
            json=payload,
            timeout=60,
        )
        
        if response.status_code != 200:
            raise Exception(f"图片生成失败: {response.text}")
        
        result = response.json()
        output = result.get("output", {})
        
        # 获取图片 URL
        if output.get("results"):
            image_url = output["results"][0].get("url")
        elif output.get("url"):
            image_url = output["url"]
        else:
            raise Exception("图片生成失败：未返回图片URL")
        
        # 下载图片到本地
        local_dir = Path(__file__).resolve().parents[2] / "uploads" / "covers"
        local_dir.mkdir(parents=True, exist_ok=True)
        
        local_filename = f"cover_{uuid.uuid4().hex[:12]}.png"
        local_path = local_dir / local_filename
        
        image_response = requests.get(image_url, timeout=30)
        with open(local_path, "wb") as f:
            f.write(image_response.content)
        
        return image_url, str(local_path)
    
    def _add_text_to_image(
        self,
        image_path: str,
        title_line1: str,
        title_line2: Optional[str],
        font_style: str,
        font_color: str,
    ) -> str:
        # 打开图片
        img = Image.open(image_path)
        draw = ImageDraw.Draw(img)
        
        # 加载字体
        font_paths = {
            "黑体": "simhei.ttf",
            "宋体": "simsun.ttf",
            "微软雅黑": "msyh.ttf",
            "楷体": "simkai.ttf",
        }
        
        font_file = font_paths.get(font_style, "simhei.ttf")
        
        try:
            font_large = ImageFont.truetype(font_file, 48)
            font_small = ImageFont.truetype(font_file, 36)
        except Exception:
            font_large = ImageFont.load_default()
            font_small = ImageFont.load_default()
        
        # 计算文字位置（居中）
        img_width, img_height = img.size
        
        # 第一行标题（较大字体）
        line1_bbox = draw.textbbox((0, 0), title_line1, font=font_large)
        line1_width = line1_bbox[2] - line1_bbox[0]
        line1_x = (img_width - line1_width) // 2
        line1_y = img_height // 3
        
        draw.text((line1_x, line1_y), title_line1, font=font_large, fill=font_color)
        
        # 第二行标题（如果有）
        if title_line2:
            line2_bbox = draw.textbbox((0, 0), title_line2, font=font_small)
            line2_width = line2_bbox[2] - line2_bbox[0]
            line2_x = (img_width - line2_width) // 2
            line2_y = line1_y + 70
            
            draw.text((line2_x, line2_y), title_line2, font=font_small, fill=font_color)
        
        # 保存图片
        output_dir = Path(image_path).parent
        output_filename = f"cover_text_{uuid.uuid4().hex[:12]}.png"
        output_path = output_dir / output_filename
        
        img.save(output_path)
        
        return str(output_path)