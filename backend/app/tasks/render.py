import os
import subprocess
import tempfile
import uuid
import asyncio
import concurrent.futures
import re
import shutil
import sys
import json
import time
from datetime import datetime

from app.config import get_settings
from app.database import SessionLocal
from app.models.project import Project
from app.models.task import Task
from app.services.manim import ManimService
from app.utils.title_utils import normalize_project_title

settings = get_settings()

RENDER_TOTAL_TIMEOUT = 240
CODE_GENERATION_ASYNC_TIMEOUT = 300
CODE_GENERATION_TOTAL_TIMEOUT = 420
MIN_VALID_VIDEO_DURATION = 2.0
MIN_VALID_VIDEO_SIZE = 200 * 1024

try:
    import redis
    redis_client = redis.from_url(settings.REDIS_URL, decode_responses=True)
except Exception:
    redis_client = None


def publish_progress(task_id: int, data: dict):
    if redis_client:
        try:
            redis_client.publish(f"task:{task_id}:progress", json.dumps(data))
        except Exception:
            pass


def get_manim_command() -> list[str]:
    if sys.platform == "win32":
        possible_paths = [
            os.path.join(os.environ.get("LOCALAPPDATA", ""), "Programs", "Python", "Python311", "Scripts", "manim.exe"),
            os.path.join(os.environ.get("LOCALAPPDATA", ""), "Programs", "Python", "Python310", "Scripts", "manim.exe"),
            "manim",
        ]
        for path in possible_paths:
            if os.path.exists(path):
                return [path]
        return ["manim"]
    else:
        manim_candidates = [
            "/root/miniconda3/envs/manim311/bin/manim",
            "/opt/miniconda3/envs/manim311/bin/manim",
        ]
        for path in manim_candidates:
            if os.path.exists(path):
                return [path]

        python_candidates = [
            "/root/miniconda3/envs/manim311/bin/python3.11",
            "/root/miniconda3/envs/manim311/bin/python",
            "/opt/miniconda3/envs/manim311/bin/python3.11",
            "/opt/miniconda3/envs/manim311/bin/python",
        ]
        for path in python_candidates:
            if os.path.exists(path):
                return [path, "-m", "manim"]

        return ["manim"]


def get_manim_python_command() -> list[str]:
    if sys.platform == "win32":
        return [sys.executable, "-m", "manim"]

    python_candidates = [
        "/root/miniconda3/envs/manim311/bin/python3.11",
        "/root/miniconda3/envs/manim311/bin/python",
        "/opt/miniconda3/envs/manim311/bin/python3.11",
        "/opt/miniconda3/envs/manim311/bin/python",
    ]
    for path in python_candidates:
        if os.path.exists(path):
            return [path, "-m", "manim"]
    return [sys.executable, "-m", "manim"]


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
            if log:
                task.log = (task.log or "") + log
            if status == "processing" and not task.started_at:
                task.started_at = datetime.utcnow()
            if status in ["completed", "failed", "cancelled"]:
                task.completed_at = datetime.utcnow()
            db.commit()
            
            publish_progress(task_id, {
                "progress": progress,
                "status": status or task.status,
                "video_url": video_url,
                "error_message": error_message,
                "log": log,
                "full_log": task.log,
                "timestamp": datetime.utcnow().isoformat()
            })
    finally:
        db.close()


def probe_video_file(video_path: str):
    try:
        result = subprocess.run(
            [
                "ffprobe",
                "-v", "error",
                "-show_entries", "format=duration,size",
                "-of", "default=noprint_wrappers=1",
                video_path,
            ],
            capture_output=True,
            text=True,
            timeout=10,
            check=True,
        )
    except Exception:
        return None

    duration = None
    size = None
    for line in result.stdout.splitlines():
        if line.startswith("duration="):
            try:
                duration = float(line.split("=", 1)[1])
            except ValueError:
                duration = None
        elif line.startswith("size="):
            try:
                size = int(float(line.split("=", 1)[1]))
            except ValueError:
                size = None
    return {"duration": duration, "size": size}


def pick_valid_rendered_video(temp_dir: str):
    candidates = []
    for root, dirs, files in os.walk(temp_dir):
        if "partial_movie_files" in root:
            continue
        for file in files:
            if not file.endswith(".mp4"):
                continue
            path = os.path.join(root, file)
            try:
                stat = os.stat(path)
            except OSError:
                continue
            probe = probe_video_file(path) or {}
            candidates.append({
                "path": path,
                "mtime": stat.st_mtime,
                "size": int(stat.st_size),
                "duration": float(probe.get("duration") or 0.0),
            })

    valid = [
        item for item in candidates
        if item["size"] >= MIN_VALID_VIDEO_SIZE and item["duration"] >= MIN_VALID_VIDEO_DURATION
    ]
    valid.sort(key=lambda item: (item["duration"], item["size"], item["mtime"]), reverse=True)
    return valid[0] if valid else None


def run_async_code_gen(script_val, template_code, video_title=None, reference_code=None, model=None):
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    try:
        db = SessionLocal()
        manim_service = ManimService(db)
        result = loop.run_until_complete(
            asyncio.wait_for(
                manim_service.generate_code(script_val, template_code=template_code, video_title=video_title, model=model, reference_code=reference_code),
                timeout=CODE_GENERATION_ASYNC_TIMEOUT
            )
        )
        db.close()
        return result
    finally:
        try:
            loop.run_until_complete(loop.shutdown_asyncgens())
        except:
            pass
        loop.close()


def _is_math_project(project: Project | None) -> bool:
    if not project:
        return False
    module_type = str(getattr(project, "module_type", "") or "").strip().lower()
    category = str(getattr(project, "category", "") or "").strip().lower()
    return module_type == "math" or category in {"math", "数学可视化"}


def _resolve_math_reference_code(template) -> str:
    if not template:
        return ""
    reference_code = str(template.reference_code or "").strip()
    if reference_code:
        return reference_code
    return str(template.code or "").strip()


def render_video_task(task_id: int, project_id: int, template_id: int = None, custom_code: str = None):
    db = SessionLocal()
    try:
        project = db.query(Project).filter(Project.id == project_id).first()
        if not project:
            update_task_progress(task_id, 0, "failed", error_message="Project not found")
            raise RuntimeError("Project not found")

        def fail_render(error_message: str, log_message: str, progress: int = 80):
            project.status = "failed"
            project.error_message = error_message
            project.video_url = None
            db.commit()
            update_task_progress(task_id, progress, "failed", error_message=error_message, log=log_message)
            raise RuntimeError(error_message)
        
        update_task_progress(task_id, 5, "processing", log="开始渲染视频...\n")
        
        # 确定使用的代码：优先使用 custom_code，其次 project.manim_code，最后生成
        manim_code = None
        
        if custom_code:
            manim_code = custom_code
            update_task_progress(task_id, 10, "processing", log="使用自定义代码\n")
        elif project.manim_code:
            manim_code = project.manim_code
            update_task_progress(task_id, 10, "processing", log=f"使用已生成的代码 (长度: {len(manim_code)})\n")
        else:
            # 需要生成代码
            update_task_progress(task_id, 10, "processing", log="正在生成 Manim 代码...\n")
            
            script_val = str(project.theme) if _is_math_project(project) else (str(project.final_script) if project.final_script is not None else "")
            project_title = normalize_project_title(project.title) or normalize_project_title(project.theme)
            
            # 获取模板的参考代码
            reference_code = None
            template_code = None
            if template_id:
                from app.models.template import Template
                template = db.query(Template).filter(Template.id == template_id).first()
                if template:
                    template_code = template.code
                    reference_code = _resolve_math_reference_code(template) if _is_math_project(project) else template.reference_code
            
            with concurrent.futures.ThreadPoolExecutor(max_workers=1) as executor:
                future = executor.submit(run_async_code_gen, script_val, template_code, project_title, reference_code, None)
                try:
                    manim_code = future.result(timeout=CODE_GENERATION_TOTAL_TIMEOUT)
                except concurrent.futures.TimeoutError:
                    update_task_progress(task_id, 20, "failed", error_message="Script generation timeout", log="脚本生成超时！\n")
                    raise RuntimeError("Code generation timeout")
            
            project.manim_code = manim_code
            db.commit()
            update_task_progress(task_id, 20, "processing", log=f"脚本生成完成 (长度: {len(manim_code)})\n")
        
        if not manim_code:
            update_task_progress(task_id, 0, "failed", error_message="No code to render", log="没有可渲染的代码\n")
            raise RuntimeError("No code to render")
        
        update_task_progress(task_id, 25, "processing", log="准备渲染...\n")
        
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
                update_task_progress(task_id, 50, "failed", error_message=f"Syntax error: {str(e)}", log=f"脚本语法检查未通过: {e}\n")
                raise RuntimeError(f"Syntax error: {str(e)}")
            
            manim_file = os.path.join(temp_dir, "scene.py")
            with open(manim_file, "w", encoding="utf-8") as f:
                f.write(code_content)
            
            update_task_progress(task_id, 30, "processing", log=f"保存代码到: {manim_file}\n")
            
            manim_cmd = get_manim_python_command()
            manim_bin = manim_cmd[0]

            if sys.platform == "win32":
                manim_check = shutil.which(manim_bin) or (os.path.exists(manim_bin) and manim_bin)
                if not manim_check:
                    update_task_progress(task_id, 50, "failed", error_message="Manim not found", log="Manim 未找到！请运行: pip install manim\n")
                    raise RuntimeError("Manim not found")
            elif not shutil.which(manim_bin) and not os.path.exists(manim_bin):
                update_task_progress(task_id, 50, "failed", error_message="Manim not found", log="Manim 未找到！\n")
                raise RuntimeError("Manim not found")
            
            update_task_progress(task_id, 35, "processing", log=f"Manim 命令: {' '.join(manim_cmd)}\n")
            
            cmd = [
                *manim_cmd,
                "-qh",
                "--disable_caching",
                "--media_dir", temp_dir,
                "-o", "video",
                manim_file,
                scene_name
            ]
            
            update_task_progress(task_id, 40, "processing", log=f"开始渲染...\n超时保护: 总超时{RENDER_TOTAL_TIMEOUT}秒\n")
            
            process = None
            start_time = time.time()
            timed_out = False
            
            try:
                process = subprocess.Popen(
                    cmd,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.STDOUT,
                    text=True,
                    bufsize=1
                )
                
                while True:
                    elapsed = time.time() - start_time
                    if elapsed > RENDER_TOTAL_TIMEOUT:
                        update_task_progress(task_id, 80, "processing", log=f"渲染总超时（超过{RENDER_TOTAL_TIMEOUT}秒），强制终止\n")
                        timed_out = True
                        try:
                            process.kill()
                            process.wait()
                        except:
                            pass
                        break
                    
                    try:
                        import select
                        if sys.platform != "win32":
                            ready, _, _ = select.select([process.stdout], [], [], 5.0)
                            if not ready:
                                continue
                        else:
                            import threading
                            line = None
                            result = [None]
                            
                            def read_line():
                                try:
                                    result[0] = process.stdout.readline()
                                except:
                                    result[0] = None
                            
                            thread = threading.Thread(target=read_line)
                            thread.daemon = True
                            thread.start()
                            thread.join(timeout=5.0)
                            
                            if thread.is_alive() or result[0] is None:
                                continue
                            
                            line = result[0]
                            
                        if not line:
                            if process.poll() is not None:
                                break
                            continue
                        
                        line = line.strip()
                        
                        if line:
                            update_task_progress(task_id, 40, "processing", log=f"[{int(elapsed)}s] {line}\n")
                            print(f"[Task {task_id}] {line}")
                            
                    except Exception:
                        continue
                
                if process.poll() is None:
                    process.wait()
                
                if timed_out:
                    fail_render("渲染超时", "渲染超时，任务已判定失败\n")
                
                if process.returncode != 0 and not timed_out:
                    fail_render("渲染失败", f"渲染失败 (code: {process.returncode})\n")
                    
            except Exception as e:
                if process:
                    try:
                        process.kill()
                        process.wait()
                    except:
                        pass
                fail_render("渲染失败", f"渲染异常: {e}\n")
            
            update_task_progress(task_id, 75, "processing", log="渲染完成，正在校验最终视频...\n")

            selected_video = pick_valid_rendered_video(temp_dir)

            if selected_video:
                video_path = selected_video["path"]
                
                backend_dir = os.path.dirname(os.path.dirname(os.path.dirname(__file__)))
                videos_dir = os.path.join(backend_dir, "videos")
                os.makedirs(videos_dir, exist_ok=True)
                
                video_filename = f"{project_id}_{uuid.uuid4().hex[:8]}.mp4"
                local_video_path = os.path.join(videos_dir, video_filename)
                
                shutil.move(video_path, local_video_path)
                elapsed_total = int(time.time() - start_time)
                update_task_progress(task_id, 90, "processing", log=f"视频保存: {video_filename}\n时长: {selected_video['duration']:.2f}秒\n大小: {selected_video['size']} bytes\n总耗时: {elapsed_total}秒\n")
                
                video_url = f"/api/videos/{video_filename}"
                project.video_url = video_url
                project.error_message = None
                project.status = "completed"
                db.commit()
                update_task_progress(task_id, 100, "completed", video_url=video_url, log="任务完成！\n")
            else:
                fail_render("渲染失败", "渲染失败！\n")
    
    except Exception as e:
        import traceback
        traceback.print_exc()
        update_task_progress(task_id, 0, "failed", error_message=str(e), log=f"任务异常: {e}\n")
        raise
    finally:
        db.close()


def generate_code_task(task_id: int, project_id: int, template_id: int = None, model: str = None):
    """后台代码生成任务核心逻辑"""
    db = SessionLocal()
    try:
        project = db.query(Project).filter(Project.id == project_id).first()
        if not project:
            update_task_progress(task_id, 0, "failed", error_message="Project not found")
            return
        
        update_task_progress(task_id, 5, "processing", log="开始生成脚本...\n")
        
        try:
            update_task_progress(task_id, 10, "processing", log="准备生成脚本...\n")
            
            script_val = str(project.theme) if _is_math_project(project) else (str(project.final_script) if project.final_script is not None else "")
            project_title = normalize_project_title(project.title) or normalize_project_title(project.theme)
            
            # 获取模板代码
            template_code = None
            reference_code = None
            if template_id:
                from app.models.template import Template
                template = db.query(Template).filter(Template.id == template_id).first()
                if template:
                    template_code = template.code
                    reference_code = _resolve_math_reference_code(template) if _is_math_project(project) else template.reference_code
                    if reference_code:
                        update_task_progress(task_id, 15, "processing", log=f"使用参考代码模板: {template.name}\n")
                    else:
                        update_task_progress(task_id, 15, "processing", log=f"使用模板: {template.name}\n")
            
            update_task_progress(task_id, 20, "processing", log="正在生成 Manim 代码...\n")
            
            # 使用线程池执行异步代码生成
            with concurrent.futures.ThreadPoolExecutor(max_workers=1) as executor:
                future = executor.submit(run_async_code_gen, script_val, template_code, project_title, reference_code, model)
                
                # 等待完成，更新进度
                progress = 30
                start_time = time.time()
                while not future.done():
                    time.sleep(2)
                    if time.time() - start_time > CODE_GENERATION_TOTAL_TIMEOUT:
                        raise concurrent.futures.TimeoutError()
                    progress = min(progress + 5, 80)
                    update_task_progress(task_id, progress, "processing", log="脚本生成中...\n")
                
                result = future.result(timeout=CODE_GENERATION_TOTAL_TIMEOUT)
            
            if result:
                # 更新项目的 manim_code
                project.manim_code = result
                project.status = "code_generated"
                db.commit()
                
                update_task_progress(task_id, 100, "completed", log="脚本生成完成！\n")
            else:
                update_task_progress(task_id, 0, "failed", error_message="Script generation returned empty result", log="脚本生成失败：返回空结果\n")
        
        except concurrent.futures.TimeoutError:
            update_task_progress(task_id, 0, "failed", error_message="Script generation timeout", log="脚本生成超时\n")
        except Exception as e:
            import traceback
            traceback.print_exc()
            update_task_progress(task_id, 0, "failed", error_message=str(e), log=f"脚本生成异常: {e}\n")
    
    except Exception as e:
        import traceback
        traceback.print_exc()
        update_task_progress(task_id, 0, "failed", error_message=str(e), log=f"任务异常: {e}\n")
    finally:
        db.close()
