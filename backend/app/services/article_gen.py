import json
import re
from datetime import datetime, date
from typing import Optional, List
from sqlalchemy.orm import Session
from app.models.article import Article
from app.models.daily_usage import UserDailyUsage
from app.config import get_settings
from app.article_prompts import get_category_prompt
from app.models.user import User

settings = get_settings()


class ArticleGenService:
    def __init__(self, db: Session):
        self.db = db

    def clean_generated_text(self, text: str) -> str:
        if not text:
            return ""
        cleaned = text.replace('**', '')
        cleaned = re.sub(r'^[ \t]*#{1,6}[ \t]*', '', cleaned, flags=re.MULTILINE)
        cleaned = re.sub(r'^[ \t]*[-*][ \t]+', '', cleaned, flags=re.MULTILINE)
        cleaned = re.sub(r'(?<!\*)\*(?!\*)', '', cleaned)
        cleaned = re.sub(r'[ \t]+\n', '\n', cleaned)
        cleaned = re.sub(r'\n{3,}', '\n\n', cleaned)
        return cleaned.strip()

    def clean_generated_title(self, text: str) -> str:
        title = self.clean_generated_text(text)
        title = title.replace('标题：', '').replace('标题:', '').strip()
        title = re.sub(r'^[一二三四五六七八九十]+、', '', title)
        return title.strip('：: -*#')
    
    async def check_daily_limit(self, user_id: int) -> dict:
        """检查用户公众号模块可用次数（按月）"""
        user = self.db.query(User).filter(User.id == user_id).first()
        if user and bool(user.is_admin):
            return {
                "used_today": 0,
                "limit": -1,
                "remaining": -1,
                "reset_time": datetime.utcnow().strftime('%Y-%m'),
                "module": "article",
                "unlimited": True,
            }

        limit = settings.ARTICLE_DAILY_LIMIT
        used_today = 0
        if user:
            permission = user.get_module_permission("article")
            limit = int(permission.get("daily_limit", limit) or limit)
            used_today = int(permission.get("used_today", 0) or 0)
        
        return {
            "used_today": used_today,
            "limit": limit,
            "remaining": max(0, limit - used_today),
            "reset_time": datetime.utcnow().strftime('%Y-%m'),
            "module": "article",
            "unlimited": False,
        }
    
    async def increment_usage(self, user_id: int):
        """增加用户公众号模块使用次数（按月）"""
        user = self.db.query(User).filter(User.id == user_id).first()
        if user and bool(user.is_admin):
            return
        if user:
            user.increment_module_usage("article")
        
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
        response = self.clean_generated_text(response)

        # 提取标题
        title = self._extract_title(response)

        return {
            "outline": response,
            "title": title
        }

    async def generate_topic_suggestions(self, category: str = "生活", keyword: str = "") -> list[str]:
        from app.utils.llm_factory import LLMFactory
        from app.models.article_category import ArticleCategory

        client = LLMFactory.get_client()
        db_category = self.db.query(ArticleCategory).filter(ArticleCategory.name == category).first()
        system_prompt = db_category.system_prompt if db_category else get_category_prompt(category)
        prompt = f"""请为公众号文章创作方向“{category}”生成 6 个适合传播的中文主题。
{f'关键词参考：{keyword}' if keyword else ''}

要求：
1. 每个主题单独一行
2. 适合公众号标题拓展
3. 兼顾实用性、情绪价值和传播性
4. 不要编号，不要解释
"""
        result = await client.chat(messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": prompt},
        ])
        return [line.strip("- 1234567890.\t") for line in result.splitlines() if line.strip()][:6]
    
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

        content = self.clean_generated_text(await client.chat(messages=messages))

        title = self._extract_title(outline)
        word_count = len(content.replace("\n", "").replace(" ", ""))

        return {
            "title": title,
            "content": content,
            "word_count": word_count
        }

    async def rewrite_outline_section(
        self,
        topic: str,
        category: str,
        current_outline: str,
        section_text: str,
        requirement: str | None = None,
    ) -> str:
        from app.utils.llm_factory import LLMFactory
        from app.models.article_category import ArticleCategory

        client = LLMFactory.get_client()
        db_category = self.db.query(ArticleCategory).filter(ArticleCategory.name == category).first()
        system_prompt = db_category.system_prompt if db_category else get_category_prompt(category)
        prompt = f"""你是公众号编辑，请只重写大纲中的一个小节标题，使其更清晰、更有吸引力、更适合公众号传播。

【主题】{topic}
【创作方向】{category}
【完整大纲】
{current_outline}

【当前小节】{section_text}
{f'【补充要求】{requirement}' if requirement else ''}

要求：
1. 只输出重写后的一条小节标题
2. 控制在 8-20 个字
3. 保持与全文结构一致
4. 不要输出解释
"""
        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": prompt},
        ]
        return self.clean_generated_text((await client.chat(messages=messages)).strip())

    async def rewrite_content_section(
        self,
        topic: str,
        category: str,
        article_title: str,
        current_outline: str,
        section_text: str,
        requirement: str | None = None,
    ) -> str:
        from app.utils.llm_factory import LLMFactory
        from app.models.article_category import ArticleCategory

        client = LLMFactory.get_client()
        db_category = self.db.query(ArticleCategory).filter(ArticleCategory.name == category).first()
        system_prompt = db_category.system_prompt if db_category else get_category_prompt(category)
        prompt = f"""你是公众号文章编辑，请只重写下面这一段正文，使它更适合公众号传播。

【文章标题】{article_title or topic}
【主题】{topic}
【创作方向】{category}
【大纲】
{current_outline}

【当前段落】
{section_text}

{f'【补充要求】{requirement}' if requirement else ''}

要求：
1. 只输出重写后的这一段内容
2. 保持与全文风格一致
3. 更有画面感、可读性和传播性
4. 不要输出解释
"""
        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": prompt},
        ]
        return self.clean_generated_text((await client.chat(messages=messages)).strip())
    
    def _extract_title(self, outline: str) -> str:
        """从大纲中提取标题"""
        lines = outline.strip().split("\n")
        for line in lines:
            line = line.strip()
            if line and not line.startswith("#") and len(line) < 50:
                return self.clean_generated_title(line)
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
            cover_image = next((img for img in images if img.get("type") == "cover"), images[0])
            html_parts.append(f'''<p style="text-align: center; margin-bottom: 20px;"><img src="{cover_image.get('url') or cover_image.get('local_url') or ''}" style="max-width: 100%; height: auto; border-radius: 8px;" /></p>''')
        
        paragraph_images = {}
        content_images = [img for img in images if img.get("type") != "cover"]
        paragraph_count = max(len([p for p in paragraphs if p.strip()]), 1)
        default_anchors = self._build_default_image_anchors(len(content_images), paragraph_count)
        for idx, image in enumerate(content_images, start=1):
            anchor = image.get("anchor_paragraph")
            if not isinstance(anchor, int) or anchor <= 0:
                anchor = default_anchors.get(idx, min(idx, paragraph_count))
            paragraph_images.setdefault(anchor, []).append(image)

        char_count = 0
        image_index = 1
        
        for para_idx, para in enumerate(paragraphs, start=1):
            para = para.strip()
            if not para:
                continue
            
            if para.startswith("##"):
                heading = para.replace("##", "").strip()
                html_parts.append(f'''<h2 style="font-size: 20px; font-weight: bold; color: #333; margin: 25px 0 15px 0;">{heading}</h2>''')
            else:
                html_parts.append(f'''<p style="font-size: 16px; line-height: 1.8; color: #333; margin-bottom: 15px;">{para}</p>''')

            if paragraph_images.get(para_idx):
                for img in paragraph_images[para_idx]:
                    html_parts.append(f'''<p style="text-align: center; margin: 20px 0;"><img src="{img['url']}" style="max-width: 100%; height: auto; border-radius: 8px;" /></p>''')
            
            char_count += len(para)
            
            if image_index < len(content_images) and char_count > 300 * image_index:
                current = content_images[image_index]
                if not isinstance(current.get("anchor_paragraph"), int):
                    image_src = current.get('url') or current.get('local_url') or ''
                    html_parts.append(f'''<p style="text-align: center; margin: 20px 0;"><img src="{image_src}" style="max-width: 100%; height: auto; border-radius: 8px;" /></p>''')
                image_index += 1
        
        html_parts.append('''</section>''')
        
        return "\n".join(html_parts)

    def _build_default_image_anchors(self, image_count: int, paragraph_count: int) -> dict[int, int]:
        if image_count <= 0:
            return {}
        if paragraph_count <= 1:
            return {index: 1 for index in range(1, image_count + 1)}
        anchors = {}
        for index in range(1, image_count + 1):
            anchor = round(index * paragraph_count / (image_count + 1))
            anchors[index] = max(1, min(paragraph_count, anchor))
        return anchors
    
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

    async def _build_image_intents(self, topic: str, category: str, content: str) -> List[dict]:
        from app.utils.llm_factory import LLMFactory

        paragraphs = [p.strip() for p in content.split("\n\n") if p.strip() and not p.startswith("#")]
        if not paragraphs:
            return []

        paragraph_count = len(paragraphs)
        default_anchors = self._build_default_image_anchors(2, paragraph_count)
        client = LLMFactory.get_client()
        prompt = f"""你是公众号视觉策划，请根据文章内容输出 3 张配图的规划，要求三张图内容差异明显，并且与文案强相关。

【主题】{topic}
【方向】{category}
【正文】
{content[:2500]}

请严格输出 JSON 数组，不要解释。每项结构如下：
{{
  "type": "cover|content",
  "anchor_paragraph": 0,
  "related_text": "对应段落摘要",
  "scene_subject": "画面主体",
  "scene_action": "主体动作",
  "scene_environment": "场景环境",
  "visual_metaphor": "视觉隐喻",
  "emotion_tone": "情绪基调",
  "composition_hint": "构图提示"
}}

要求：
1. 第一张必须是封面图，后两张是内容图
2. 两张内容图分别对应文章不同段落，anchor_paragraph 必须不同
3. 三张图的主体、场景、情绪要明显不同
4. related_text 必须概括对应段落含义，不超过 30 字
"""

        try:
            raw = await client.chat(messages=[
                {"role": "system", "content": "你擅长把文章内容拆解成具有传播力的公众号配图方案。"},
                {"role": "user", "content": prompt},
            ])
            match = re.search(r"\[[\s\S]*\]", raw)
            plans = json.loads(match.group()) if match else []
        except Exception:
            plans = []

        if not isinstance(plans, list) or not plans:
            key_paragraphs = self._extract_key_paragraphs(content)
            prompt_builder = PromptBuilderService(self.db)
            plans = [
                {
                    "type": "cover",
                    "anchor_paragraph": 0,
                    "related_text": topic[:30],
                    "scene_subject": topic,
                    "scene_action": "using a symbolic cover composition",
                    "scene_environment": "clean editorial environment",
                    "visual_metaphor": "core topic metaphor",
                    "emotion_tone": "strong and attractive",
                    "composition_hint": "clean central composition",
                }
            ]
            for idx, para in enumerate(key_paragraphs[:2], start=1):
                plans.append({
                    "type": "content",
                    "anchor_paragraph": default_anchors.get(idx, idx),
                    "related_text": (para.get("text") or para.get("heading") or "")[:30],
                    "scene_subject": para.get("heading") or topic,
                    "scene_action": "expressing the key point visually",
                    "scene_environment": "editorial storytelling scene",
                    "visual_metaphor": "article insight metaphor",
                    "emotion_tone": prompt_builder.detect_emotion(para.get("text") or para.get("heading") or ""),
                    "composition_hint": "avoid repeating previous image composition",
                })

        normalized = []
        used_anchors = set()
        for index, plan in enumerate(plans[:3], start=1):
            item = dict(plan)
            if item.get("type") == "cover" or index == 1:
                item["type"] = "cover"
                item["anchor_paragraph"] = 0
            else:
                anchor = int(item.get("anchor_paragraph") or default_anchors.get(index - 1, index))
                while anchor in used_anchors and anchor < paragraph_count:
                    anchor += 1
                anchor = max(1, min(paragraph_count, anchor))
                item["anchor_paragraph"] = anchor
                item["type"] = "content"
                used_anchors.add(anchor)
            normalized.append(item)

        return normalized
    
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
        prompt_builder = PromptBuilderService(self.db)
        image_plans = await self._build_image_intents(topic, category, content)
        paragraphs = [p.strip() for p in content.split("\n\n") if p.strip() and not p.startswith("#")]

        for idx, plan in enumerate(image_plans, start=1):
            context = " ".join(filter(None, [
                plan.get("related_text", ""),
                plan.get("scene_subject", ""),
                plan.get("scene_action", ""),
                plan.get("scene_environment", ""),
                plan.get("visual_metaphor", ""),
                plan.get("emotion_tone", ""),
                plan.get("composition_hint", ""),
            ]))
            image_type = plan.get("type", "content")
            prompt = prompt_builder.build_prompt(
                topic=topic,
                category=category,
                context=context,
                image_type=image_type,
            )
            anchor = int(plan.get("anchor_paragraph") or 0)
            position = 0 if image_type == "cover" else sum(len(p) for p in paragraphs[:max(anchor - 1, 0)])
            images.append({
                "url": "",
                "position": position,
                "anchor_paragraph": anchor,
                "prompt": prompt,
                "related_text": plan.get("related_text", ""),
                "scene_subject": plan.get("scene_subject", ""),
                "scene_action": plan.get("scene_action", ""),
                "type": image_type,
            })
        
        return images

    async def generate_draft(self, article_id: int, requirement: str | None = None) -> Article:
        article = self.get_article(article_id)
        if not article:
            return None

        outline_result = await self.generate_outline(str(article.topic), str(article.category or "生活"), requirement)
        content_result = await self.generate_content(
            str(article.topic),
            outline_result["outline"],
            str(article.category or "生活"),
            requirement,
        )
        return await self.update_article(
            article_id,
            title=content_result["title"],
            outline=outline_result["outline"],
            content_text=content_result["content"],
            word_count=content_result["word_count"],
            status="draft",
        )
    
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
