from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from contextlib import asynccontextmanager
import os
import pathlib

from app.config import get_settings
from app.database import engine, Base
from app.api import auth, projects, tasks, templates

settings = get_settings()


@asynccontextmanager
async def lifespan(app: FastAPI):
    Base.metadata.create_all(bind=engine)
    from app.models.template import Template
    from app.database import SessionLocal
    
    db = SessionLocal()
    system_templates = [
        {
            "name": "公式展示",
            "description": "标题 + 公式淡入动画，适合开场",
            "category": "intro",
            "code": '''from manim import *

class FormulaScene(Scene):
    def construct(self):
        title = Text("勾股定理").scale(1.5)
        formula = MathTex("a^2 + b^2 = c^2", font_size=72)
        
        self.play(Write(title))
        self.wait()
        self.play(title.animate.shift(UP * 2))
        self.play(Write(formula))
        self.wait()
'''
        },
        {
            "name": "几何证明",
            "description": "图形变换 + 步骤标注，适合证明过程",
            "category": "proof",
            "code": '''from manim import *

class ProofScene(Scene):
    def construct(self):
        square = Square(side_length=3, color=BLUE)
        label = MathTex("a^2").next_to(square, DOWN)
        
        self.play(Create(square))
        self.play(Write(label))
        self.wait()
        
        triangle = Polygon(
            [-1.5, -1.5, 0], [1.5, -1.5, 0], [0, 1.5, 0],
            color=GREEN, fill_opacity=0.3
        )
        self.play(Transform(square, triangle))
        self.wait()
'''
        },
        {
            "name": "函数图像",
            "description": "函数曲线绘制 + 坐标轴",
            "category": "animation",
            "code": '''from manim import *

class FunctionScene(Scene):
    def construct(self):
        axes = Axes(
            x_range=[-3, 3, 1],
            y_range=[-2, 8, 2],
            x_length=6,
            y_length=4,
            axis_config={"include_tip": True}
        )
        
        labels = axes.get_axis_labels(x_label="x", y_label="y")
        
        graph = axes.plot(
            lambda x: x**2,
            color=YELLOW,
            x_range=[-2, 2]
        )
        
        self.play(Create(axes), Write(labels))
        self.play(Create(graph))
        self.wait()
'''
        },
        {
            "name": "定理讲解",
            "description": "分步推导 + 高亮强调",
            "category": "explanation",
            "code": '''from manim import *

class TheoremScene(Scene):
    def construct(self):
        step1 = Text("1. 画三角形", font_size=36).to_edge(UP)
        triangle = Polygon(
            [-2, -1, 0], [2, -1, 0], [0, 1.5, 0],
            color=BLUE
        )
        
        self.play(Write(step1))
        self.play(Create(triangle))
        self.wait()
        
        step2 = Text("2. 标注边长 a, b, c", font_size=36).next_to(step1, DOWN)
        self.play(Write(step2))
        self.wait()
        
        step3 = MathTex("a^2 + b^2 = c^2", font_size=48).to_edge(DOWN)
        self.play(Write(step3))
        self.wait()
'''
        }
    ]
    
    for template_data in system_templates:
        exists = db.query(Template).filter(
            Template.name == template_data["name"],
            Template.is_system == True
        ).first()
        if not exists:
            template = Template(**template_data, is_system=True)
            db.add(template)
    
    db.commit()
    db.close()
    
    yield


app = FastAPI(title="Manim Video Platform API", version="1.0.0", lifespan=lifespan)

origins = settings.CORS_ORIGINS.split(",")
app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth.router, prefix="/api")
app.include_router(projects.router, prefix="/api")
app.include_router(tasks.router, prefix="/api")
app.include_router(templates.router, prefix="/api")


@app.get("/")
def root():
    return {"message": "Manim Video Platform API"}


@app.get("/health")
def health():
    return {"status": "healthy"}


@app.get("/api/videos/{filename}")
def download_video(filename: str):
    """下载本地视频"""
    videos_dir = pathlib.Path(__file__).parent.parent / "videos"
    video_path = videos_dir / filename
    
    if not video_path.exists():
        from fastapi.responses import JSONResponse
        return JSONResponse({"error": "Video not found"}, status_code=404)
    
    return FileResponse(video_path, media_type="video/mp4", filename=filename)
