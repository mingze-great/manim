from sqlalchemy.orm import Session
from app.utils.llm_factory import LLMFactory
from app.models.article_category import ArticleCategory
from app.article_prompts import get_category_prompt


class ArticleGenStreamService:
    def __init__(self, db: Session):
        self.db = db

    def clean_generated_text(self, text: str) -> str:
        if not text:
            return ''
        import re
        cleaned = text.replace('**', '')
        cleaned = re.sub(r'^[ \t]*#{1,6}[ \t]*', '', cleaned, flags=re.MULTILINE)
        cleaned = re.sub(r'^[ \t]*[-*][ \t]+', '', cleaned, flags=re.MULTILINE)
        cleaned = re.sub(r'(?<!\*)\*(?!\*)', '', cleaned)
        cleaned = re.sub(r'\n{3,}', '\n\n', cleaned)
        return cleaned.strip()
    
    async def generate_outline_stream(self, topic: str, category: str = "生活", requirement: str = None):
        """流式生成文章大纲"""
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
        
        response = await client.stream_chat(messages=messages)
        async for chunk in response:
            if not getattr(chunk, 'choices', None):
                continue
            delta = chunk.choices[0].delta
            if getattr(delta, 'content', None):
                yield delta.content
    
    async def generate_content_stream(self, topic: str, outline: str, category: str = "生活", requirement: str = None):
        """流式生成完整文章内容"""
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
        
        response = await client.stream_chat(messages=messages)
        async for chunk in response:
            if not getattr(chunk, 'choices', None):
                continue
            delta = chunk.choices[0].delta
            if getattr(delta, 'content', None):
                yield delta.content
    
    def extract_title(self, outline: str) -> str:
        """从大纲中提取标题"""
        lines = self.clean_generated_text(outline).strip().split("\n")
        for line in lines:
            line = line.strip()
            if line and not line.startswith("#") and len(line) < 50:
                return line.replace("标题：", "").replace("标题:", "").strip('：: -*#')
        return "公众号文章"
