import json
from datetime import datetime, date
from typing import Optional, List
from sqlalchemy.orm import Session
from app.models.article import Article
from app.models.daily_usage import UserDailyUsage
from app.config import get_settings
from app.article_prompts import get_category_prompt

settings = get_settings()


class ArticleGenService:
    def __init__(self, db: Session):
        self.db = db
    
    async def check_daily_limit(self, user_id: int) -> dict:
        """检查用户当日使用次数"""
        today = date.today()
        usage = self.db.query(UserDailyUsage).filter(
            UserDailyUsage.user_id == user_id,
            UserDailyUsage.usage_date == today
        ).first()
        
        used_today = usage.article_count if usage else 0
        limit = settings.ARTICLE_DAILY_LIMIT
        
        return {
            "used_today": used_today,
            "limit": limit,
            "remaining": max(0, limit - used_today),
            "reset_time": f"{(datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)).isoformat()}"
        }
    
    async def increment_usage(self, user_id: int):
        """增加用户当日使用次数"""
        today = date.today()
        usage = self.db.query(UserDailyUsage).filter(
            UserDailyUsage.user_id == user_id,
            UserDailyUsage.usage_date == today
        ).first()
        
        if usage:
            usage.article_count += 1
        else:
            usage = UserDailyUsage(
                user_id=user_id,
                usage_date=today,
                article_count=1
            )
            self.db.add(usage)
        
        self.db.commit()
    
    async def generate_outline(self, topic: str, category: str = "生活", requirement: str = None) -> dict:
        """生成文章大纲，包含标题"""
        from app.utils.llm_factory import LLMFactory
        from app.models.article_category import ArticleCategory
        import json

        client = LLMFactory.get_client()

        # 从数据库读取系统提示词
        db_category = self.db.query(ArticleCategory).filter(
            ArticleCategory.name == category
        ).first()

        if db_category:
            system_prompt = db_category.system_prompt
        else:
            system_prompt = get_category_prompt(category)

        # 优化prompt模板
        prompt = f"""请为以下主题生成一个专业的公众号文章大纲：

【创作方向】{category}
【主题】{topic}
{f'【补充要求】{requirement}' if requirement else ''}

【输出格式】
标题：[吸引人的标题]

一、[第一个要点]
二、[第二个要点]
三、[第三个要点]
...

【要求】
1. 标题要吸引眼球，符合{category}风格，20字以内
2. 要点要具体、可展开，每个要点10-20字
3. 结构清晰，逻辑连贯
4. 总字数100-200字

请直接输出大纲，不要其他解释。"""

        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": prompt}
        ]

        response = await client.chat(messages=messages)

        # 提取标题
        title = self._extract_title(response)

        return {
            "outline": response,
            "title": title
        }
    
    async def generate_content(self, topic: str, outline: str, category: str = "生活", requirement: str = None) -> dict:
        """生成完整文章内容"""
        from app.utils.llm_factory import LLMFactory
        from app.models.article_category import ArticleCategory

        client = LLMFactory.get_client()

        # 从数据库读取系统提示词
        db_category = self.db.query(ArticleCategory).filter(
            ArticleCategory.name == category
        ).first()

        if db_category:
            system_prompt = db_category.system_prompt
        else:
            system_prompt = get_category_prompt(category)

        # 优化prompt模板
        prompt = f"""请根据以下信息生成一篇高质量公众号文章：

【创作方向】{category}
【主题】{topic}

【大纲】
{outline}

{f'【补充要求】{requirement}' if requirement else ''}

【写作要求】
1. 字数700-1000字
2. 符合{category}的风格特点
3. 语言通俗易懂，有感染力
4. 段落清晰，使用小标题分隔
5. 开头吸引人，结尾有升华
6. 可适当加入案例或数据支撑

【输出要求】
直接输出文章正文内容，不要输出标题和大纲。"""

        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": prompt}
        ]

        content = await client.chat(messages=messages)

        title = self._extract_title(outline)
        word_count = len(content.replace("\n", "").replace(" ", ""))

        return {
            "title": title,
            "content": content,
            "word_count": word_count
        }
    
    def _extract_title(self, outline: str) -> str:
        """从大纲中提取标题"""
        lines = outline.strip().split("\n")
        for line in lines:
            line = line.strip()
            if line and not line.startswith("#") and len(line) < 50:
                return line.replace("标题：", "").replace("标题:", "").strip()
        return "公众号文章"
    
    def convert_to_html(self, title: str, content: str, images: list) -> str:
        """转换为微信公众号兼容的 HTML 格式"""
        # 处理 images 参数类型（可能是 JSON 字符串）
        if isinstance(images, str):
            try:
                images = json.loads(images)
            except:
                images = []
        
        if not isinstance(images, list):
            images = []
        
        paragraphs = content.split("\n\n")
        html_parts = []
        
        html_parts.append(f'''<section style="padding: 20px; font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;">''')
        
        html_parts.append(f'''<h1 style="font-size: 24px; font-weight: bold; color: #333; margin-bottom: 20px; text-align: center;">{title}</h1>''')
        
        if images and len(images) > 0:
            html_parts.append(f'''<p style="text-align: center; margin-bottom: 20px;"><img src="{images[0]['url']}" style="max-width: 100%; height: auto; border-radius: 8px;" /></p>''')
        
        char_count = 0
        image_index = 1
        
        for para in paragraphs:
            para = para.strip()
            if not para:
                continue
            
            if para.startswith("##"):
                heading = para.replace("##", "").strip()
                html_parts.append(f'''<h2 style="font-size: 20px; font-weight: bold; color: #333; margin: 25px 0 15px 0;">{heading}</h2>''')
            else:
                html_parts.append(f'''<p style="font-size: 16px; line-height: 1.8; color: #333; margin-bottom: 15px;">{para}</p>''')
            
            char_count += len(para)
            
            if image_index < len(images) and char_count > 300 * image_index:
                html_parts.append(f'''<p style="text-align: center; margin: 20px 0;"><img src="{images[image_index]['url']}" style="max-width: 100%; height: auto; border-radius: 8px;" /></p>''')
                image_index += 1
        
        html_parts.append('''</section>''')
        
        return "\n".join(html_parts)
    
    def _extract_key_paragraphs(self, content: str) -> List[dict]:
        """智能提取关键段落用于配图"""
        paragraphs = [p.strip() for p in content.split("\n\n") if p.strip()]
        key_paras = []
        
        for i, para in enumerate(paragraphs):
            # 支持多种标题格式
            is_heading = False
            heading = ""
            
            # 格式1: ## 标题
            if para.startswith("##"):
                is_heading = True
                heading = para.replace("##", "").strip()
            
            # 格式2: **一、标题** 或 **1. 标题**
            elif para.startswith("**") and ("、" in para[:15] or para[2:3].isdigit()):
                is_heading = True
                # 提取标题：移除 ** 和数字编号
                heading = para.replace("**", "")
                if "、" in heading:
                    heading = heading.split("、", 1)[-1].strip()
                elif heading[0].isdigit():
                    # 移除数字和点号
                    parts = heading.split(".", 1)
                    heading = parts[-1].strip() if len(parts) > 1 else heading
            
            if is_heading:
                next_para = paragraphs[i+1] if i+1 < len(paragraphs) else ""
                keywords = self._extract_keywords(next_para or heading)
                
                key_paras.append({
                    "position": self._calculate_position(content, i),
                    "heading": heading,
                    "text": next_para,
                    "keywords": keywords
                })
        
        return key_paras[:2]
    
    def _extract_keywords(self, text: str) -> str:
        """提取关键词"""
        import re
        text = re.sub(r'[#*\n]', '', text)
        words = text.split()[:10]
        keywords = ' '.join(words)
        return keywords[:50] if len(keywords) > 50 else keywords
    
    def _calculate_position(self, content: str, paragraph_index: int) -> int:
        """计算段落位置（字符数）"""
        paragraphs = content.split("\n\n")
        position = 0
        for i in range(paragraph_index):
            position += len(paragraphs[i])
        return position
    
    async def generate_smart_images(self, content: str, topic: str, category: str) -> List[dict]:
        """根据内容智能生成配图"""
        from app.models.article_category import ArticleCategory
        from app.services.prompt_builder import PromptBuilderService
        
        images = []
        
        # 使用提示词构建服务
        prompt_builder = PromptBuilderService(self.db)
        
        # 生成封面图提示词
        cover_prompt = prompt_builder.build_prompt(
            topic=topic,
            category=category,
            context="",
            image_type="cover"
        )
        
        images.append({
            "url": "",
            "position": 0,
            "prompt": cover_prompt,
            "type": "cover"
        })
        
        # 提取关键段落用于内容图
        key_paragraphs = self._extract_key_paragraphs(content)
        
        for para in key_paragraphs:
            # 使用提示词构建服务生成内容图提示词
            content_prompt = prompt_builder.build_prompt(
                topic=topic,
                category=category,
                context=para["text"] or para["heading"],
                image_type="content"
            )
            
            images.append({
                "url": "",
                "position": para["position"],
                "prompt": content_prompt,
                "related_text": para["text"][:50] if para["text"] else "",
                "type": "content"
            })
        
        return images
    
    async def create_article(self, user_id: int, topic: str, category: str = "生活", outline: str = None) -> Article:
        """创建文章"""
        article = Article(
            user_id=user_id,
            topic=topic,
            category=category,
            outline=outline,
            status="draft"
        )
        self.db.add(article)
        self.db.commit()
        self.db.refresh(article)
        return article
    
    async def update_article(self, article_id: int, **kwargs) -> Article:
        """更新文章"""
        article = self.db.query(Article).filter(Article.id == article_id).first()
        if not article:
            return None
        
        for key, value in kwargs.items():
            if hasattr(article, key):
                # 将 list 类型序列化为 JSON 字符串存储
                if key == "images" and isinstance(value, list):
                    value = json.dumps(value, ensure_ascii=False)
                setattr(article, key, value)
        
        article.updated_at = datetime.utcnow()
        self.db.commit()
        self.db.refresh(article)
        return article
    
    def get_article(self, article_id: int) -> Optional[Article]:
        """获取文章"""
        return self.db.query(Article).filter(Article.id == article_id).first()
    
    def get_user_articles(self, user_id: int, limit: int = 10) -> List[Article]:
        """获取用户文章列表"""
        return self.db.query(Article).filter(
            Article.user_id == user_id
        ).order_by(Article.created_at.desc()).limit(limit).all()
    
    def delete_article(self, article_id: int) -> bool:
        """删除文章"""
        article = self.db.query(Article).filter(Article.id == article_id).first()
        if article:
            self.db.delete(article)
            self.db.commit()
            return True
        return False