#!/usr/bin/env python3
import subprocess
import tempfile
import os

# 模板6代码（从数据库中）
template6_code = '''from manim import *
import numpy as np

class TopTenThinking(Scene):
    def construct(self):
        # 创建标题
        title = Text("十大思维模型").scale(0.8)
        title.to_edge(UP)
        self.play(Write(title))
        self.wait()

        # 创建思维模型列表
        models = VGroup(
            Text("1. 第一性原理"),
            Text("2. 逆向思维"),
            Text("3. 系统思维"),
            Text("4. 批判性思维"),
            Text("5. 设计思维"),
            Text("6. 侧向思维"),
            Text("7. 归纳演绎"),
            Text("8. 类比思维"),
            Text("9. 发散思维"),
            Text("10. 收敛思维")
        )

        # 排列模型
        models.arrange(DOWN, aligned_edge=LEFT, buff=0.5)
        models.shift(LEFT * 2)

        # 逐个显示模型
        for model in models:
            self.play(FadeIn(model))
            self.wait(0.5)

        # 创建连接线
        arrows = VGroup()
        for i in range(len(models) - 1):
            arrow = Arrow(
                models[i].get_right(),
                models[i + 1].get_left(),
                color=YELLOW
            )
            arrows.add(arrow)

        self.play(Create(arrows))
        self.wait()

        # 添加装饰
        circle = Circle(radius=2, color=BLUE, fill_opacity=0.1)
        circle.to_edge(RIGHT)
        self.play(Create(circle))

        # 总结文字
        summary = Text("思维模型是思考的工具").scale(0.5)
        summary.move_to(circle)
        self.play(Write(summary))
        self.wait(2)

        # 结束
        self.play(FadeOut(models), FadeOut(arrows), FadeOut(circle), FadeOut(summary))
'''

# 测试修复函数
def fix_manim_compatibility(code):
    import re

    # GrowArrow 只能用于 Arrow，不能用于 Line
    code = re.sub(r'GrowArrow\(', 'Create(', code)

    # 修复 API 参数
    code = re.sub(r'Sector\s*\(\s*outer_radius\s*=\s*([^,\)]+)', r'Sector(radius=\1', code)

    # 修复未定义的颜色常量
    color_replacements = {
        'GREY_BLUE': '#607D8B',
        'GREY_BROWN': '#795548',
        # 其他颜色常量...
    }
    for old_color, new_color in color_replacements.items():
        code = re.sub(rf'={old_color}\b', f'="{new_color}"', code)

    return code

# 修复代码
fixed_code = fix_manim_compatibility(template6_code)

print("=" * 60)
print("测试模板6代码渲染（使用新环境 manim311）")
print("=" * 60)

# 创建临时目录
with tempfile.TemporaryDirectory() as temp_dir:
    # 写入代码文件
    code_file = os.path.join(temp_dir, "test_template6.py")
    with open(code_file, "w", encoding="utf-8") as f:
        f.write(fixed_code)

    print(f"代码文件: {code_file}")
    print(f"修复后代码长度: {len(fixed_code)}")

    # 使用新环境渲染
    manim_path = "/opt/miniconda3/envs/manim311/bin/manim"
    cmd = [
        manim_path,
        "-pqh",  # 高质量 1080p60
        "--disable_caching",
        "--media_dir", temp_dir,
        "-o", "test_template6",
        code_file,
        "TopTenThinking"
    ]

    print(f"\n执行命令: {' '.join(cmd)}")
    print("-" * 60)

    # 执行渲染
    try:
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=300  # 5分钟超时
        )

        print("标准输出:")
        print(result.stdout)

        if result.stderr:
            print("\n标准错误:")
            print(result.stderr)

        print("\n" + "-" * 60)
        print(f"返回码: {result.returncode}")

        # 查找生成的视频文件
        video_files = []
        for root, dirs, files in os.walk(temp_dir):
            for file in files:
                if file.endswith(".mp4"):
                    video_path = os.path.join(root, file)
                    video_files.append((video_path, os.path.getsize(video_path)))

        if video_files:
            print("\n✅ 渲染成功！找到视频文件:")
            for video_path, size in video_files:
                print(f"  - {video_path} ({size / 1024 / 1024:.2f} MB)")
        else:
            print("\n❌ 渲染失败，未找到视频文件")

    except subprocess.TimeoutExpired:
        print("\n❌ 渲染超时（5分钟）")
    except Exception as e:
        print(f"\n❌ 渲染异常: {e}")

print("=" * 60)
