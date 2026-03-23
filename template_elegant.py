from manim import *
import numpy as np
import random

# =======================
# 全局视觉配置 (极简轻颜风)
# =======================
config.pixel_width = 1920
config.pixel_height = 1080
config.frame_rate = 60
config.background_color = "#F8FAFC"
config.frame_width = 16
config.frame_height = 9

# 高级感配色 (深灰主色，莫兰迪强调色)
C_MAIN = "#0F172A"
C_SUB = "#475569"
C_DIM = "#94A3B8"
C_BLUE = "#3B82F6"
C_GREEN = "#10B981"
C_RED = "#EF4444"
C_WARN = "#F59E0B"
C_PURP = "#8B5CF6"

FONTS = ["Microsoft YaHei", "Heiti SC", "sans-serif"]

def get_safe_text(s, size, color=C_MAIN, max_width=6.5, is_bold=True):
    """确保文字渲染稳定，防报错"""
    for font_name in FONTS:
        try:
            t = Text(s, font=font_name, font_size=size, color=color, weight=BOLD if is_bold else NORMAL)
            if t.width > 0.05:
                if t.width > max_width: t.scale(max_width / t.width)
                return t
        except: continue
    return Text(s, font_size=size, color=color).scale_to_fit_width(max_width)

def play_elegant_intro(scene, text_str, color):
    """优雅的入场动画：平滑浮现 + 线条展开"""
    title = get_safe_text(text_str, size=80, color=color, max_width=12)
    line = Line(LEFT, RIGHT, color=color, stroke_width=4).scale(title.width / 2.2).next_to(title, DOWN, buff=0.3)
    
    scene.play(
        FadeIn(title, shift=UP*0.5),
        Create(line),
        run_time=1.5, rate_func=rate_functions.smooth
    )
    scene.wait(0.5)
    
    group = VGroup(title, line)
    scene.play(group.animate.scale(0.4).to_edge(UP, buff=0.4).set_opacity(0.8), run_time=1.2)
    return group


class SceneName(Scene):
    def construct(self):
        top_title = play_elegant_intro(self, "主题标题", C_BLUE)
        
        # 【排版反转】左侧动画，右侧文字
        L_POS = LEFT * 4 + DOWN * 0.5
        R_X = 2.5

        items = [
            ("1. 要点一", "副标题", "描述内容"),
            ("2. 要点二", "副标题", "描述内容"),
            ("3. 要点三", "副标题", "描述内容"),
            ("4. 要点四", "副标题", "描述内容"),
            ("5. 要点五", "副标题", "描述内容"),
        ]
        
        for i, (t, d, s) in enumerate(items):
            t_obj = get_safe_text(t, 65, C_BLUE)
            d_obj = get_safe_text(d, 40, C_SUB, is_bold=False)
            s_obj = get_safe_text(s, 28, C_DIM, is_bold=False)
            
            text_grp = VGroup(t_obj, d_obj, s_obj).arrange(DOWN, aligned_edge=LEFT, buff=0.8)
            text_grp.move_to([R_X, 0, 0])
            
            self.play(FadeIn(text_grp, shift=UP * 0.5), run_time=0.8)
            anim_grp = VGroup()

            if i == 0:
                target = VGroup(*[Circle(radius=r, color=C_BLUE, stroke_width=2) for r in [1.5, 1.0, 0.5]]).move_to(L_POS)
                arrow_wrong = CurvedArrow(L_POS+DOWN*2+RIGHT*2, L_POS+UP*1, color=C_RED, angle=-PI/4)
                arrow_right = CurvedArrow(L_POS+DOWN*2+RIGHT*2, L_POS, color=C_GREEN, angle=-PI/4)
                self.play(Create(target), Create(arrow_wrong))
                self.play(ReplacementTransform(arrow_wrong, arrow_right), target[2].animate.set_fill(C_BLUE, opacity=0.5))
                anim_grp.add(target, arrow_right)
            
            elif i == 1:
                lines = VGroup(*[Line(L_POS+LEFT*2+UP*random.uniform(-1,1), L_POS+RIGHT*2+UP*random.uniform(-1,1), color=C_DIM, stroke_width=2) for _ in range(5)])
                solid = VGroup(*[Line(L_POS+LEFT*2+UP*y, L_POS+RIGHT*2+UP*y, color=C_BLUE, stroke_width=4) for y in np.linspace(-1, 1, 3)])
                self.play(Create(lines))
                self.play(ReplacementTransform(lines, solid), run_time=1.5)
                anim_grp.add(solid)
            
            elif i == 2:
                layers = VGroup(*[RoundedRectangle(corner_radius=0.2, width=w, height=w, color=C_DIM) for w in [3, 2.2, 1.4]]).move_to(L_POS)
                core = Dot(L_POS, color=C_WARN, radius=0.25)
                self.play(DrawBorderThenFill(layers), FadeIn(core, scale=0.5))
                self.play(LaggedStart(*[l.animate.scale(1.1).set_opacity(0) for l in layers], lag_ratio=0.3), core.animate.scale(2).set_color(C_BLUE), run_time=1.5)
                anim_grp.add(layers, core)
            
            elif i == 3:
                dots = VGroup(*[Dot(L_POS + [x, random.uniform(-1.5,1.5), 0], color=C_SUB) for x in np.linspace(-2, 2, 6)])
                curve = FunctionGraph(lambda x: 0.5 * np.sin(2 * x), color=C_BLUE, x_range=[-2, 2]).move_to(L_POS)
                self.play(FadeIn(dots, shift=UP*0.2))
                self.play(Create(curve), *[d.animate.move_to(curve.point_from_proportion((i_d+0.5)/6)).set_color(C_BLUE) for i_d, d in enumerate(dots)], run_time=1.5)
                anim_grp.add(dots, curve)
            
            elif i == 4:
                circle_outline = Circle(radius=1.2, color=C_BLUE, stroke_width=4).move_to(L_POS)
                check = VGroup(Line(LEFT*0.5+UP*0.1, DOWN*0.4, color=C_GREEN, stroke_width=8), 
                               Line(DOWN*0.4, RIGHT*0.6+UP*0.5, color=C_GREEN, stroke_width=8)).move_to(L_POS)
                self.play(Create(circle_outline))
                self.play(Create(check), circle_outline.animate.set_fill(C_BLUE, opacity=0.1), run_time=1.2)
                anim_grp.add(circle_outline, check)

            self.wait(1.2)
            self.play(FadeOut(text_grp, shift=UP*0.3), FadeOut(anim_grp, scale=0.9), run_time=0.6)

        self.play(FadeOut(top_title), Write(get_safe_text("总结语", 55, C_MAIN)), run_time=1.5)
        self.wait(3)