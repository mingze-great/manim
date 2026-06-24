import json
import shutil
import subprocess
import threading
import time
from datetime import datetime
from pathlib import Path
from typing import Any

from sqlalchemy.orm import Session

from app.database import SessionLocal
from app.models.ai_video import AiVideoJob, AiVideoProject, AiVideoVersion


STAGE_MESSAGES = {
    "pending": "任务已创建",
    "scripting": "正在理解文案",
    "scene_planning": "正在拆分视频场景",
    "tts_generating": "正在生成配音",
    "audio_processing": "正在处理音频",
    "rendering": "正在渲染视频",
    "uploading": "正在保存视频",
    "completed": "生成完成",
    "failed": "生成失败",
    "cancelled": "任务已取消",
}


class AiVideoService:
    def __init__(self) -> None:
        self.storage_root = Path("storage") / "ai-video" / "tasks"

    def create_generation_job(self, db: Session, user_id: int, payload: dict[str, Any]) -> AiVideoJob:
        title = str(payload.get("title") or self._derive_title(str(payload.get("script") or "")))
        project = AiVideoProject(
            user_id=user_id,
            title=title[:200],
            video_type=str(payload.get("videoType") or "knowledge_visualization"),
            aspect_ratio=str(payload.get("aspectRatio") or "16:9"),
            status="pending",
        )
        db.add(project)
        db.commit()
        db.refresh(project)

        job = AiVideoJob(
            user_id=user_id,
            project_id=project.id,
            job_type="generate",
            status="pending",
            stage="pending",
            progress=0,
            input_payload=json.dumps(payload, ensure_ascii=False),
        )
        db.add(job)
        db.commit()
        db.refresh(job)

        thread = threading.Thread(target=self._run_generation_job, args=(job.id,), daemon=True)
        thread.start()
        return job

    def get_project_json(self, version: AiVideoVersion | None) -> dict[str, Any] | None:
        if not version:
            return None
        try:
            return json.loads(version.project_json)
        except json.JSONDecodeError:
            return None

    def build_edit_plan(self, message: str) -> list[str]:
        normalized = message.strip()
        plan = []
        if any(word in normalized for word in ["开场", "前 5 秒", "前三秒", "冲击"]):
            plan.append("重写开场旁白，并增强前 5 秒镜头推进。")
        if any(word in normalized for word in ["节奏", "太慢", "压缩", "缩短"]):
            plan.append("压缩目标场景时长，并提高字幕信息密度。")
        if any(word in normalized for word in ["高级", "发布会", "科技", "风格"]):
            plan.append("将视觉风格调整为更克制的企业级科技风。")
        if any(word in normalized for word in ["字幕", "关键词"]):
            plan.append("降低字幕密度，只保留关键短语。")
        if not plan:
            plan = [
                "分析用户修改意图并定位到全片风格。",
                "更新 project.json 的风格、字幕和场景描述。",
                "生成一个新的可回退版本。",
            ]
        return plan

    def apply_edit_plan(self, db: Session, project: AiVideoProject, user_id: int, plan: list[str], message: str | None) -> AiVideoVersion:
        latest = (
            db.query(AiVideoVersion)
            .filter(AiVideoVersion.project_id == project.id)
            .order_by(AiVideoVersion.version_no.desc())
            .first()
        )
        project_json = self.get_project_json(latest) or self._default_project_json(project, {})
        project_json.setdefault("editHistory", []).append(
            {
                "message": message or "",
                "plan": plan,
                "createdAt": datetime.utcnow().isoformat(),
            }
        )
        project_json.setdefault("style", {})["motion"] = "refined"
        version_no = (latest.version_no if latest else 0) + 1
        version = AiVideoVersion(
            project_id=project.id,
            version_no=version_no,
            project_json=json.dumps(project_json, ensure_ascii=False, indent=2),
            output_url=latest.output_url if latest else None,
            cover_url=latest.cover_url if latest else None,
            change_summary="; ".join(plan),
            created_by=user_id,
        )
        db.add(version)
        db.commit()
        db.refresh(version)
        project.current_version_id = version.id
        project.updated_at = datetime.utcnow()
        db.commit()
        return version

    def _run_generation_job(self, job_id: int) -> None:
        db = SessionLocal()
        try:
            job = db.query(AiVideoJob).filter(AiVideoJob.id == job_id).first()
            if not job:
                return
            payload = json.loads(job.input_payload or "{}")
            task_dir = self.storage_root / f"job_{job.id}"
            (task_dir / "audio").mkdir(parents=True, exist_ok=True)
            (task_dir / "subtitles").mkdir(parents=True, exist_ok=True)
            (task_dir / "output").mkdir(parents=True, exist_ok=True)
            (task_dir / "logs").mkdir(parents=True, exist_ok=True)
            job.log_path = str(task_dir / "logs" / "render.log")
            db.commit()

            project = db.query(AiVideoProject).filter(AiVideoProject.id == job.project_id).first()
            if not project:
                return

            stages = [
                ("scripting", 12),
                ("scene_planning", 28),
                ("tts_generating", 48),
                ("audio_processing", 62),
                ("rendering", 82),
                ("uploading", 94),
            ]
            for stage, progress in stages:
                self._update_job(db, job, stage=stage, status=stage, progress=progress)
                self._append_log(job.log_path, STAGE_MESSAGES[stage])
                time.sleep(0.25)

            project_json = self._default_project_json(project, payload)
            (task_dir / "project.json").write_text(json.dumps(project_json, ensure_ascii=False, indent=2), encoding="utf-8")
            (task_dir / "scenes.json").write_text(json.dumps(project_json["scenes"], ensure_ascii=False, indent=2), encoding="utf-8")
            (task_dir / "subtitles" / "subtitles.srt").write_text(self._build_srt(project_json["scenes"]), encoding="utf-8")
            output_path = task_dir / "output" / "video.mp4"
            cover_path = task_dir / "output" / "cover.svg"
            self._render_placeholder_video(output_path, project.title, project.aspect_ratio)
            cover_path.write_text(self._build_cover_svg(project.title), encoding="utf-8")

            output_url = f"/api/ai-video/files/{job.id}/output/video.mp4"
            cover_url = f"/api/ai-video/files/{job.id}/output/cover.svg"
            version = AiVideoVersion(
                project_id=project.id,
                version_no=1,
                project_json=json.dumps(project_json, ensure_ascii=False, indent=2),
                output_url=output_url,
                cover_url=cover_url,
                change_summary="Initial AI video generation",
                created_by=job.user_id,
            )
            db.add(version)
            db.commit()
            db.refresh(version)

            project.current_version_id = version.id
            project.status = "completed"
            project.cover_url = cover_url
            project.updated_at = datetime.utcnow()
            job.output_url = output_url
            job.cover_url = cover_url
            job.completed_at = datetime.utcnow()
            self._update_job(db, job, stage="completed", status="completed", progress=100)
            db.commit()
        except Exception as exc:
            job = db.query(AiVideoJob).filter(AiVideoJob.id == job_id).first()
            if job:
                job.status = "failed"
                job.stage = "failed"
                job.error_message = str(exc)
                job.updated_at = datetime.utcnow()
                db.commit()
        finally:
            db.close()

    def _update_job(self, db: Session, job: AiVideoJob, *, stage: str, status: str, progress: int) -> None:
        job.stage = stage
        job.status = status
        job.progress = progress
        job.updated_at = datetime.utcnow()
        db.commit()

    def _default_project_json(self, project: AiVideoProject, payload: dict[str, Any]) -> dict[str, Any]:
        script = str(payload.get("script") or project.title)
        chunks = self._split_script(script)
        scenes = []
        for index, text in enumerate(chunks, start=1):
            scenes.append(
                {
                    "id": f"scene_{index:02d}",
                    "duration": 6,
                    "voiceText": text,
                    "subtitleText": text[:28],
                    "visual": {
                        "type": ["central_node", "timeline", "contrast_matrix"][min(index - 1, 2)],
                        "headline": text[:18] or project.title,
                        "nodes": ["洞察", "结构", "行动"],
                    },
                }
            )
        return {
            "title": project.title,
            "videoType": project.video_type,
            "aspectRatio": project.aspect_ratio,
            "style": {
                "theme": payload.get("style") or "futuristic",
                "palette": "teal_blue_gold",
                "motion": "cinematic",
                "subtitleDensity": payload.get("subtitleMode") or "keywords",
            },
            "voice": {
                "provider": payload.get("voiceProvider") or "cosyvoice",
                "speaker": payload.get("voiceId") or "中文女",
                "emotion": "confident",
                "speed": 1.0,
            },
            "scenes": scenes,
        }

    def _split_script(self, script: str) -> list[str]:
        normalized = " ".join(script.replace("\n", " ").split())
        if not normalized:
            return ["用一个清晰的问题开场。", "拆解核心观点。", "给出行动建议。"]
        parts = [part.strip(" 。.!?！？") for part in normalized.replace("。", ".").split(".") if part.strip()]
        if len(parts) >= 3:
            return parts[:3]
        while len(parts) < 3:
            parts.append(["拆解关键原因", "形成可执行结论", "给出下一步行动"][len(parts)])
        return parts[:3]

    def _derive_title(self, script: str) -> str:
        cleaned = " ".join(script.split())
        return cleaned[:24] or "AI 视频项目"

    def _build_srt(self, scenes: list[dict[str, Any]]) -> str:
        blocks = []
        cursor = 0
        for index, scene in enumerate(scenes, start=1):
            start = cursor
            end = cursor + int(scene.get("duration") or 6)
            blocks.append(
                f"{index}\n00:00:{start:02d},000 --> 00:00:{end:02d},000\n{scene.get('subtitleText') or ''}\n"
            )
            cursor = end
        return "\n".join(blocks)

    def _render_placeholder_video(self, output_path: Path, title: str, aspect_ratio: str) -> None:
        ffmpeg = shutil.which("ffmpeg")
        size = "1080x1920" if aspect_ratio == "9:16" else "1280x720"
        if ffmpeg:
            cmd = [
                ffmpeg,
                "-y",
                "-f",
                "lavfi",
                "-i",
                f"color=c=0f172a:s={size}:d=6",
                "-f",
                "lavfi",
                "-i",
                "sine=frequency=440:duration=6",
                "-shortest",
                "-c:v",
                "libx264",
                "-pix_fmt",
                "yuv420p",
                "-c:a",
                "aac",
                str(output_path),
            ]
            subprocess.run(cmd, check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, timeout=60)
            return
        output_path.write_bytes(b"")

    def _build_cover_svg(self, title: str) -> str:
        safe = title.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
        return f"""<svg xmlns="http://www.w3.org/2000/svg" width="1280" height="720" viewBox="0 0 1280 720">
<rect width="1280" height="720" fill="#0f172a"/>
<rect x="80" y="80" width="1120" height="560" rx="24" fill="#111827" stroke="#14b8a6" stroke-width="3"/>
<circle cx="170" cy="160" r="42" fill="#f59e0b"/>
<text x="120" y="350" fill="#f8fafc" font-size="54" font-family="Arial, sans-serif">{safe}</text>
<text x="120" y="430" fill="#67e8f9" font-size="28" font-family="Arial, sans-serif">AI Video Director Workspace</text>
</svg>"""

    def _append_log(self, path: str | None, line: str) -> None:
        if not path:
            return
        Path(path).parent.mkdir(parents=True, exist_ok=True)
        with open(path, "a", encoding="utf-8") as handle:
            handle.write(f"{datetime.utcnow().isoformat()} {line}\n")
