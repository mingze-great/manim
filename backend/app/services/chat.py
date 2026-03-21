import json
from sqlalchemy.orm import Session

from app.models.project import Conversation, Project
from app.utils.llm_factory import LLMFactory

SYSTEM_PROMPT = """你是一个专业的动画内容策划专家。

## 你的任务
根据用户给定的视频主题，列出各个要点的内容摘要和动态图描述。

## 输出格式要求
请用简洁的结构化格式输出：

### 第1点：[标题]
- 内容：[核心文字内容，20-50字]
- 动态图：[1-2句话描述动态效果]

### 第2点：[标题]
- 内容：[核心文字内容]
- 动态图：[描述动态效果]

...（以此类推）

## 重要规则
1. 内容要精炼，每个要点20-50字
2. 动态图描述要具体：如"圆形展开→文字淡入→箭头指示"
3. 只列出用户给定的主题要点，不要自己添加
4. 列出后询问用户是否满意，或需要调整哪些内容
5. 当用户说"可以了"或"开始生成"或"确认生成"时，设置 is_final=true
6. 当用户要求调整某些内容时，根据反馈修改对应要点
"""


class ChatService:
    def __init__(self, db: Session):
        self.db = db
        self.client = LLMFactory.get_client()
    
    async def process_message(self, project_id: int, theme: str, user_message: str) -> dict:
        conversations = self.db.query(Conversation).filter(
            Conversation.project_id == project_id
        ).order_by(Conversation.created_at).all()
        
        project = self.db.query(Project).filter(Project.id == project_id).first()
        
        messages = [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": f"视频主题：{theme}"}
        ]
        
        for conv in conversations:
            messages.append({"role": conv.role, "content": conv.content})
        
        messages.append({"role": "user", "content": user_message})
        
        content = await self.client.chat(
            messages=messages,
            temperature=0.7,
            max_tokens=3000
        )
        
        # 检查是否确认生成
        confirm_keywords = ["可以了", "开始生成", "确认生成", "开始吧", "好的"]
        is_final = any(keyword in content for keyword in confirm_keywords)
        
        # 如果确认生成，同时生成代码并存入项目
        if is_final:
            from app.services.manim import ManimService
            manim_service = ManimService(self.db)
            
            # 获取项目关联的模板代码
            template_code = ""
            if project.template_id:
                from app.models.template import Template
                template = self.db.query(Template).filter(Template.id == project.template_id).first()
                if template:
                    template_code = template.code
            
            # 获取用户自定义代码（如果有）
            custom_code = project.custom_code or ""
            
            # 生成代码
            manim_code = await manim_service.generate_code(content, custom_code=custom_code or None)
            
            # 保存代码到项目（但不包含在返回给用户的内容中）
            project.manim_code = manim_code
            project.final_script = content
            project.status = "chatting"
            self.db.commit()
        
        return {
            "content": content,
            "is_final": is_final,
            "final_script": content if is_final else None
        }
