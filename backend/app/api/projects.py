from typing import Annotated, List
from fastapi import APIRouter, Depends, HTTPException, status, Request
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session
from slowapi import Limiter
from slowapi.util import get_remote_address
import json
import asyncio
import re

from app.database import get_db
from app.models.user import User
from app.models.project import Project, Conversation
from app.models.task import Task
from app.schemas.project import (
    ProjectCreate, ProjectUpdate, ProjectResponse,
    ConversationCreate, ConversationResponse, ConversationUpdate, CustomScriptRequest
)
from app.schemas.task import TaskCreate, TaskResponse
from app.api.auth import get_current_user
from app.services.chat import ChatService
from app.services.manim import ManimService

router = APIRouter(prefix="/projects", tags=["projects"])
limiter = Limiter(key_func=get_remote_address)


@router.post("", response_model=ProjectResponse)
def create_project(
    project: ProjectCreate,
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[Session, Depends(get_db)]
):
    MAX_PROJECTS = 3
    if not current_user.is_admin:
        project_count = db.query(Project).filter(Project.user_id == current_user.id).count()
        if project_count >= MAX_PROJECTS:
            raise HTTPException(
                status_code=400,
                detail=f"作品数量已达上限({MAX_PROJECTS}个)，请下载后删除旧作品"
            )
    
    new_project = Project(
        user_id=current_user.id,
        title=project.title,
        theme=project.theme
    )
    db.add(new_project)
    db.commit()
    db.refresh(new_project)
    return new_project


@router.get("", response_model=List[ProjectResponse])
def list_projects(
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[Session, Depends(get_db)]
):
    projects = db.query(Project).filter(Project.user_id == current_user.id).order_by(Project.created_at.desc()).all()
    return projects


@router.get("/{project_id}", response_model=ProjectResponse)
def get_project(
    project_id: int,
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[Session, Depends(get_db)]
):
    project = db.query(Project).filter(
        Project.id == project_id,
        Project.user_id == current_user.id
    ).first()
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    return project


@router.put("/{project_id}", response_model=ProjectResponse)
def update_project(
    project_id: int,
    project_update: ProjectUpdate,
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[Session, Depends(get_db)]
):
    project = db.query(Project).filter(
        Project.id == project_id,
        Project.user_id == current_user.id
    ).first()
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    
    for key, value in project_update.model_dump(exclude_unset=True).items():
        setattr(project, key, value)
    
    db.commit()
    db.refresh(project)
    return project


@router.delete("/{project_id}")
def delete_project(
    project_id: int,
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[Session, Depends(get_db)]
):
    project = db.query(Project).filter(
        Project.id == project_id,
        Project.user_id == current_user.id
    ).first()
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    
    db.query(Conversation).filter(Conversation.project_id == project_id).delete()
    db.query(Task).filter(Task.project_id == project_id).delete()
    db.delete(project)
    db.commit()
    return {"message": "Project deleted"}


@router.post("/batch-delete")
def batch_delete_projects(
    data: dict,
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[Session, Depends(get_db)]
):
    project_ids = data.get("project_ids", [])
    if not project_ids:
        raise HTTPException(status_code=400, detail="No project IDs provided")
    
    deleted_count = 0
    for project_id in project_ids:
        project = db.query(Project).filter(
            Project.id == project_id,
            Project.user_id == current_user.id
        ).first()
        if project:
            db.query(Conversation).filter(Conversation.project_id == project_id).delete()
            db.query(Task).filter(Task.project_id == project_id).delete()
            db.delete(project)
            deleted_count += 1
    
    db.commit()
    return {"message": f"Deleted {deleted_count} projects", "deleted_count": deleted_count}


@router.get("/{project_id}/conversations", response_model=List[ConversationResponse])
def get_conversations(
    project_id: int,
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[Session, Depends(get_db)]
):
    project = db.query(Project).filter(
        Project.id == project_id,
        Project.user_id == current_user.id
    ).first()
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    
    conversations = db.query(Conversation).filter(
        Conversation.project_id == project_id
    ).order_by(Conversation.created_at).all()
    return conversations


@router.post("/{project_id}/chat", response_model=ConversationResponse)
@limiter.limit("10/minute")
async def send_message(
    request: Request,
    project_id: int,
    message: ConversationCreate,
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[Session, Depends(get_db)]
):
    """发送消息 - 立即返回，不等待AI响应"""
    project = db.query(Project).filter(
        Project.id == project_id,
        Project.user_id == current_user.id
    ).first()
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    
    user_message = Conversation(
        project_id=project_id,
        role="user",
        content=message.content
    )
    db.add(user_message)
    db.commit()
    db.refresh(user_message)
    
    return user_message


@router.post("/{project_id}/chat/stream")
async def chat_stream(
    project_id: int,
    message: ConversationCreate,
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[Session, Depends(get_db)]
):
    """流式聊天 - SSE 输出"""
    project = db.query(Project).filter(
        Project.id == project_id,
        Project.user_id == current_user.id
    ).first()
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    
    theme = str(project.theme)
    
    # 获取模板代码
    template_code = None
    if project.template_id:
        from app.models.template import Template
        template = db.query(Template).filter(Template.id == project.template_id).first()
        if template:
            template_code = template.code
    
    # 提取数据，避免会话问题
    project_manim_code = str(project.manim_code) if project.manim_code else None
    project_final_script = str(project.final_script) if project.final_script else None
    
    user_message = Conversation(
        project_id=project_id,
        role="user",
        content=message.content
    )
    db.add(user_message)
    db.commit()
    db.refresh(user_message)
    
    async def event_generator():
        chat_service = ChatService(db)
        
        full_content = ""
        reasoning_content = ""
        
        try:
            async for chunk in chat_service.stream_process_message(
                project_id, theme, message.content,
                manim_code=project_manim_code,
                template_code=template_code,
                final_script=project_final_script
            ):
                chunk_type = chunk.get("type")
                
                if chunk_type == "reasoning":
                    reasoning_content += chunk["content"]
                    yield f"data: {json.dumps({'type': 'reasoning', 'content': chunk['content']})}\n\n"
                elif chunk_type == "content":
                    full_content += chunk["content"]
                    yield f"data: {json.dumps({'type': 'content', 'content': chunk['content']})}\n\n"
                elif chunk_type == "final":
                    yield f"data: {json.dumps({'type': 'done', 'content': chunk['content'], 'is_final': True})}\n\n"
                elif chunk_type == "done":
                    ai_msg = Conversation(
                        project_id=project_id,
                        role="assistant",
                        content=full_content
                    )
                    db.add(ai_msg)
                    
                    proj = db.query(Project).filter(Project.id == project_id).first()
                    if proj:
                        if chunk.get("is_final"):
                            proj.status = "chatting_completed"
                        if chunk.get("final_script"):
                            proj.final_script = chunk["final_script"]
                    
                    db.commit()
                    
                    result = {
                        'type': 'done', 
                        'content': full_content, 
                        'is_final': chunk.get('is_final', False)
                    }
                    if chunk.get("code_updated"):
                        result['code_updated'] = True
                        result['updated_code'] = chunk['updated_code']
                        result['has_template'] = project.template_id is not None
                    
                    yield f"data: {json.dumps(result)}\n\n"
                elif chunk_type == "error":
                    yield f"data: {json.dumps({'type': 'error', 'error': chunk['error']})}\n\n"
                
                await asyncio.sleep(0.01)
        except Exception as e:
            yield f"data: {json.dumps({'type': 'error', 'error': str(e)})}\n\n"
        finally:
            yield "data: [DONE]\n\n"
    
    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        }
    )


@router.get("/{project_id}/chat/pending")
async def get_pending_response(
    project_id: int,
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[Session, Depends(get_db)]
):
    """获取AI响应 - 前端轮询此接口"""
    project = db.query(Project).filter(
        Project.id == project_id,
        Project.user_id == current_user.id
    ).first()
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    
    # 获取最新的用户消息
    last_user = db.query(Conversation).filter(
        Conversation.project_id == project_id,
        Conversation.role == "user"
    ).order_by(Conversation.created_at.desc()).first()
    
    if not last_user:
        return {"status": "no_message"}
    
    # 检查是否已有AI回复
    last_ai = db.query(Conversation).filter(
        Conversation.project_id == project_id,
        Conversation.role == "assistant",
        Conversation.created_at > last_user.created_at
    ).order_by(Conversation.created_at.asc()).first()
    
    if last_ai:
        # 已处理过，返回已有回复
        if last_ai.content.startswith("【"):
            return {
                "status": "completed",
                "response": last_ai,
                "has_final_script": True
            }
        return {"status": "completed", "response": last_ai}
    
    # 生成AI响应
    try:
        chat_service = ChatService(db)
        project_theme = str(project.theme)
        response = await chat_service.process_message(project_id, project_theme, last_user.content)
        
        assistant_message = Conversation(
            project_id=project_id,
            role="assistant",
            content=response["content"]
        )
        db.add(assistant_message)
        
        if response.get("is_final"):
            project.final_script = response.get("final_script")
            project.status = "chatting_completed"
        
        db.commit()
        db.refresh(assistant_message)
        
        return {
            "status": "completed",
            "response": assistant_message,
            "has_final_script": response.get("is_final", False)
        }
    except Exception as e:
        return {"status": "error", "error": str(e)}


@router.post("/{project_id}/regenerate-code")
async def regenerate_code(
    project_id: int,
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[Session, Depends(get_db)]
):
    """重新生成代码（基于最新的final_script）"""
    project = db.query(Project).filter(
        Project.id == project_id,
        Project.user_id == current_user.id
    ).first()
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    
    if not project.final_script:
        raise HTTPException(status_code=400, detail="No final script to generate code from")
    
    manim_service = ManimService(db)
    template_code = ""
    if project.template_id:
        from app.models.template import Template
        template = db.query(Template).filter(Template.id == project.template_id).first()
        if template:
            template_code = template.code
    
    manim_code = await manim_service.generate_code(
        project.final_script,
        template_code=template_code,
        video_title=project.theme
    )
    
    project.manim_code = manim_code
    project.status = "chatting"
    db.commit()
    
    return {"message": "代码已重新生成", "code_updated": True}


@router.post("/{project_id}/optimize-code")
async def optimize_code(
    project_id: int,
    feedback: str,
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[Session, Depends(get_db)]
):
    """根据用户反馈优化代码"""
    project = db.query(Project).filter(
        Project.id == project_id,
        Project.user_id == current_user.id
    ).first()
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    
    if not project.manim_code:
        raise HTTPException(status_code=400, detail="No code to optimize")
    
    # 使用AI根据反馈优化代码
    manim_service = ManimService(db)
    optimized_code = await manim_service.optimize_code(
        project.manim_code,
        project.final_script or "",
        feedback
    )
    
    project.manim_code = optimized_code
    db.commit()
    
    return {"message": "代码已根据反馈优化", "code_updated": True}


@router.post("/{project_id}/optimize-code/stream")
async def optimize_code_stream(
    project_id: int,
    feedback: str,
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[Session, Depends(get_db)]
):
    """流式优化代码 - 用于渲染失败后的一键修复"""
    project = db.query(Project).filter(
        Project.id == project_id,
        Project.user_id == current_user.id
    ).first()
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    
    if not project.manim_code:
        raise HTTPException(status_code=400, detail="No code to optimize")
    
    # 在生成器外部提取数据，避免会话问题
    current_code = str(project.manim_code)
    current_final_script = str(project.final_script or "")
    
    async def event_generator():
        manim_service = ManimService(db)
        
        try:
            yield f"data: {json.dumps({'type': 'progress', 'message': '正在分析错误...'})}\n\n"
            await asyncio.sleep(0.3)
            
            yield f"data: {json.dumps({'type': 'progress', 'message': '正在修复代码...'})}\n\n"
            
            optimized_code = await manim_service.optimize_code(
                current_code,
                current_final_script,
                feedback
            )
            
            yield f"data: {json.dumps({'type': 'code', 'code': optimized_code})}\n\n"
            
            yield f"data: {json.dumps({'type': 'done'})}\n\n"
            
        except Exception as e:
            yield f"data: {json.dumps({'type': 'error', 'error': str(e)})}\n\n"
        finally:
            yield "data: [DONE]\n\n"
    
    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        }
    )


@router.put("/conversations/{conv_id}")
async def update_conversation(
    conv_id: int,
    data: ConversationUpdate,
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[Session, Depends(get_db)]
):
    """修改对话内容"""
    conv = db.query(Conversation).filter(Conversation.id == conv_id).first()
    
    if not conv:
        raise HTTPException(status_code=404, detail="对话不存在")
    
    project = db.query(Project).filter(Project.id == conv.project_id).first()
    if not project or project.user_id != current_user.id:
        raise HTTPException(status_code=403, detail="无权限")
    
    conv.content = data.content
    
    if conv.role == 'assistant':
        project.final_script = data.content
    
    db.commit()
    
    return {
        "message": "更新成功",
        "conversation": {
            "id": conv.id,
            "content": conv.content,
            "role": conv.role
        },
        "final_script_updated": conv.role == 'assistant'
    }


@router.post("/{project_id}/use-custom-script")
async def use_custom_script(
    project_id: int,
    data: CustomScriptRequest,
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[Session, Depends(get_db)]
):
    """使用自定义文案"""
    project = db.query(Project).filter(Project.id == project_id).first()
    
    if not project or project.user_id != current_user.id:
        raise HTTPException(status_code=403, detail="无权限")
    
    project.final_script = data.script
    project.status = "chatting_completed"
    
    conv = Conversation(
        project_id=project_id,
        role="user",
        content=f"[自定义文案]\n{data.script}"
    )
    db.add(conv)
    
    db.commit()
    
    return {
        "message": "文案已保存",
        "final_script": data.script
    }
