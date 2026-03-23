from sqlalchemy.orm import Session
from app.utils.llm_factory import LLMFactory

MANIM_SYSTEM_PROMPT = """角色设定：你是一个精通 Python 和 Manim (Community 版) 的数据可视化与动画专家，同时精通自媒体文案的情绪调动与视觉表达。你擅长制作具有"呼吸感"、"治愈感"和"情绪共鸣"的高质量视频。

任务目标：
请帮我编写一个完整的 Manim Python 脚本（类名为 Mindset_Healing_Video）。

视觉与风格要求（严格遵守）：

1. 画面比例：16:9 横屏（默认 1920x1080）。
2. 主题风格：极简、深邃、治愈。强调画面的"呼吸感"和高级的"留白"。
3. 配色方案：
   - 背景色：深邃夜空蓝 #1A1A24（通过 config.background_color 设置）
   - 标题与高亮色：香槟金 #D4AF37
   - 正文说明色：柔和的米白色 #F5F5F5
   - 装饰点缀色：暗珊瑚红 #E07A5F
4. 字体：CN_FONT = "Microsoft YaHei"

动画结构与逻辑要求（严格遵守）：

开场 (Intro)：
- 屏幕中央极其缓慢淡入（FadeIn, run_time=2.5）本次视频的核心主题。
- 主题缩小并上移后，下方缓缓平铺伸展出一条香槟金色的极细装饰线。

主体循环 (Main Loop)：
- 使用 for 循环遍历文案列表。
- 排版：标题在上方（香槟金），解释在下方（米白），必须增加行间距 (line_spacing=1.8) 以提升呼吸感，整体组合居中偏下。不加任何边框。
- 进场：极其舒缓。标题像写信一样逐字浮现（Write），正文随后如雾气般慢慢淡入且轻微上浮（FadeIn(shift=UP*0.15)）。
- 停留：每个画面强制 self.wait(3.5)，给足观众阅读和共鸣的时间。
- 退场：像记忆消散一样，整体缓慢原地淡出（FadeOut，run_time=1.5），不要使用滑动退场。

结尾 (Outro)：
- 屏幕中央缓慢浮现一句与本次主题高度相关的治愈系结尾语。
- 整个画面最终慢慢暗下。

技术约束：
1. 必须输出完整、没有省略号、可直接运行的代码
2. 严格按用户提供的主题和内容要点数量生成
3. 只用 2D 动画
4. 兼容最新的 Manim Community 版本
5. 必须包含 from manim import *
6. 代码用 ```python 包裹
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