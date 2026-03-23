# 默认模板代码
DEFAULT_TEMPLATES = [
    {
        "name": "基础动画",
        "category": "通用",
        "description": "最基本的Manim动画模板，包含文字和图形动画",
        "code": '''from manim import *

class BasicAnimation(Scene):
    def construct(self):
        # 创建标题
        title = Text("欢迎来到AI视频").scale(0.8)
        self.play(Write(title))
        self.wait(1)
        
        self.play(FadeOut(title))
        
        # 创建圆形和方形
        circle = Circle(radius=1, color=BLUE)
        square = Square(side_length=2, color=RED)
        
        self.play(Create(circle))
        self.wait(1)
        
        self.play(Transform(circle, square))
        self.wait(1)
        
        # 文字演示
        text = Text("AI生成动画").scale(0.6)
        self.play(ReplacementTransform(circle, text))
        self.wait(2)
''',
        "is_system": True  
    },
    {
        "name": "数学公式",
        "category": "教育",
        "description": "演示数学公式的动画效果",
        "code": '''from manim import *

class MathFormula(Scene):
    def construct(self):
        # 展示勾股定理
        formula = MathTex("a^2 + b^2 = c^2").scale(1.5)
        self.play(Write(formula))
        self.wait(2)
        
        # 创建直角三角形
        triangle = Polygon(
            np.array([-2, -1, 0]),
            np.array([2, -1, 0]), 
            np.array([2, 2, 0]),
            color=YELLOW,
            fill_opacity=0.2
        )
        
        a_label = Tex("a").next_to(triangle, DOWN, buff=0.2)
        b_label = Tex("b").next_to(triangle, RIGHT, buff=0.2)
        c_label = Tex("c").next_to(triangle.get_center(), UP, buff=0.2).shift(RIGHT*0.5 + UP*0.5)
        
        self.play(Transform(formula, triangle))
        self.play(
            Write(a_label),
            Write(b_label), 
            Write(c_label)
        )
        self.wait(3)
        
        # 面积演示
        squares = VGroup()
        a_square = Square(side_length=0.8, color=GREEN).move_to(np.array([-1.6, -1.4, 0]))
        b_square = Square(side_length=1.3, color=PURPLE).move_to(np.array([2.65, 0.15, 0]))
        c_square = Square(side_length=1.5, color=ORANGE).move_to(np.array([0.7, 1.2, 0]))
        
        a2 = Tex("$a^2$").move_to(a_square.get_center())
        b2 = Tex("$b^2$").move_to(b_square.get_center())
        c2 = Tex("$c^2$").move_to(c_square.get_center())
        
        self.play(
            FadeIn(a_square), FadeIn(a2),
            FadeIn(b_square), FadeIn(b2),
            FadeIn(c_square), FadeIn(c2)
        )
        self.wait(3)
''',
        "is_system": True
    },
    {
        "name": "数据动画",
        "category": "商业",
        "description": "展示柱状图等数据图表的动态效果",
        "code": '''from manim import *

class DataAnimation(Scene):
    def construct(self):
        # 创建坐标轴
        axes = Axes(
            x_range=[0, 5, 1],
            y_range=[0, 10, 2],
            axis_config={"color": WHITE},
            x_axis_config={"numbers_to_include": [1, 2, 3, 4]},
            y_axis_config={"numbers_to_include": [2, 4, 6, 8]},
        ).add_coordinates()
        
        # 添加标签
        x_label = axes.get_x_axis_label("月份")
        y_label = axes.get_y_axis_label("销量")
        
        chart_title = Title("月度销售数据")
        
        self.play(Create(axes), run_time=2)
        self.play(Write(x_label), Write(y_label))
        self.play(Write(chart_title))
        self.wait(1)
        
        # 创建柱状图数据
        bars_data = [3, 7, 5, 8, 6]
        colors = [BLUE, GREEN, YELLOW, RED, PURPLE]
        
        bars = VGroup()
        for i, (value, color) in enumerate(zip(bars_data, colors)):
            bar = Rectangle(
                width=0.6,
                height=value,
                color=color,
                fill_opacity=0.8
            ).move_to(axes.coords_to_point(i + 1, value / 2))
            
            # 添加数值标签
            value_label = Text(str(value)).scale(0.4).next_to(bar, UP)
            
            bars.add(VGroup(bar, value_label))
        
        # 动画添加柱状图
        for i, bar_group in enumerate(bars):
            bar, label = bar_group
            self.play(Create(bar), Write(label), run_time=0.8)
        
        self.wait(2)
        
        # 添加趋势线
        trend_points = [(1, 3), (2, 7), (3, 5), (4, 8), (5, 6)]
        trend_line = VMobject()
        trend_line.set_points_smoothly([
            axes.coords_to_point(x, y) 
            for x, y in trend_points
        ]).set_color(RED)
        
        self.play(Create(trend_line), run_time=2)
        self.wait(3)
        
        # 结束
        self.play(FadeOut(axes), FadeOut(bars), FadeOut(trend_line))
        conclusion = Text("感谢观看！").scale(1.2)
        self.play(Write(conclusion))
        self.wait(2)
''',
        "is_system": True
    },
    {
        "name": "思维导图",
        "category": "教育", 
        "description": "创建概念关系图和思维导图动画",
        "code": '''from manim import *

class MindMap(Scene):
    def construct(self):
        # 中心主题
        center_circle = Circle(radius=0.8, color=GOLD, fill_opacity=1).set_fill(YELLOW)
        center_text = Text("中心主题", font_size=24)
        center_group = VGroup(center_circle, center_text).arrange(DOWN, buff=0.2)
        
        self.play(DrawBorderThenFill(center_circle), Write(center_text))
        self.wait(1)
        
        # 主要分支
        angles = [PI/2, PI/6, -PI/6, -PI/2]  # 上右左下四个方向
        main_topics = ["分支1", "分支2", "分支3", "分支4"]
        main_circles = VGroup()
        main_texts = VGroup()
        lines = VGroup()
        
        for i, (angle, topic) in enumerate(zip(angles, main_topics)):
            # 计算位置
            pos = center_group.get_center() + 2.5 * np.array([np.cos(angle), np.sin(angle), 0])
            
            # 创建圆圈和文本
            circle = Circle(radius=0.5, color=BLUE, fill_opacity=0.8).set_fill(BLUE_A)
            text = Text(topic, font_size=20).scale(0.8)
            group = VGroup(circle, text).move_to(pos)
            
            # 创建连接线
            line = Line(center_group.get_center(), group.get_center(), color=WHITE)
            
            main_circles.add(circle)
            main_texts.add(text)
            lines.add(line)
        
        self.play(
            *(Create(line) for line in lines),
            *(DrawBorderThenFill(circle) for circle in main_circles),
            *(Write(text) for text in main_texts),
            run_time=3
        )
        self.wait(1)
        
        # 添加子分支
        sub_angles = [PI/3, 2*PI/3]  # 用于第一个主分支的子分支
        sub_topics = ["子项1", "子项2"]
        sub_texts = VGroup()
        sub_lines = VGroup()
        
        for i, (angle, topic) in enumerate(zip(sub_angles, sub_topics)):
            # 从第一个主分支延伸
            base_pos = main_circles[0].get_center()
            pos = base_pos + 1.5 * np.array([np.cos(angle-PI/3), np.sin(angle-PI/3), 0])
            
            text = Text(topic, font_size=16).scale(0.6).move_to(pos)
            line = DashedLine(main_circles[0].get_center(), pos, color=GRAY)
            
            sub_texts.add(text)
            sub_lines.add(line)
        
        self.play(
            *(Create(line) for line in sub_lines),
            *(Write(text) for text in sub_texts),
            run_time=2
        )
        self.wait(2)
        
        # 总结
        summary = Text("思维导图完成", font_size=28).to_edge(UP)
        self.play(Write(summary))
        self.wait(2)
''',
        "is_system": True
    },
    {
        "name": "循环动画",
        "category": "通用",
        "description": "适合制作重复播放的循环动画序列",
        "code": '''from manim import *

class LoopAnimation(Scene):
    def construct(self):
        # 创建多个相同元素
        circles = VGroup()
        for i in range(8):
            angle = i * TAU / 8
            pos = np.array([2*np.cos(angle), 2*np.sin(angle), 0])
            circle = Circle(
                radius=0.3,
                color=[RED, GREEN, BLUE, YELLOW][i % 4],
                fill_opacity=0.8
            ).move_to(pos)
            circles.add(circle)
        
        self.play(LaggedStartMap(GrowFromCenter, circles, lag_ratio=0.2))
        self.wait(1)
        
        # 额色变化
        all_colors = [
            RED, GREEN, BLUE, YELLOW, PURPLE, ORANGE, PINK, LIGHT_BROWN
        ]
        
        for j in range(8):
            anims = []
            for i in range(len(circles)):
                target_index = (i + j) % len(all_colors)
                anims.append(circles[i].animate.set_color(all_colors[target_index]))
            self.play(*anims, run_time=0.8)
        
        # 大小循环变化
        original_sizes = [circle.radius for circle in circles]
        sizes = [0.4, 0.35, 0.3, 0.25, 0.2]
        
        for size in sizes * 2:  # 重复两次形成循环
            self.play(
                *[circles[i].animate.set_width(size*2) for i in range(len(circles))],
                run_time=0.5
            )
        
        # 恢复原状
        for i, orig_size in enumerate(original_sizes):
            circles[i].radius = orig_size
            circles[i].scale(orig_size/circles[i].width*2)
        
        # 旋转循环
        self.play(
            Rotate(circles, angle=TAU, about_point=ORIGIN),
            rate_func=rate_functions.linear,
            run_time=4
        )
        
        # 最后聚焦到中心
        self.play(circles.animate.arrange(buff=0.2).center())
        self.wait(2)
''',
        "is_system": True
    }
]


def init_default_templates(db):
    """初始化默认模板"""
    from app.models.template import Template
    
    # 检查是否已存在系统模板
    existing = db.query(Template).filter(Template.is_system == True).count()
    if existing > 0:
        print(f"已有 {existing} 个系统模板，跳过初始化")
        return
    
    print("正在初始化默认系统模板...")
    for template_data in DEFAULT_TEMPLATES:
        template = Template(
            name=template_data["name"],
            category=template_data["category"],
            description=template_data["description"],
            code=template_data["code"],
            is_system=True,
            usage_count=0,
            is_active=True
        )
        db.add(template)
    
    db.commit()
    print(f"成功添加 {len(DEFAULT_TEMPLATES)} 个系统模板")