from celery import Celery
from app.config import get_settings

settings = get_settings()

celery_app = Celery(
    "manim_platform",
    broker=settings.REDIS_URL,
    backend=settings.REDIS_URL,
    include=["app.tasks.celery_tasks"]
)

celery_app.conf.update(
    task_serializer="json",
    result_serializer="json",
    accept_content=["json"],
    timezone="Asia/Shanghai",
    enable_utc=True,
    task_track_started=True,
    task_time_limit=600,
    task_soft_time_limit=540,
)
