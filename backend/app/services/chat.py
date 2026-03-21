import json
from sqlalchemy.orm import Session

from app.models.project import Conversation, Project
from app.utils.llm_factory import LLMFactory

SYSTEM_PROMPT = """你是一个专业的动画内容策划专家。

## 你的任务
根据用户给定的视频主题，直接生成完整的视频内容脚本，包括各个要点的详细内容。

## 工作流程（重要）
1. 用户输入主题后，**直接生成完整内容**，不要询问用户要补充什么
2. 根据主题自己扩展3-5个要点，生成完整内容
3. 列出内容后，**自动确认**，不需要再问用户是否满意
4. 只有当用户明确要求调整某个部分时，才进行修改

## 输出格式要求
请用结构化格式输出，结尾必须包含下一步指引：

【视频内容】

### 第1点：[标题]
- 内容：[完整文字内容，30-80字，充实有内涵]
- 动态图：[描述动画效果]

### 第2点：[标题]
- 内容：[完整文字内容]
- 动态图：[描述动画效果]

...（以此类推）

---

💡 **下一步**：如果你对以上内容满意，请输入「满意」，我将为你生成视频代码和预览。

## 重要规则
1. **不要询问用户补充信息**，直接生成
2. 内容要充实，每个要点30-80字
3. 动态图描述要具体可执行
4. 生成内容后，在结尾添加「下一步」指引
5. 当用户说"可以"、"满意"、"开始生成"、"确认"时，直接设置 is_final=true 并生成代码
6. 如果用户要求调整某部分，只修改指定内容，不要重新生成全部
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
        
        # 检查是否确认生成
        confirm_keywords = ["满意", "可以了", "开始生成", "确认生成", "好的", "开始吧"]
        user_confirmed = any(keyword in user_message for keyword in confirm_keywords)
        
        # 如果用户确认，使用之前生成的完整内容
        if user_confirmed and project.final_script:
            # 用户确认，保存状态
            project.status = "chatting_completed"
            self.db.commit()
            
            return {
                "content": f"✅ 内容已确认！\n\n{project.final_script}\n\n⏳ 现在点击下方「生成代码和视频」按钮开始生成。",
                "is_final": True,
                "final_script": project.final_script
            }
        
        # 正常对话流程 - AI生成内容后自动保存为草稿
        content = await self.client.chat(
            messages=messages,
            temperature=0.7,
            max_tokens=3000
        )
        
        # 如果对话已经有内容了，保存为最终脚本（第一轮对话后自动生成）
        if not project.final_script and len(conversations) == 0:
            project.final_script = content
            self.db.commit()
            return {
                "content": content,
                "is_final": False,
                "final_script": content
            }
        
        # 后续对话中，如果AI说"确认"则更新final_script
        is_final = any(keyword in content for keyword in confirm_keywords)
        if is_final:
            project.final_script = content
            self.db.commit()
        
        return {
            "content": content,
            "is_final": is_final,
            "final_script": content if is_final else project.final_script
        }
    
    async def stream_process_message(self, project_id: int, theme: str, user_message: str):
        """流式处理消息 - 返回 SSE 生成器"""
        print(f"[DEBUG] stream_process_message called: project_id={project_id}, theme={theme}, message={user_message[:50]}...")
        
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
        
        confirm_keywords = ["满意", "可以了", "开始生成", "确认生成", "好的", "开始吧"]
        user_confirmed = any(keyword in user_message for keyword in confirm_keywords)
        
        if user_confirmed and project.final_script:
            project.status = "chatting_completed"
            self.db.commit()
            
            yield {
                "type": "final",
                "content": f"✅ 内容已确认！\n\n{project.final_script}\n\n⏳ 现在点击下方「生成代码和视频」按钮开始生成。",
                "is_final": True,
                "final_script": project.final_script
            }
            return
        
        content = ""
        reasoning_content = ""
        
        try:
            print(f"[DEBUG] Calling stream_chat with {len(messages)} messages")
            response = await self.client.stream_chat(
                messages=messages,
                temperature=0.7,
                max_tokens=3000
            )
            print(f"[DEBUG] Got response, starting iteration")
            
            async for chunk in response:
                delta = chunk.choices[0].delta
                
                # 只有 DeepSeek 支持 reasoning_content
                reasoning = getattr(delta, 'reasoning_content', None)
                if reasoning:
                    reasoning_content += reasoning
                    yield {
                        "type": "reasoning",
                        "content": reasoning
                    }
                
                if delta.content:
                    content += delta.content
                    yield {
                        "type": "content",
                        "content": delta.content
                    }
            
            print(f"[DEBUG] Stream finished, content length: {len(content)}")
            
            is_first_response = len(conversations) == 0
            if is_first_response and content:
                project.final_script = content
                self.db.commit()
                yield {
                    "type": "done",
                    "content": content,
                    "is_final": False,
                    "final_script": content
                }
            else:
                is_final = any(keyword in content for keyword in confirm_keywords)
                if is_final:
                    project.final_script = content
                    self.db.commit()
                yield {
                    "type": "done",
                    "content": content,
                    "is_final": is_final,
                    "final_script": content if is_final else project.final_script
                }
                
        except Exception as e:
            print(f"[ERROR] Exception in stream_process_message: {type(e).__name__}: {e}")
            import traceback
            traceback.print_exc()
            yield {
                "type": "error",
                "error": str(e)
            }
