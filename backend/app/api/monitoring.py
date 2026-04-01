from fastapi import APIRouter, Depends
from datetime import datetime
import logging

from app.api.auth import get_current_admin_user
from app.models.user import User
from app.utils.process_cleanup import cleanup_all as cleanup_processes, get_process_stats
from app.utils.resource_cleanup import cleanup_all as cleanup_resources, get_storage_stats

router = APIRouter(prefix="/monitoring", tags=["monitoring"])
logger = logging.getLogger(__name__)


@router.get("/health")
async def health_check():
    """健康检查"""
    return {
        "status": "healthy",
        "timestamp": datetime.utcnow().isoformat()
    }


@router.get("/system")
async def system_status():
    """系统状态"""
    import shutil
    import psutil
    
    # CPU
    cpu_percent = psutil.cpu_percent(interval=1)
    cpu_count = psutil.cpu_count()
    
    # 内存
    memory = psutil.virtual_memory()
    
    # 磁盘
    disk = shutil.disk_usage('/')
    
    return {
        "cpu": {
            "percent": cpu_percent,
            "count": cpu_count
        },
        "memory": {
            "total_gb": round(memory.total / 1024 / 1024 / 1024, 2),
            "used_gb": round(memory.used / 1024 / 1024 / 1024, 2),
            "available_gb": round(memory.available / 1024 / 1024 / 1024, 2),
            "percent": memory.percent
        },
        "disk": {
            "total_gb": round(disk.total / 1024 / 1024 / 1024, 2),
            "used_gb": round(disk.used / 1024 / 1024 / 1024, 2),
            "free_gb": round(disk.free / 1024 / 1024 / 1024, 2),
            "percent": round(disk.used / disk.total * 100, 2)
        }
    }


@router.get("/processes")
async def list_processes(current_user: User = Depends(get_current_admin_user)):
    """列出进程状态"""
    return get_process_stats()


@router.get("/storage")
async def storage_status(current_user: User = Depends(get_current_admin_user)):
    """存储状态"""
    return get_storage_stats()


@router.post("/cleanup/processes")
async def manual_cleanup_processes(
    max_age_seconds: int = 7200,
    current_user: User = Depends(get_current_admin_user)
):
    """手动清理进程"""
    logger.info(f"Manual process cleanup triggered by user {current_user.username}")
    
    result = cleanup_processes(max_process_age=max_age_seconds)
    
    return {
        "message": "Process cleanup completed",
        "result": result
    }


@router.post("/cleanup/resources")
async def manual_cleanup_resources(
    days_to_keep_videos: int = 30,
    days_to_keep_tasks: int = 7,
    max_video_size_gb: float = 10.0,
    current_user: User = Depends(get_current_admin_user)
):
    """手动清理资源"""
    logger.info(f"Manual resource cleanup triggered by user {current_user.username}")
    
    result = cleanup_resources(
        days_to_keep_videos=days_to_keep_videos,
        days_to_keep_tasks=days_to_keep_tasks,
        max_video_size_gb=max_video_size_gb
    )
    
    return {
        "message": "Resource cleanup completed",
        "result": result
    }


@router.post("/cleanup/all")
async def manual_cleanup_all(
    max_process_age_seconds: int = 7200,
    days_to_keep_videos: int = 30,
    days_to_keep_tasks: int = 7,
    current_user: User = Depends(get_current_admin_user)
):
    """手动执行所有清理"""
    logger.info(f"Manual full cleanup triggered by user {current_user.username}")
    
    # 清理进程
    process_result = cleanup_processes(max_process_age=max_process_age_seconds)
    
    # 清理资源
    resource_result = cleanup_resources(
        days_to_keep_videos=days_to_keep_videos,
        days_to_keep_tasks=days_to_keep_tasks
    )
    
    return {
        "message": "Full cleanup completed",
        "processes": process_result,
        "resources": resource_result,
        "timestamp": datetime.utcnow().isoformat()
    }