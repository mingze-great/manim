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
from app.api import auth, projects, tasks, templates, admin, payment

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
    db.close()
    
    from app.tasks.cleanup import start_scheduler
    start_scheduler()
    print("[Startup] Cleanup scheduler started")

    # OpenClaw 独立 scheduler（AI 热点每日 09:00 推送 + 日程 08:30/22:00/分钟扫描 + 监控 09:15）
    try:
        from app.openclaw import is_enabled as _oc_enabled
        if _oc_enabled():
            from app.openclaw.news import start_scheduler as _oc_start_news
            from app.openclaw.schedule import start_schedule_scheduler as _oc_start_sched
            from app.openclaw.monitor import start_monitor_scheduler as _oc_start_mon
            _oc_start_news()
            _oc_start_sched()
            _oc_start_mon()
    except Exception as _e:
        print(f"[openclaw] scheduler 启动失败（不影响主平台）: {type(_e).__name__}: {_e}")

    yield

    from app.tasks.cleanup import shutdown_scheduler
    shutdown_scheduler()
    print("[Shutdown] Cleanup scheduler stopped")

    try:
        from app.openclaw.news import shutdown_scheduler as _oc_stop_news
        from app.openclaw.schedule import shutdown_schedule_scheduler as _oc_stop_sched
        from app.openclaw.monitor import shutdown_monitor_scheduler as _oc_stop_mon
        _oc_stop_news()
        _oc_stop_sched()
        _oc_stop_mon()
    except Exception:
        pass


app = FastAPI(title="Manim Video Platform API", version="2.0.0", lifespan=lifespan)

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

# OpenClaw 独立模块（可选）—— OPENCLAW_ENABLED=true 时才挂载
try:
    from app.openclaw import router as openclaw_router, is_enabled as openclaw_enabled
    if openclaw_enabled():
        app.include_router(openclaw_router, prefix="/api")
        print("[openclaw] 模块已启用，路由挂载在 /api/openclaw/*")
except Exception as e:
    print(f"[openclaw] 模块加载失败（不影响主平台）: {type(e).__name__}: {e}")

# 语音助手「小曼」（可选）—— VOICE_ENABLED != false 时挂载
try:
    from app.voice import router as voice_router, is_enabled as voice_enabled
    if voice_enabled():
        app.include_router(voice_router, prefix="/api")
        print("[voice] 语音助手模块已启用，路由挂载在 /api/voice/*")
except Exception as e:
    print(f"[voice] 模块加载失败（不影响主平台）: {type(e).__name__}: {e}")


@app.get("/")
def root():
    return {"message": "Manim Video Platform API", "version": "2.0.0"}


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
