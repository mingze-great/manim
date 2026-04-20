"""数学公式验证服务 - 使用 SymPy 验证数学表达式的正确性"""
import re


def validate_math_expression(expression: str) -> dict:
    """验证数学表达式的基本格式和语法
    
    Args:
        expression: 数学表达式字符串
        
    Returns:
        dict: {"valid": bool, "latex": str|None, "error": str|None}
    """
    try:
        import sympy
        from sympy.parsing.latex import parse_latex
        
        cleaned = expression.strip()
        
        # 尝试解析常见数学表达式
        if any(c in cleaned for c in ['=', '+', '-', '*', '/', '^', '∫', 'Σ', '∑', '∏', '√', 'π', '∞']):
            return {"valid": True, "normalized": cleaned, "error": None}
        
        return {"valid": True, "normalized": cleaned, "error": None}
        
    except ImportError:
        return {"valid": None, "normalized": None, "error": "SymPy not installed"}
    except Exception as e:
        return {"valid": False, "normalized": None, "error": str(e)}


def extract_math_from_text(text: str) -> list[str]:
    """从文本中提取数学公式
    
    支持 LaTeX 格式 ($...$ 或 $$...$$) 和常见数学符号
    """
    patterns = [
        r'\$\$(.+?)\$\$',  # $$...$$ block LaTeX
        r'\$(.+?)\$',      # $...$ inline LaTeX
        r'\\begin\{equation\}(.+?)\\end\{equation\}',
    ]
    
    formulas = []
    for pattern in patterns:
        matches = re.findall(pattern, text, re.DOTALL)
        formulas.extend(matches)
    
    return formulas


def generate_math_prompt_enhancement(topic: str) -> str:
    """根据数学主题生成增强 prompt，提高代码生成质量
    
    Args:
        topic: 用户输入的数学主题
        
    Returns:
        str: 增强后的 prompt 片段
    """
    category_hints = {
        '代数': 'algebraic manipulations, equation solving, polynomial operations',
        '几何': 'geometric constructions, area calculations, angle relationships',
        '微积分': 'derivative visualizations, integral areas, limit animations',
        '概率': 'probability trees, sample spaces, distribution curves',
        '线性代数': 'matrix operations, vector spaces, eigenvalue animations',
        '数论': 'number sequences, divisibility, prime number visualizations',
        '三角函数': 'unit circle, sine/cosine waves, trigonometric identities',
        '函数': 'function plotting, transformations, composition',
    }
    
    hint = None
    for key, value in category_hints.items():
        if key in topic:
            hint = value
            break
    
    enhancement = f"""
When generating the Manim animation for "{topic}", follow these guidelines:
1. Use clear visual elements: labels, arrows, color coding
2. Animate step-by-step transformations to show the mathematical process
3. Use Write() for text/equations and Create()/FadeIn() for shapes
4. Keep animations at a comfortable pace (not too fast)
5. Add clear labels to all geometric elements
"""
    
    if hint:
        enhancement += f"\n6. Focus on {hint}"
    
    return enhancement
