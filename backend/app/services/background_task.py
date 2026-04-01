import asyncio
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
import pathlib
from datetime import datetime
from typing import Optional, Dict, Any
from sqlalchemy.orm import Session
from app.database import SessionLocal
from app.models.background_task import BackgroundTask
from app.models.project import Project
from app.models.user import User
from app.models.template import Template
from app.services.manim import ManimService


def get_manim_python_path() -> str:
    """获取 Manim 环境的 Python 路径"""
    if sys.platform == "win32":
        return sys.executable
    else:
        return "/opt/miniconda3/envs/manim311/bin/python"


class BackgroundTaskManager:
    _instance = None
    _tasks: Dict[int, asyncio.Task] = {}
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance
    
    def create_task(
        self,
        db: Session,
        task_type: str,
        project_id: int,
        user_id: int,
        input_params: Optional[Dict[str, Any]] = None
    ) -> BackgroundTask:
        bg_task = BackgroundTask(
            task_type=task_type,
            project_id=project_id,
            user_id=user_id,
            input_params=input_params or {},
            status="pending",
            progress=0,
            message="任务已创建"
        )
        db.add(bg_task)
        db.commit()
        db.refresh(bg_task)
        return bg_task
    
    def start_task(self, task_id: int):
        if task_id in self._tasks:
            return
        
        async def run_task():
            db = SessionLocal()
            try:
                bg_task = db.query(BackgroundTask).filter(BackgroundTask.id == task_id).first()
                if not bg_task:
                    return
                
                bg_task.status = "processing"
                bg_task.started_at = datetime.utcnow()
                bg_task.message = "任务开始处理"
                db.commit()
                
                if bg_task.task_type == "generate_code":
                    await self._run_generate_code(db, bg_task)
                elif bg_task.task_type == "render_video":
                    await self._run_render_video(db, bg_task)
                elif bg_task.task_type == "render_template_preview":
                    await self._run_render_template_preview(db, bg_task)
                    
            except Exception as e:
                import traceback
                traceback.print_exc()
                bg_task = db.query(BackgroundTask).filter(BackgroundTask.id == task_id).first()
                if bg_task:
                    bg_task.status = "failed"
                    bg_task.error = str(e)
                    bg_task.completed_at = datetime.utcnow()
                    db.commit()
            finally:
                db.close()
                if task_id in self._tasks:
                    del self._tasks[task_id]
        
        # 使用 asyncio.ensure_future 确保在正确的 event loop 中创建任务
        try:
            loop = asyncio.get_running_loop()
            self._tasks[task_id] = asyncio.ensure_future(run_task(), loop=loop)
        except RuntimeError:
            # 如果没有运行的 event loop，创建一个新的
            self._tasks[task_id] = asyncio.create_task(run_task())
    
    async def _run_generate_code(self, db: Session, bg_task: BackgroundTask):
        try:
            project = db.query(Project).filter(Project.id == bg_task.project_id).first()
            if not project:
                bg_task.status = "failed"
                bg_task.error = "项目不存在"
                bg_task.completed_at = datetime.utcnow()
                db.commit()
                return
            
            params = bg_task.input_params or {}
            template_id = params.get("template_id")
            model = params.get("model")
            
            # 计算预估点数
            estimated_points = self._count_content_points(project.final_script or "")
            
            bg_task.progress = 10
            bg_task.message = f"准备生成代码（预计 {estimated_points} 个内容点）..."
            db.commit()
            
            template_prompt = None
            if template_id:
                from app.models.template import Template
                template = db.query(Template).filter(Template.id == template_id).first()
                if template:
                    template_prompt = template.prompt
            
            bg_task.progress = 20
            bg_task.message = "AI 正在生成代码..."
            db.commit()
            
            # 进度更新回调函数
            def progress_callback(progress: int):
                bg_task.progress = min(progress, 99)
                bg_task.message = "AI 正在生成代码..."
                db.commit()
            
            manim_service = ManimService(db)
            code = await manim_service.generate_code_with_progress(
                script=project.final_script,
                template_prompt=template_prompt,
                model=model,
                user_id=bg_task.user_id,
                progress_callback=progress_callback
            )
            
            bg_task.progress = 99
            bg_task.message = "代码验证中..."
            db.commit()
            
            fixed_code, warnings = manim_service.validate_code(code)
            
            if project.theme:
                import re
                fixed_code = re.sub(
                    r'INTRO_TITLE\s*=\s*"[^"]*"',
                    f'INTRO_TITLE = "{project.theme}"',
                    fixed_code
                )
            
            project.manim_code = fixed_code
            project.status = "code_generated"
            db.commit()
            
            bg_task.status = "completed"
            bg_task.progress = 100
            bg_task.message = "代码生成完成"
            bg_task.result = fixed_code
            bg_task.completed_at = datetime.utcnow()
            db.commit()
            
        except Exception as e:
            import traceback
            traceback.print_exc()
            bg_task.status = "failed"
            bg_task.error = str(e)
            bg_task.completed_at = datetime.utcnow()
            db.commit()
            raise
    
    def _count_content_points(self, script: str) -> int:
        """计算脚本中的内容点数"""
        import re
        if not script:
            return 5
        
        # 匹配多种格式的内容点
        patterns = [
            r'第\s*\d+\s*点',  # 第 1 点
            r'\d+\.\s*[^。\n]{5,}',  # 1. xxx（至少5个字符）
            r'###\s*第\s*\d+\s*点',  # ### 第 1 点
        ]
        
        for pattern in patterns:
            matches = re.findall(pattern, script)
            if matches:
                return len(matches)
        
        return 5  # 默认 5 个点
    
    async def _run_render_video(self, db: Session, bg_task: BackgroundTask):
        pass
    
    async def _run_render_template_preview(self, db: Session, bg_task: BackgroundTask):
        """渲染模板预览视频"""
        temp_dir = None
        try:
            template_id = bg_task.input_params.get("template_id")
            if not template_id:
                raise ValueError("缺少 template_id 参数")
            
            template = db.query(Template).filter(Template.id == template_id).first()
            if not template:
                raise ValueError(f"模板 {template_id} 不存在")
            
            bg_task.progress = 10
            bg_task.message = "准备渲染模板预览视频..."
            db.commit()
            
            code = template.code
            if not code:
                raise ValueError("模板代码为空")
            
            # 动态获取 Scene 类名
            scene_match = re.search(r'class\s+(\w+)\s*\(\s*Scene\s*\)', code)
            scene_name = scene_match.group(1) if scene_match else "SceneName"
            
            # 创建临时目录
            temp_dir = tempfile.mkdtemp(prefix=f"template_{template_id}_")
            
            # 写入代码文件
            manim_file = os.path.join(temp_dir, "scene.py")
            with open(manim_file, "w", encoding="utf-8") as f:
                f.write(code)
            
            bg_task.progress = 20
            bg_task.message = f"正在执行 Manim 渲染 (场景: {scene_name})..."
            db.commit()
            
            # 获取 Manim 环境的 Python 路径
            python_path = get_manim_python_path()
            
            # 构建命令
            cmd = [
                python_path, "-m", "manim",
                "-qm",  # 中等质量 720p30
                "--disable_caching",
                "--media_dir", temp_dir,
                "-o", f"template_{template_id}",
                manim_file,
                scene_name
            ]
            
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=300
            )
            
            if result.returncode != 0:
                error_msg = result.stderr or result.stdout or "未知渲染错误"
                raise RuntimeError(f"Manim 渲染失败: {error_msg[:500]}")
            
            bg_task.progress = 80
            bg_task.message = "正在处理渲染结果..."
            db.commit()
            
            # 查找生成的视频文件
            video_files = []
            for root, dirs, files in os.walk(temp_dir):
                for file in files:
                    if file.endswith(".mp4"):
                        video_files.append(os.path.join(root, file))
            
            if not video_files:
                raise RuntimeError("未找到生成的视频文件")
            
            # 移动到最终位置
            backend_dir = pathlib.Path(__file__).parent.parent
            videos_dir = backend_dir / "videos" / "template_examples"
            videos_dir.mkdir(parents=True, exist_ok=True)
            
            final_filename = f"template_{template_id}_preview.mp4"
            final_path = videos_dir / final_filename
            
            # 使用最新的视频文件
            latest_video = max(video_files, key=lambda x: os.path.getmtime(x))
            shutil.move(latest_video, str(final_path))
            
            # 更新数据库
            video_url = f"/api/videos/template_examples/{final_filename}"
            template.example_video_url = video_url
            db.commit()
            
            bg_task.status = "completed"
            bg_task.progress = 100
            bg_task.message = "模板预览视频渲染完成"
            bg_task.result = {"video_url": video_url, "template_id": template_id}
            bg_task.completed_at = datetime.utcnow()
            db.commit()
            
        except subprocess.TimeoutExpired:
            bg_task.status = "failed"
            bg_task.error = "渲染超时（超过5分钟）"
            bg_task.completed_at = datetime.utcnow()
            db.commit()
        except Exception as e:
            import traceback
            traceback.print_exc()
            bg_task.status = "failed"
            bg_task.error = str(e)
            bg_task.completed_at = datetime.utcnow()
            db.commit()
        finally:
            # 清理临时目录
            if temp_dir and os.path.exists(temp_dir):
                try:
                    shutil.rmtree(temp_dir)
                except Exception:
                    pass
    
    def get_task_status(self, db: Session, task_id: int) -> Optional[BackgroundTask]:
        return db.query(BackgroundTask).filter(BackgroundTask.id == task_id).first()
    
    def get_project_latest_task(self, db: Session, project_id: int, task_type: str) -> Optional[BackgroundTask]:
        return (
            db.query(BackgroundTask)
            .filter(BackgroundTask.project_id == project_id, BackgroundTask.task_type == task_type)
            .order_by(BackgroundTask.created_at.desc())
            .first()
        )


task_manager = BackgroundTaskManager()
