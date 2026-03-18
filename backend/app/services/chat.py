import json
from sqlalchemy.orm import Session

from app.models.project import Conversation
from app.utils.llm_factory import LLMFactory

SYSTEM_PROMPT = """你是一个专业的数学动画视频脚本策划专家。
你的任务是根据用户给定的视频主题，通过多轮对话帮助用户完善视频脚本。

## 输出格式要求
请始终输出以下JSON格式：
{
    "scene": "场景名称",
    "description": "画面描述",
    "animation": "动画效果说明",
    "duration": "预估时长(秒)",
    "script": "旁白台词",
    "is_final": false,
    "final_script": null
}

## 视频脚本结构
一个完整的视频应该包含多个场景，每个场景包括：
1. 场景名称：简洁明了
2. 画面描述：详细说明要展示的数学内容、图形、图表等
3. 动画效果：说明元素如何运动、变换
4. 时长：建议5-15秒
5. 旁白：配合画面的讲解台词

## 对话策略
1. 首次响应：分析主题，提出脚本框架，询问用户是否满意或有修改意见
2. 后续轮次：根据用户反馈优化脚本细节
3. 当用户确认"满意"或"可以"或"开始生成"时，输出最终脚本并设置is_final为true，同时将完整脚本放入final_script

## 注意事项
- 保持数学内容准确
- 动画效果要考虑Manim实现可行性
- 考虑视频节奏，避免单一动画过长
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
        
        # 添加文本-only说明以防止触发多模态处理
        text_only_prefix = "重要提示：此任务基于纯文本输入。请勿处理或期望任何图像输入。仅根据文本描述生成内容。\n\n"
        
        content = await self.client.chat(
            messages=messages,
            temperature=0.7,
            max_tokens=2000
        )
        
        try:
            result = json.loads(content)
            return {
                "content": json.dumps(result, ensure_ascii=False, indent=2),
                "is_final": result.get("is_final", False),
                "final_script": result.get("final_script") if result.get("is_final") else None
            }
        except json.JSONDecodeError:
            return {
                "content": content,
                "is_final": False,
                "final_script": None
            }
