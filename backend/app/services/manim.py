from sqlalchemy.orm import Session
from app.utils.llm_factory import LLMFactory
from app.models.template import Template


class ManimService:
    def __init__(self, db: Session):
        self.db = db
        self.client = LLMFactory.get_client()
    
    def _get_default_template_prompt(self) -> str:
        """获取默认模板（ID=1）的prompt"""
        template = self.db.query(Template).filter(Template.id == 1).first()
        if template and template.prompt:
            return template.prompt
        return ""
    
    def generate_code_sync(self, script: str) -> str:
        """同步版本的代码生成"""
        import asyncio
        return asyncio.run(self.generate_code(script))
    
    async def generate_code(self, script: str, template_prompt: str = None) -> str:
        system_prompt = template_prompt if template_prompt else self._get_default_template_prompt()
        
        user_message = f"""请根据以下主题和内容生成 Manim 动画代码：

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
            max_tokens=30000
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
        
        # 10. 修复颜色函数 - interpolate_color 需要ManimColor对象
        def replace_interpolate_color(match):
            color1 = match.group(1)
            color2 = match.group(2)
            rest = match.group(3) if match.lastindex >= 3 else ''
            return f'interpolate_color(ManimColor("{color1}"), ManimColor("{color2}"){rest}'
        
        code = re.sub(
            r'interpolate_color\s*\(\s*["\']([^"\']+)["\']\s*,\s*["\']([^"\']+)["\']([^)]*)\)',
            replace_interpolate_color,
            code
        )
        
        # 11. 修复 color_to_rgb, rgb_to_color 等颜色函数
        code = re.sub(
            r'color_to_rgb\s*\(\s*["\']([^"\']+)["\']\s*\)',
            r'color_to_rgb(ManimColor("\1"))',
            code
        )
        code = re.sub(
            r'rgb_to_color\s*\(\s*([^)]+)\s*\)',
            r'rgb_to_color(\1)',
            code
        )
        
        # 12. 修复 average_color 函数
        def replace_average_color(match):
            colors = match.group(1)
            colors_list = re.findall(r'["\']([^"\']+)["\']', colors)
            if colors_list:
                new_colors = ', '.join([f'ManimColor("{c}")' for c in colors_list])
                return f'average_color({new_colors})'
            return match.group(0)
        
        code = re.sub(
            r'average_color\s*\(([^)]+)\)',
            replace_average_color,
            code
        )
        
        # 13. 确保 ManimColor 被导入
        if 'ManimColor' in code and 'from manim import *' in code:
            pass
        elif 'ManimColor' in code:
            if 'from manim import' in code:
                code = code.replace('from manim import', 'from manim import ManimColor, ', 1)
            else:
                code = 'from manim import ManimColor\n' + code
        
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