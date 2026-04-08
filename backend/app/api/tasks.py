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
from app.config import get_settings
from app.utils.cos_storage import cos_storage
from app.tasks.celery_tasks import render_video_celery

router = APIRouter(prefix="/tasks", tags=["tasks"])
settings = get_settings()

RENDER_SEMAPHORE = asyncio.Semaphore(4)
CURRENT_RENDERS = 0
OLD_SERVER_SEMAPHORE = asyncio.Semaphore(2)
MAX_TOTAL_RENDERS = 6
RENDER_TOTAL_TIMEOUT = 300
RENDER_NO_OUTPUT_TIMEOUT = 60


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
    
    if not project.final_script:
        async def error_gen():
            yield f"data: {json.dumps({'step': 'error', 'progress': 0, 'message': '请先完成内容对话'})}\n\n"
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
                    project_local.final_script, 
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
    project = db.query(Project).filter(
        Project.id == project_id,
        Project.user_id == current_user.id
    ).first()
    
    if not project:
        async def error_gen():
            yield f"data: {json.dumps({'type': 'error', 'content': 'Project not found'})}\n\n"
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
                        
                        if timed_out:
                            project_local.status = "failed"
                            project_local.error_message = "渲染超时"
                            db_session.commit()
                            yield f"data: {json.dumps({'type': 'error', 'content': '渲染已因超时终止，请检查代码或降低视频复杂度'})}\n\n"
                        
                        elif returncode == 0:
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
                                db_session.commit()
                                
                                yield f"data: {json.dumps({'type': 'success', 'content': f'渲染完成！耗时{int(elapsed)}秒', 'video_url': video_url})}\n\n"
                            else:
                                yield f"data: {json.dumps({'type': 'error', 'content': '未找到视频文件'})}\n\n"
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


@router.get("/project/{project_id}")
def get_project_task(
    project_id: int,
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[Session, Depends(get_db)]
):
    task = db.query(Task).filter(Task.project_id == project_id).order_by(Task.created_at.desc()).first()
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
        project.custom_code
    )
    
    task.celery_task_id = celery_result.id
    db.commit()
    
    return {
        "task_id": task.id,
        "celery_task_id": celery_result.id,
        "message": "任务已提交，后台运行中，可关闭浏览器"
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