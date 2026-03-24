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
from app.services.manim import ManimService
from app.config import get_settings

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
            manim_code = await manim_service.generate_code(project_local.final_script, template_prompt)
            
            fixed_code, warnings = manim_service.validate_code(manim_code)
            
            yield f"data: {json.dumps({'step': 'validate', 'progress': 80, 'message': '代码验证中...'})}\n\n"
            await asyncio.sleep(0.1)
            
            if warnings:
                yield f"data: {json.dumps({'step': 'warnings', 'progress': 85, 'message': '; '.join(warnings)})}\n\n"
            
            project_local.manim_code = fixed_code
            project_local.status = "code_generated"
            db_session.commit()
            
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
                            db_session.commit()
                            
                            yield f"data: {json.dumps({'type': 'success', 'content': f'渲染完成！', 'video_url': video_url})}\n\n"
                        else:
                            yield f"data: {json.dumps({'type': 'error', 'content': '未找到视频文件'})}\n\n"
                    else:
                        yield f"data: {json.dumps({'type': 'error', 'content': f'渲染失败 (code: {result})'})}\n\n"
                        
                except subprocess.TimeoutExpired:
                    if process:
                        process.kill()
                    yield f"data: {json.dumps({'type': 'error', 'content': '渲染超时 (10分钟)'})}\n\n"
                except Exception as e:
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