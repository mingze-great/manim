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
    
    def _fix_unclosed_strings(self, code: str) -> str:
        """修复未闭合的字符串"""
        import re
        
        lines = code.split('\n')
        fixed_lines = []
        i = 0
        
        while i < len(lines):
            line = lines[i]
            
            # 检查是否有未闭合的字符串赋值
            string_match = re.search(r'^(\s*)(\w+)\s*=\s*"([^"]*)$', line)
            if not string_match:
                string_match = re.search(r"^(\s*)(\w+)\s*=\s*'([^']*)$", line)
            
            if string_match and not line.rstrip().endswith('"') and not line.rstrip().endswith("'"):
                # 找到未闭合的字符串
                indent = string_match.group(1)
                var_name = string_match.group(2)
                partial_value = string_match.group(3)
                
                # 收集后续行直到找到闭合引号或到达类/函数定义
                full_value = partial_value
                j = i + 1
                found_close = False
                
                while j < len(lines):
                    next_line = lines[j]
                    if '"' in next_line:
                        # 找到闭合引号
                        close_idx = next_line.index('"')
                        full_value += next_line[:close_idx]
                        found_close = True
                        break
                    elif next_line.strip().startswith('def ') or next_line.strip().startswith('class '):
                        # 到达新的定义，停止
                        break
                    else:
                        full_value += ' ' + next_line.strip()
                    j += 1
                
                # 清理值中的特殊字符
                clean_value = full_value.replace('\n', ' ').replace('"', "'")[:100]
                
                # 添加修复后的行
                fixed_lines.append(f'{indent}{var_name} = "{clean_value}"')
                
                if found_close:
                    i = j + 1
                else:
                    i = j
            else:
                fixed_lines.append(line)
                i += 1
        
        return '\n'.join(fixed_lines)
    
    def _fix_syntax_error(self, code: str, error_msg: str) -> str:
        """尝试修复语法错误"""
        import re
        
        lines = code.split('\n')
        
        # 提取错误行号
        line_match = re.search(r'line (\d+)', error_msg)
        if not line_match:
            return code
        
        error_line = int(line_match.group(1))
        if error_line < 1 or error_line > len(lines):
            return code
        
        # 获取错误行
        line = lines[error_line - 1]
        
        # 处理 unterminated string literal
        if 'unterminated string literal' in error_msg.lower():
            # 检查是否是未闭合的字符串
            # 查找行中的字符串开始
            double_quote_count = line.count('"') - line.count('\\"')
            single_quote_count = line.count("'") - line.count("\\'")
            
            if double_quote_count % 2 != 0:
                # 双引号未闭合
                lines[error_line - 1] = line.rstrip() + '"'
            elif single_quote_count % 2 != 0:
                # 单引号未闭合
                lines[error_line - 1] = line.rstrip() + "'"
            else:
                # 可能是多行字符串问题，尝试删除后续行直到找到闭合
                if 'INTRO_TITLE' in line or 'TITLE_TEXT' in line or 'OUTRO_TEXT' in line:
                    # 这是一个标题/文本赋值，删除多行内容
                    # 找到变量名和值
                    match = re.match(r"(\s*)(\w+)\s*=\s*['\"](.*)", line)
                    if match:
                        indent, var_name, value = match.groups()
                        # 截断到第一个换行或特殊字符
                        clean_value = value.split('\n')[0][:50]  # 限制长度
                        lines[error_line - 1] = f'{indent}{var_name} = "{clean_value}"'
        
        return '\n'.join(lines)
    
    def generate_code_sync(self, script: str) -> str:
        """同步版本的代码生成"""
        import asyncio
        return asyncio.run(self.generate_code(script))
    
    async def generate_code(self, script: str, template_prompt: str = None, model: str = None, user_id: int = None) -> str:
        system_prompt = template_prompt if template_prompt else self._get_default_template_prompt()
        
        user_message = f"""请根据以下主题和内容生成 Manim 动画代码：

{script}

要求：
1. 严格按内容要点数量生成动画
2. 每个要点必须有标题和解释文案
3. 代码必须完整可运行
"""

        response = await self.client.chat(
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_message}
            ],
            model=model or LLMFactory.get_code_model(),
            temperature=0.7,
            max_tokens=30000
        )
        
        # 统计 token 使用量
        tokens_used = 0
        try:
            if hasattr(response, 'usage') and response.usage:
                tokens_used = response.usage.total_tokens
                if user_id:
                    from app.models.user import User
                    user_obj = self.db.query(User).filter(User.id == user_id).first()
                    if user_obj:
                        user_obj.code_token_usage = (user_obj.code_token_usage or 0) + tokens_used
                        self.db.commit()
                        print(f"[DEBUG] Code token usage updated: +{tokens_used}")
        except Exception as e:
            print(f"[DEBUG] Failed to update code token usage: {e}")
        
        # 获取 content
        if hasattr(response, 'choices') and response.choices:
            content = response.choices[0].message.content
        else:
            content = response
        
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
        
        # 语法检查
        try:
            compile(code, '<string>', 'exec')
            print("[DEBUG] Code syntax check passed")
        except SyntaxError as e:
            print(f"[DEBUG] Code syntax error: {e}")
            # 尝试修复语法错误
            code = self._fix_syntax_error(code, str(e))
            # 再次检查
            try:
                compile(code, '<string>', 'exec')
                print("[DEBUG] Code syntax fixed successfully")
            except SyntaxError as e2:
                print(f"[DEBUG] Code syntax still has error after fix: {e2}")
        
        return code
    
    def fix_manim_compatibility(self, code: str) -> str:
        """修复 Manim 代码兼容性问题"""
        import re
        
        # 0. 清理 AI 错误输出的系统提示信息
        code = re.sub(r'<system-reminder>.*?</system-reminder>', '', code, flags=re.DOTALL)
        code = re.sub(r'# Plan Mode.*', '', code)
        code = re.sub(r'## Responsibility.*', '', code)
        code = re.sub(r'## Important.*', '', code)
        code = re.sub(r'CRITICAL:.*', '', code)
        
        # 0.1 提取有效的 Python 代码（从 from manim 或 import 开始）
        code_match = re.search(r'(from manim import.*|import manim.*)', code, re.DOTALL)
        if code_match:
            code = code[code_match.start():]
        
        # 0.2 修复未闭合的字符串（多行文本被放在单行字符串中）
        code = self._fix_unclosed_strings(code)
        
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
        code = re.sub(r'Rectangle\s*\(\s*([\d.]+)\s*,\s*([\d.]+)\s*,\s*(\w+)\s*\)', r'Rectangle(width=\1, height=\2, color=\3)', code)
        
        # 4.1 修复 Line 构造函数参数
        # Line(start, end, C_XXX) -> Line(start, end, color=C_XXX)
        # 只匹配第三个参数是颜色变量（C_开头）的情况
        code = re.sub(
            r'Line\(([^,]+),\s*([^,]+),\s*(C_[A-Z]+)\s*(\)|,)',
            r'Line(\1, \2, color=\3\4',
            code
        )
        
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


INCREMENTAL_FIX_PROMPT = """你是 Manim 代码修复专家。

## 当前代码
```python
{current_code}
```

## 错误信息
```
{error_message}
```

## 修复要求
**只输出需要修改的部分，不要输出完整代码！**

## 输出格式（严格遵守）
```
## 错误位置
行 X-Y（或 行 X）

## 原代码
```python
需要修改的原代码
```

## 修复后代码
```python
修复后的代码
```

## 修复说明
简要说明修复内容
```

## 注意
- 精确定位错误行
- 只输出需要修改的那几行
- 保持代码缩进一致
"""


def parse_and_apply_fix(original_code: str, ai_response: str) -> tuple[str, str]:
    """解析AI响应并应用修复，返回 (修复后代码, 修复说明)"""
    import re
    
    lines = original_code.split('\n')
    
    # 解析行号
    line_match = re.search(r'行\s*(\d+)(?:\s*[-~至]\s*(\d+))?', ai_response)
    if not line_match:
        raise ValueError("无法解析错误位置")
    
    start_line = int(line_match.group(1))
    end_line = int(line_match.group(2)) if line_match.group(2) else start_line
    
    if start_line < 1 or start_line > len(lines):
        raise ValueError(f"行号超出范围: {start_line}")
    
    # 提取修复后代码
    code_match = re.search(r'## 修复后代码\s*```python\s*(.*?)\s*```', ai_response, re.DOTALL)
    if not code_match:
        raise ValueError("无法解析修复代码")
    
    fixed_code_block = code_match.group(1).strip()
    fixed_lines = fixed_code_block.split('\n')
    
    # 替换指定行
    lines[start_line - 1:end_line] = fixed_lines
    
    # 提取修复说明
    desc_match = re.search(r'## 修复说明\s*(.+?)(?=##|$)', ai_response, re.DOTALL)
    fix_desc = desc_match.group(1).strip() if desc_match else f"已修复第 {start_line} 行"
    
    return '\n'.join(lines), fix_desc


class ManimFixService:
    def __init__(self, db: Session):
        self.db = db
        self.client = LLMFactory.get_client()
    
    async def fix_code_incremental(self, current_code: str, error_message: str, user_id: int = None) -> tuple[str, str]:
        """增量修复代码，返回 (修复后代码, 修复说明)"""
        prompt = INCREMENTAL_FIX_PROMPT.format(
            current_code=current_code,
            error_message=error_message
        )
        
        response = await self.client.chat(
            messages=[
                {"role": "system", "content": "你是 Manim 代码修复专家，只输出需要修改的部分。"},
                {"role": "user", "content": prompt}
            ],
            model=LLMFactory.get_code_model(),
            temperature=0.3,
            max_tokens=2000
        )
        
        # 获取 content
        if hasattr(response, 'choices') and response.choices:
            ai_response = response.choices[0].message.content
        else:
            ai_response = response
        
        # 统计 token
        try:
            if hasattr(response, 'usage') and response.usage:
                tokens = response.usage.total_tokens
                if user_id:
                    from app.models.user import User
                    user_obj = self.db.query(User).filter(User.id == user_id).first()
                    if user_obj:
                        user_obj.code_token_usage = (user_obj.code_token_usage or 0) + tokens
                        self.db.commit()
        except Exception as e:
            print(f"[DEBUG] Failed to update token: {e}")
        
        # 解析并应用修复
        fixed_code, fix_desc = parse_and_apply_fix(current_code, ai_response)
        
        # 应用兼容性修复
        manim_service = ManimService(self.db)
        fixed_code = manim_service.fix_manim_compatibility(fixed_code)
        
        return fixed_code, fix_desc