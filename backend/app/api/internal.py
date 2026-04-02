from fastapi import APIRouter, HTTPException, Header
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
import json
import asyncio
import subprocess
import tempfile
import os
import uuid
import re
import shutil
import sys

from app.config import get_settings
from app.utils.cos_storage import cos_storage

router = APIRouter(prefix="/internal", tags=["internal"])
settings = get_settings()

RENDER_SEMAPHORE = asyncio.Semaphore(2)


def get_python_path() -> str:
    if sys.platform == "win32":
        return "python"
    else:
        paths = [
            "/root/miniconda3/envs/manim311/bin/python",
            "/opt/miniconda3/envs/manim311/bin/python"
        ]
        for path in paths:
            if os.path.exists(path):
                return path
        return paths[0]


class RenderRequest(BaseModel):
    project_id: int
    manim_code: str


def verify_internal_api_key(x_internal_key: str = Header(None)):
    if not x_internal_key or x_internal_key != settings.INTERNAL_API_KEY:
        raise HTTPException(status_code=401, detail="Invalid internal API key")
    return x_internal_key


@router.post("/render")
async def internal_render(
    request: RenderRequest,
    x_internal_key: str = Header(None)
):
    verify_internal_api_key(x_internal_key)
    
    async def event_generator():
        async with RENDER_SEMAPHORE:
            try:
                with tempfile.TemporaryDirectory() as temp_dir:
                    scene_name = "SceneName"
                    
                    if request.manim_code:
                        match = re.search(r'class\s+(\w+)\s*\(Scene\)', request.manim_code)
                        if match:
                            scene_name = match.group(1)
                    
                    code_content = request.manim_code
                    
                    try:
                        compile(code_content, '<string>', 'exec')
                    except SyntaxError as e:
                        yield f"data: {json.dumps({'type': 'error', 'content': '代码语法错误: ' + str(e)})}\n\n"
                        return
                    
                    manim_file = os.path.join(temp_dir, "scene.py")
                    with open(manim_file, "w", encoding="utf-8") as f:
                        f.write(code_content)
                    
                    yield f"data: {json.dumps({'type': 'info', 'content': '代码已保存到临时文件'})}\n\n"
                    
                    python_path = get_python_path()
                    
                    if sys.platform == "win32":
                        python_check = shutil.which(python_path)
                        if not python_check:
                            yield f"data: {json.dumps({'type': 'error', 'content': 'Python 未安装'})}\n\n"
                            return
                    elif not os.path.exists(python_path):
                        yield f"data: {json.dumps({'type': 'error', 'content': 'Python 环境不存在'})}\n\n"
                        return
                    
                    cmd = [
                        python_path,
                        "-m", "manim",
                        "-qh",
                        "--disable_caching",
                        "--media_dir", temp_dir,
                        "-o", "video",
                        manim_file,
                        scene_name
                    ]
                    
                    yield f"data: {json.dumps({'type': 'info', 'content': '开始渲染...'})}\n\n"
                    yield f"data: {json.dumps({'type': 'info', 'content': '-' * 50})}\n\n"
                    
                    process = None
                    try:
                        process = subprocess.Popen(
                            cmd,
                            stdout=subprocess.PIPE,
                            stderr=subprocess.STDOUT,
                            text=True,
                            bufsize=1
                        )
                        
                        for line in process.stdout:
                            line = line.strip()
                            if line:
                                yield f"data: {json.dumps({'type': 'output', 'content': line})}\n\n"
                                await asyncio.sleep(0.01)
                        
                        result = process.wait(timeout=600)
                        
                        yield f"data: {json.dumps({'type': 'info', 'content': '-' * 50})}\n\n"
                        
                        if result == 0:
                            video_files = []
                            for root, dirs, files in os.walk(temp_dir):
                                for file in files:
                                    if file.endswith(".mp4"):
                                        video_files.append(os.path.join(root, file))
                            
                            if video_files:
                                video_path = video_files[0]
                                
                                backend_dir = os.path.dirname(os.path.dirname(os.path.dirname(__file__)))
                                videos_dir = os.path.join(backend_dir, "videos")
                                os.makedirs(videos_dir, exist_ok=True)
                                
                                video_filename = f"{request.project_id}_{uuid.uuid4().hex[:8]}.mp4"
                                local_video_path = os.path.join(videos_dir, video_filename)
                                
                                shutil.move(video_path, local_video_path)
                                
                                video_url = None
                                if cos_storage.enabled:
                                    success, cos_key, cos_url = cos_storage.upload_file(
                                        local_video_path, 
                                        request.project_id, 
                                        0
                                    )
                                    if success and cos_url:
                                        video_url = cos_url
                                        try:
                                            os.remove(local_video_path)
                                        except:
                                            pass
                                
                                if not video_url:
                                    video_url = f"/api/videos/{video_filename}"
                                
                                # 回调新服务器更新数据库
                                try:
                                    import httpx
                                    async with httpx.AsyncClient(timeout=10.0) as client:
                                        await client.post(
                                            f"{settings.NEW_SERVER_URL}/api/tasks/internal/update-video",
                                            params={"project_id": request.project_id, "video_url": video_url},
                                            headers={"X-Internal-Key": settings.INTERNAL_API_KEY}
                                        )
                                        print(f"[Callback] Updated project {request.project_id} on new server")
                                except Exception as e:
                                    print(f"[Callback] Failed to update new server: {e}")
                                
                                yield f"data: {json.dumps({'type': 'success', 'content': '渲染完成！', 'video_url': video_url})}\n\n"
                            else:
                                yield f"data: {json.dumps({'type': 'error', 'content': '未找到视频文件'})}\n\n"
                        else:
                            yield f"data: {json.dumps({'type': 'error', 'content': f'渲染失败 (code: {result})'})}\n\n"
                            
                    except subprocess.TimeoutExpired:
                        if process:
                            process.kill()
                        yield f"data: {json.dumps({'type': 'error', 'content': '渲染超时 (10分钟)'})}\n\n"
                    except Exception as e:
                        yield f"data: {json.dumps({'type': 'error', 'content': f'渲染异常: {e}'})}\n\n"
            except Exception as e:
                import traceback
                traceback.print_exc()
                yield f"data: {json.dumps({'type': 'error', 'content': f'渲染异常: {str(e)}'})}\n\n"
    
    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
        }
    )


@router.get("/status")
async def internal_status(x_internal_key: str = Header(None)):
    verify_internal_api_key(x_internal_key)
    return {
        "status": "healthy",
        "max_concurrent_renders": 2,
        "server_type": "old"
    }