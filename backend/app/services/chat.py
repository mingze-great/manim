import json
from sqlalchemy.orm import Session

from app.models.project import Conversation, Project
from app.utils.llm_factory import LLMFactory


def detect_language(text: str) -> str:
    """检测文本语言：zh 或 en"""
    if any('一' <= char <= '鿿' for char in text):
        return 'zh'
    return 'en'


SYSTEM_PROMPT_ZH = """你是一个专业的动画内容策划专家。

## 第一步：判断主题类型

根据用户输入的主题，判断属于哪种类型：

### 类型 A：思维可视化（方法论、情绪治愈、自我提升等）
关键词：思维、方法、习惯、心理、情绪、认知、技巧、步骤、原则、真相、觉醒、思维模型...

### 类型 B：数学/科学可视化（公式、定理、物理概念等）
关键词：傅里叶变换、欧拉公式、洛伦兹吸引子、微积分、物理、定理、证明、方程、函数、几何、向量、概率、积分、导数、矩阵...

## 输出格式

### 类型 A 格式：
【视频内容】

### 第 1 点：[标题，8-10字]
- 内容：[30-40字]
- 动态图：[15-20字]

...（以此类推）

### 类型 B 格式：
【核心概念】
[30-40字]

【关键公式】
- [公式1]：[10-20字]
- [公式2]：[10-20字]

【动态演示】
[20-30字]

【视觉亮点】
[15-20字]

## 重要规则
1. 直接输出结果，不要输出思考过程
2. 内容简洁精炼，严格控制在规定字数内
3. 动态图描述要简短具体
4. 不要询问用户，直接生成
"""

SYSTEM_PROMPT_EN = """You are a professional animation content planning expert.

## Step 1: Determine Topic Type

Based on the user's input topic, determine which type it belongs to:

### Type A: Mind Visualization (methodology, emotional healing, self-improvement, etc.)
Keywords: mindset, method, habit, psychology, emotion, cognition, skill, step, principle, truth, awakening, mental model...

### Type B: Math/Science Visualization (formulas, theorems, physics concepts, etc.)
Keywords: Fourier transform, Euler's formula, Lorenz attractor, calculus, physics, theorem, proof, equation, function, geometry, vector, probability, integral, derivative, matrix...

## Output Format

### Type A Format:
【Video Content】

### Point 1: [Title, 40-60 characters]
- Content: [120-180 characters]
- Animation: [60-100 characters]

... (and so on)

### Type B Format:
【Core Concept】
[120-180 characters]

【Key Formulas】
- [Formula 1]: [40-80 characters]
- [Formula 2]: [40-80 characters]

【Dynamic Demonstration】
[80-120 characters]

【Visual Highlight】
[60-100 characters]

## Important Rules
1. Output the result directly, do not output the thinking process
2. Keep content concise and strictly within the specified character limit
3. Keep animation descriptions brief and specific
4. Do not ask the user, generate directly
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

### 颜色函数（重要！）
- 颜色常量直接使用：WHITE, BLUE, YELLOW, GREEN, RED, PURPLE, ORANGE 等
- **interpolate_color 必须使用 ManimColor 对象**：
  ```python
  # 正确写法
  interpolate_color(ManimColor("#FF0000"), ManimColor("#00FF00"), 0.5)
  interpolate_color(RED, BLUE, 0.5)
  
  # 错误写法（会报错）
  interpolate_color("#FF0000", "#00FF00", 0.5)
  ```
- **average_color 也需要 ManimColor 对象**：
  ```python
  average_color(ManimColor(RED), ManimColor(BLUE))
  ```

### 其他兼容性
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

### 2. 颜色函数错误（重要！）
- AttributeError: 'str' object has no attribute 'interpolate'
- **原因**：interpolate_color 需要传 ManimColor 对象，不能传字符串
- **修复方法**：
  ```python
  # 错误
  interpolate_color("#FF0000", "#00FF00", 0.5)
  # 正确
  interpolate_color(ManimColor("#FF0000"), ManimColor("#00FF00"), 0.5)
  # 或使用颜色常量
  interpolate_color(RED, BLUE, 0.5)
  ```
- 同样适用于 average_color 等颜色函数

### 3. 只修复错误行
- 找到错误日志中的行号
- 只修改报错的那一行，其他代码不要动

### 4. Manim 0.20.1 兼容性
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
        
        # 检测语言并选择提示词
        language = detect_language(theme + " " + user_message)
        system_prompt = SYSTEM_PROMPT_ZH if language == 'zh' else SYSTEM_PROMPT_EN_ZH if language == 'zh' else SYSTEM_PROMPT_EN
        
        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": f"视频主题：{theme}"}
        ]
        
        for conv in conversations:
            messages.append({"role": conv.role, "content": conv.content})
        
        messages.append({"role": "user", "content": user_message})
        
        # 检查是否确认生成
        confirm_keywords_zh = ["满意", "可以了", "开始生成", "确认生成", "好的", "开始吧"]
        confirm_keywords_en = ["satisfied", "ok", "confirm", "confirmed", "good", "done", "yes"]
        confirm_keywords = confirm_keywords_zh + confirm_keywords_en
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
            model=LLMFactory.get_chat_model(),
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
        
        # 检测语言并选择提示词
        language = detect_language(theme + " " + user_message)
        system_prompt = SYSTEM_PROMPT_ZH if language == 'zh' else SYSTEM_PROMPT_EN_ZH if language == 'zh' else SYSTEM_PROMPT_EN
        
        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": f"视频主题：{theme}"}
        ]
        
        for conv in conversations:
            messages.append({"role": conv.role, "content": str(conv.content)})
        
        messages.append({"role": "user", "content": user_message})
        
        confirm_keywords_zh = ["满意", "可以了", "开始生成", "确认生成", "好的", "开始吧"]
        confirm_keywords_en = ["satisfied", "ok", "confirm", "confirmed", "good", "done", "yes"]
        confirm_keywords = confirm_keywords_zh + confirm_keywords_en
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
                generated_code = await manim_service.generate_code(
                    project_final_script, 
                    user_id=project.user_id if project else None
                )
                
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
        language = detect_language(theme + " " + user_message)
        system_prompt = SYSTEM_PROMPT_ZH if language == 'zh' else SYSTEM_PROMPT_EN
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
        
        try:
            print(f"[DEBUG] Calling stream_chat with {len(messages)} messages")
            response = await self.client.stream_chat(
                messages=messages,
                model=LLMFactory.get_chat_model(),
                temperature=0.7,
                max_tokens=8000
            )
            print(f"[DEBUG] Got response, starting iteration")
            
            async for chunk in response:
                if not chunk.choices:
                    continue
                
                delta = chunk.choices[0].delta
                
                if delta.content:
                    content += delta.content
                    yield {
                        "type": "content",
                        "content": delta.content
                    }
            
            # 统计 token 使用量
            try:
                if hasattr(chunk, 'usage') and chunk.usage:
                    tokens = chunk.usage.total_tokens
                    if project and project.user_id:
                        user = self.db.query(Project).filter(Project.id == project_id).first()
                        if user:
                            from app.models.user import User
                            user_obj = self.db.query(User).filter(User.id == project.user_id).first()
                            if user_obj:
                                user_obj.chat_token_usage = (user_obj.chat_token_usage or 0) + tokens
                                self.db.commit()
                                print(f"[DEBUG] Token usage updated: +{tokens}")
            except Exception as e:
                print(f"[DEBUG] Failed to update token usage: {e}")
            
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
            # 检测结构化内容 - 包含思维类型和数学/科学类型
            has_structured_content = (
                "【视频内容】" in content or 
                "【Video Content】" in content or 
                "【核心概念】" in content or 
                "【Core Concept】" in content or
                "### 第" in content or 
                "### Point" in content or 
                "### 1" in content
            )
            
            if is_first_response or has_structured_content:
                proj = self.db.query(Project).filter(Project.id == project_id).first()
                if proj:
                    proj.final_script = content
                    self.db.commit()
                result = {
                    "type": "done",
                    "content": content,
                    "is_final": True,
                    "final_script": content
                }
                if extracted_code:
                    result["code_updated"] = True
                    result["updated_code"] = extracted_code
                yield result
            else:
                is_final = any(keyword in content for keyword in confirm_keywords)
                # 检测结构化内容 - 包含思维类型和数学/科学类型
                has_structured_content = (
                    "【视频内容】" in content or 
                    "【Video Content】" in content or 
                    "【核心概念】" in content or 
                    "【Core Concept】" in content or
                    "### 第" in content or 
                    "### Point" in content or 
                    "### 1" in content
                )
                
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
        
        # 检测语言并选择提示词
        language = detect_language(theme + " " + user_message)
        system_prompt = SYSTEM_PROMPT_ZH if language == 'zh' else SYSTEM_PROMPT_EN_ZH if language == 'zh' else SYSTEM_PROMPT_EN
        
        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": f"视频主题：{theme}"}
        ]
        
        messages.extend(conversation_history)
        messages.append({"role": "user", "content": user_message})
        
        confirm_keywords_zh = ["满意", "可以了", "开始生成", "确认生成", "好的", "开始吧"]
        confirm_keywords_en = ["satisfied", "ok", "confirm", "confirmed", "good", "done", "yes"]
        confirm_keywords = confirm_keywords_zh + confirm_keywords_en
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
                model=LLMFactory.get_chat_model(),
                temperature=0.7,
                max_tokens=8000
            )
            
            async for chunk in response:
                if not chunk.choices:
                    continue
                
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
