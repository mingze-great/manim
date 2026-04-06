from celery_app import celery_app
from .render import render_video_task


@celery_app.task(bind=True, name="app.tasks.render_video_celery")
def render_video_celery(self, task_id: int, project_id: int, template_id: int = None, custom_code: str = None):
    """Celery 后台渲染任务"""
    try:
        render_video_task(task_id, project_id, template_id, custom_code)
        return {"status": "completed", "task_id": task_id}
    except Exception as e:
        return {"status": "failed", "error": str(e), "task_id": task_id}