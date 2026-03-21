import json
from sqlalchemy.orm import Session

from app.models.project import Conversation
from app.utils.llm_factory import LLMFactory

SYSTEM_PROMPT = """你是一个专业的动画内容策划专家。

## 你的任务
根据用户给定的视频主题，列出各个要点的内容摘要和动态图描述。

## 输出格式要求
请用简洁的结构化格式输出：

### 第1点：[标题]
- 内容：[核心文字内容]
- 动态图：[1-2句话描述动态效果，如：圆形从大变小，文字逐字出现等]

### 第2点：[标题]
- 内容：[核心文字内容]
- 动态图：[描述动态效果]

...（以此类推）

## 重要规则
1. 内容要精炼，每个要点20-50字
2. 动态图描述要具体：如"圆形展开→文字淡入→箭头指示"
3. 只列出用户给定的主题要点，不要自己添加
4. 列出后询问用户是否满意，或需要调整哪些内容
5. 当用户说"可以了"或"开始生成"时，设置 is_final=true

## 示例
用户输入："世界十大顶级思维：1. 刻意练习 2. 复利思维 3. 终身学习"

你输出：
### 第1点：刻意练习
- 内容：专注于技能提升的关键方法
- 动态图：数字从1增长到10000，同步文字"10000小时定律"

### 第2点：复利思维  
- 内容：收益随时间指数级增长
- 动态图：曲线平滑上升，金额数字跳动增长

请确认以上内容是否需要调整？
"""


class ChatService:
    def __init__(self, db: Session):
        self.db = db
        self.client = LLMFactory.get_client()
    
    async def process_message(self, project_id: int, theme: str, user_message: str) -> dict:
        conversations = self.db.query(Conversation).filter(
            Conversation.project_id == project_id
        ).order_by(Conversation.created_at).all()
        
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
        
        is_final = any(word in content.lower() for word in ["可以了", "开始生成", "is_final", "确认生成"])
        
        return {
            "content": content,
            "is_final": is_final,
            "final_script": content if is_final else None
        }
