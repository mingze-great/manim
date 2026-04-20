"""视频缩略图生成服务"""
import os
import subprocess
import logging

logger = logging.getLogger(__name__)


def generate_thumbnail(video_path: str, output_path: str = None, timestamp: float = 1.0) -> str | None:
    """从视频提取缩略图
    
    Args:
        video_path: 视频文件路径
        output_path: 输出图片路径（默认与视频同目录）
        timestamp: 提取的时间点（秒），默认1.0秒
        
    Returns:
        str: 缩略图路径，失败返回 None
    """
    if not os.path.exists(video_path):
        logger.warning(f"Video not found: {video_path}")
        return None
    
    if output_path is None:
        base = os.path.splitext(video_path)[0]
        output_path = f"{base}_thumb.jpg"
    
    try:
        cmd = [
            'ffmpeg', '-y',
            '-ss', str(timestamp),
            '-i', video_path,
            '-vframes', '1',
            '-q:v', '2',
            '-vf', 'scale=320:-1',
            output_path
        ]
        result = subprocess.run(cmd, capture_output=True, timeout=10)
        if result.returncode == 0 and os.path.exists(output_path):
            logger.info(f"Thumbnail generated: {output_path}")
            return output_path
        else:
            logger.warning(f"ffmpeg failed: {result.stderr.decode()[:200]}")
            return None
    except FileNotFoundError:
        logger.warning("ffmpeg not found, skipping thumbnail generation")
        return None
    except Exception as e:
        logger.warning(f"Thumbnail generation failed: {e}")
        return None
