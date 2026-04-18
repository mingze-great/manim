from celery_app import celery_app
from .render import render_video_task, generate_code_task


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