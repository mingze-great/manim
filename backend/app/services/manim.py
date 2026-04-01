from sqlalchemy.orm import Session
from app.utils.llm_factory import LLMFactory

MANIM_SYSTEM_PROMPT = """角色与任务：你是一个精通自媒体爆款文案的创作者，同时也是精通 Python Manim 的数据可视化"导演"。
我需要你根据我提供的新主题，创作具有极强吸引力、情绪共鸣和自我提升感的短句文案。并为每句文案"智能匹配"最适合的动态图形，最后严格填入我提供的代码模板中。

步骤 1：生成文案与匹配图形
请围绕上述主题，为我生成对应数量的内容。要求：
- 标题简短有力。
- 解释正文一针见血、治愈且有力量（严格控制在两行以内，必须使用 \\n 换行）。
- 【核心】 为每个内容选择最匹配的"图形ID"（0, 1, 或 2）：
  - 0 代表"数据点阵"（适合描述：底层逻辑、系统、积累、规则、准备）
  - 1 代表"循环光环"（适合描述：思维认知、闭环、视野、包容、因果）
  - 2 代表"多边形裂变"（适合描述：突破重构、锐利、改变、果断、出击）
- 构思一句震撼且治愈的结尾语。

步骤 2：填入代码模板（严格要求）
请严格复制以下 Python 代码模板，绝不允许修改任何动画逻辑、颜色配置和排版参数。
你只能修改代码中标记了 <<<替换>>> 的 3 个地方：
- INTRO_TITLE 的值（本次视频大标题）。
- models 列表的值。注意格式必须是 3 个元素的元组：("序号. 标题", "正文第一行\\n正文第二行", 图形ID)。
- OUTRO_TEXT 的值（结尾语）。

请直接输出完整的、可直接运行的 Python 代码：

from manim import *


class Dynamic_HUD_Review(Scene):
    def construct(self):
        # --- 1. 核心配置 (严禁修改) ---
        BG_COLOR = "#0D0D12"
        COLORS = ["#00F0FF", "#FF003C", "#FCEE09", "#B026FF", "#00FF66"]
        self.camera.background_color = BG_COLOR


        # ==========================================
        # 文案与调度注入区 (仅修改此处内容)
        # ==========================================
        INTRO_TITLE = "【<<<替换1：视频大标题>>>】"
        
        # 格式：("序号. 标题", "正文第一行\\n正文第二行", 图形ID)
        models = [
            # 【<<<替换2：将生成的文案按此格式填入，数量不限>>>】
            ("01. 示例标题一", "示例正文的第一句话，\\n示例正文的第二句话。", 1),
            ("02. 示例标题二", "示例正文的第一句话，\\n示例正文的第二句话。", 0)
        ]
        
        OUTRO_TEXT = "【<<<替换3：震撼结尾语，可用\\\\n换行>>>】"
        # ==========================================


        # --- 2. 动态图形渲染工厂 (严禁修改) ---
        def get_dynamic_visual(v_type, color):
            if v_type == 0:  # 数据点阵
                mob = VGroup(*[Dot(radius=0.06, color=color) for _ in range(16)])
                mob.arrange_in_grid(4, 4, buff=0.6)
                mob.add_updater(lambda m, dt: m.rotate(dt * 0.3))
                return mob
            elif v_type == 1:  # 循环光环
                mob = VGroup(
                    DashedVMobject(Circle(radius=1.8, color=color), num_dashes=20),
                    Circle(radius=2.4, color=color).set_opacity(0.3)
                )
                mob[0].add_updater(lambda m, dt: m.rotate(dt * 0.5))
                mob[1].add_updater(lambda m, dt: m.rotate(-dt * 0.3))
                return mob
            else:  # 多边形裂变
                mob = VGroup(
                    RegularPolygon(n=3, radius=1.6, color=color),
                    RegularPolygon(n=6, radius=2.2, color=color).set_opacity(0.4)
                )
                mob[0].add_updater(lambda m, dt: m.rotate(-dt * 0.6))
                mob[1].add_updater(lambda m, dt: m.rotate(dt * 0.4))
                return mob


        # --- 3. 动画流 (严禁修改) ---
        title_text = Text(INTRO_TITLE, color=COLORS[0], weight=BOLD).scale(1.5)
        self.play(Write(title_text), run_time=2)
        self.wait(1.5)
        self.play(FadeOut(title_text))


        for i, (title_str, desc_str, v_type) in enumerate(models):
            current_color = COLORS[i % len(COLORS)]
            
            # 左侧文字排版
            title = Text(title_str, color=current_color, weight=BOLD).scale(1.2)
            desc = Text(desc_str, color=WHITE, line_spacing=1.5).scale(0.8)
            text_group = VGroup(title, desc).arrange(DOWN, aligned_edge=LEFT, buff=0.8).to_edge(LEFT, buff=1.5)


            # 右侧动态图形
            visual = get_dynamic_visual(v_type, current_color).to_edge(RIGHT, buff=2.0)


            # 进场
            self.play(
                Write(title), 
                FadeIn(desc, shift=UP*0.3), 
                FadeIn(visual, scale=0.5), 
                run_time=1.5
            )
            self.wait(3.5)
            
            # 退场并清除缓存
            self.play(FadeOut(text_group), FadeOut(visual), run_time=1)
            visual.clear_updaters() 


        # 结尾
        outro = Text(OUTRO_TEXT, color=WHITE, line_spacing=1.5).scale(1.2)
        self.play(FadeIn(outro, shift=UP*0.3))
        self.wait(3.5)
        self.play(FadeOut(outro), run_time=2)
"""


class ManimService:
    def __init__(self, db: Session):
        self.db = db
        self.client = LLMFactory.get_client()
    
    def generate_code_sync(self, script: str) -> str:
        """同步版本的代码生成"""
        import asyncio
        return asyncio.run(self.generate_code(script))
    
    async def generate_code(self, script: str, template_code: str = None, video_title: str = None) -> str:
        """生成Manim代码
        
        Args:
            script: 视频内容脚本
            template_code: 模板代码（可选），如果提供则按模板风格生成
            video_title: 视频标题（可选），将作为视频开头的大标题
        """
        if template_code:
            system_prompt = f"""你是 Manim 动画代码专家。请参考以下模板代码的风格和结构生成新代码：

```python
{template_code}
```

重要要求：
1. 保持模板的动画风格、颜色配置、排版方式
2. 只替换内容部分（标题、文案等）
3. 保持代码结构不变
4. 代码必须语法正确，能通过 Python ast.parse() 检查
5. 参数之间用逗号分隔，如 color=C_CYAN, opacity=0.15（注意逗号后有空格）
6. 不要漏掉逗号或添加多余字符
"""
        else:
            system_prompt = MANIM_SYSTEM_PROMPT
        
        title_instruction = ""
        if video_title:
            title_instruction = f"\n视频标题：「{video_title}」\n请使用这个标题作为视频开头的大标题。\n"
        
        user_message = f"""请根据以下内容生成 Manim 动画代码：
{title_instruction}
{script}

要求：
1. 严格按内容要点数量生成动画
2. 每个要点必须有标题和解释文案
3. 代码必须完整可运行
"""

        content = await self.client.chat(
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_message}
            ],
            temperature=0.7,
            max_tokens=15000
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
        import ast
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
        
        # 自动修复常见语法错误
        code = self._fix_common_syntax_errors(code)
        
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
        
        # 语法验证
        try:
            ast.parse(code)
        except SyntaxError as e:
            warnings.append(f"语法错误: {e.msg} (行 {e.lineno})")
            # 尝试修复
            code = self._try_fix_syntax(code, e)
            try:
                ast.parse(code)
                warnings.append("语法错误已自动修复")
            except:
                warnings.append("无法自动修复语法错误，请检查代码")
        
        return code, warnings
    
    def _fix_common_syntax_errors(self, code: str) -> str:
        """修复常见的语法拼写错误"""
        import re
        
        # 修复参数分隔错误：color=X,1 opacity=Y → color=X, opacity=Y
        code = re.sub(r'(\w+)=([^,\s]+),(\d+)\s+(\w+)=', r'\1=\2, \4=', code)
        
        # 修复多余数字：set_fill(color=X, 0.5 opacity=Y) → set_fill(color=X, opacity=Y)
        code = re.sub(r'set_fill\(([^)]+),\s*\d+\s+opacity', r'set_fill(\1, opacity', code)
        
        # 修复缺少逗号：color=X opacity=Y → color=X, opacity=Y
        code = re.sub(r'(\w+)=([^\s,)]+)\s+(\w+)=', r'\1=\2, \3=', code)
        
        # 修复括号内多余空格
        code = re.sub(r'\(\s+', '(', code)
        code = re.sub(r'\s+\)', ')', code)
        
        # 修复字符串拼接错误
        code = re.sub(r'"([^"]*)"\s*\+\s*\d+\s*"([^"]*)"', r'"\1\2"', code)
        
        return code
    
    def _try_fix_syntax(self, code: str, error: SyntaxError) -> str:
        """尝试修复语法错误"""
        lines = code.split('\n')
        if error.lineno and error.lineno <= len(lines):
            line = lines[error.lineno - 1]
            if "invalid syntax" in error.msg:
                line = self._fix_common_syntax_errors(line)
                lines[error.lineno - 1] = line
        return '\n'.join(lines)