from sqlalchemy.orm import Session
from app.utils.llm_factory import LLMFactory

MANIM_SYSTEM_PROMPT = """角色与任务：
你是一个精通自媒体爆款文案的创作者，同时也是一个严谨的 Python 程序员。
我需要你根据我提供的新主题，创作治愈、走心、有深度的短句文案，并将这些文案严格填入我提供的 Manim 代码模板中。

步骤 1：生成文案
请围绕用户提供的主题，生成对应数量的内容。要求：
- 标题简短有力。
- 解释正文富有哲理、治愈且有力量（严格控制在两行以内，使用 \\n 换行）。
- 构思一句高度相关的治愈系结尾语。

步骤 2：填入代码模板（严格要求）
请严格复制以下 Python 代码模板，绝不允许修改任何动画逻辑（如 FadeIn, Wait, FadeOut 等）和排版参数。
你只能修改代码中标记了 <<<替换>>> 的三个地方：
- INTRO_TITLE 的值（替换为本次核心主题）。
- models 列表的值（替换为你刚刚生成的文案，注意格式为 ("序号. 标题", "正文第一行\\n正文第二行")）。
- OUTRO_TEXT_CONTENT 的值（替换为你构思的结尾语）。

请输出完整的、可直接运行的 Python 代码：

from manim import *
import random

class Mindset_Healing_Dynamic(Scene):
    def construct(self):
        # --- 颜色与基础配置 (严禁修改) ---
        BG_COLOR = "#1A1A24"       
        CHAMPAGNE_GOLD = "#D4AF37" 
        TEXT_WHITE = "#F5F5F5"     
        ACCENT_COLOR = "#E07A5F"   
        CN_FONT = "Microsoft YaHei" 
        self.camera.background_color = BG_COLOR

        # ==========================================
        # 文案数据注入区 (仅修改此处内容)
        # ==========================================
        INTRO_TITLE = "【<<<替换1：视频大标题>>>】"
        
        models = [
            # 【<<<替换2：将生成的文案按此格式填入，数量不限>>>】
            ("01. 标题一", "这里是正文的第一句话，\\n这里是正文的第二句话。"),
            ("02. 标题二", "这里是正文的第一句话，\\n这里是正文的第二句话。")
        ]
        
        OUTRO_TEXT_CONTENT = "【<<<替换3：治愈系结尾语，可使用\\\\n换行>>>】"
        # ==========================================

        # --- 动态背景粒子 (严禁修改) ---
        particles = VGroup(*[
            Dot(radius=random.uniform(0.01, 0.03), point=[random.uniform(-7, 7), random.uniform(-4, 4), 0], color=TEXT_WHITE, fill_opacity=random.uniform(0.05, 0.2)) for _ in range(150)
        ])
        def update_particles(mob, dt):
            mob.shift(UP * dt * 0.15)
            for p in mob:
                if p.get_center()[1] > 4.5:
                    p.move_to([p.get_center()[0], -4.5, 0])
        particles.add_updater(update_particles)
        self.add(particles)

        # --- 1. 开场动画 (严禁修改) ---
        intro_text = Text(INTRO_TITLE, font=CN_FONT, weight=NORMAL).scale(1.4).set_color(CHAMPAGNE_GOLD)
        self.play(FadeIn(intro_text, shift=UP * 0.3), run_time=2.5)
        self.wait(1.5)
        self.play(intro_text.animate.scale(0.6).to_edge(UP).set_opacity(0.8), run_time=1.5)
        line = Line(LEFT*2, RIGHT*2, color=ACCENT_COLOR).set_width(4).set_opacity(0.6).next_to(intro_text, DOWN, buff=0.3)
        self.play(Create(line), run_time=1.5)
        self.wait(0.5)

        # --- 2. 循环展示动画 (严禁修改代码，它会自动读取 models 列表) ---
        for title_str, desc_str in models:
            title = Text(title_str, font=CN_FONT, color=CHAMPAGNE_GOLD).scale(1.1)
            desc = Text(desc_str, font=CN_FONT, color=TEXT_WHITE, line_spacing=1.8).scale(0.7)
            
            # 修复了 CENTER 报错，使用默认居中
            card_group = VGroup(title, desc).arrange(DOWN, buff=0.8).move_to(ORIGIN).shift(DOWN * 0.3)

            self.play(Write(title), run_time=2)
            self.play(FadeIn(desc, shift=UP * 0.15), run_time=2)
            self.wait(4.0)
            self.play(FadeOut(card_group), run_time=1.5)
            self.wait(0.8)

        # --- 3. 结尾动画 (严禁修改) ---
        self.play(FadeOut(intro_text), FadeOut(line), run_time=1)
        outro_text = Text(OUTRO_TEXT_CONTENT, font=CN_FONT, line_spacing=1.5, color=CHAMPAGNE_GOLD).scale(1.2)
        self.play(FadeIn(outro_text, shift=UP*0.2), run_time=3)
        self.wait(3.5)
        self.play(FadeOut(outro_text), FadeOut(particles), run_time=2)
"""


class ManimService:
    def __init__(self, db: Session):
        self.db = db
        self.client = LLMFactory.get_client()
    
    def generate_code_sync(self, script: str) -> str:
        """同步版本的代码生成"""
        import asyncio
        return asyncio.run(self.generate_code(script))
    
    async def generate_code(self, script: str) -> str:
        user_message = f"""请根据以下主题和内容生成 Manim 动画代码：

{script}

要求：
1. 严格按内容要点数量生成动画
2. 每个要点必须有标题和解释文案
3. 代码必须完整可运行
"""

        content = await self.client.chat(
            messages=[
                {"role": "system", "content": MANIM_SYSTEM_PROMPT},
                {"role": "user", "content": user_message}
            ],
            temperature=0.7,
            max_tokens=8000
        )
        
        if "```python" in content:
            start = content.find("```python") + len("```python")
            end = content.find("```", start)
            if end != -1:
                code = content[start:end].strip()
            else:
                code = content[start:].strip()
        else:
            code = content.strip()
        
        code = self.fix_manim_compatibility(code)
        
        return code
    
    def fix_manim_compatibility(self, code: str) -> str:
        """修复 Manim 代码兼容性问题"""
        import re
        
        # 1. 修复 rate_functions
        code = re.sub(r'\brate_func\s*=\s*reverse_smooth\b', 'rate_func=smooth', code)
        code = re.sub(r'\brate_func\s*=\s*ease_out_expo\b', 'rate_func=rate_functions.ease_out_expo', code)
        code = re.sub(r'\brate_func\s*=\s*rush_into\b', 'rate_func=rate_functions.rush_into', code)
        code = re.sub(r'\brate_func\s*=\s*there_and_back\b', 'rate_func=rate_functions.there_and_back', code)
        
        # 2. 修复方法调用
        code = re.sub(r'\.down\s*\(\)', '.get_bottom()', code)
        code = re.sub(r'\.up\s*\(\)', '.get_top()', code)
        code = re.sub(r'\.left\s*\(\)', '.get_left()', code)
        code = re.sub(r'\.right\s*\(\)', '.get_right()', code)
        code = re.sub(r'\.center\s*\(\)', '.get_center()', code)
        
        # 3. 移除不兼容的 style 参数
        code = re.sub(r',\s*style\s*=\s*\{[^}]*\}', '', code)
        code = re.sub(r',\s*background_line_style\s*=\s*\{[^}]*\}', '', code)
        
        # 4. 修复 API 参数
        code = re.sub(r'Circle\s*\(\s*([\d.]+)\s*,\s*(\w+)\s*\)', r'Circle(radius=\1, color=\2)', code)
        code = re.sub(r'Dot\s*\(\s*([\d.]+)\s*,\s*(\w+)\s*\)', r'Dot(radius=\1, color=\2)', code)
        code = re.sub(r'Square\s*\(\s*([\d.]+)\s*,\s*(\w+)\s*\)', r'Square(side_length=\1, color=\2)', code)
        
        # 5. 修复 Sector 参数
        code = re.sub(r'Sector\s*\(\s*outer_radius\s*=\s*([^,\)]+)', r'Sector(radius=\1', code)
        code = re.sub(r',\s*inner_radius\s*=\s*[^,\)]+', '', code)
        code = re.sub(r'outer_radius\s*=\s*', 'radius=', code)
        
        # 6. 替换外部资源为内置图形
        code = re.sub(r'SVGMobject\s*\(\s*["\']([^"\']+)["\'][^)]*\)', 'Circle(radius=0.5, color=WHITE)', code)
        code = re.sub(r'ImageMobject\s*\(\s*["\'][^"\']+["\']\s*\)', 'Rectangle(width=2, height=1.5, color=BLUE)', code)
        
        # 7. 移除不支持的动画参数
        code = re.sub(r'(FadeOut|FadeIn)\(([^)]+),\s*rotate\s*=\s*[^,)]+', r'\1(\2', code)
        code = re.sub(r'(FadeOut|FadeIn)\(([^)]+),\s*scale\s*=\s*[^,)]+', r'\1(\2', code)
        code = re.sub(r'(FadeOut|FadeIn)\(([^)]+),\s*shift\s*=\s*[^,)]+', r'\1(\2', code)
        
        # 8. GrowArrow 替换为 Create
        code = re.sub(r'GrowArrow\(', 'Create(', code)
        
        # 9. 修复 API 方法调用
        code = code.replace('.point_at_proportion', '.point_from_proportion')
        code = code.replace('.n2p(', '.number_to_point(')
        code = re.sub(r'(\w+)\.length(?!\()', r'\1.get_length()', code)
        
        return code
    
    def validate_code(self, code: str) -> tuple:
        """验证并修复代码，返回 (fixed_code, warnings)"""
        import re
        warnings = []
        
        if not code:
            return code, warnings
        
        code = code.strip()
        
        # 提取代码块
        if "```python" in code:
            start = code.find("```python") + len("```python")
            end = code.find("```", start)
            if end != -1:
                code = code[start:end]
            else:
                code = code[start:]
        
        code = code.strip()
        
        # 确保必要的 import
        if 'from manim import *' not in code and 'import manim' not in code:
            code = 'from manim import *\n\n' + code
            warnings.append("已添加必要的 import 语句")
        
        # 重命名 Scene 类为 SceneName
        scene_match = re.search(r'class\s+(\w+)\s*\(\s*Scene\s*\)', code)
        if scene_match:
            old_name = scene_match.group(1)
            if old_name != 'SceneName':
                code = code.replace(f'class {old_name}(Scene)', 'class SceneName(Scene)')
                warnings.append(f"已将类名 {old_name} 改为 SceneName")
        
        # 调用兼容性修复
        code = self.fix_manim_compatibility(code)
        
        return code, warnings