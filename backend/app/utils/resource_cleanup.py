import os
import shutil
import logging
from datetime import datetime, timedelta
from pathlib import Path
from typing import List, Dict

logger = logging.getLogger(__name__)


def cleanup_old_videos(
    videos_dir: str = "/opt/manim/backend/videos",
    days_to_keep: int = 30,
    max_total_size_gb: float = 10.0
) -> Dict:
    """清理旧视频文件
    
    Args:
        videos_dir: 视频目录
        days_to_keep: 保留天数
        max_total_size_gb: 最大总大小（GB）
    
    Returns:
        清理结果
    """
    videos_path = Path(videos_dir)
    
    if not videos_path.exists():
        return {'error': f'Videos directory not found: {videos_dir}'}
    
    # 获取所有 mp4 文件
    mp4_files = list(videos_path.glob("*.mp4"))
    
    # 排除 template_examples 目录中的文件（模板预览视频保留）
    mp4_files = [f for f in mp4_files if 'template_' not in f.name]
    
    # 计算总大小
    total_size = sum(f.stat().st_size for f in mp4_files if f.exists())
    max_size_bytes = max_total_size_gb * 1024 * 1024 * 1024
    
    # 按修改时间排序（旧的在前）
    files_sorted = sorted(
        mp4_files,
        key=lambda f: f.stat().st_mtime
    )
    
    deleted_files = []
    cutoff_time = datetime.now() - timedelta(days=days_to_keep)
    freed_space = 0
    
    for f in files_sorted:
        if not f.exists():
            continue
            
        file_size = f.stat().st_size
        mtime = datetime.fromtimestamp(f.stat().st_mtime)
        
        # 判断是否需要删除
        should_delete = False
        reason = ""
        
        # 超过保留天数
        if mtime < cutoff_time:
            should_delete = True
            reason = f"older than {days_to_keep} days"
        
        # 超过总大小限制
        elif total_size > max_size_bytes:
            should_delete = True
            reason = "exceeds size limit"
        
        if should_delete:
            try:
                f.unlink()
                deleted_files.append({
                    'path': str(f),
                    'size_mb': round(file_size / 1024 / 1024, 2),
                    'reason': reason,
                    'mtime': mtime.isoformat()
                })
                total_size -= file_size
                freed_space += file_size
                logger.info(f"Deleted video: {f.name} ({reason})")
            except Exception as e:
                logger.error(f"Failed to delete {f}: {e}")
    
    return {
        'deleted_count': len(deleted_files),
        'freed_space_mb': round(freed_space / 1024 / 1024, 2),
        'remaining_files': len(mp4_files) - len(deleted_files),
        'remaining_size_gb': round(total_size / 1024 / 1024 / 1024, 2),
        'deleted_files': deleted_files[:10]  # 只返回前10个
    }


def cleanup_temp_render_directories(
    videos_dir: str = "/opt/manim/backend/videos"
) -> Dict:
    """清理渲染临时目录
    
    Args:
        videos_dir: 视频目录
    
    Returns:
        清理结果
    """
    videos_path = Path(videos_dir)
    cleaned_dirs = []
    cleaned_size = 0
    
    # 清理 media 目录（manim 渲染临时文件）
    media_dir = videos_path / "media"
    if media_dir.exists():
        try:
            dir_size = sum(
                f.stat().st_size 
                for f in media_dir.rglob('*') 
                if f.is_file()
            )
            shutil.rmtree(media_dir)
            cleaned_dirs.append({
                'path': str(media_dir),
                'size_mb': round(dir_size / 1024 / 1024, 2)
            })
            cleaned_size += dir_size
            logger.info(f"Cleaned media directory: {media_dir}")
        except Exception as e:
            logger.error(f"Failed to clean media dir: {e}")
    
    # 清理临时 Python 文件
    temp_files = list(videos_path.glob("temp_*.py"))
    for temp_file in temp_files:
        try:
            temp_file.unlink()
            cleaned_dirs.append({'path': str(temp_file), 'size_mb': 0})
        except:
            pass
    
    return {
        'cleaned_count': len(cleaned_dirs),
        'freed_space_mb': round(cleaned_size / 1024 / 1024, 2),
        'cleaned_dirs': cleaned_dirs
    }


def cleanup_old_background_tasks(days_to_keep: int = 7) -> Dict:
    """清理旧的后台任务记录
    
    Args:
        days_to_keep: 保留天数
    
    Returns:
        清理结果
    """
    from app.database import SessionLocal
    from app.models.background_task import BackgroundTask
    
    db = SessionLocal()
    try:
        cutoff = datetime.utcnow() - timedelta(days=days_to_keep)
        
        # 统计要删除的记录数
        count_before = db.query(BackgroundTask).count()
        
        # 删除旧记录
        deleted = db.query(BackgroundTask).filter(
            BackgroundTask.created_at < cutoff,
            BackgroundTask.status.in_(['completed', 'failed'])
        ).delete()
        
        db.commit()
        
        count_after = db.query(BackgroundTask).count()
        
        # 清理卡住的任务（超过1小时的processing任务）
        stuck_cutoff = datetime.utcnow() - timedelta(hours=1)
        stuck_tasks = db.query(BackgroundTask).filter(
            BackgroundTask.status == 'processing',
            BackgroundTask.created_at < stuck_cutoff
        ).all()
        
        for task in stuck_tasks:
            task.status = 'failed'
            task.error = '任务超时，已自动标记为失败'
            task.completed_at = datetime.utcnow()
        
        if stuck_tasks:
            db.commit()
        
        return {
            'deleted_records': deleted,
            'stuck_tasks_marked_failed': len(stuck_tasks),
            'records_before': count_before,
            'records_after': count_after
        }
    except Exception as e:
        logger.error(f"Failed to cleanup background tasks: {e}")
        return {'error': str(e)}
    finally:
        db.close()


def cleanup_template_preview_cache(videos_dir: str = "/opt/manim/backend/videos") -> Dict:
    """清理模板预览视频缓存
    
    保留最新的预览视频，删除旧的
    """
    videos_path = Path(videos_dir)
    template_examples_dir = videos_path / "template_examples"
    
    if not template_examples_dir.exists():
        return {'message': 'No template examples directory'}
    
    # 获取所有模板预览视频
    preview_files = list(template_examples_dir.glob("template_*_preview.mp4"))
    
    # 按模板ID分组
    from collections import defaultdict
    by_template = defaultdict(list)
    for f in preview_files:
        # 提取模板ID（如 template_2_preview.mp4 -> 2）
        try:
            template_id = f.name.split('_')[1]
            by_template[template_id].append(f)
        except:
            pass
    
    # 对每个模板，保留最新的预览视频
    deleted = []
    for template_id, files in by_template.items():
        if len(files) > 1:
            # 按修改时间排序，保留最新的
            files.sort(key=lambda f: f.stat().st_mtime, reverse=True)
            for old_file in files[1:]:
                try:
                    old_file.unlink()
                    deleted.append(str(old_file))
                except:
                    pass
    
    return {
        'deleted_old_previews': len(deleted),
        'deleted_files': deleted
    }


def cleanup_all(
    days_to_keep_videos: int = 30,
    days_to_keep_tasks: int = 7,
    max_video_size_gb: float = 10.0
) -> Dict:
    """执行所有清理任务
    
    Args:
        days_to_keep_videos: 视频保留天数
        days_to_keep_tasks: 任务记录保留天数
        max_video_size_gb: 最大视频总大小
    
    Returns:
        清理结果
    """
    results = {
        'timestamp': datetime.utcnow().isoformat(),
        'videos': cleanup_old_videos(
            days_to_keep=days_to_keep_videos,
            max_total_size_gb=max_video_size_gb
        ),
        'temp_dirs': cleanup_temp_render_directories(),
        'background_tasks': cleanup_old_background_tasks(
            days_to_keep=days_to_keep_tasks
        ),
        'template_previews': cleanup_template_preview_cache()
    }
    
    return results


def get_storage_stats(videos_dir: str = "/opt/manim/backend/videos") -> Dict:
    """获取存储统计信息"""
    videos_path = Path(videos_dir)
    
    if not videos_path.exists():
        return {'error': f'Directory not found: {videos_dir}'}
    
    # 统计各类文件
    mp4_files = list(videos_path.glob("**/*.mp4"))
    
    total_size = 0
    user_videos_size = 0
    template_previews_size = 0
    other_size = 0
    
    for f in mp4_files:
        if not f.exists():
            continue
        size = f.stat().st_size
        total_size += size
        
        if 'template_' in f.name:
            template_previews_size += size
        elif f.parent.name == videos_path.name:
            user_videos_size += size
        else:
            other_size += size
    
    return {
        'total_videos': len(mp4_files),
        'total_size_gb': round(total_size / 1024 / 1024 / 1024, 2),
        'user_videos': {
            'count': len([f for f in mp4_files if 'template_' not in f.name and f.parent.name == videos_path.name]),
            'size_gb': round(user_videos_size / 1024 / 1024 / 1024, 2)
        },
        'template_previews': {
            'count': len([f for f in mp4_files if 'template_' in f.name]),
            'size_gb': round(template_previews_size / 1024 / 1024 / 1024, 2)
        },
        'other': {
            'size_gb': round(other_size / 1024 / 1024 / 1024, 2)
        }
    }