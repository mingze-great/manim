import os
import subprocess
import tempfile
import uuid
import asyncio
import concurrent.futures
import re
import shutil
import sys
from datetime import datetime

from app.config import get_settings
from app.database import SessionLocal
from app.models.project import Project
from app.models.task import Task
from app.services.manim import ManimService

settings = get_settings()


def get_manim_path() -> str:
    if sys.platform == "win32":
        possible_paths = [
            os.path.join(os.environ.get("LOCALAPPDATA", ""), "Programs", "Python", "Python311", "Scripts", "manim.exe"),
            os.path.join(os.environ.get("LOCALAPPDATA", ""), "Programs", "Python", "Python310", "Scripts", "manim.exe"),
            "manim",
        ]
        for path in possible_paths:
            if os.path.exists(path):
                return path
        return "manim"
    else:
        return "/opt/miniconda3/envs/manim311/bin/manim"


def update_task_progress(task_id: int, progress: int, status: str = None, video_url: str = None, error_message: str = None, log: str = None):
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


def run_async_code_gen(script_val, template_id, code_ref_val):
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    try:
        db = SessionLocal()
        manim_service = ManimService(db)
        result = loop.run_until_complete(
            asyncio.wait_for(
                manim_service.generate_code(script_val, template_id, code_ref_val),
                timeout=120
            )
        )
        db.close()
        return result
    finally:
        loop.close()


def render_video_task(task_id: int, project_id: int, template_id: int = None, custom_code: str = None):
    db = SessionLocal()
    try:
        project = db.query(Project).filter(Project.id == project_id).first()
        if not project:
            update_task_progress(task_id, 0, "failed", error_message="Project not found")
            return
        
        update_task_progress(task_id, 5, "processing", log="🚀 开始生成视频...\n")
        
        try:
            update_task_progress(task_id, 10, "processing", log="📝 正在生成 Manim 代码...\n")
            
            script_val = str(project.final_script) if project.final_script is not None else ""
            code_ref_val = custom_code or (str(project.custom_code) if project.custom_code is not None else "")
            
            with concurrent.futures.ThreadPoolExecutor(max_workers=1) as executor:
                future = executor.submit(run_async_code_gen, script_val, template_id, code_ref_val)
                try:
                    manim_code = future.result(timeout=180)
                except concurrent.futures.TimeoutError:
                    update_task_progress(task_id, 20, "failed", error_message="Code generation timeout", log="❌ 代码生成超时！\n")
                    return
            
            project.manim_code = manim_code
            db.commit()
            update_task_progress(task_id, 20, "processing", log=f"✅ 代码生成完成 (长度: {len(manim_code)})\n")
        except Exception as e:
            import traceback
            traceback.print_exc()
            update_task_progress(task_id, 20, "failed", error_message=f"Generate code error: {str(e)}", log=f"❌ 生成代码失败: {e}\n")
            return
        
        update_task_progress(task_id, 25, "processing", log="🎬 准备渲染...\n")
        
        with tempfile.TemporaryDirectory() as temp_dir:
            scene_name = "Scene"
            if manim_code:
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
            
            try:
                compile(code_content, '<string>', 'exec')
            except SyntaxError as e:
                update_task_progress(task_id, 50, "failed", error_message=f"Syntax error: {str(e)}", log=f"❌ 代码语法错误: {e}\n")
                return
            
            manim_file = os.path.join(temp_dir, "scene.py")
            with open(manim_file, "w", encoding="utf-8") as f:
                f.write(code_content)
            
            update_task_progress(task_id, 30, "processing", log=f"📁 保存代码到: {manim_file}\n")
            
            manim_path = get_manim_path()
            
            if sys.platform == "win32":
                manim_check = shutil.which(manim_path) or (os.path.exists(manim_path) and manim_path)
                if not manim_check:
                    update_task_progress(task_id, 50, "failed", error_message="Manim not found", log="❌ Manim 未找到！请运行: pip install manim\n")
                    return
            elif not os.path.exists(manim_path):
                update_task_progress(task_id, 50, "failed", error_message="Manim not found", log="❌ Manim 未找到！\n")
                return
            
            update_task_progress(task_id, 35, "processing", log=f"🎥 Manim 路径: {manim_path}\n")
            
            cmd = [
                manim_path,
                "-ql",
                "--disable_caching",
                "--media_dir", temp_dir,
                "-o", "video",
                manim_file,
                scene_name
            ]
            
            update_task_progress(task_id, 40, "processing", log=f"⚡ 开始渲染 (高质量模式)...\n命令: {' '.join(cmd)}\n\n")
            
            try:
                process = subprocess.Popen(
                    cmd,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.STDOUT,
                    text=True,
                    bufsize=1
                )
                
                # 使用 communicate 替代逐行读取，避免死锁
                try:
                    output, _ = process.communicate(timeout=600)
                    
                    # 输出日志
                    for line in output.strip().split('\n'):
                        if line:
                            update_task_progress(task_id, 40, "processing", log=f"{line}\n")
                            print(f"[Task {task_id}] {line}")
                    
                    if process.returncode != 0:
                        update_task_progress(task_id, 80, "failed", error_message="Render failed", log=f"❌ 渲染失败 (code: {process.returncode})\n")
                        return
                        
                except subprocess.TimeoutExpired:
                    process.kill()
                    process.wait()  # 确保进程完全终止
                    update_task_progress(task_id, 80, "failed", error_message="Render timeout", log="❌ 渲染超时！\n")
                    return
                except Exception as e:
                    process.kill()
                    process.wait()
                    update_task_progress(task_id, 80, "failed", error_message=f"Render error: {str(e)}", log=f"❌ 渲染异常: {e}\n")
                    return
            except Exception as e:
                update_task_progress(task_id, 80, "failed", error_message=f"Process error: {str(e)}", log=f"❌ 进程异常: {e}\n")
                return
            
            update_task_progress(task_id, 75, "processing", log="🎉 渲染完成！\n")
            
            video_files = []
            for root, dirs, files in os.walk(temp_dir):
                for file in files:
                    if file.endswith(".mp4"):
                        video_files.append(os.path.join(root, file))
            
            if video_files:
                video_path = video_files[0]
                
                backend_dir = os.path.dirname(os.path.dirname(os.path.dirname(__file__)))
                videos_dir = os.path.join(backend_dir, "videos")
                os.makedirs(videos_dir, exist_ok=True)
                
                video_filename = f"{project_id}_{uuid.uuid4().hex[:8]}.mp4"
                local_video_path = os.path.join(videos_dir, video_filename)
                
                import shutil
                shutil.move(video_path, local_video_path)
                update_task_progress(task_id, 90, "processing", log=f"💾 视频保存: {video_filename}\n")
                
                video_url = f"/api/videos/{video_filename}"
                project.status = "completed"
                db.commit()
                update_task_progress(task_id, 100, "completed", video_url=video_url, log="✅ 任务完成！\n")
            else:
                update_task_progress(task_id, 80, "failed", error_message="No MP4 file found", log="❌ 未找到视频文件！\n")
    
    except Exception as e:
        import traceback
        traceback.print_exc()
        update_task_progress(task_id, 0, "failed", error_message=str(e), log=f"❌ 任务异常: {e}\n")
    finally:
        db.close()
