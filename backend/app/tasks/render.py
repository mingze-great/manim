import os
import subprocess
import tempfile
import uuid
from datetime import datetime
from sqlalchemy.orm import Session

from app.config import get_settings
from app.database import SessionLocal
from app.models.project import Project
from app.models.task import Task
from app.services.manim import ManimService
from app.services.oss import OSSService

settings = get_settings()


def update_task_progress(task_id: int, progress: int, status: str = None, video_url: str = None, error_message: str = None):
    db = SessionLocal()
    try:
        task = db.query(Task).filter(Task.id == task_id).first()
        if task:
            task.progress = progress
            if status:
                task.status = status
            if video_url:
                task.video_url = video_url
            if error_message:
                task.error_message = error_message
            if status == "processing" and not task.started_at:
                task.started_at = datetime.utcnow()
            if status in ["completed", "failed"]:
                task.completed_at = datetime.utcnow()
            db.commit()
    finally:
        db.close()


def render_video_task(task_id: int, project_id: int, template_id: int = None, custom_code: str = None):
    db = SessionLocal()
    try:
        project = db.query(Project).filter(Project.id == project_id).first()
        if not project:
            update_task_progress(task_id, 0, "failed", error_message="Project not found")
            return
        
        update_task_progress(task_id, 10, "processing")
        
        import asyncio
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        
        manim_service = ManimService(db)
        script = project.final_script
        # 优先使用传入的custom_code，否则使用项目的custom_code
        code_ref = custom_code or project.custom_code
        manim_code = loop.run_until_complete(
            manim_service.generate_code(script, template_id, code_ref)
        )
        
        project.manim_code = manim_code
        db.commit()
        
        update_task_progress(task_id, 30, "processing")
        
        with tempfile.TemporaryDirectory() as temp_dir:
            # 从生成的代码中提取类名
            scene_name = "Scene"
            if manim_code:
                import re
                match = re.search(r'class\s+(\w+)\s*\(Scene\)', manim_code)
                if match:
                    scene_name = match.group(1)
            
            code_content = manim_code or f"""from manim import *

class {scene_name}(Scene):
    def construct(self):
        text = Text("Generating Animation...").scale(0.5)
        self.play(Write(text))
        self.wait()
"""
            
            manim_file = os.path.join(temp_dir, "scene.py")
            with open(manim_file, "w", encoding="utf-8") as f:
                f.write(code_content)
            
            output_dir = os.path.join(temp_dir, "output")
            os.makedirs(output_dir, exist_ok=True)
            
            update_task_progress(task_id, 50, "processing")
            
            # 使用 manim 的 -o 指定输出目录
            cmd = [
                "manim",
                "-ql",
                "--disable_caching",
                "--media_dir", temp_dir,
                "-o", "video",
                manim_file,
                scene_name
            ]
            
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True
            )
            
            update_task_progress(task_id, 80, "processing")
            
            # 在 temp_dir 中查找生成的视频
            video_files = []
            for root, dirs, files in os.walk(temp_dir):
                for file in files:
                    if file.endswith(".mp4"):
                        video_files.append(os.path.join(root, file))
            
            if video_files:
                video_path = video_files[0]
                
                # 创建videos目录
                backend_dir = os.path.dirname(os.path.dirname(os.path.dirname(__file__)))
                videos_dir = os.path.join(backend_dir, "videos")
                os.makedirs(videos_dir, exist_ok=True)
                
                video_filename = f"{project_id}_{uuid.uuid4().hex[:8]}.mp4"
                local_video_path = os.path.join(videos_dir, video_filename)
                
                # 复制视频到videos目录
                import shutil
                shutil.copy2(video_path, local_video_path)
                print(f"视频已保存到: {local_video_path}")
                
                # 更新任务为完成，使用本地路径
                video_url = f"/api/videos/{video_filename}"
                project.status = "completed"
                db.commit()
                update_task_progress(task_id, 100, "completed", video_url=video_url)
            else:
                error_output = result.stdout + result.stderr
                print(f"渲染错误: {error_output}")
                update_task_progress(task_id, 80, "failed", error_message=f"Render failed: {error_output[:500]}")
    
    except Exception as e:
        update_task_progress(task_id, 0, "failed", error_message=str(e))
    finally:
        db.close()
