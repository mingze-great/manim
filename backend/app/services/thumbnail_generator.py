import subprocess
import os
import uuid
import tempfile
import requests
from typing import Optional


def generate_thumbnail_from_video(
    video_path: str, 
    output_dir: str, 
    timestamp: str = "00:00:01"
) -> Optional[str]:
    """
    从视频提取指定时间点的帧作为缩略图
    
    Args:
        video_path: 视频文件路径
        output_dir: 输出目录
        timestamp: 提取时间点，默认第1秒
    
    Returns:
        生成的缩略图文件名，失败返回 None
    """
    try:
        # 确保输出目录存在
        os.makedirs(output_dir, exist_ok=True)
        
        # 生成输出文件名
        thumbnail_filename = f"thumb_{uuid.uuid4().hex[:8]}.jpg"
        output_path = os.path.join(output_dir, thumbnail_filename)
        
        # 使用 ffmpeg 提取帧
        cmd = [
            'ffmpeg',
            '-i', video_path,
            '-ss', timestamp,
            '-vframes', '1',
            '-q:v', '2',
            '-y',  # 覆盖已存在的文件
            output_path
        ]
        
        result = subprocess.run(
            cmd, 
            capture_output=True, 
            text=True,
            timeout=30
        )
        
        if result.returncode == 0 and os.path.exists(output_path):
            return thumbnail_filename
        else:
            print(f"FFmpeg error: {result.stderr}")
            return None
            
    except subprocess.TimeoutExpired:
        print("Thumbnail generation timeout")
        return None
    except Exception as e:
        print(f"Thumbnail generation error: {e}")
        return None


def generate_thumbnail_from_url(
    video_url: str,
    output_dir: str,
    timestamp: str = "00:00:01"
) -> Optional[str]:
    """
    从视频URL提取缩略图
    
    Args:
        video_url: 视频URL
        output_dir: 输出目录
        timestamp: 提取时间点
    
    Returns:
        生成的缩略图文件名，失败返回 None
    """
    try:
        # 下载视频到临时文件
        response = requests.get(video_url, stream=True, timeout=30)
        if response.status_code != 200:
            return None
        
        with tempfile.NamedTemporaryFile(suffix='.mp4', delete=False) as tmp:
            for chunk in response.iter_content(chunk_size=8192):
                tmp.write(chunk)
            tmp_path = tmp.name
        
        try:
            # 从临时文件生成缩略图
            result = generate_thumbnail_from_video(tmp_path, output_dir, timestamp)
            return result
        finally:
            # 清理临时文件
            if os.path.exists(tmp_path):
                os.remove(tmp_path)
                
    except Exception as e:
        print(f"Generate thumbnail from URL error: {e}")
        return None


def get_video_first_frame_url(video_path_or_url: str, base_url: str = "/api/thumbnails") -> Optional[str]:
    """
    获取视频第一帧的URL
    
    Args:
        video_path_or_url: 视频路径或URL
        base_url: 缩略图基础URL
    
    Returns:
        缩略图URL
    """
    # 如果是URL，提取文件名
    if video_path_or_url.startswith('http'):
        filename = os.path.basename(video_path_or_url.split('?')[0])
        name_without_ext = os.path.splitext(filename)[0]
        return f"{base_url}/{name_without_ext}_thumb.jpg"
    else:
        # 本地路径
        name_without_ext = os.path.splitext(os.path.basename(video_path_or_url))[0]
        return f"{base_url}/{name_without_ext}_thumb.jpg"
