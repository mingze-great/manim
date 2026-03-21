from typing import Annotated
from fastapi import APIRouter, Depends, HTTPException, status, BackgroundTasks
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session
import json
import asyncio

from app.database import get_db
from app.models.user import User
from app.models.project import Project
from app.models.task import Task
from app.schemas.task import TaskCreate, TaskResponse, TaskStatusResponse
from app.api.auth import get_current_user
from app.tasks.render import render_video_task
from app.services.manim import ManimService
from app.database import SessionLocal

router = APIRouter(prefix="/tasks", tags=["tasks"])


@router.post("/{project_id}/generate", response_model=TaskResponse)
def generate_video(
    project_id: int,
    template_id: int | None = None,
    current_user: Annotated[User, Depends(get_current_user)] = None,
    db: Annotated[Session, Depends(get_db)] = None
):
    project = db.query(Project).filter(
        Project.id == project_id,
        Project.user_id == current_user.id
    ).first()
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    
    if not project.final_script and not project.manim_code:
        raise HTTPException(status_code=400, detail="Script not confirmed yet")
    
    task = Task(
        project_id=project_id,
        status="pending",
        progress=0
    )
    db.add(task)
    db.commit()
    db.refresh(task)
    
    project.status = "pending"
    db.commit()
    
    # 直接同步执行渲染任务
    try:
        render_video_task(task.id, project_id, template_id)
    except Exception as e:
        print(f"渲染任务执行失败: {e}")
    
    # 刷新task获取最新状态
    db.refresh(task)
    
    return task


@router.get("/{project_id}/generate-code")
async def generate_code_stream(
    project_id: int,
    template_id: int | None = None,
    current_user: Annotated[User, Depends(get_current_user)] = None,
    db: Annotated[Session, Depends(get_db)] = None
):
    """实时生成代码的API，流式返回进度"""
    project = db.query(Project).filter(
        Project.id == project_id,
        Project.user_id == current_user.id
    ).first()
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    
    if not project.final_script and not project.manim_code:
        raise HTTPException(status_code=400, detail="Script not confirmed yet")
    
    async def event_generator():
        yield "data: " + json.dumps({"step": "start", "message": "正在调用AI生成代码...", "progress": 10}) + "\n\n"
        
        try:
            from app.services.manim import ManimService
            
            manim_service = ManimService(db)
            
            yield "data: " + json.dumps({"step": "calling_llm", "message": "AI正在生成Manim代码...", "progress": 20}) + "\n\n"
            
            # 直接调用异步方法（因为当前函数已经是async）
            manim_code = await manim_service.generate_code(project.final_script, template_id, project.custom_code)
            
            # 提取代码
            if "```python" in manim_code:
                start = manim_code.find("```python") + len("```python")
                end = manim_code.find("```", start)
                manim_code = manim_code[start:end].strip()
            
            # 保存代码到项目
            project.manim_code = manim_code
            project.status = "code_generated"
            db.commit()
            
            yield "data: " + json.dumps({
                "step": "code_generated", 
                "message": "代码生成完成！", 
                "progress": 50,
                "code": manim_code
            }) + "\n\n"
            
            yield "data: " + json.dumps({
                "step": "complete", 
                "message": "可以开始渲染视频了", 
                "progress": 100
            }) + "\n\n"
                
        except Exception as e:
            error_msg = str(e)
            # 处理图片错误
            if "image.png" in error_msg or "image input" in error_msg.lower():
                error_msg = "当前使用的AI模型不支持图像输入，请检查API配置或更换模型"
            
            yield "data: " + json.dumps({
                "step": "error", 
                "message": f"生成失败: {error_msg}", 
                "progress": 0
            }) + "\n\n"
    
    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
        }
    )


@router.get("/project/{project_id}", response_model=TaskResponse)
def get_project_task(
    project_id: int,
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[Session, Depends(get_db)]
):
    """获取项目的最新任务"""
    task = db.query(Task).filter(
        Task.project_id == project_id,
        Project.user_id == current_user.id
    ).order_by(Task.created_at.desc()).first()
    
    if not task:
        raise HTTPException(status_code=404, detail="No task found for this project")
    return task


@router.get("/{task_id}", response_model=TaskResponse)
def get_task(
    task_id: int,
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[Session, Depends(get_db)]
):
    task = db.query(Task).join(Project).filter(
        Task.id == task_id,
        Project.user_id == current_user.id
    ).first()
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")
    return task


@router.get("/{task_id}/status", response_model=TaskStatusResponse)
async def get_task_status(
    task_id: int,
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[Session, Depends(get_db)]
):
    task = db.query(Task).join(Project).filter(
        Task.id == task_id,
        Project.user_id == current_user.id
    ).first()
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")
    
    return TaskStatusResponse(
        status=task.status,
        progress=task.progress,
        video_url=task.video_url,
        error_message=task.error_message
    )


@router.get("/{task_id}/stream")
async def stream_task_status(
    task_id: int,
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[Session, Depends(get_db)]
):
    task = db.query(Task).join(Project).filter(
        Task.id == task_id,
        Project.user_id == current_user.id
    ).first()
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")
    
    async def event_generator():
        while True:
            db.refresh(task)
            yield "data: " + json.dumps({
                "status": task.status,
                "progress": task.progress,
                "video_url": task.video_url,
                "error_message": task.error_message
            }) + "\n\n"
            
            if task.status in ["completed", "failed"]:
                break
            
            await asyncio.sleep(2)
    
    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
        }
    )
