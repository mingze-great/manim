import asyncio

from celery_app import celery_app
from .render import render_video_task, generate_code_task, update_task_progress


@celery_app.task(
    bind=True, 
    name="app.tasks.render_video_celery",
    max_retries=2,
    default_retry_delay=60,
    acks_late=True,
    reject_on_worker_lost=True
)
def render_video_celery(self, task_id: int, project_id: int, template_id: int = None, custom_code: str = None):
    """Celery 后台渲染任务（支持重试）"""
    from app.database import SessionLocal
    from app.models.task import Task
    
    db = SessionLocal()
    try:
        # 检查任务是否已取消
        task = db.query(Task).filter(Task.id == task_id).first()
        if task and task.status == "cancelled":
            return {"status": "cancelled", "task_id": task_id}
        
        render_video_task(task_id, project_id, template_id, custom_code)
        return {"status": "completed", "task_id": task_id}
    except Exception as e:
        # 更新任务状态为失败
        try:
            task = db.query(Task).filter(Task.id == task_id).first()
            if task:
                task.status = "failed"
                task.error_message = f"{str(e)} (retry {self.request.retries}/{self.max_retries})"
                db.commit()
        except:
            pass
        
        # 尝试重试
        if self.request.retries < self.max_retries:
            raise self.retry(exc=e)
        return {"status": "failed", "error": str(e), "task_id": task_id}
    finally:
        db.close()


@celery_app.task(
    bind=True, 
    name="app.tasks.generate_code_celery",
    max_retries=2,
    default_retry_delay=30,
    acks_late=True,
    reject_on_worker_lost=True
)
def generate_code_celery(self, task_id: int, project_id: int, template_id: int = None, model: str = None):
    """Celery 后台代码生成任务（支持重试）"""
    from app.database import SessionLocal
    from app.models.task import Task
    
    db = SessionLocal()
    try:
        # 检查任务是否已取消
        task = db.query(Task).filter(Task.id == task_id).first()
        if task and task.status == "cancelled":
            return {"status": "cancelled", "task_id": task_id}
        
        generate_code_task(task_id, project_id, template_id, model)
        return {"status": "completed", "task_id": task_id}
    except Exception as e:
        # 更新任务状态为失败
        try:
            task = db.query(Task).filter(Task.id == task_id).first()
            if task:
                task.status = "failed"
                task.error_message = f"{str(e)} (retry {self.request.retries}/{self.max_retries})"
                db.commit()
        except:
            pass
        
        # 尝试重试
        if self.request.retries < self.max_retries:
            raise self.retry(exc=e)
        return {"status": "failed", "error": str(e), "task_id": task_id}
    finally:
        db.close()


@celery_app.task(
    bind=True,
    name="app.tasks.generate_chat_celery",
    max_retries=2,
    default_retry_delay=15,
    acks_late=True,
    reject_on_worker_lost=True
)
def generate_chat_celery(self, task_id: int, project_id: int, user_message: str, style_code: str = None):
    """Celery 后台对话生成任务（支持重试）"""
    from app.database import SessionLocal
    from app.models.task import Task
    from app.models.project import Project, Conversation
    from app.services.chat import ChatService

    db = SessionLocal()
    try:
        task = db.query(Task).filter(Task.id == task_id).first()
        if task and task.status == "cancelled":
            return {"status": "cancelled", "task_id": task_id}

        project = db.query(Project).filter(Project.id == project_id).first()
        if not project:
            update_task_progress(task_id, 0, "failed", error_message="Project not found")
            return {"status": "failed", "task_id": task_id}

        update_task_progress(task_id, 10, "processing", log="开始生成对话内容...\n")

        chat_service = ChatService(db)
        result = asyncio.run(
            chat_service.process_message(project_id, str(project.theme), user_message, style_code=style_code)
        )

        update_task_progress(task_id, 80, "processing", log="AI 响应生成完成，正在保存结果...\n")

        assistant_message = Conversation(
            project_id=project_id,
            role="assistant",
            content=result["content"]
        )
        db.add(assistant_message)

        if result.get("is_final"):
            project.status = "chatting_completed"
        elif project.status == "draft":
            project.status = "chatting"

        if result.get("final_script"):
            project.final_script = result["final_script"]

        db.commit()
        update_task_progress(task_id, 100, "completed", log="对话内容已保存\n")
        return {"status": "completed", "task_id": task_id}
    except Exception as e:
        try:
            task = db.query(Task).filter(Task.id == task_id).first()
            if task:
                task.status = "failed"
                task.error_message = f"{str(e)} (retry {self.request.retries}/{self.max_retries})"
                db.commit()
        except Exception:
            pass

        if self.request.retries < self.max_retries:
            raise self.retry(exc=e)
        return {"status": "failed", "error": str(e), "task_id": task_id}
    finally:
        db.close()


@celery_app.task(
    bind=True,
    name="app.tasks.generate_material_library_celery",
    max_retries=1,
    default_retry_delay=30,
    acks_late=True,
    reject_on_worker_lost=True,
    soft_time_limit=15000,
    time_limit=15600,
)
def generate_material_library_celery(self, generation_id: int, phase: str):
    from app.database import SessionLocal
    from app.models.material_library_generation import MaterialLibraryGeneration
    from app.services.material_library_generation import material_library_generation_service

    db = SessionLocal()
    try:
        generation = db.query(MaterialLibraryGeneration).filter(MaterialLibraryGeneration.id == generation_id).first()
        if not generation:
            return {"status": "missing", "generation_id": generation_id}
        if phase == "samples":
            asyncio.run(material_library_generation_service.generate_samples(db, generation))
        elif phase == "batch":
            asyncio.run(material_library_generation_service.generate_batch(db, generation))
        else:
            raise ValueError(f"未知素材库生成阶段: {phase}")
        return {"status": generation.status, "generation_id": generation_id}
    except Exception as exc:
        if self.request.retries < self.max_retries:
            raise self.retry(exc=exc)
        return {"status": "failed", "generation_id": generation_id, "error": str(exc)}
    finally:
        db.close()
