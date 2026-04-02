import asyncio
import json
import httpx
from typing import AsyncGenerator

from app.config import get_settings

settings = get_settings()


class RenderDispatcher:
    def __init__(self):
        self.old_server_url = settings.OLD_SERVER_URL
        self.internal_api_key = settings.INTERNAL_API_KEY
    
    async def dispatch_to_old_server(
        self, 
        project_id: int, 
        manim_code: str
    ) -> AsyncGenerator[str, None]:
        async with httpx.AsyncClient(timeout=600.0) as client:
            try:
                response = await client.post(
                    f"{self.old_server_url}/api/internal/render",
                    json={
                        "project_id": project_id,
                        "manim_code": manim_code
                    },
                    headers={
                        "X-Internal-Key": self.internal_api_key
                    }
                )
                
                async for line in response.aiter_lines():
                    if line.startswith("data: "):
                        yield line
                
            except httpx.ConnectError:
                yield f"data: {json.dumps({'type': 'error', 'content': '无法连接到旧服务器'})}\n\n"
            except Exception as e:
                yield f"data: {json.dumps({'type': 'error', 'content': f'分发渲染失败: {str(e)}'})}\n\n"
    
    async def check_old_server_status(self) -> dict:
        async with httpx.AsyncClient(timeout=10.0) as client:
            try:
                response = await client.get(
                    f"{self.old_server_url}/api/internal/status",
                    headers={
                        "X-Internal-Key": self.internal_api_key
                    }
                )
                return response.json()
            except Exception as e:
                return {"status": "unavailable", "error": str(e)}


render_dispatcher = RenderDispatcher()