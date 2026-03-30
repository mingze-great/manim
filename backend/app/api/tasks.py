from typing import Annotated, Optional
from fastapi import APIRouter, Depends, HTTPException, Query
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

from app.database import get_db
from app.models.user import User
from app.models.project import Project
from app.models.task import Task
from app.models.template import Template
from app.api.auth import get_current_user
from app.services.manim import ManimService, ManimFixService
from app.services.code_cache import CodeCache
from app.config import get_settings
from app.schemas.task import FixCodeRequest, FixCodeResponse

router = APIRouter(prefix="/tasks", tags=["tasks"])
settings = get_settings()


def get_python_path() -> str:
    if sys.platform == "win32":
        return "python"
    else:
        return "/opt/miniconda3/envs/manim311/bin/python"


@router.get("/{project_id}/generate-code")
async def generate_code_stream(
    project_id: int,
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[Session, Depends(get_db)],
    template_id: Optional[int] = Query(None),
    model: Optional[str] = Query(None),
):
    """生成Manim代码，流式返回进度"""
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
            
            yield f"data: {json.dumps({'step': 'start', 'progress': 5, 'message': '开始生成代码...'})}\n\n"
            await asyncio.sleep(0.1)
            
            yield f"data: {json.dumps({'step': 'prepare', 'progress': 10, 'message': '准备提示词...'})}\n\n"
            await asyncio.sleep(0.1)
            
            template = None
            if template_id:
                template = db_session.query(Template).filter(Template.id == template_id).first()
                if template:
                    yield f"data: {json.dumps({'step': 'template', 'progress': 15, 'message': f'使用模板: {template.name}'})}\n\n"
            
            yield f"data: {json.dumps({'step': 'generate', 'progress': 20, 'message': 'AI正在生成代码...'})}\n\n"
            
            manim_service = ManimService(db_session)
            template_prompt = template.prompt if template else None
            manim_code = await manim_service.generate_code(project_local.final_script, template_prompt, model)
            
            fixed_code, warnings = manim_service.validate_code(manim_code)
            
            if project_local.theme:
                import re
                fixed_code = re.sub(
                    r'INTRO_TITLE\s*=\s*"[^"]*"',
                    f'INTRO_TITLE = "{project_local.theme}"',
                    fixed_code
                )
                fixed_code = re.sub(
                    r'TITLE_TEXT\s*=\s*"[^"]*"',
                    f'TITLE_TEXT = "{project_local.theme}"',
                    fixed_code
                )
            
            yield f"data: {json.dumps({'step': 'validate', 'progress': 80, 'message': '代码验证中...'})}\n\n"
            await asyncio.sleep(0.1)
            
            if warnings:
                yield f"data: {json.dumps({'step': 'warnings', 'progress': 85, 'message': '; '.join(warnings)})}\n\n"
            
            project_local.manim_code = fixed_code
            project_local.status = "code_generated"
            db_session.commit()
            
            # 保存代码到缓存，用于后续增量修复
            CodeCache.save(project_id, fixed_code)
            
            yield f"data: {json.dumps({'step': 'done', 'progress': 100, 'message': '代码生成完成！', 'code': fixed_code})}\n\n"
            
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
    """直接渲染视频，流式返回终端输出"""
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
        db_session = SessionLocal()
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
                yield f"data: {json.dumps({'type': 'info', 'content': '-' * 50})}\n\n"
                
                process = None
                try:
                    process = subprocess.Popen(
                        cmd,
                        stdout=subprocess.PIPE,
                        stderr=subprocess.STDOUT,
                        text=True,
                        bufsize=1
                    )
                    
                    for line in process.stdout:
                        line = line.strip()
                        if line:
                            yield f"data: {json.dumps({'type': 'output', 'content': line})}\n\n"
                            await asyncio.sleep(0.01)
                    
                    result = process.wait(timeout=600)
                    
                    yield f"data: {json.dumps({'type': 'info', 'content': '-' * 50})}\n\n"
                    
                    if result == 0:
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
                            
                            project_local.status = "completed"
                            project_local.video_url = video_url
                            project_local.render_fail_count = 0
                            db_session.commit()
                            
                            # 渲染成功，清除代码缓存
                            CodeCache.delete(project_id)
                            
                            yield f"data: {json.dumps({'type': 'success', 'content': f'渲染完成！', 'video_url': video_url})}\n\n"
                        else:
                            project_local.render_fail_count = (project_local.render_fail_count or 0) + 1
                            db_session.commit()
                            yield f"data: {json.dumps({'type': 'error', 'content': '未找到视频文件'})}\n\n"
                    else:
                        project_local.render_fail_count = (project_local.render_fail_count or 0) + 1
                        db_session.commit()
                        yield f"data: {json.dumps({'type': 'error', 'content': f'渲染失败 (code: {result})'})}\n\n"
                        
                except subprocess.TimeoutExpired:
                    if process:
                        process.kill()
                    project_local.render_fail_count = (project_local.render_fail_count or 0) + 1
                    db_session.commit()
                    yield f"data: {json.dumps({'type': 'error', 'content': '渲染超时 (10分钟)'})}\n\n"
                except Exception as e:
                    project_local.render_fail_count = (project_local.render_fail_count or 0) + 1
                    db_session.commit()
                    yield f"data: {json.dumps({'type': 'error', 'content': f'渲染异常: {e}'})}\n\n"
        except Exception as e:
            import traceback
            traceback.print_exc()
            yield f"data: {json.dumps({'type': 'error', 'content': f'渲染异常: {str(e)}'})}\n\n"
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
    task = db.query(Task).filter(Task.project_id == project_id).order_by(Task.created_at.desc()).first()
    return task


@router.post("/{project_id}/fix-code", response_model=FixCodeResponse)
async def fix_code(
    project_id: int,
    request: FixCodeRequest,
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[Session, Depends(get_db)]
):
    """根据错误信息增量修复代码"""
    project = db.query(Project).filter(
        Project.id == project_id,
        Project.user_id == current_user.id
    ).first()
    
    if not project:
        raise HTTPException(status_code=404, detail="项目不存在")
    
    # 从缓存获取代码，如果没有则使用请求中的代码
    cached_code = CodeCache.load(project_id)
    current_code = cached_code or request.current_code
    
    if not current_code:
        return FixCodeResponse(
            success=False,
            message="没有可修复的代码"
        )
    
    try:
        # 调用增量修复服务
        fix_service = ManimFixService(db)
        fixed_code, fix_desc = await fix_service.fix_code_incremental(
            current_code,
            request.error_message,
            user_id=current_user.id
        )
        
        # 更新缓存
        CodeCache.save(project_id, fixed_code)
        
        # 更新项目代码
        project.manim_code = fixed_code
        db.commit()
        
        return FixCodeResponse(
            success=True,
            fixed_code=fixed_code,
            fix_description=fix_desc
        )
        
    except Exception as e:
        return FixCodeResponse(
            success=False,
            message=f"修复失败: {str(e)}"
        )


@router.delete("/{project_id}/code-cache")
def clear_code_cache(
    project_id: int,
    current_user: Annotated[User, Depends(get_current_user)]
):
    """清除代码缓存（渲染成功后调用）"""
    CodeCache.delete(project_id)
    return {"message": "缓存已清除"}


# ============ 后台任务 API ============

from app.services.background_task import task_manager
from app.models.background_task import BackgroundTask


@router.post("/{project_id}/generate-code-async")
async def generate_code_async(
    project_id: int,
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[Session, Depends(get_db)],
    template_id: Optional[int] = Query(None),
    model: Optional[str] = Query(None),
):
    """创建后台代码生成任务"""
    project = db.query(Project).filter(
        Project.id == project_id,
        Project.user_id == current_user.id
    ).first()
    
    if not project:
        raise HTTPException(status_code=404, detail="项目不存在")
    
    if not project.final_script:
        raise HTTPException(status_code=400, detail="请先完成内容对话")
    
    bg_task = task_manager.create_task(
        db=db,
        task_type="generate_code",
        project_id=project_id,
        user_id=current_user.id,
        input_params={
            "template_id": template_id,
            "model": model
        }
    )
    
    task_manager.start_task(bg_task.id)
    
    return {
        "task_id": bg_task.id,
        "status": bg_task.status,
        "message": "任务已创建，正在后台处理"
    }


@router.get("/background/{task_id}")
def get_background_task_status(
    task_id: int,
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[Session, Depends(get_db)]
):
    """获取后台任务状态"""
    bg_task = db.query(BackgroundTask).filter(
        BackgroundTask.id == task_id,
        BackgroundTask.user_id == current_user.id
    ).first()
    
    if not bg_task:
        raise HTTPException(status_code=404, detail="任务不存在")
    
    result = {
        "task_id": bg_task.id,
        "task_type": bg_task.task_type,
        "status": bg_task.status,
        "progress": bg_task.progress,
        "message": bg_task.message,
        "error": bg_task.error,
        "created_at": bg_task.created_at.isoformat() if bg_task.created_at else None,
        "started_at": bg_task.started_at.isoformat() if bg_task.started_at else None,
        "completed_at": bg_task.completed_at.isoformat() if bg_task.completed_at else None,
    }
    
    if bg_task.status == "completed" and bg_task.result:
        result["code"] = bg_task.result
    
    return result


@router.get("/{project_id}/latest-code-task")
def get_latest_code_task(
    project_id: int,
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[Session, Depends(get_db)]
):
    """获取项目最新的代码生成任务"""
    bg_task = task_manager.get_project_latest_task(db, project_id, "generate_code")
    
    if not bg_task:
        return {"task_id": None, "status": None}
    
    return {
        "task_id": bg_task.id,
        "status": bg_task.status,
        "progress": bg_task.progress,
        "message": bg_task.message,
        "error": bg_task.error
    }