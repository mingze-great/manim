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
USER_VIDEO_RETENTION_DAYS = 30
BACKGROUND_TASK_RETENTION_DAYS = 7

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


def cleanup_expired_users():
    """检查并禁用过期用户"""
    print(f"[Cleanup] Checking expired users at {datetime.utcnow()}")
    db = SessionLocal()
    try:
        now = datetime.utcnow()
        
        expired_users = db.query(User).filter(
            User.expires_at.isnot(None),
            User.expires_at < now,
            User.is_active == True
        ).all()
        
        disabled_count = 0
        for user in expired_users:
            user.is_active = False
            disabled_count += 1
            print(f"[Cleanup] Disabled expired user: {user.username} (expired at {user.expires_at})")
        
        db.commit()
        if disabled_count > 0:
            print(f"[Cleanup] Disabled {disabled_count} expired users")
        
    except Exception as e:
        print(f"[Cleanup Error] Expired users check failed: {e}")
        db.rollback()
    finally:
        db.close()


def cleanup_processes():
    """清理僵尸进程和孤儿进程"""
    print(f"[Cleanup] Starting process cleanup at {datetime.utcnow()}")
    try:
        from app.utils.process_cleanup import cleanup_all
        result = cleanup_all(max_process_age=7200)  # 2小时
        
        zombies = result.get('zombies_cleaned', [])
        orphans = result.get('orphan_processes_killed', [])
        
        if zombies or orphans:
            print(f"[Cleanup] Cleaned {len(zombies)} zombie processes, killed {len(orphans)} orphan processes")
        
    except Exception as e:
        print(f"[Cleanup Error] Process cleanup failed: {e}")


def cleanup_old_videos():
    """清理旧的视频文件（保留30天）"""
    print(f"[Cleanup] Starting old videos cleanup at {datetime.utcnow()}")
    try:
        from app.utils.resource_cleanup import cleanup_old_videos, cleanup_temp_render_directories
        
        # 清理旧视频
        video_result = cleanup_old_videos(
            videos_dir=VIDEOS_DIR,
            days_to_keep=USER_VIDEO_RETENTION_DAYS,
            max_total_size_gb=10.0
        )
        
        # 清理临时渲染目录
        temp_result = cleanup_temp_render_directories(videos_dir=VIDEOS_DIR)
        
        freed_mb = video_result.get('freed_space_mb', 0) + temp_result.get('freed_space_mb', 0)
        deleted_count = video_result.get('deleted_count', 0)
        
        if deleted_count > 0 or freed_mb > 0:
            print(f"[Cleanup] Deleted {deleted_count} old videos, freed {freed_mb}MB")
        
    except Exception as e:
        print(f"[Cleanup Error] Old videos cleanup failed: {e}")


def cleanup_background_tasks():
    """清理旧的后台任务记录"""
    print(f"[Cleanup] Starting background tasks cleanup at {datetime.utcnow()}")
    try:
        from app.utils.resource_cleanup import cleanup_old_background_tasks
        
        result = cleanup_old_background_tasks(days_to_keep=BACKGROUND_TASK_RETENTION_DAYS)
        
        deleted = result.get('deleted_records', 0)
        stuck = result.get('stuck_tasks_marked_failed', 0)
        
        if deleted > 0 or stuck > 0:
            print(f"[Cleanup] Deleted {deleted} old task records, marked {stuck} stuck tasks as failed")
        
    except Exception as e:
        print(f"[Cleanup Error] Background tasks cleanup failed: {e}")


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
    
    scheduler.add_job(
        cleanup_expired_users,
        IntervalTrigger(hours=1),
        id="cleanup_expired_users",
        replace_existing=True
    )
    
    # 新增：进程清理（每小时）
    scheduler.add_job(
        cleanup_processes,
        IntervalTrigger(hours=1),
        id="cleanup_processes",
        replace_existing=True
    )
    
    # 新增：旧视频清理（每天凌晨3点）
    scheduler.add_job(
        cleanup_old_videos,
        IntervalTrigger(hours=24),
        id="cleanup_old_videos",
        replace_existing=True
    )
    
    # 新增：后台任务记录清理（每天）
    scheduler.add_job(
        cleanup_background_tasks,
        IntervalTrigger(hours=24),
        id="cleanup_background_tasks",
        replace_existing=True
    )
    
    from app.api.admin import update_daily_statistics
    scheduler.add_job(
        update_daily_statistics,
        IntervalTrigger(hours=1),
        id="update_daily_statistics",
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