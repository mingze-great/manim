import os
import shutil
from datetime import datetime, timedelta
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.interval import IntervalTrigger

from app.database import SessionLocal
from app.models.project import Project, Conversation
from app.models.user import User

scheduler = AsyncIOScheduler()

VIDEO_RETENTION_HOURS = 3
CONVERSATION_RETENTION_HOURS = 24
TEMP_RETENTION_HOURS = 1

VIDEOS_DIR = "/opt/manim/backend/videos"
TEMP_DIR = "/tmp"


def cleanup_videos():
    """清理超过3小时的视频文件"""
    print(f"[Cleanup] Starting video cleanup at {datetime.utcnow()}")
    db = SessionLocal()
    try:
        cutoff = datetime.utcnow() - timedelta(hours=VIDEO_RETENTION_HOURS)
        
        projects = db.query(Project).filter(
            Project.video_url.isnot(None),
            Project.video_created_at.isnot(None),
            Project.video_created_at < cutoff
        ).all()
        
        cleaned_count = 0
        for project in projects:
            if project.video_url:
                filename = project.video_url.split('/')[-1]
                filepath = os.path.join(VIDEOS_DIR, filename)
                if os.path.exists(filepath):
                    os.remove(filepath)
                    cleaned_count += 1
                    print(f"[Cleanup] Deleted video: {filename}")
                
                project.video_url = None
                project.video_created_at = None
                project.status = "expired"
        
        db.commit()
        print(f"[Cleanup] Cleaned {cleaned_count} videos")
        
    except Exception as e:
        print(f"[Cleanup Error] Video cleanup failed: {e}")
        db.rollback()
    finally:
        db.close()


def cleanup_conversations():
    """清理超过24小时的对话内容"""
    print(f"[Cleanup] Starting conversation cleanup at {datetime.utcnow()}")
    db = SessionLocal()
    try:
        cutoff = datetime.utcnow() - timedelta(hours=CONVERSATION_RETENTION_HOURS)
        
        result = db.query(Conversation).filter(
            Conversation.created_at < cutoff
        ).delete()
        
        projects = db.query(Project).filter(
            Project.created_at < cutoff,
            Project.status.in_(["completed", "expired", "failed"])
        ).all()
        
        for project in projects:
            project.final_script = None
            project.manim_code = None
        
        db.commit()
        print(f"[Cleanup] Cleaned {result} conversations")
        
    except Exception as e:
        print(f"[Cleanup Error] Conversation cleanup failed: {e}")
        db.rollback()
    finally:
        db.close()


def cleanup_temp_files():
    """清理临时文件"""
    print(f"[Cleanup] Starting temp files cleanup at {datetime.utcnow()}")
    try:
        cutoff = datetime.utcnow() - timedelta(hours=TEMP_RETENTION_HOURS)
        cutoff_timestamp = cutoff.timestamp()
        
        cleaned_count = 0
        for item in os.listdir(TEMP_DIR):
            item_path = os.path.join(TEMP_DIR, item)
            if item.startswith('tmp') and os.path.isdir(item_path):
                try:
                    if os.path.getmtime(item_path) < cutoff_timestamp:
                        shutil.rmtree(item_path)
                        cleaned_count += 1
                except Exception as e:
                    print(f"[Cleanup] Failed to remove {item_path}: {e}")
        
        print(f"[Cleanup] Cleaned {cleaned_count} temp directories")
        
    except Exception as e:
        print(f"[Cleanup Error] Temp cleanup failed: {e}")


def init_scheduler():
    """初始化定时任务"""
    scheduler.add_job(
        cleanup_videos,
        IntervalTrigger(minutes=30),
        id="cleanup_videos",
        replace_existing=True
    )
    
    scheduler.add_job(
        cleanup_conversations,
        IntervalTrigger(hours=1),
        id="cleanup_conversations",
        replace_existing=True
    )
    
    scheduler.add_job(
        cleanup_temp_files,
        IntervalTrigger(minutes=10),
        id="cleanup_temp_files",
        replace_existing=True
    )
    
    print("[Scheduler] Cleanup jobs registered")


def start_scheduler():
    """启动定时任务调度器"""
    init_scheduler()
    scheduler.start()
    print("[Scheduler] Started")


def shutdown_scheduler():
    """关闭定时任务调度器"""
    scheduler.shutdown()
    print("[Scheduler] Shutdown")