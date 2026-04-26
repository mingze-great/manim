from typing import Annotated, Optional
from fastapi import APIRouter, Depends, HTTPException, Query, Header, BackgroundTasks
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session
import json
import asyncio
import subprocess
import tempfile
import os
import uuid
import re
import shutil
import sys
import time

from app.database import get_db
from app.models.user import User
from app.models.project import Project
from app.models.task import Task
from app.models.template import Template
from app.api.auth import get_current_user
from app.services.manim import ManimService
from app.services.stickman_generator import StickmanGenerator as StickmanGeneratorLegacy
from app.services.stickman_generator_v2 import StickmanGenerator as StickmanGeneratorV2
from app.config import get_settings
from app.utils.cos_storage import cos_storage
from app.tasks.celery_tasks import render_video_celery, generate_code_celery, generate_chat_celery

router = APIRouter(prefix="/tasks", tags=["tasks"])


def _build_stickman_generator(project: Project | None = None):
    if project and str(getattr(project, 'stickman_variant', 'legacy') or 'legacy') == 'v2':
        return StickmanGeneratorV2()
    return StickmanGeneratorLegacy()


def _stickman_variant_label(project: Project | None = None):
    return '优化版' if project and str(getattr(project, 'stickman_variant', 'legacy') or 'legacy') == 'v2' else '经典版'


def _project_query_for_user(db: Session, current_user: User):
    query = db.query(Project)
    if not current_user.is_admin:
        query = query.filter(Project.user_id == current_user.id)
    return query
settings = get_settings()

RENDER_SEMAPHORE = asyncio.Semaphore(4)
CURRENT_RENDERS = 0
OLD_SERVER_SEMAPHORE = asyncio.Semaphore(2)
MAX_TOTAL_RENDERS = 6
RENDER_TOTAL_TIMEOUT = 300
RENDER_NO_OUTPUT_TIMEOUT = 60
MIN_VALID_VIDEO_DURATION = 2.0
MIN_VALID_VIDEO_SIZE = 200 * 1024


def _probe_video_file(video_path: str):
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


def _pick_valid_rendered_video(temp_dir: str):
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
            probe = _probe_video_file(path) or {}
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


def _task_message(task: Task) -> str:
    if task.error_message and task.status in ["failed", "cancelled"]:
        return task.error_message
    if task.log:
        lines = [line.strip() for line in task.log.splitlines() if line.strip()]
        if lines:
            return lines[-1]
    return f"任务{task.status}"


@router.post("/internal/update-video")
async def update_video_url(
    project_id: int,
    video_url: str,
    x_internal_key: str = Header(None)
):
    if x_internal_key != settings.INTERNAL_API_KEY:
        raise HTTPException(status_code=401, detail="Invalid API key")
    
    from app.database import SessionLocal
    db = SessionLocal()
    try:
        project = db.query(Project).filter(Project.id == project_id).first()
        if project:
            project.video_url = video_url
            project.status = "completed"
            db.commit()
            return {"success": True, "message": f"Project {project_id} updated"}
        return {"success": False, "message": "Project not found"}
    finally:
        db.close()


async def try_dispatch_to_old_server(project_id: int, manim_code: str):
    from app.services.render_dispatcher import render_dispatcher
    old_status = await render_dispatcher.check_old_server_status()
    if old_status.get("status") == "healthy":
        try:
            async with OLD_SERVER_SEMAPHORE:
                async for line in render_dispatcher.dispatch_to_old_server(project_id, manim_code):
                    yield line
                return
        except Exception as e:
            print(f"[Dispatch] Failed: {e}")
            yield f"data: {json.dumps({'type': 'error', 'content': f'渲染失败: {str(e)}'})}\n\n"
            return
    yield f"data: {json.dumps({'type': 'error', 'content': '系统繁忙，请稍后再试'})}\n\n"


@router.get("/render-status")
async def get_render_status():
    from app.services.render_dispatcher import render_dispatcher
    
    old_server_status = await render_dispatcher.check_old_server_status()
    old_server_available = OLD_SERVER_SEMAPHORE._value if old_server_status.get("status") == "healthy" else 0
    
    return {
        "new_server": {
            "max_concurrent": 4,
            "current_renders": CURRENT_RENDERS,
            "available_slots": RENDER_SEMAPHORE._value
        },
        "old_server": {
            **old_server_status,
            "available_slots": old_server_available
        },
        "total_capacity": 4 + (old_server_status.get("max_concurrent_renders", 0) if old_server_status.get("status") == "healthy" else 0)
    }


@router.get("/available-models")
async def get_available_models():
    from app.utils.llm_factory import LLMFactory
    return {
        "models": LLMFactory.get_available_models(),
        "default_code_model": LLMFactory.get_code_model(),
        "default_chat_model": LLMFactory.get_chat_model()
    }


def get_python_path() -> str:
    if sys.platform == "win32":
        return "python"
    else:
        paths = [
            "/root/miniconda3/envs/manim311/bin/python",
            "/opt/miniconda3/envs/manim311/bin/python"
        ]
        for path in paths:
            if os.path.exists(path):
                return path
        return paths[-1]


@router.get("/{project_id}/generate-code")
async def generate_code_stream(
    project_id: int,
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[Session, Depends(get_db)],
    template_id: Optional[int] = Query(None),
    model: Optional[str] = Query(None),
):
    project = db.query(Project).filter(
        Project.id == project_id,
        Project.user_id == current_user.id
    ).first()
    
    if not project:
        async def error_gen():
            yield f"data: {json.dumps({'step': 'error', 'progress': 0, 'message': 'Project not found'})}\n\n"
        return StreamingResponse(error_gen(), media_type="text/event-stream")
    
    # 数学可视化项目可能没有 final_script，使用 theme 作为输入
    input_content = project.final_script or project.theme
    if not input_content:
        async def error_gen():
            yield f"data: {json.dumps({'step': 'error', 'progress': 0, 'message': '请先输入主题或完成内容对话'})}\n\n"
        return StreamingResponse(error_gen(), media_type="text/event-stream")
    
    async def event_generator():
        from app.database import SessionLocal
        db_session = SessionLocal()
        try:
            project_local = db_session.query(Project).filter(Project.id == project_id).first()
            if not project_local:
                yield f"data: {json.dumps({'step': 'error', 'progress': 0, 'message': 'Project not found'})}\n\n"
                return
            
            yield f"data: {json.dumps({'step': 'start', 'progress': 5, 'message': '开始生成脚本...'})}\n\n"
            await asyncio.sleep(0.1)
            
            yield f"data: {json.dumps({'step': 'prepare', 'progress': 10, 'message': '准备提示词...'})}\n\n"
            await asyncio.sleep(0.1)
            
            template = None
            template_code = None
            if template_id:
                template = db_session.query(Template).filter(Template.id == template_id).first()
                if template:
                    template_code = template.code
                    yield f"data: {json.dumps({'step': 'template', 'progress': 15, 'message': f'使用模板: {template.name}'})}\n\n"
            
            yield f"data: {json.dumps({'step': 'generate', 'progress': 20, 'message': '脚本生成中...'})}\n\n"
            
            manim_service = ManimService(db_session)
            
            yield f"data: {json.dumps({'step': 'generate', 'progress': 30, 'message': '正在生成脚本，预计需要 1-2 分钟...'})}\n\n"
            
            progress_messages = [
                (35, "正在分析内容结构..."),
                (40, "正在生成动画场景..."),
                (45, "正在编写脚本..."),
                (50, "脚本生成中，请耐心等待..."),
                (55, "继续生成中..."),
                (60, "即将完成..."),
                (65, "正在收尾..."),
            ]
            
            generate_task = asyncio.create_task(
                manim_service.generate_code(
                    input_content, 
                    template_code,
                    video_title=project_local.theme,
                    model=model
                )
            )
            
            progress_index = 0
            while not generate_task.done():
                try:
                    await asyncio.wait_for(asyncio.shield(generate_task), timeout=8)
                except asyncio.TimeoutError:
                    if progress_index < len(progress_messages):
                        progress, msg = progress_messages[progress_index]
                        yield f"data: {json.dumps({'step': 'generate', 'progress': progress, 'message': msg})}\n\n"
                        progress_index += 1
            
            manim_code = generate_task.result()
            
            yield f"data: {json.dumps({'step': 'generate', 'progress': 70, 'message': '脚本生成完成，正在验证...'})}\n\n"
            
            fixed_code, warnings = manim_service.validate_code(manim_code)
            
            yield f"data: {json.dumps({'step': 'validate', 'progress': 80, 'message': '脚本验证中...'})}\n\n"
            await asyncio.sleep(0.1)
            
            if warnings:
                yield f"data: {json.dumps({'step': 'warnings', 'progress': 85, 'message': '; '.join(warnings)})}\n\n"
            
            project_local.manim_code = fixed_code
            project_local.status = "code_generated"
            db_session.commit()
            
            yield f"data: {json.dumps({'step': 'done', 'progress': 100, 'message': '脚本生成完成！', 'code': fixed_code})}\n\n"
            
        except Exception as e:
            import traceback
            traceback.print_exc()
            yield f"data: {json.dumps({'step': 'error', 'progress': 0, 'message': f'生成失败: {str(e)}'})}\n\n"
        finally:
            db_session.close()
    
    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
        }
    )


@router.get("/{project_id}/render")
async def render_video_stream(
    project_id: int,
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[Session, Depends(get_db)]
):
    current_user_id = int(current_user.id)
    project_query = db.query(Project).filter(Project.id == project_id)
    if not current_user.is_admin:
        project_query = project_query.filter(Project.user_id == current_user_id)
    project = project_query.first()
    
    if not project:
        async def error_gen():
            yield f"data: {json.dumps({'type': 'error', 'content': 'Project not found'})}\n\n"
        return StreamingResponse(error_gen(), media_type="text/event-stream")
    
    allowed, reason = current_user.can_use_module_new(db, "visual")
    if not allowed:
        async def error_gen():
            yield f"data: {json.dumps({'type': 'error', 'content': '系统繁忙，请稍后再试'})}\n\n"
        return StreamingResponse(error_gen(), media_type="text/event-stream")
    
    manim_code_str = str(project.manim_code) if project.manim_code else ""
    if not manim_code_str:
        async def error_gen():
            yield f"data: {json.dumps({'type': 'error', 'content': '请先生成代码'})}\n\n"
        return StreamingResponse(error_gen(), media_type="text/event-stream")
    
    async def event_generator():
        from app.database import SessionLocal
        from app.services.render_dispatcher import render_dispatcher
        global CURRENT_RENDERS
        
        old_server_status = await render_dispatcher.check_old_server_status()
        old_server_available = OLD_SERVER_SEMAPHORE._value if old_server_status.get("status") == "healthy" else 0
        total_available = RENDER_SEMAPHORE._value + old_server_available
        
        if total_available == 0:
            yield f"data: {json.dumps({'type': 'error', 'content': '系统繁忙，请稍后再试'})}\n\n"
            return
        
        yield f"data: {json.dumps({'type': 'info', 'content': '正在准备渲染...'})}\n\n"
        
        if RENDER_SEMAPHORE._value == 0 and old_server_available > 0:
            async for line in try_dispatch_to_old_server(project_id, manim_code_str):
                yield line
            return
        
        db_session = SessionLocal()
        
        async with RENDER_SEMAPHORE:
            CURRENT_RENDERS += 1
            try:
                project_local = db_session.query(Project).filter(Project.id == project_id).first()
                if not project_local:
                    yield f"data: {json.dumps({'type': 'error', 'content': 'Project not found'})}\n\n"
                    return
                
                with tempfile.TemporaryDirectory() as temp_dir:
                    scene_name = "SceneName"
                    
                    if manim_code_str:
                        match = re.search(r'class\s+(\w+)\s*\(Scene\)', manim_code_str)
                        if match:
                            scene_name = match.group(1)
                    
                    code_content = manim_code_str
                    
                    try:
                        compile(code_content, '<string>', 'exec')
                    except SyntaxError as e:
                        yield f"data: {json.dumps({'type': 'error', 'content': '代码语法错误: ' + str(e)})}\n\n"
                        return
                    
                    manim_file = os.path.join(temp_dir, "scene.py")
                    with open(manim_file, "w", encoding="utf-8") as f:
                        f.write(code_content)
                    
                    yield f"data: {json.dumps({'type': 'info', 'content': f'代码已保存到临时文件'})}\n\n"
                    
                    python_path = get_python_path()
                    
                    if sys.platform == "win32":
                        python_check = shutil.which(python_path)
                        if not python_check:
                            yield f"data: {json.dumps({'type': 'error', 'content': 'Python 未安装'})}\n\n"
                            return
                    elif not os.path.exists(python_path):
                        yield f"data: {json.dumps({'type': 'error', 'content': 'Python 环境不存在'})}\n\n"
                        return
                    
                    cmd = [
                        python_path,
                        "-m", "manim",
                        "-qh",
                        "--disable_caching",
                        "--media_dir", temp_dir,
                        "-o", "video",
                        manim_file,
                        scene_name
                    ]
                    
                    yield f"data: {json.dumps({'type': 'info', 'content': f'开始渲染 (高质量1080p60模式)...'})}\n\n"
                    yield f"data: {json.dumps({'type': 'info', 'content': '命令: ' + ' '.join(cmd)})}\n\n"
                    yield f"data: {json.dumps({'type': 'info', 'content': f'超时保护: 总超时{RENDER_TOTAL_TIMEOUT}秒, 无输出超时{RENDER_NO_OUTPUT_TIMEOUT}秒'})}\n\n"
                    yield f"data: {json.dumps({'type': 'info', 'content': '-' * 50})}\n\n"
                    
                    process = None
                    start_time = time.time()
                    last_output_time = start_time
                    timed_out = False
                    
                    try:
                        process = await asyncio.create_subprocess_exec(
                            *cmd,
                            stdout=asyncio.subprocess.PIPE,
                            stderr=asyncio.subprocess.STDOUT
                        )
                        
                        while True:
                            elapsed = time.time() - start_time
                            no_output_elapsed = time.time() - last_output_time
                            
                            if elapsed > RENDER_TOTAL_TIMEOUT:
                                yield f"data: {json.dumps({'type': 'error', 'content': f'渲染总超时（超过{RENDER_TOTAL_TIMEOUT}秒），强制终止进程'})}\n\n"
                                timed_out = True
                                try:
                                    process.kill()
                                    await process.wait()
                                except:
                                    pass
                                break
                            
                            if no_output_elapsed > RENDER_NO_OUTPUT_TIMEOUT:
                                yield f"data: {json.dumps({'type': 'error', 'content': f'渲染无输出超时（{RENDER_NO_OUTPUT_TIMEOUT}秒无输出），强制终止进程'})}\n\n"
                                timed_out = True
                                try:
                                    process.kill()
                                    await process.wait()
                                except:
                                    pass
                                break
                            
                            try:
                                line_bytes = await asyncio.wait_for(
                                    process.stdout.readline(),
                                    timeout=5.0
                                )
                                
                                if not line_bytes:
                                    break
                                
                                last_output_time = time.time()
                                line = line_bytes.decode('utf-8', errors='replace').strip()
                                
                                if line:
                                    elapsed_str = f"[{int(elapsed)}s]"
                                    yield f"data: {json.dumps({'type': 'output', 'content': elapsed_str + ' ' + line})}\n\n"
                                    await asyncio.sleep(0.01)
                                    
                            except asyncio.TimeoutError:
                                continue
                        
                        if process and process.returncode is None:
                            try:
                                returncode = await asyncio.wait_for(process.wait(), timeout=5.0)
                            except asyncio.TimeoutError:
                                process.kill()
                                await process.wait()
                                returncode = -1
                        else:
                            returncode = process.returncode if process else -1
                        
                        yield f"data: {json.dumps({'type': 'info', 'content': '-' * 50})}\n\n"
                        
                        selected_video = _pick_valid_rendered_video(temp_dir) if returncode == 0 or timed_out else None

                        if timed_out and not selected_video:
                            project_local.status = "failed"
                            project_local.error_message = "渲染超时，未生成完整视频"
                            db_session.commit()
                            yield f"data: {json.dumps({'type': 'error', 'content': '渲染已因超时终止，且未生成完整视频，请检查代码或降低视频复杂度'})}\n\n"

                        elif (returncode == 0 or timed_out) and selected_video:
                            video_path = selected_video["path"]
                            
                            backend_dir = os.path.dirname(os.path.dirname(os.path.dirname(__file__)))
                            videos_dir = os.path.join(backend_dir, "videos")
                            os.makedirs(videos_dir, exist_ok=True)
                            
                            video_filename = f"{project_id}_{uuid.uuid4().hex[:8]}.mp4"
                            local_video_path = os.path.join(videos_dir, video_filename)
                            
                            shutil.move(video_path, local_video_path)
                            
                            video_url = f"/api/videos/{video_filename}"
                            
                            if cos_storage.enabled:
                                success, cos_key, cos_url = cos_storage.upload_file(
                                    local_video_path, 
                                    project_id, 
                                    0
                                )
                                if success and cos_url:
                                    video_url = cos_url
                                    try:
                                        os.remove(local_video_path)
                                    except:
                                        pass
                            
                            project_local.status = "completed"
                            project_local.video_url = video_url
                            project_local.error_message = None
                            user_local = db_session.query(User).filter(User.id == current_user_id).first()
                            if user_local:
                                user_local.increment_module_usage_new(db_session, "visual")
                            db_session.commit()
                            
                            success_content = f"渲染完成！耗时{int(elapsed)}秒，视频时长{selected_video['duration']:.2f}秒"
                            yield f"data: {json.dumps({'type': 'success', 'content': success_content, 'video_url': video_url})}\n\n"

                        elif returncode == 0:
                            project_local.status = "failed"
                            project_local.error_message = "未找到完整视频文件"
                            db_session.commit()
                            yield f"data: {json.dumps({'type': 'error', 'content': '未找到完整视频文件'})}\n\n"
                        else:
                            project_local.status = "failed"
                            project_local.error_message = f"渲染失败 (code: {returncode})"
                            db_session.commit()
                            yield f"data: {json.dumps({'type': 'error', 'content': f'渲染失败 (code: {returncode})'})}\n\n"
                            
                    except Exception as e:
                        import traceback
                        traceback.print_exc()
                        if process:
                            try:
                                process.kill()
                                await process.wait()
                            except:
                                pass
                        yield f"data: {json.dumps({'type': 'error', 'content': f'渲染异常: {e}'})}\n\n"
            except Exception as e:
                import traceback
                traceback.print_exc()
                yield f"data: {json.dumps({'type': 'error', 'content': f'渲染异常: {str(e)}'})}\n\n"
            finally:
                CURRENT_RENDERS -= 1
                db_session.close()
    
    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
        }
    )


@router.get("/{project_id}/stickman-generate")
async def generate_stickman_video_stream(
    project_id: int,
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[Session, Depends(get_db)]
):
    current_user_id = int(current_user.id)
    project_query = db.query(Project).filter(Project.id == project_id)
    if not current_user.is_admin:
        project_query = project_query.filter(Project.user_id == current_user_id)
    project = project_query.first()

    if not project:
        async def error_gen():
            yield f"data: {json.dumps({'type': 'error', 'content': 'Project not found'})}\n\n"
        return StreamingResponse(error_gen(), media_type="text/event-stream")

    if str(project.module_type or "manim") != "stickman":
        async def error_gen():
            yield f"data: {json.dumps({'type': 'error', 'content': '当前项目不是火柴人模块'})}\n\n"
        return StreamingResponse(error_gen(), media_type="text/event-stream")

    task = Task(
        project_id=project_id,
        user_id=current_user_id,
        task_type="stickman_generate",
        status="pending",
        progress=0,
        log="",
    )
    db.add(task)
    db.commit()
    db.refresh(task)

    async def event_generator():
        from app.database import SessionLocal

        db_session = SessionLocal()
        try:
            project_local = db_session.query(Project).filter(Project.id == project_id).first()
            task_local = db_session.query(Task).filter(Task.id == task.id).first()

            if not project_local or not task_local:
                yield f"data: {json.dumps({'type': 'error', 'content': '任务初始化失败'})}\n\n"
                return

            task_local.status = "processing"
            task_local.progress = 1
            project_local.status = "rendering"
            task_local.log = (task_local.log or "") + f"开始{_stickman_variant_label(project_local)}火柴人生成\n"
            db_session.commit()

            progress_queue: asyncio.Queue[dict] = asyncio.Queue()
            loop = asyncio.get_running_loop()

            def report(progress: int, message: str):
                loop.call_soon_threadsafe(
                    progress_queue.put_nowait,
                    {"type": "progress", "progress": progress, "content": message},
                )

            generator = _build_stickman_generator(project_local)
            try:
                generation_flags = json.loads(project_local.generation_flags or "{}")
            except Exception:
                generation_flags = {}
            generation_task = asyncio.create_task(asyncio.to_thread(
                generator.generate,
                str(project_local.theme),
                int(project_local.storyboard_count or 3),
                report,
                str(project_local.aspect_ratio or "16:9"),
                str(project_local.voice_source or "ai"),
                str(project_local.voice_file_path) if project_local.voice_file_path else None,
                str(project_local.tts_provider or "edge_tts"),
                str(project_local.tts_voice or "zh-CN-XiaoxiaoNeural"),
                str(project_local.tts_rate or "+0%"),
                str(project_local.background_image_path) if getattr(project_local, 'background_image_path', None) else None,
                str(project_local.style_reference_image_path) if project_local.style_reference_image_path else None,
                str(project_local.style_reference_notes) if project_local.style_reference_notes else None,
                str(generation_flags.get("opening_template_key") or "hook_question"),
            ))

            while True:
                if generation_task.done() and progress_queue.empty():
                    break
                try:
                    event = await asyncio.wait_for(progress_queue.get(), timeout=0.5)
                    task_local.progress = event.get("progress", task_local.progress)
                    task_local.status = "processing"
                    task_local.log = (task_local.log or "") + event.get("content", "") + "\n"
                    db_session.commit()
                    yield f"data: {json.dumps(event)}\n\n"
                except asyncio.TimeoutError:
                    continue

            result = await generation_task

            video_path = result["video_path"]
            video_filename = os.path.basename(video_path)
            video_url = f"/api/videos/{video_filename}"

            if cos_storage.enabled and os.path.exists(video_path):
                success, _, cos_url = cos_storage.upload_file(video_path, project_id, task.id)
                if success and cos_url:
                    video_url = cos_url
                    try:
                        os.remove(video_path)
                    except OSError:
                        pass

            project_local.final_script = result.get("script")
            project_local.storyboard_json = json.dumps(result.get("storyboards") or [], ensure_ascii=False)
            project_local.image_assets_json = json.dumps(result.get("image_assets") or [], ensure_ascii=False)
            project_local.generation_flags = json.dumps(result.get("generation_flags") or {}, ensure_ascii=False)
            project_local.video_url = video_url
            project_local.status = "completed"
            project_local.error_message = None
            try:
                user_local = db_session.query(User).filter(User.id == current_user_id).first()
                if user_local:
                    user_local.increment_module_usage("stickman")
            except Exception:
                pass

            task_local.progress = 100
            task_local.status = "completed"
            task_local.video_url = video_url
            task_local.error_message = None
            task_local.log = (task_local.log or "") + "火柴人视频生成完成\n"
            db_session.commit()

            yield f"data: {json.dumps({'type': 'success', 'content': '火柴人视频生成完成', 'video_url': video_url})}\n\n"
        except Exception as exc:
            task_local = db_session.query(Task).filter(Task.id == task.id).first()
            project_local = db_session.query(Project).filter(Project.id == project_id).first()
            if task_local:
                task_local.status = "failed"
                task_local.error_message = str(exc)
                task_local.log = (task_local.log or "") + f"失败: {exc}\n"
            if project_local:
                project_local.status = "failed"
                project_local.error_message = str(exc)
            db_session.commit()
            yield f"data: {json.dumps({'type': 'error', 'content': str(exc)})}\n\n"
        finally:
            db_session.close()

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
        }
    )


@router.get("/{project_id}/stickman-compose")
async def compose_stickman_video_stream(
    project_id: int,
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[Session, Depends(get_db)]
):
    current_user_id = int(current_user.id)
    project_query = db.query(Project).filter(Project.id == project_id)
    if not current_user.is_admin:
        project_query = project_query.filter(Project.user_id == current_user_id)
    project = project_query.first()

    if not project:
        async def error_gen():
            yield f"data: {json.dumps({'type': 'error', 'content': 'Project not found'})}\n\n"
        return StreamingResponse(error_gen(), media_type="text/event-stream")

    if str(project.module_type or "manim") != "stickman":
        async def error_gen():
            yield f"data: {json.dumps({'type': 'error', 'content': '当前项目不是火柴人模块'})}\n\n"
        return StreamingResponse(error_gen(), media_type="text/event-stream")

    task = Task(
        project_id=project_id,
        user_id=current_user_id,
        task_type="stickman_compose",
        status="pending",
        progress=0,
        log="",
    )
    db.add(task)
    db.commit()
    db.refresh(task)

    async def event_generator():
        from app.database import SessionLocal

        db_session = SessionLocal()
        try:
            project_local = db_session.query(Project).filter(Project.id == project_id).first()
            task_local = db_session.query(Task).filter(Task.id == task.id).first()

            if not project_local or not task_local:
                yield f"data: {json.dumps({'type': 'error', 'content': '任务初始化失败'})}\n\n"
                return

            storyboards = json.loads(project_local.storyboard_json or "[]")
            image_assets = json.loads(project_local.image_assets_json or "[]")
            if not storyboards:
                yield f"data: {json.dumps({'type': 'error', 'content': '请先生成并确认分镜'})}\n\n"
                return
            if not image_assets:
                yield f"data: {json.dumps({'type': 'error', 'content': '请先生成并确认图片'})}\n\n"
                return

            task_local.status = "processing"
            task_local.progress = 1
            project_local.status = "rendering"
            task_local.log = (task_local.log or "") + f"开始{_stickman_variant_label(project_local)}火柴人合成\n"
            db_session.commit()

            progress_queue: asyncio.Queue[dict] = asyncio.Queue()
            loop = asyncio.get_running_loop()

            def report(progress: int, message: str):
                loop.call_soon_threadsafe(
                    progress_queue.put_nowait,
                    {"type": "progress", "progress": progress, "content": message},
                )

            generator = _build_stickman_generator(project_local)
            generation_task = asyncio.create_task(asyncio.to_thread(
                generator.compose_from_assets,
                str(project_local.theme),
                storyboards,
                image_assets,
                report,
                str(project_local.voice_source or "ai"),
                str(project_local.voice_file_path) if project_local.voice_file_path else None,
                str(project_local.tts_provider or "edge_tts"),
                str(project_local.tts_voice or "zh-CN-XiaoxiaoNeural"),
                str(project_local.tts_rate or "+0%"),
            ))

            while True:
                if generation_task.done() and progress_queue.empty():
                    break
                try:
                    event = await asyncio.wait_for(progress_queue.get(), timeout=0.5)
                    task_local.progress = event.get("progress", task_local.progress)
                    task_local.status = "processing"
                    task_local.log = (task_local.log or "") + event.get("content", "") + "\n"
                    db_session.commit()
                    yield f"data: {json.dumps(event)}\n\n"
                except asyncio.TimeoutError:
                    continue

            result = await generation_task
            video_path = result["video_path"]
            video_filename = os.path.basename(video_path)
            video_url = f"/api/videos/{video_filename}"

            if cos_storage.enabled and os.path.exists(video_path):
                success, _, cos_url = cos_storage.upload_file(video_path, project_id, task.id)
                if success and cos_url:
                    video_url = cos_url
                    try:
                        os.remove(video_path)
                    except OSError:
                        pass

            project_local.video_url = video_url
            project_local.status = "completed"
            project_local.error_message = None
            try:
                user_local = db_session.query(User).filter(User.id == current_user_id).first()
                if user_local:
                    user_local.increment_module_usage("stickman")
            except Exception:
                pass
            task_local.progress = 100
            task_local.status = "completed"
            task_local.video_url = video_url
            task_local.error_message = None
            task_local.log = (task_local.log or "") + "火柴人视频合成完成\n"
            db_session.commit()

            yield f"data: {json.dumps({'type': 'success', 'content': '火柴人视频合成完成', 'video_url': video_url})}\n\n"
        except Exception as exc:
            task_local = db_session.query(Task).filter(Task.id == task.id).first()
            project_local = db_session.query(Project).filter(Project.id == project_id).first()
            if task_local:
                task_local.status = "failed"
                task_local.error_message = str(exc)
                task_local.log = (task_local.log or "") + f"失败: {exc}\n"
            if project_local:
                project_local.status = "failed"
                project_local.error_message = str(exc)
            db_session.commit()
            yield f"data: {json.dumps({'type': 'error', 'content': str(exc)})}\n\n"
        finally:
            db_session.close()

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
        }
    )


@router.get("/project/{project_id}")
def get_project_task(
    project_id: int,
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[Session, Depends(get_db)]
):
    project = _project_query_for_user(db, current_user).filter(Project.id == project_id).first()
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")

    task = db.query(Task).filter(Task.project_id == project_id).order_by(Task.created_at.desc()).first()
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")
    return task


@router.post("/{project_id}/render-async")
async def render_video_async(
    project_id: int,
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[Session, Depends(get_db)],
    background_tasks: BackgroundTasks
):
    project = db.query(Project).filter(
        Project.id == project_id,
        Project.user_id == current_user.id
    ).first()
    
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    
    if not project.manim_code:
        raise HTTPException(status_code=400, detail="请先生成脚本")
    
    task = Task(
        project_id=project_id,
        user_id=current_user.id,
        task_type="video_render",
        status="pending",
        progress=0
    )
    db.add(task)
    db.commit()
    db.refresh(task)
    
    celery_result = render_video_celery.delay(
        task.id,
        project_id,
        None,
        None
    )
    
    task.celery_task_id = celery_result.id
    db.commit()
    
    return {
        "task_id": task.id,
        "celery_task_id": celery_result.id,
        "message": "视频渲染已开始，可关闭页面"
    }


@router.get("/{project_id}/latest-render-task")
def get_latest_render_task(
    project_id: int,
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[Session, Depends(get_db)]
):
    task = db.query(Task).filter(
        Task.project_id == project_id,
        Task.user_id == current_user.id,
        Task.task_type.in_(["video_render", "manim_render"])
    ).order_by(Task.created_at.desc()).first()

    if not task:
        return {
            "task_id": None,
            "status": None,
            "progress": 0,
            "message": None,
            "error": None
        }

    return {
        "task_id": task.id,
        "status": task.status,
        "progress": task.progress or 0,
        "message": _task_message(task),
        "error": task.error_message,
        "video_url": task.video_url
    }


@router.get("/task/{task_id}/status")
def get_task_status(
    task_id: int,
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[Session, Depends(get_db)]
):
    task = db.query(Task).filter(
        Task.id == task_id,
        Task.user_id == current_user.id
    ).first()
    
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")
    
    return {
        "task_id": task.id,
        "status": task.status,
        "progress": task.progress or 0,
        "video_url": task.video_url,
        "error_message": task.error_message,
        "celery_task_id": task.celery_task_id
    }


@router.post("/{project_id}/generate-code-async")
async def generate_code_async(
    project_id: int,
    template_id: Optional[int] = Query(None),
    model: Optional[str] = Query(None),
    current_user: Annotated[User, Depends(get_current_user)] = None,
    db: Annotated[Session, Depends(get_db)] = None
):
    """异步后台生成脚本（可关闭页面）"""
    project = db.query(Project).filter(
        Project.id == project_id,
        Project.user_id == current_user.id
    ).first()
    
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    
    if not project.final_script:
        raise HTTPException(status_code=400, detail="请先完成内容对话")
    
    # 创建任务记录
    task = Task(
        project_id=project_id,
        user_id=current_user.id,
        task_type="code_generation",
        status="pending",
        progress=0
    )
    db.add(task)
    db.commit()
    db.refresh(task)
    
    # 提交 Celery 任务
    celery_result = generate_code_celery.delay(
        task.id,
        project_id,
        template_id,
        model
    )
    
    task.celery_task_id = celery_result.id
    db.commit()
    
    return {
        "task_id": task.id,
        "celery_task_id": celery_result.id,
        "message": "脚本生成已开始，可关闭页面"
    }


@router.get("/{project_id}/latest-code-task")
def get_latest_code_task(
    project_id: int,
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[Session, Depends(get_db)]
):
    """获取项目最新的代码生成任务"""
    task = db.query(Task).filter(
        Task.project_id == project_id,
        Task.user_id == current_user.id,
        Task.task_type == "code_generation"
    ).order_by(Task.created_at.desc()).first()
    
    if not task:
        return {
            "task_id": None,
            "status": None,
            "progress": 0,
            "message": None,
            "error": None
        }
    
    return {
        "task_id": task.id,
        "status": task.status,
        "progress": task.progress or 0,
        "message": _task_message(task),
        "error": task.error_message
    }


@router.get("/background/{task_id}")
def get_background_task(
    task_id: int,
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[Session, Depends(get_db)]
):
    """获取后台任务详情"""
    task = db.query(Task).filter(
        Task.id == task_id,
        Task.user_id == current_user.id
    ).first()
    
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")
    
    return {
        "task_id": task.id,
        "task_type": task.task_type,
        "status": task.status,
        "progress": task.progress or 0,
        "message": _task_message(task),
        "error": task.error_message,
        "video_url": task.video_url,
        "log": task.log,
        "created_at": task.created_at.isoformat() if task.created_at else None,
        "started_at": task.started_at.isoformat() if task.started_at else None,
        "completed_at": task.completed_at.isoformat() if task.completed_at else None
    }


@router.get("/celery-status")
async def get_celery_status():
    """检查 Celery 和 Redis 状态"""
    import redis
    from celery import Celery
    
    # 检查 Redis
    redis_connected = False
    try:
        r = redis.from_url(settings.REDIS_URL)
        r.ping()
        redis_connected = True
    except Exception:
        pass
    
    # 检查 Celery Worker
    celery_active = False
    active_tasks = 0
    try:
        from celery_app import celery_app
        inspect = celery_app.control.inspect()
        active = inspect.active()
        if active:
            celery_active = True
            for worker, tasks in active.items():
                active_tasks += len(tasks)
    except Exception:
        pass
    
    return {
        "redis_connected": redis_connected,
        "celery_active": celery_active,
        "active_tasks": active_tasks,
        "status": "healthy" if redis_connected and celery_active else "degraded"
    }


@router.get("/in-progress")
def get_in_progress_tasks(
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[Session, Depends(get_db)]
):
    """获取用户进行中的任务"""
    tasks = db.query(Task).filter(
        Task.user_id == current_user.id,
        Task.status.in_(["pending", "processing"])
    ).order_by(Task.created_at.desc()).all()
    
    return {
        "tasks": [
            {
                "task_id": t.id,
                "project_id": t.project_id,
                "task_type": t.task_type,
                "status": t.status,
                "progress": t.progress or 0,
                "celery_task_id": t.celery_task_id,
                "created_at": t.created_at.isoformat() if t.created_at else None
            }
            for t in tasks
        ],
        "count": len(tasks)
    }


@router.post("/task/{task_id}/cancel")
async def cancel_task(
    task_id: int,
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[Session, Depends(get_db)]
):
    """取消任务"""
    task = db.query(Task).filter(
        Task.id == task_id,
        Task.user_id == current_user.id
    ).first()
    
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")
    
    if task.status in ["completed", "failed", "cancelled"]:
        raise HTTPException(status_code=400, detail=f"Task already {task.status}")
    
    # 取消 Celery 任务
    if task.celery_task_id:
        try:
            from celery_app import celery_app
            celery_app.control.revoke(task.celery_task_id, terminate=True)
        except Exception as e:
            print(f"Failed to revoke Celery task: {e}")
    
    # 更新任务状态
    task.status = "cancelled"
    task.error_message = "User cancelled"
    db.commit()
    
    return {
        "task_id": task.id,
        "status": "cancelled",
        "message": "Task cancelled successfully"
    }
