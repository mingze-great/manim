from fastapi import FastAPI, Request, Depends
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse
from contextlib import asynccontextmanager
import os
import pathlib
import re
import time
from collections import defaultdict
from datetime import datetime

from app.config import get_settings
from app.database import engine, Base
from app.api import auth, projects, tasks, templates, admin, payment, monitoring, internal, video_topics, articles, articles_stream

settings = get_settings()

request_counts = defaultdict(int)
request_times = defaultdict(list)
start_time = time.time()


@asynccontextmanager
async def lifespan(app: FastAPI):
    from sqlalchemy import text
    from app.database import engine, SessionLocal
    from app.models.template import Template
    from app.models.user import User
    from app.models.subscription import Order, Subscription
    
    Base.metadata.create_all(bind=engine)
    
    with engine.connect() as conn:
        result = conn.execute(text("PRAGMA table_info(templates)"))
        columns = [row[1] for row in result.fetchall()]
        
        if 'is_active' not in columns:
            conn.execute(text("ALTER TABLE templates ADD COLUMN is_active BOOLEAN DEFAULT 1"))
            conn.commit()
            print("Added is_active column to templates")
        
        if 'updated_at' not in columns:
            conn.execute(text("ALTER TABLE templates ADD COLUMN updated_at DATETIME"))
            conn.commit()
            print("Added updated_at column to templates")
        
        if 'prompt' not in columns:
            conn.execute(text("ALTER TABLE templates ADD COLUMN prompt TEXT"))
            conn.commit()
            print("Added prompt column to templates")
        
        if 'example_video_url' not in columns:
            conn.execute(text("ALTER TABLE templates ADD COLUMN example_video_url VARCHAR(500)"))
            conn.commit()
            print("Added example_video_url column to templates")
        
        if 'is_visible' not in columns:
            conn.execute(text("ALTER TABLE templates ADD COLUMN is_visible BOOLEAN DEFAULT 1"))
            conn.commit()
            print("Added is_visible column to templates")

        result = conn.execute(text("PRAGMA table_info(projects)"))
        project_columns = [row[1] for row in result.fetchall()]

        if 'module_type' not in project_columns:
            conn.execute(text("ALTER TABLE projects ADD COLUMN module_type VARCHAR(20) DEFAULT 'manim'"))
            conn.commit()
            print("Added module_type column to projects")

        if 'storyboard_count' not in project_columns:
            conn.execute(text("ALTER TABLE projects ADD COLUMN storyboard_count INTEGER DEFAULT 3"))
            conn.commit()
            print("Added storyboard_count column to projects")

        if 'aspect_ratio' not in project_columns:
            conn.execute(text("ALTER TABLE projects ADD COLUMN aspect_ratio VARCHAR(10) DEFAULT '16:9'"))
            conn.commit()
            print("Added aspect_ratio column to projects")

        if 'voice_source' not in project_columns:
            conn.execute(text("ALTER TABLE projects ADD COLUMN voice_source VARCHAR(20) DEFAULT 'ai'"))
            conn.commit()
            print("Added voice_source column to projects")

        if 'voice_file_path' not in project_columns:
            conn.execute(text("ALTER TABLE projects ADD COLUMN voice_file_path VARCHAR(500)"))
            conn.commit()
            print("Added voice_file_path column to projects")

        if 'voice_duration' not in project_columns:
            conn.execute(text("ALTER TABLE projects ADD COLUMN voice_duration INTEGER"))
            conn.commit()
            print("Added voice_duration column to projects")

        if 'tts_provider' not in project_columns:
            conn.execute(text("ALTER TABLE projects ADD COLUMN tts_provider VARCHAR(30) DEFAULT 'dashscope_cosyvoice'"))
            conn.commit()
            print("Added tts_provider column to projects")

        if 'tts_voice' not in project_columns:
            conn.execute(text("ALTER TABLE projects ADD COLUMN tts_voice VARCHAR(80) DEFAULT 'longshuo_v3'"))
            conn.commit()
            print("Added tts_voice column to projects")

        if 'tts_rate' not in project_columns:
            conn.execute(text("ALTER TABLE projects ADD COLUMN tts_rate VARCHAR(20) DEFAULT '+0%'"))
            conn.commit()
            print("Added tts_rate column to projects")

        if 'style_reference_image_path' not in project_columns:
            conn.execute(text("ALTER TABLE projects ADD COLUMN style_reference_image_path VARCHAR(500)"))
            conn.commit()
            print("Added style_reference_image_path column to projects")

        if 'style_reference_notes' not in project_columns:
            conn.execute(text("ALTER TABLE projects ADD COLUMN style_reference_notes TEXT"))
            conn.commit()
            print("Added style_reference_notes column to projects")

        if 'style_reference_profile' not in project_columns:
            conn.execute(text("ALTER TABLE projects ADD COLUMN style_reference_profile TEXT"))
            conn.commit()
            print("Added style_reference_profile column to projects")

        if 'preview_image_asset_json' not in project_columns:
            conn.execute(text("ALTER TABLE projects ADD COLUMN preview_image_asset_json TEXT"))
            conn.commit()
            print("Added preview_image_asset_json column to projects")

        if 'preview_regen_count' not in project_columns:
            conn.execute(text("ALTER TABLE projects ADD COLUMN preview_regen_count INTEGER DEFAULT 0"))
            conn.commit()
            print("Added preview_regen_count column to projects")

        if 'quota_consumed' not in project_columns:
            conn.execute(text("ALTER TABLE projects ADD COLUMN quota_consumed INTEGER DEFAULT 0"))
            conn.commit()
            print("Added quota_consumed column to projects")

        result = conn.execute(text("PRAGMA table_info(users)"))
        user_columns = [row[1] for row in result.fetchall()]
        if 'module_permissions_json' not in user_columns:
            conn.execute(text("ALTER TABLE users ADD COLUMN module_permissions_json TEXT"))
            conn.commit()
            print("Added module_permissions_json column to users")
        if 'custom_voices_json' not in user_columns:
            conn.execute(text("ALTER TABLE users ADD COLUMN custom_voices_json TEXT"))
            conn.commit()
            print("Added custom_voices_json column to users")

        if 'generation_mode' not in project_columns:
            conn.execute(text("ALTER TABLE projects ADD COLUMN generation_mode VARCHAR(20) DEFAULT 'one_click'"))
            conn.commit()
            print("Added generation_mode column to projects")

        if 'storyboard_json' not in project_columns:
            conn.execute(text("ALTER TABLE projects ADD COLUMN storyboard_json TEXT"))
            conn.commit()
            print("Added storyboard_json column to projects")

        if 'image_assets_json' not in project_columns:
            conn.execute(text("ALTER TABLE projects ADD COLUMN image_assets_json TEXT"))
            conn.commit()
            print("Added image_assets_json column to projects")

        if 'generation_flags' not in project_columns:
            conn.execute(text("ALTER TABLE projects ADD COLUMN generation_flags TEXT"))
            conn.commit()
            print("Added generation_flags column to projects")

        result = conn.execute(text("PRAGMA table_info(tasks)"))
        task_columns = [row[1] for row in result.fetchall()]

        if 'task_type' not in task_columns:
            conn.execute(text("ALTER TABLE tasks ADD COLUMN task_type VARCHAR(50) DEFAULT 'manim_render'"))
            conn.commit()
            print("Added task_type column to tasks")

        result = conn.execute(text("PRAGMA table_info(articles)"))
        article_columns = [row[1] for row in result.fetchall()] if result is not None else []

        if article_columns:
            if 'category' not in article_columns:
                conn.execute(text("ALTER TABLE articles ADD COLUMN category VARCHAR(50) DEFAULT '生活'"))
                conn.commit()
                print("Added category column to articles")
            if 'title' not in article_columns:
                conn.execute(text("ALTER TABLE articles ADD COLUMN title VARCHAR(200)"))
                conn.commit()
                print("Added title column to articles")
            if 'outline' not in article_columns:
                conn.execute(text("ALTER TABLE articles ADD COLUMN outline TEXT"))
                conn.commit()
                print("Added outline column to articles")
            if 'content_html' not in article_columns:
                conn.execute(text("ALTER TABLE articles ADD COLUMN content_html TEXT"))
                conn.commit()
                print("Added content_html column to articles")
            if 'content_text' not in article_columns:
                conn.execute(text("ALTER TABLE articles ADD COLUMN content_text TEXT"))
                conn.commit()
                print("Added content_text column to articles")
            if 'images' not in article_columns:
                conn.execute(text("ALTER TABLE articles ADD COLUMN images TEXT"))
                conn.commit()
                print("Added images column to articles")
            if 'status' not in article_columns:
                conn.execute(text("ALTER TABLE articles ADD COLUMN status VARCHAR(20) DEFAULT 'draft'"))
                conn.commit()
                print("Added status column to articles")
            if 'word_count' not in article_columns:
                conn.execute(text("ALTER TABLE articles ADD COLUMN word_count INTEGER DEFAULT 0"))
                conn.commit()
                print("Added word_count column to articles")
            if 'updated_at' not in article_columns:
                conn.execute(text("ALTER TABLE articles ADD COLUMN updated_at DATETIME"))
                conn.commit()
                print("Added updated_at column to articles")
            if 'quota_consumed' not in article_columns:
                conn.execute(text("ALTER TABLE articles ADD COLUMN quota_consumed INTEGER DEFAULT 0"))
                conn.commit()
                print("Added quota_consumed column to articles")

        result = conn.execute(text("PRAGMA table_info(article_categories)"))
        article_category_columns = [row[1] for row in result.fetchall()] if result is not None else []

        if article_category_columns:
            if 'visual_style' not in article_category_columns:
                conn.execute(text("ALTER TABLE article_categories ADD COLUMN visual_style VARCHAR(200)"))
                conn.commit()
                print("Added visual_style column to article_categories")
            if 'emotion_tone' not in article_category_columns:
                conn.execute(text("ALTER TABLE article_categories ADD COLUMN emotion_tone VARCHAR(200)"))
                conn.commit()
                print("Added emotion_tone column to article_categories")
            if 'color_palette' not in article_category_columns:
                conn.execute(text("ALTER TABLE article_categories ADD COLUMN color_palette VARCHAR(200)"))
                conn.commit()
                print("Added color_palette column to article_categories")
        
        result = conn.execute(text("SELECT name FROM sqlite_master WHERE type='table' AND name='user_module_permissions'"))
        if not result.fetchone():
            conn.execute(text("""
                CREATE TABLE user_module_permissions (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id INTEGER NOT NULL,
                    module_key VARCHAR(20) NOT NULL,
                    enabled BOOLEAN DEFAULT 1,
                    quota_limit INTEGER DEFAULT 0,
                    quota_used INTEGER DEFAULT 0,
                    period VARCHAR(20) DEFAULT 'daily',
                    last_reset_at DATETIME,
                    expires_at DATETIME,
                    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (user_id) REFERENCES users(id),
                    UNIQUE(user_id, module_key)
                )
            """))
            conn.commit()
            print("Created user_module_permissions table")
    
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
    
    admin_email = os.getenv("ADMIN_EMAIL")
    if admin_email:
        admin_user = db.query(User).filter(User.email == admin_email).first()
        if admin_user and not admin_user.is_admin:
            admin_user.is_admin = True
            db.commit()
    
    db.commit()

    try:
        from app.utils.init_article_categories import init_article_categories
        init_article_categories()
    except Exception as exc:
        print(f"[Startup] Init article categories skipped: {exc}")
    db.close()
    
    from app.tasks.cleanup import start_scheduler
    start_scheduler()
    print("[Startup] Cleanup scheduler started")
    
    yield
    
    from app.tasks.cleanup import shutdown_scheduler
    shutdown_scheduler()
    print("[Shutdown] Cleanup scheduler stopped")


app = FastAPI(title="思维可视化内容平台 API", version="2.0.0", lifespan=lifespan)

from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded

limiter = Limiter(key_func=get_remote_address)
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

origins = settings.CORS_ORIGINS.split(",") if settings.CORS_ORIGINS else ["*"]
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
app.include_router(admin.router, prefix="/api")
app.include_router(payment.router, prefix="/api")
app.include_router(monitoring.router, prefix="/api")
app.include_router(internal.router, prefix="/api")
app.include_router(video_topics.router, prefix="/api")
app.include_router(articles.router, prefix="/api")
app.include_router(articles_stream.router, prefix="/api")


@app.get("/")
def root():
    return {"message": "思维可视化内容平台 API", "version": "2.0.0"}


@app.middleware("http")
async def log_requests(request: Request, call_next):
    start = time.time()
    path = request.url.path
    
    if not path.startswith("/health") and not path.startswith("/api/videos"):
        print(f"[{datetime.now().isoformat()}] {request.method} {path}")
    
    response = await call_next(request)
    
    process_time = time.time() - start
    request_counts[path] += 1
    request_times[path].append(process_time)
    
    if process_time > 1.0:
        print(f"[SLOW] {request.method} {path} took {process_time:.2f}s")
    
    return response


@app.get("/health")
def health():
    uptime = time.time() - start_time
    memory_mb = 0
    try:
        import resource
        memory_mb = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss / 1024
    except:
        pass
    
    return {
        "status": "healthy",
        "version": "2.0.0",
        "uptime_seconds": round(uptime),
        "memory_mb": round(memory_mb, 2)
    }


@app.get("/metrics")
def metrics():
    uptime = time.time() - start_time
    
    avg_times = {}
    for path, times in request_times.items():
        if times:
            avg_times[path] = round(sum(times) / len(times), 4)
    
    top_endpoints = sorted(request_counts.items(), key=lambda x: x[1], reverse=True)[:10]
    
    return JSONResponse({
        "uptime_seconds": round(uptime),
        "total_requests": sum(request_counts.values()),
        "requests_by_endpoint": dict(request_counts),
        "top_endpoints": [{"path": p, "count": c} for p, c in top_endpoints],
        "avg_response_times": avg_times,
        "timestamp": datetime.now().isoformat()
    })


@app.get("/api/videos/{filename}")
def download_video(
    filename: str,
    current_user = Depends(lambda: None)
):
    safe_filename = pathlib.Path(filename).name
    
    if not re.match(r'^[\w\-\.]+\.mp4$', safe_filename):
        from fastapi.responses import JSONResponse
        return JSONResponse({"error": "Invalid filename"}, status_code=400)
    
    videos_dir = pathlib.Path(__file__).parent.parent / "videos"
    video_path = videos_dir / safe_filename
    
    if not video_path.exists():
        from fastapi.responses import JSONResponse
        return JSONResponse({"error": "Video not found"}, status_code=404)
    
    if not video_path.is_file():
        from fastapi.responses import JSONResponse
        return JSONResponse({"error": "Not a file"}, status_code=400)
    
    return FileResponse(video_path, media_type="video/mp4", filename=safe_filename)


@app.get("/api/videos/template_examples/{filename}")
def download_template_example_video(filename: str):
    safe_filename = pathlib.Path(filename).name
    
    if not re.match(r'^[\w\-\.]+\.mp4$', safe_filename):
        from fastapi.responses import JSONResponse
        return JSONResponse({"error": "Invalid filename"}, status_code=400)
    
    videos_dir = pathlib.Path(__file__).parent / "videos" / "template_examples"
    video_path = videos_dir / safe_filename
    
    if not video_path.exists():
        from fastapi.responses import JSONResponse
        return JSONResponse({"error": "Video not found"}, status_code=404)
    
    if not video_path.is_file():
        from fastapi.responses import JSONResponse
        return JSONResponse({"error": "Not a file"}, status_code=400)
    
    return FileResponse(video_path, media_type="video/mp4", filename=safe_filename)


@app.get("/api/stickman-images/{filename}")
def download_stickman_image(filename: str):
    safe_filename = pathlib.Path(filename).name
    if not re.match(r'^[\w\-\.]+\.(png|jpg|jpeg|webp)$', safe_filename):
        return JSONResponse({"error": "Invalid filename"}, status_code=400)

    uploads_dir = pathlib.Path(__file__).parent.parent / "uploads" / "stickman_images"
    candidates = list(uploads_dir.glob(f"**/{safe_filename}"))
    if not candidates:
        return JSONResponse({"error": "Image not found"}, status_code=404)

    return FileResponse(candidates[0], media_type="image/png", filename=safe_filename)


@app.get("/api/style-reference-images/{filename}")
def download_style_reference_image(filename: str):
    safe_filename = pathlib.Path(filename).name
    if not re.match(r'^[\w\-\.]+\.(png|jpg|jpeg|webp)$', safe_filename):
        return JSONResponse({"error": "Invalid filename"}, status_code=400)

    uploads_dir = pathlib.Path(__file__).parent.parent / "uploads" / "style_references"
    candidates = list(uploads_dir.glob(f"**/{safe_filename}"))
    if not candidates:
        return JSONResponse({"error": "Image not found"}, status_code=404)

    return FileResponse(candidates[0], media_type="image/png", filename=safe_filename)


@app.get("/api/article-images/{filename}")
def download_article_image(filename: str):
    safe_filename = pathlib.Path(filename).name
    if not re.match(r'^[\w\-\.]+\.(png|jpg|jpeg|webp)$', safe_filename):
        return JSONResponse({"error": "Invalid filename"}, status_code=400)

    uploads_dir = pathlib.Path(__file__).parent.parent / "uploads" / "article_images"
    image_path = uploads_dir / safe_filename
    if not image_path.exists() or not image_path.is_file():
        return JSONResponse({"error": "Image not found"}, status_code=404)

    return FileResponse(image_path, media_type="image/png", filename=safe_filename)
