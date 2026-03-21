from sqlalchemy.orm import Session

from app.models.template import Template
from app.utils.llm_factory import LLMFactory

MANIM_SYSTEM_PROMPT = """你是一个专业的Manim动画代码生成专家。
你的任务是将已确定的视频脚本转换为可执行的Manim Python代码。

## 核心要求
当你看到"## 参考代码"部分时，必须严格遵循该代码的：
1. 整体结构（class定义方式、函数组织）
2. 动画风格（使用的动画类型、过渡效果）
3. 代码模式（常见的代码写法、习惯用法）
4. 配色方案（使用的颜色常量）
5. 注释风格（如果有的话）

**重要：参考代码是你的模板，必须完全遵循其风格！**

## 技术约束
- 使用Manim 0.18.x版本（Manim Community Edition）
- 场景分辨率：1920x1080 (DEFAULT: 1920x1080)
- 使用ManimCE (Manim Community Edition) 语法
- 代码必须可以直接运行

## 代码结构要求
```python
from manim import *

class SceneName(Scene):
    def construct(self):
        # 动画代码
```

## 常用动画模式
- 文字显示：Text(), MathTex()
- 图形绘制：Circle(), Square(), Line(), Polygon()
- 变换：Transform(), ReplacementTransform(), TransformFromCopy()
- 运动：MoveAlongPath(), Rotate(), FadeIn(), FadeOut(), Write()
- 组合：VGroup(), Group()
- 颜色：RED, BLUE, GREEN, YELLOW, WHITE, BLACK等
- 动画：self.play(), self.wait()

## 质量要求
1. 代码语法正确，可直接运行
2. 动画流畅自然
3. 适当添加camera运动增加动感
4. 颜色搭配美观
5. 确保代码在标准配置下可运行
6. **必须完全遵循参考代码的风格！**

请直接输出代码，不要包含解释说明。
"""


class ManimService:
    def __init__(self, db: Session):
        self.db = db
        self.client = LLMFactory.get_client()
    
    def generate_code_sync(self, script: str, template_id: int = None, custom_code: str = None) -> str:
        """同步版本的代码生成"""
        import asyncio
        return asyncio.run(self.generate_code(script, template_id, custom_code))
    
    async def generate_code(self, script: str, template_id: int | None = None, custom_code: str = None) -> str:
        template_code = ""
        if template_id:
            template = self.db.query(Template).filter(Template.id == template_id).first()
            if template:
                template_code = template.code
                template.usage_count += 1
                self.db.commit()
        
        # 添加文本-only说明以防止触发多模态处理
        text_only_prefix = "重要提示：此任务基于纯文本输入。请勿处理或期望任何图像输入。仅根据文本描述生成Manim代码。\n\n"
        
        # 构建参考代码部分
        reference_parts = []
        if custom_code:
            reference_parts.append(f"【用户代码模板】以下代码是你的模板，生成的代码必须完全遵循其风格、结构、动画模式、配色方案：\n```python\n{custom_code}\n```")
        if template_code:
            reference_parts.append(f"【系统模板参考】：\n```python\n{template_code}\n```")
        
        reference_section = "\n\n".join(reference_parts) if reference_parts else "无"
        
        user_message = f"""{text_only_prefix}## 参考代码（必须严格遵循）
{reference_section}

## 视频脚本
{script}

## 任务要求
请严格按照"参考代码"的风格生成Manim代码！要求：
1. 完全复制参考代码的整体结构
2. 使用相同的动画模式和技术
3. 遵循相同的代码风格和习惯
4. 保持一致的配色方案
5. 只替换主题相关的内容（文字、图形等）

请直接输出代码，不要包含任何解释！"""

        content = await self.client.chat(
            messages=[
                {"role": "system", "content": MANIM_SYSTEM_PROMPT},
                {"role": "user", "content": user_message}
            ],
            temperature=0.3,
            max_tokens=4000
        )
        
        if "```python" in content:
            start = content.find("```python") + len("```python")
            end = content.find("```", start)
            code = content[start:end].strip()
        else:
            code = content.strip()
        
        return code
