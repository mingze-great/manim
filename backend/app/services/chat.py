import json
from sqlalchemy.orm import Session

from app.models.project import Conversation, Project
from app.utils.llm_factory import LLMFactory

SYSTEM_PROMPT = """你是一个专业的动画内容策划专家。

## 你的任务
根据用户给定的视频主题，直接生成完整的视频内容脚本，包括各个要点的详细内容。

## 工作流程（重要）
1. 用户输入主题后，**直接生成完整内容**，不要询问用户要补充什么
2. **严格按用户要求的数量生成**：用户说"十大思维"就生成 10 个，说"5 个方法"就生成 5 个
3. 列出内容后，**自动确认**，不需要再问用户是否满意
4. 只有当用户明确要求调整某个部分时，才进行修改

## 输出格式要求
请用结构化格式输出，结尾必须包含下一步指引：

【视频内容】

### 第 1 点：[标题]
- 内容：[完整文字内容，30-80 字，充实有内涵]
- 动态图：[描述动画效果]

### 第 2 点：[标题]
- 内容：[完整文字内容]
- 动态图：[描述动画效果]

...（以此类推，严格按用户要求的数量）

---

💡 **下一步**：如果你对以上内容满意，请输入「满意」，我将为你生成视频代码和预览。

## 重要规则
1. **不要询问用户补充信息**，直接生成
2. **内容数量严格按用户要求**：用户要几个就生成几个，不要擅自减少
3. 内容要充实，每个要点 30-80 字
4. 动态图描述要具体可执行
5. 生成内容后，在结尾添加「下一步」指引
6. 当用户说"可以"、"满意"、"开始生成"、"确认"时，直接设置 is_final=true 并生成代码
7. 如果用户要求调整某部分，只修改指定内容，不要重新生成全部
"""

CODE_GENERATE_PROMPT = """你是 Manim 动画代码专家。

## 用户内容
{final_script}

## 现有代码（如有）
{current_code}

## 技术约束
- Manim 版本：0.20.1
- Python 版本：3.11
- 中文字体：Microsoft YaHei

## 动画要求（必须遵守）
1. **只用 2D 动画**，禁止使用任何 3D 效果（ThreeDScene、Cube、Sphere 等）
2. **简单结构**：标题 + 文字 + 简单图形（圆形、矩形、箭头等）
3. **动画简洁**：FadeIn、Write、Transform 等基础动画即可
4. **代码必须完整**：包含所有 import、完整的 construct 方法、所有内容点

## 必须检查的 import
```python
from manim import *
import random  # 如果使用 random
import numpy as np  # 如果使用 numpy
```

## Manim 0.20.1 兼容
- 使用 Text() 不是 TextMobject()
- 使用 Paragraph() 显示多行文字
- 颜色使用：WHITE, BLUE, YELLOW, GREEN, RED 等

## 输出要求
- **代码必须完整可运行**，不要省略任何部分
- **严格按用户内容要点数量生成**：用户要 10 个就生成 10 个，要 5 个就生成 5 个
- 用 ```python 包裹
- 不要解释，只输出代码
"""

CODE_FIX_PROMPT = """你是 Manim 代码修复专家。

## 当前代码
```python
{current_code}
```

## 错误日志
```
{error_message}
```

## 修复规则

### 1. 先检查 import（最常见错误）
- NameError: name 'xxx' is not defined → 缺少 import
- 常见缺失：`import random`, `import numpy as np`
- 修复时在代码开头添加缺失的 import

### 2. 只修复错误行
- 找到错误日志中的行号
- 只修改报错的那一行，其他代码不要动

### 3. Manim 0.20.1 兼容性
- AttributeError → 检查方法是否存在
- Cube 没有 get_front/get_back/get_top/get_bottom 方法

## 输出
直接输出修复后的完整代码，用 ```python 包裹。
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
        
        # 提取数据，避免会话问题
        project_final_script = str(project.final_script) if project and project.final_script else ""
        
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
        if user_confirmed and project_final_script:
            # 用户确认，保存状态
            proj = self.db.query(Project).filter(Project.id == project_id).first()
            if proj:
                proj.status = "chatting_completed"
                self.db.commit()
            
            return {
                "content": f"✅ 内容已确认！\n\n{project_final_script}\n\n⏳ 现在点击下方「生成代码和视频」按钮开始生成。",
                "is_final": True,
                "final_script": project_final_script
            }
        
        # 正常对话流程 - AI生成内容后自动保存为草稿
        content = await self.client.chat(
            messages=messages,
            temperature=0.7,
            max_tokens=8000
        )
        
        # 如果对话已经有内容了，保存为最终脚本（第一轮对话后自动生成）
        if not project_final_script and len(conversations) == 0:
            proj = self.db.query(Project).filter(Project.id == project_id).first()
            if proj:
                proj.final_script = content
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
    
    async def stream_process_message(
        self, 
        project_id: int, 
        theme: str, 
        user_message: str,
        manim_code: str = None,
        template_code: str = None,
        final_script: str = None
    ):
        """流式处理消息 - 返回 SSE 生成器"""
        print(f"[DEBUG] stream_process_message called: project_id={project_id}, theme={theme}, message={user_message[:50]}...")
        
        conversations = self.db.query(Conversation).filter(
            Conversation.project_id == project_id
        ).order_by(Conversation.created_at).all()
        
        project = self.db.query(Project).filter(Project.id == project_id).first()
        
        # 提取所有需要的数据，避免会话问题
        project_final_script = str(project.final_script) if project.final_script else ""
        project_status = str(project.status) if project.status else "draft"
        
        # 检测用户意图
        code_keywords = ['生成代码', '写代码', '代码', '调整代码', '修改代码', '更新代码']
        fix_keywords = ['修复', '错误', '报错', 'fix', 'error', '问题', '失败']
        
        is_code_request = any(kw in user_message for kw in code_keywords)
        is_fix_request = any(kw in user_message for kw in fix_keywords)
        
        messages = [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": f"视频主题：{theme}"}
        ]
        
        for conv in conversations:
            messages.append({"role": conv.role, "content": str(conv.content)})
        
        messages.append({"role": "user", "content": user_message})
        
        confirm_keywords = ["满意", "可以了", "开始生成", "确认生成", "好的", "开始吧"]
        user_confirmed = any(keyword in user_message for keyword in confirm_keywords)
        
        if user_confirmed and project_final_script:
            project.status = "chatting_completed"
            self.db.commit()
            
            yield {
                "type": "status",
                "content": "⏳ 正在生成代码，请稍候..."
            }
            
            try:
                from app.services.manim import ManimService
                manim_service = ManimService(self.db)
                generated_code = await manim_service.generate_code(project_final_script)
                
                yield {
                    "type": "final",
                    "content": f"✅ 代码生成完成！\n\n```python\n{generated_code[:500]}...\n```\n\n请点击「使用此代码」保存并渲染视频。",
                    "is_final": True,
                    "final_script": project_final_script,
                    "generated_code": generated_code
                }
            except Exception as e:
                yield {
                    "type": "error",
                    "error": f"代码生成失败: {str(e)}"
                }
            return
        
        # 确定使用的 prompt 和消息
        system_prompt = SYSTEM_PROMPT
        user_context = user_message
        
        # 如果是代码生成或修复请求，且有必要的信息
        if (is_code_request or is_fix_request) and (manim_code or final_script):
            if is_fix_request and manim_code:
                system_prompt = CODE_FIX_PROMPT.format(
                    current_code=manim_code,
                    error_message=user_message
                )
                user_context = "请根据以上信息修复代码。"
            elif is_code_request:
                system_prompt = CODE_GENERATE_PROMPT.format(
                    final_script=final_script or project_final_script,
                    current_code=manim_code,
                    template_style=template_code
                )
                user_context = user_message
        
        messages[0] = {"role": "system", "content": system_prompt}
        messages[-1] = {"role": "user", "content": user_context}
        
        content = ""
        reasoning_content = ""
        
        try:
            print(f"[DEBUG] Calling stream_chat with {len(messages)} messages")
            response = await self.client.stream_chat(
                messages=messages,
                temperature=0.7,
                max_tokens=8000
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
            
            # 检测是否包含代码 - 修复正则表达式，匹配各种代码块格式
            extracted_code = None
            if "```python" in content:
                import re
                # 匹配 ```python 开头，``` 结尾，中间所有内容（包括空行）
                code_match = re.search(r'```python\s*(.*?)\s*```', content, re.DOTALL)
                if code_match:
                    extracted_code = code_match.group(1).strip()
                    print(f"[DEBUG] Code extracted, length: {len(extracted_code)}")
                else:
                    print(f"[DEBUG] Failed to extract code from content")
            
            is_first_response = len(conversations) == 0
            has_structured_content = "【视频内容】" in content or "### 第" in content or "### 1" in content
            
            if is_first_response or has_structured_content:
                proj = self.db.query(Project).filter(Project.id == project_id).first()
                if proj:
                    proj.final_script = content
                    self.db.commit()
                result = {
                    "type": "done",
                    "content": content,
                    "is_final": False,
                    "final_script": content
                }
                if extracted_code:
                    result["code_updated"] = True
                    result["updated_code"] = extracted_code
                yield result
            else:
                is_final = any(keyword in content for keyword in confirm_keywords)
                has_structured_content = "【视频内容】" in content or "### 第" in content or "### 1" in content
                
                if is_final or has_structured_content:
                    proj = self.db.query(Project).filter(Project.id == project_id).first()
                    if proj:
                        proj.final_script = content
                        self.db.commit()
                result = {
                    "type": "done",
                    "content": content,
                    "is_final": is_final,
                    "final_script": content if (is_final or has_structured_content) else project_final_script
                }
                if extracted_code:
                    result["code_updated"] = True
                    result["updated_code"] = extracted_code
                yield result
                
        except Exception as e:
            print(f"[ERROR] Exception in stream_process_message: {type(e).__name__}: {e}")
            import traceback
            traceback.print_exc()
            yield {
                "type": "error",
                "error": str(e)
            }
    
    async def stream_process_message_direct(self, project_id: int, theme: str, user_message: str, conversation_history: list, final_script: str = None):
        """直接处理消息流式输出 - 供 projects.py 调用，接受已准备好的对话历史"""
        print(f"[DEBUG] stream_process_message_direct called: project_id={project_id}, message={user_message[:50]}...")
        
        # 提取数据，避免会话问题
        project = self.db.query(Project).filter(Project.id == project_id).first()
        project_final_script = str(project.final_script) if project and project.final_script else ""
        
        messages = [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": f"视频主题：{theme}"}
        ]
        
        messages.extend(conversation_history)
        messages.append({"role": "user", "content": user_message})
        
        confirm_keywords = ["满意", "可以了", "开始生成", "确认生成", "好的", "开始吧"]
        user_confirmed = any(keyword in user_message for keyword in confirm_keywords)
        
        if user_confirmed and final_script:
            proj = self.db.query(Project).filter(Project.id == project_id).first()
            if proj:
                proj.status = "chatting_completed"
                self.db.commit()
            
            yield {
                "type": "final",
                "content": f"✅ 内容已确认！\n\n{final_script}\n\n⏳ 现在点击下方「生成代码和视频」按钮开始生成。",
                "is_final": True,
                "final_script": final_script
            }
            return
        
        content = ""
        reasoning_content = ""
        
        try:
            response = await self.client.stream_chat(
                messages=messages,
                temperature=0.7,
                max_tokens=8000
            )
            
            async for chunk in response:
                delta = chunk.choices[0].delta
                
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
            
            is_first_response = len(conversation_history) == 0
            if is_first_response and content:
                proj = self.db.query(Project).filter(Project.id == project_id).first()
                if proj:
                    proj.final_script = content
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
                    proj = self.db.query(Project).filter(Project.id == project_id).first()
                    if proj:
                        proj.final_script = content
                        self.db.commit()
                yield {
                    "type": "done",
                    "content": content,
                    "is_final": is_final,
                    "final_script": content if is_final else (final_script or project_final_script)
                }
                
        except Exception as e:
            print(f"[ERROR] Exception in stream_process_message_direct: {type(e).__name__}: {e}")
            import traceback
            traceback.print_exc()
            yield {
                "type": "error",
                "error": str(e)
            }
