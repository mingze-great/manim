import json
from datetime import datetime, date
from typing import Optional, List
from sqlalchemy.orm import Session
from app.models.article import Article
from app.models.daily_usage import UserDailyUsage
from app.config import get_settings

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
    
    async def generate_outline(self, topic: str) -> str:
        """生成文章大纲"""
        from app.utils.llm_factory import LLMFactory
        
        client = LLMFactory.get_client()
        
        prompt = f"""请为以下主题生成一个公众号文章大纲，要求：
1. 包含标题和3-5个要点
2. 每个要点一行，简洁明了
3. 总字数100-200字

主题：{topic}

请直接输出大纲，不要其他解释。"""
        
        messages = [
            {"role": "system", "content": "你是一个公众号文章创作专家，擅长生成吸引人的文章大纲。"},
            {"role": "user", "content": prompt}
        ]
        
        response = await client.chat(messages=messages)
        return response
    
    async def generate_content(self, topic: str, outline: str) -> dict:
        """生成完整文章内容"""
        from app.utils.llm_factory import LLMFactory
        
        client = LLMFactory.get_client()
        
        prompt = f"""请根据以下主题和大纲，生成一篇公众号文章，要求：
1. 字数700-1000字
2. 每个要点详细展开，有深度有见解
3. 语言通俗易懂，有感染力
4. 段落清晰，使用二级标题分隔
5. 结尾有总结

主题：{topic}

大纲：
{outline}

请直接输出文章正文，不要输出标题和大纲。"""
        
        messages = [
            {"role": "system", "content": "你是一个公众号文章创作专家，擅长写深度好文。"},
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
    
    async def create_article(self, user_id: int, topic: str, outline: str = None) -> Article:
        """创建文章"""
        article = Article(
            user_id=user_id,
            topic=topic,
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