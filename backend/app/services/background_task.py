import asyncio
import json
from datetime import datetime
from typing import Optional, Dict, Any
from sqlalchemy.orm import Session
from app.database import SessionLocal
from app.models.background_task import BackgroundTask
from app.models.project import Project
from app.models.user import User
from app.services.manim import ManimService


class BackgroundTaskManager:
    _instance = None
    _tasks: Dict[int, asyncio.Task] = {}
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance
    
    def create_task(
        self,
        db: Session,
        task_type: str,
        project_id: int,
        user_id: int,
        input_params: Optional[Dict[str, Any]] = None
    ) -> BackgroundTask:
        bg_task = BackgroundTask(
            task_type=task_type,
            project_id=project_id,
            user_id=user_id,
            input_params=input_params or {},
            status="pending",
            progress=0,
            message="任务已创建"
        )
        db.add(bg_task)
        db.commit()
        db.refresh(bg_task)
        return bg_task
    
    def start_task(self, task_id: int):
        if task_id in self._tasks:
            return
        
        async def run_task():
            db = SessionLocal()
            try:
                bg_task = db.query(BackgroundTask).filter(BackgroundTask.id == task_id).first()
                if not bg_task:
                    return
                
                bg_task.status = "processing"
                bg_task.started_at = datetime.utcnow()
                bg_task.message = "任务开始处理"
                db.commit()
                
                if bg_task.task_type == "generate_code":
                    await self._run_generate_code(db, bg_task)
                elif bg_task.task_type == "render_video":
                    await self._run_render_video(db, bg_task)
                    
            except Exception as e:
                import traceback
                traceback.print_exc()
                bg_task = db.query(BackgroundTask).filter(BackgroundTask.id == task_id).first()
                if bg_task:
                    bg_task.status = "failed"
                    bg_task.error = str(e)
                    bg_task.completed_at = datetime.utcnow()
                    db.commit()
            finally:
                db.close()
                if task_id in self._tasks:
                    del self._tasks[task_id]
        
        # 使用 asyncio.ensure_future 确保在正确的 event loop 中创建任务
        try:
            loop = asyncio.get_running_loop()
            self._tasks[task_id] = asyncio.ensure_future(run_task(), loop=loop)
        except RuntimeError:
            # 如果没有运行的 event loop，创建一个新的
            self._tasks[task_id] = asyncio.create_task(run_task())
    
    async def _run_generate_code(self, db: Session, bg_task: BackgroundTask):
        try:
            project = db.query(Project).filter(Project.id == bg_task.project_id).first()
            if not project:
                bg_task.status = "failed"
                bg_task.error = "项目不存在"
                bg_task.completed_at = datetime.utcnow()
                db.commit()
                return
            
            params = bg_task.input_params or {}
            template_id = params.get("template_id")
            model = params.get("model")
            
            bg_task.progress = 10
            bg_task.message = "准备生成代码..."
            db.commit()
            
            template_prompt = None
            if template_id:
                from app.models.template import Template
                template = db.query(Template).filter(Template.id == template_id).first()
                if template:
                    template_prompt = template.prompt
            
            bg_task.progress = 20
            bg_task.message = "AI 正在生成代码..."
            db.commit()
            
            manim_service = ManimService(db)
            code = await manim_service.generate_code(
                script=project.final_script,
                template_prompt=template_prompt,
                model=model,
                user_id=bg_task.user_id
            )
            
            bg_task.progress = 80
            bg_task.message = "代码验证中..."
            db.commit()
            
            fixed_code, warnings = manim_service.validate_code(code)
            
            if project.theme:
                import re
                fixed_code = re.sub(
                    r'INTRO_TITLE\s*=\s*"[^"]*"',
                    f'INTRO_TITLE = "{project.theme}"',
                    fixed_code
                )
            
            project.manim_code = fixed_code
            project.status = "code_generated"
            db.commit()
            
            bg_task.status = "completed"
            bg_task.progress = 100
            bg_task.message = "代码生成完成"
            bg_task.result = fixed_code
            bg_task.completed_at = datetime.utcnow()
            db.commit()
            
        except Exception as e:
            import traceback
            traceback.print_exc()
            bg_task.status = "failed"
            bg_task.error = str(e)
            bg_task.completed_at = datetime.utcnow()
            db.commit()
            raise
    
    async def _run_render_video(self, db: Session, bg_task: BackgroundTask):
        pass
    
    def get_task_status(self, db: Session, task_id: int) -> Optional[BackgroundTask]:
        return db.query(BackgroundTask).filter(BackgroundTask.id == task_id).first()
    
    def get_project_latest_task(self, db: Session, project_id: int, task_type: str) -> Optional[BackgroundTask]:
        return (
            db.query(BackgroundTask)
            .filter(BackgroundTask.project_id == project_id, BackgroundTask.task_type == task_type)
            .order_by(BackgroundTask.created_at.desc())
            .first()
        )


task_manager = BackgroundTaskManager()
