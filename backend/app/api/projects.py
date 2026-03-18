from typing import Annotated, List
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.user import User
from app.models.project import Project, Conversation
from app.models.task import Task
from app.schemas.project import (
    ProjectCreate, ProjectUpdate, ProjectResponse,
    ConversationCreate, ConversationResponse
)
from app.schemas.task import TaskCreate, TaskResponse
from app.api.auth import get_current_user
from app.services.chat import ChatService

router = APIRouter(prefix="/projects", tags=["projects"])


@router.post("", response_model=ProjectResponse)
def create_project(
    project: ProjectCreate,
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[Session, Depends(get_db)]
):
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
    projects = db.query(Project).filter(Project.user_id == current_user.id).all()
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
async def send_message(
    project_id: int,
    message: ConversationCreate,
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[Session, Depends(get_db)]
):
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
    
    chat_service = ChatService(db)
    response = await chat_service.process_message(project_id, project.theme, message.content)
    
    assistant_message = Conversation(
        project_id=project_id,
        role="assistant",
        content=response["content"]
    )
    db.add(assistant_message)
    
    if response.get("is_final"):
        project.final_script = response.get("final_script")
        project.status = "chatting"
    
    db.commit()
    db.refresh(assistant_message)
    
    return assistant_message
