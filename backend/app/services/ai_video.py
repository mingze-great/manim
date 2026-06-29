import json
import os
import re
import shutil
import threading
import urllib.error
import urllib.parse
import urllib.request
import wave
from datetime import datetime, timedelta
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

ACTIVE_JOB_STATUSES = {"pending", "scripting", "scene_planning", "tts_generating", "audio_processing", "rendering", "uploading"}
AI_VIDEO_STORAGE_ROOT = Path(os.getenv("AI_VIDEO_STORAGE_ROOT", Path(__file__).resolve().parents[1] / "storage" / "ai-video" / "tasks")).resolve()


CONTENT_TEMPLATES: dict[str, dict[str, Any]] = {
    "product_seed": {
        "label": "带货种草",
        "defaultStyle": "commerce_boost",
        "tone": "confident",
        "pace": "fast",
        "sceneTypes": ["commerce_hook", "compare_split", "benefit_stack", "use_case", "cta_burst"],
        "steps": [
            ("痛点开场", "指出用户正在遇到的购买问题", ["痛点", "需求", "差距"]),
            ("产品亮点", "展示核心卖点和可信理由", ["卖点", "场景", "证明"]),
            ("场景代入", "让用户看到使用后的变化", ["使用", "变化", "结果"]),
            ("行动引导", "给出明确购买或咨询理由", ["下单", "优惠", "行动"]),
        ],
    },
    "teaching": {
        "label": "教学讲解",
        "defaultStyle": "clean_explainer",
        "tone": "professional",
        "pace": "medium",
        "sceneTypes": ["question_board", "step_board", "diagram_flow", "example_card", "summary_cards"],
        "steps": [
            ("提出问题", "把学习难点讲清楚", ["问题", "目标", "误区"]),
            ("拆解原理", "解释背后的概念和逻辑", ["原理", "结构", "原因"]),
            ("操作步骤", "给出可执行步骤", ["第一步", "第二步", "例子"]),
            ("总结练习", "提炼口诀和练习建议", ["总结", "练习", "避坑"]),
        ],
    },
    "insight": {
        "label": "知识观点",
        "defaultStyle": "dark_editorial",
        "tone": "sharp",
        "pace": "medium",
        "sceneTypes": ["editorial_title", "quote_wall", "contrast_cards", "insight_card", "punchline"],
        "steps": [
            ("反常识开场", "用一句反直觉观点抓住注意力", ["反常识", "观点", "冲突"]),
            ("逻辑拆解", "解释观点为什么成立", ["逻辑", "原因", "案例"]),
            ("案例证明", "加入更具体的例子", ["案例", "证据", "细节"]),
            ("金句收束", "留下可传播的结论", ["结论", "金句", "行动"]),
        ],
    },
    "lifestyle": {
        "label": "生活分享",
        "defaultStyle": "lifestyle_magazine",
        "tone": "storytelling",
        "pace": "slow",
        "sceneTypes": ["magazine_cover", "photo_strip", "soft_caption", "detail_moment", "gentle_close"],
        "steps": [
            ("日常片段", "打开一个具体生活场景", ["地点", "物件", "瞬间"]),
            ("细节记录", "放大让人有画面感的细节", ["光线", "动作", "感受"]),
            ("情绪表达", "说出这个场景带来的情绪", ["情绪", "陪伴", "变化"]),
            ("温柔结尾", "留下轻盈的共鸣", ["共鸣", "分享", "明天"]),
        ],
    },
    "mood": {
        "label": "情绪共鸣",
        "defaultStyle": "warm_healing",
        "tone": "warm",
        "pace": "slow",
        "sceneTypes": ["soft_quote", "breathing_cards", "emotion_wave", "gentle_close"],
        "steps": [
            ("扎心开场", "说出用户不愿承认的情绪", ["疲惫", "委屈", "真实"]),
            ("场景代入", "让用户看见自己的处境", ["场景", "关系", "沉默"]),
            ("情绪释放", "帮用户命名感受", ["理解", "释放", "接纳"]),
            ("温柔建议", "给出一个低压力行动", ["选择", "照顾", "明天"]),
        ],
    },
    "briefing": {
        "label": "热点快评",
        "defaultStyle": "news_flash",
        "tone": "sharp",
        "pace": "fast",
        "sceneTypes": ["breaking_headline", "timeline", "conflict_map", "data_report", "discussion_prompt"],
        "steps": [
            ("事件一句话", "用一句话讲清楚发生了什么", ["事件", "时间", "人物"]),
            ("矛盾展开", "指出争议核心", ["矛盾", "影响", "风险"]),
            ("判断输出", "给出清晰观点", ["判断", "信号", "趋势"]),
            ("讨论引导", "抛出评论区问题", ["讨论", "选择", "立场"]),
        ],
    },
    "creator_talk": {
        "label": "个人 IP 口播",
        "defaultStyle": "viral_pop",
        "tone": "energetic",
        "pace": "fast",
        "sceneTypes": ["hook_flash", "creator_caption", "experience_card", "big_subtitle", "follow_prompt"],
        "steps": [
            ("人设开场", "用个人身份和判断打开", ["我发现", "经验", "判断"]),
            ("经验背书", "说出亲历或观察", ["经历", "方法", "教训"]),
            ("观点输出", "给出可记住的建议", ["观点", "选择", "行动"]),
            ("关注引导", "让用户知道为什么继续关注", ["价值", "系列", "关注"]),
        ],
    },
    "case_study": {
        "label": "案例复盘",
        "defaultStyle": "data_report",
        "tone": "professional",
        "pace": "medium",
        "sceneTypes": ["case_context", "decision_map", "metric_wall", "method_card", "summary_cards"],
        "steps": [
            ("背景设定", "交代案例发生的条件", ["背景", "约束", "目标"]),
            ("关键决策", "指出真正改变结果的动作", ["决策", "取舍", "执行"]),
            ("结果呈现", "呈现变化和指标", ["结果", "数据", "反馈"]),
            ("方法复用", "提炼可复制框架", ["方法", "框架", "复用"]),
        ],
    },
}


STYLE_PRESETS: dict[str, dict[str, Any]] = {
    "dark_editorial": {"label": "暗黑高级", "palette": "dark_orange", "motion": "cinematic", "density": "medium"},
    "clean_explainer": {"label": "极简白板", "palette": "paper_ink", "motion": "precise", "density": "high"},
    "tech_blueprint": {"label": "科技蓝图", "palette": "blueprint_cyan", "motion": "scan", "density": "high"},
    "commerce_boost": {"label": "电商促销", "palette": "commerce_orange", "motion": "snap", "density": "high"},
    "lifestyle_magazine": {"label": "杂志生活", "palette": "magazine_mono", "motion": "slow_pan", "density": "low"},
    "warm_healing": {"label": "温柔治愈", "palette": "warm_glow", "motion": "slow_breath", "density": "low"},
    "viral_pop": {"label": "短视频爆款", "palette": "pop_contrast", "motion": "snap", "density": "high"},
    "data_report": {"label": "数据报告", "palette": "data_green", "motion": "precise", "density": "high"},
    "news_flash": {"label": "热点快讯", "palette": "news_red", "motion": "fast_cut", "density": "high"},
    "premium_black_gold": {"label": "高级黑金", "palette": "black_gold", "motion": "cinematic", "density": "medium"},
}


class AiVideoService:
    def __init__(self) -> None:
        self.storage_root = AI_VIDEO_STORAGE_ROOT
        self.render_service_url = os.getenv("AI_VIDEO_RENDER_SERVICE_URL", "http://127.0.0.1:18787").rstrip("/")
        self.render_audio_root = Path(
            os.getenv(
                "AI_VIDEO_RENDER_AUDIO_ROOT",
                "../video-render-service/remotion-mind-video/public/generated-audio",
            )
        )
        self.render_timeout = int(os.getenv("AI_VIDEO_RENDER_TIMEOUT", "600"))
        self.cosyvoice_url = os.getenv("AI_VIDEO_COSYVOICE_URL", "http://127.0.0.1:50000").rstrip("/")
        self.cosyvoice_timeout = int(os.getenv("AI_VIDEO_COSYVOICE_TIMEOUT", "300"))
        self.cosyvoice_sample_rate = int(os.getenv("AI_VIDEO_COSYVOICE_SAMPLE_RATE", "22050"))
        self._running_jobs: set[int] = set()
        self._lock = threading.Lock()

    def create_generation_job(self, db: Session, user_id: int, payload: dict[str, Any]) -> AiVideoJob:
        payload = self._normalize_prompt_payload(payload)
        title_source = str(payload.get("script") or payload.get("creativeBrief") or payload.get("requirements") or "")
        title = str(payload.get("title") or self._derive_title(title_source))
        content_type = self._resolve_content_type(payload)
        project = AiVideoProject(
            user_id=user_id,
            title=title[:200],
            video_type=content_type,
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

    def retry_job(self, db: Session, source_job: AiVideoJob, user_id: int) -> AiVideoJob:
        payload = json.loads(source_job.input_payload or "{}")
        project = db.query(AiVideoProject).filter(AiVideoProject.id == source_job.project_id).first()
        if project:
            project.status = "pending"
            project.updated_at = datetime.utcnow()
        job = AiVideoJob(
            user_id=user_id,
            project_id=source_job.project_id,
            job_type="retry",
            status="pending",
            stage="pending",
            progress=0,
            input_payload=json.dumps(payload, ensure_ascii=False),
        )
        db.add(job)
        db.commit()
        db.refresh(job)
        threading.Thread(target=self._run_generation_job, args=(job.id,), daemon=True).start()
        return job

    def cancel_job(self, db: Session, job: AiVideoJob) -> AiVideoJob:
        if job.status in {"completed", "failed", "cancelled"}:
            return job
        job.status = "cancelled"
        job.stage = "cancelled"
        job.progress = min(job.progress or 0, 99)
        job.updated_at = datetime.utcnow()
        project = db.query(AiVideoProject).filter(AiVideoProject.id == job.project_id).first()
        if project and project.status not in {"completed", "failed"}:
            project.status = "cancelled"
            project.updated_at = datetime.utcnow()
        db.commit()
        db.refresh(job)
        return job

    def reconcile_stale_job(self, db: Session, job: AiVideoJob) -> AiVideoJob:
        if job.status not in ACTIVE_JOB_STATUSES:
            return job
        if job.id in self._running_jobs:
            return job
        stale_after = datetime.utcnow() - timedelta(minutes=10)
        checkpoint = job.updated_at or job.created_at
        if checkpoint and checkpoint > stale_after:
            return job
        job.status = "failed"
        job.stage = "failed"
        job.progress = min(job.progress or 0, 99)
        job.error_message = "生成任务已中断，可能是服务重启或部署导致后台线程退出。请点击重试重新生成。"
        job.updated_at = datetime.utcnow()
        project = db.query(AiVideoProject).filter(AiVideoProject.id == job.project_id).first()
        if project and project.status not in {"completed", "failed", "cancelled"}:
            project.status = "failed"
            project.updated_at = datetime.utcnow()
        db.commit()
        db.refresh(job)
        return job

    def get_render_capabilities(self) -> dict[str, Any]:
        ffmpeg_path = shutil.which("ffmpeg")
        return {
            "module": "ai-video",
            "storageRoot": str(self.storage_root),
            "renderServiceUrl": self.render_service_url,
            "renderService": self._probe_render_service(),
            "cosyVoiceService": self._probe_cosyvoice_service(),
            "ffmpeg": {"available": bool(ffmpeg_path), "path": ffmpeg_path},
            "isolation": {
                "apiNamespace": "/api/ai-video/*",
                "frontendRoutes": "/ai-video/*",
                "storage": "storage/ai-video/tasks/job_{id}",
                "mainProcessRendering": False,
            },
            "limits": {"renderConcurrency": 1, "cosyVoiceConcurrency": 1, "cosyVoiceRequired": True},
            "templates": self.get_templates(),
            "styles": self.get_styles(),
        }

    def get_templates(self) -> list[dict[str, Any]]:
        return [
            {
                "key": key,
                "name": value["label"],
                "defaultStyle": value["defaultStyle"],
                "sceneTypes": value["sceneTypes"],
                "steps": [step[0] for step in value["steps"]],
            }
            for key, value in CONTENT_TEMPLATES.items()
        ]

    def get_styles(self) -> list[dict[str, Any]]:
        return [{"key": key, **value} for key, value in STYLE_PRESETS.items()]

    def get_project_json(self, version: AiVideoVersion | None) -> dict[str, Any] | None:
        if not version:
            return None
        try:
            return json.loads(version.project_json)
        except json.JSONDecodeError:
            return None

    def build_storyboard_draft(self, payload: dict[str, Any]) -> dict[str, Any]:
        payload = self._normalize_prompt_payload(payload)
        title_source = str(payload.get("script") or payload.get("creativeBrief") or payload.get("requirements") or "")
        project = AiVideoProject(
            user_id=0,
            title=str(payload.get("title") or self._derive_title(title_source)),
            video_type=self._resolve_content_type(payload),
            aspect_ratio=str(payload.get("aspectRatio") or "16:9"),
        )
        project_json = self._default_project_json(project, payload)
        return {
            "projectJson": project_json,
            "scenes": project_json["scenes"],
            "recommendations": self._draft_recommendations(project_json),
        }

    def build_edit_plan(self, message: str) -> list[str]:
        patch = self._parse_edit_intent(message)
        plan: list[str] = []
        if patch.get("contentType"):
            plan.append(f"切换为「{CONTENT_TEMPLATES.get(patch['contentType'], {}).get('label', patch['contentType'])}」叙事结构。")
        if patch.get("visualStyle"):
            plan.append(f"切换为「{STYLE_PRESETS.get(patch['visualStyle'], {}).get('label', patch['visualStyle'])}」视觉风格。")
        if patch.get("pace"):
            plan.append(f"把整体节奏调整为 {patch['pace']}。")
        if patch.get("subtitleMode"):
            plan.append(f"字幕密度调整为 {patch['subtitleMode']}。")
        if patch.get("sceneType"):
            plan.append(f"将相关分镜画面切换为 {patch['sceneType']}。")
        if patch.get("openingEffect") == "impact":
            plan.append("强化首幕开场钩子：高冲击转场、快推镜头、强视觉节奏。")
        if patch.get("visualIntensity"):
            plan.append(f"将整体动效强度调整为 {patch['visualIntensity']}。")
        if patch.get("regenerateScenes"):
            plan.append("按当前文案和新导演要求重新拆分分镜，而不是沿用旧分镜。")
        if not plan:
            plan = [
                "理解修改要求并更新 project.json 的结构化导演参数。",
                "调整分镜画面类型、字幕密度、节奏和视觉风格。",
                "生成一个新的可回退版本，并重新渲染成片。",
            ]
        return plan

    def apply_edit_plan(
        self,
        db: Session,
        project: AiVideoProject,
        user_id: int,
        plan: list[str],
        message: str | None,
    ) -> tuple[AiVideoVersion, AiVideoJob]:
        latest = (
            db.query(AiVideoVersion)
            .filter(AiVideoVersion.project_id == project.id)
            .order_by(AiVideoVersion.version_no.desc())
            .first()
        )
        project_json = self.get_project_json(latest) or self._default_project_json(project, {})
        project_json = self._apply_edit_to_project_json(project_json, message or "")
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
        project.video_type = project_json.get("videoType") or project.video_type
        project.updated_at = datetime.utcnow()
        db.commit()

        payload = self._payload_from_project_json(project_json)
        director = project_json.get("director") if isinstance(project_json.get("director"), dict) else {}
        payload["editDirective"] = director.get("editDirective") or message or ""
        if not director.get("regeneratedScenes"):
            payload["draftScenes"] = project_json.get("scenes") or []
        retry = AiVideoJob(
            user_id=user_id,
            project_id=project.id,
            job_type="edit_render",
            status="pending",
            stage="pending",
            progress=0,
            input_payload=json.dumps(payload, ensure_ascii=False),
        )
        db.add(retry)
        db.commit()
        db.refresh(retry)
        threading.Thread(target=self._run_generation_job, args=(retry.id,), daemon=True).start()
        return version, retry

    def rollback_project_version(self, db: Session, project: AiVideoProject, version_id: int) -> AiVideoVersion:
        version = (
            db.query(AiVideoVersion)
            .filter(AiVideoVersion.project_id == project.id, AiVideoVersion.id == version_id)
            .first()
        )
        if not version:
            raise ValueError("Version not found")
        project.current_version_id = version.id
        project.cover_url = version.cover_url
        project.status = "completed"
        project.updated_at = datetime.utcnow()
        db.commit()
        db.refresh(version)
        return version

    def _run_generation_job(self, job_id: int) -> None:
        with self._lock:
            if job_id in self._running_jobs:
                return
            self._running_jobs.add(job_id)
        db = SessionLocal()
        try:
            job = db.query(AiVideoJob).filter(AiVideoJob.id == job_id).first()
            if not job:
                return
            payload = json.loads(job.input_payload or "{}")
            task_dir = self.storage_root / f"job_{job.id}"
            for child in ["audio", "subtitles", "output", "logs"]:
                (task_dir / child).mkdir(parents=True, exist_ok=True)
            job.log_path = str(task_dir / "logs" / "render.log")
            db.commit()

            project = db.query(AiVideoProject).filter(AiVideoProject.id == job.project_id).first()
            if not project:
                return
            project.status = "rendering"
            db.commit()

            for stage, progress in [("scripting", 12), ("scene_planning", 28), ("tts_generating", 48)]:
                db.refresh(job)
                if job.status == "cancelled":
                    self._append_log(job.log_path, STAGE_MESSAGES["cancelled"])
                    return
                self._update_job(db, job, stage=stage, status=stage, progress=progress)
                self._append_log(job.log_path, STAGE_MESSAGES[stage])

            project_json = self._default_project_json(project, payload)
            audio_scenes = self._generate_cosyvoice_audio(project_json, task_dir, job.log_path, payload)
            self._update_job(db, job, stage="audio_processing", status="audio_processing", progress=62)
            self._append_log(job.log_path, STAGE_MESSAGES["audio_processing"])

            (task_dir / "project.json").write_text(json.dumps(project_json, ensure_ascii=False, indent=2), encoding="utf-8")
            (task_dir / "scenes.json").write_text(json.dumps(project_json["scenes"], ensure_ascii=False, indent=2), encoding="utf-8")
            (task_dir / "subtitles" / "subtitles.srt").write_text(self._build_srt(project_json["scenes"]), encoding="utf-8")

            self._update_job(db, job, stage="rendering", status="rendering", progress=82)
            self._append_log(job.log_path, STAGE_MESSAGES["rendering"])
            output_path = task_dir / "output" / "video.mp4"
            render_result = self._render_with_external_service(
                payload,
                audio_scenes,
                project_json.get("scenes") or [],
                output_path,
                job.log_path,
            )
            if not render_result.get("ok"):
                raise RuntimeError(f"Remotion 渲染失败: {render_result.get('message')}")
            project_json["render"] = {
                "provider": render_result.get("provider", "external_remotion_cosyvoice"),
                "externalService": self.render_service_url,
                "message": render_result.get("message"),
            }
            (task_dir / "project.json").write_text(json.dumps(project_json, ensure_ascii=False, indent=2), encoding="utf-8")

            cover_path = task_dir / "output" / "cover.svg"
            cover_path.write_text(self._build_cover_svg(project.title, project_json), encoding="utf-8")
            output_url = f"/api/ai-video/files/{job.id}/output/video.mp4"
            cover_url = f"/api/ai-video/files/{job.id}/output/cover.svg"
            latest = (
                db.query(AiVideoVersion)
                .filter(AiVideoVersion.project_id == project.id)
                .order_by(AiVideoVersion.version_no.desc())
                .first()
            )
            version_no = (latest.version_no if latest and job.job_type == "edit_render" else 0) + 1
            version = AiVideoVersion(
                project_id=project.id,
                version_no=version_no,
                project_json=json.dumps(project_json, ensure_ascii=False, indent=2),
                output_url=output_url,
                cover_url=cover_url,
                change_summary="AI video render" if job.job_type != "edit_render" else "对话修改后重新渲染",
                created_by=job.user_id,
            )
            db.add(version)
            db.commit()
            db.refresh(version)

            project.current_version_id = version.id
            project.status = "completed"
            project.cover_url = cover_url
            project.video_type = project_json.get("videoType") or project.video_type
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
            with self._lock:
                self._running_jobs.discard(job_id)
            db.close()

    def _default_project_json(self, project: AiVideoProject, payload: dict[str, Any]) -> dict[str, Any]:
        payload = self._normalize_prompt_payload(payload)
        payload.setdefault("title", project.title)
        content_type = self._resolve_content_type(payload, fallback=project.video_type)
        template = CONTENT_TEMPLATES.get(content_type, CONTENT_TEMPLATES["insight"])
        visual_style = self._resolve_visual_style(payload, template)
        style_preset = STYLE_PRESETS.get(visual_style, STYLE_PRESETS["dark_editorial"])
        pace = str(payload.get("pace") or template.get("pace") or "medium")
        tone = str(payload.get("tone") or template.get("tone") or "professional")
        platform = str(payload.get("targetPlatform") or "douyin")
        subtitle_mode = str(payload.get("subtitleMode") or style_preset.get("density") or "keywords")
        visual_intensity = str(payload.get("visualIntensity") or payload.get("motionIntensity") or self._default_visual_intensity(visual_style, pace))
        opening_effect = str(payload.get("openingEffect") or self._default_opening_effect(visual_style, pace))
        script = str(payload.get("script") or payload.get("creativeBrief") or payload.get("requirements") or payload.get("prompt") or project.title)
        script_source = str(payload.get("scriptSource") or ("user" if str(payload.get("script") or "").strip() else "generated"))

        draft_scenes = payload.get("draftScenes")
        if isinstance(draft_scenes, list) and draft_scenes:
            scenes = self._normalize_draft_scenes(draft_scenes, content_type, visual_style, pace)
        else:
            scenes = self._build_scenes(script, payload, content_type, visual_style, pace, project.title, script_source)

        return {
            "title": project.title,
            "videoType": content_type,
            "aspectRatio": project.aspect_ratio,
            "platform": platform,
            "goal": payload.get("goal") or payload.get("customPrompt") or "完成一条可发布的视频",
            "prompt": payload.get("prompt") or payload.get("creativeBrief") or payload.get("requirements") or "",
            "requirements": payload.get("requirements") or payload.get("creativeBrief") or "",
            "creativeBrief": payload.get("creativeBrief") or payload.get("requirements") or "",
            "scriptSource": script_source,
            "customPrompt": payload.get("customPrompt") or "",
            "style": {
                "theme": visual_style,
                "label": style_preset["label"],
                "palette": style_preset["palette"],
                "motion": self._motion_for_pace(pace, style_preset),
                "visualIntensity": visual_intensity,
                "openingEffect": opening_effect,
                "subtitleDensity": subtitle_mode,
                "tone": tone,
            },
            "voice": {
                "provider": payload.get("voiceProvider") or "cosyvoice",
                "speaker": payload.get("voiceId") or "中文女",
                "emotion": tone,
                "speed": {"fast": 1.08, "medium": 1.0, "slow": 0.92}.get(pace, 1.0),
            },
            "director": {
                "template": template["label"],
                "sceneCount": len(scenes),
                "editable": True,
                "sceneRegistry": sorted({scene.get("visual", {}).get("type", "") for scene in scenes}),
            },
            "scenes": scenes,
        }

    def _build_scenes(
        self,
        script: str,
        payload: dict[str, Any],
        content_type: str,
        visual_style: str,
        pace: str,
        project_title: str = "",
        script_source: str = "generated",
    ) -> list[dict[str, Any]]:
        template = CONTENT_TEMPLATES.get(content_type, CONTENT_TEMPLATES["insight"])
        requested_count = int(payload.get("sceneCount") or 0)
        scene_count = requested_count if requested_count else self._infer_scene_count(payload, template)
        chunks = self._split_script(script, scene_count, content_type, allow_prompt_expansion=script_source != "user")
        scene_types = template["sceneTypes"]
        steps = template["steps"]
        scenes: list[dict[str, Any]] = []
        opening_effect = str(payload.get("openingEffect") or self._default_opening_effect(visual_style, pace))
        visual_intensity = str(payload.get("visualIntensity") or self._default_visual_intensity(visual_style, pace))
        edit_directive = str(payload.get("editDirective") or payload.get("customPrompt") or payload.get("goal") or "")
        for index in range(scene_count):
            text = chunks[index] if index < len(chunks) else self._fallback_sentence(index, content_type)
            step = steps[min(index, len(steps) - 1)]
            scene_type = scene_types[index % len(scene_types)]
            if index == 0 and script_source != "user":
                text = self._strengthen_opening_hook(text, content_type, payload)
            target_seconds = int(payload.get("targetSeconds") or 0)
            min_scene_seconds = max(0, target_seconds // scene_count) if target_seconds else 0
            media = self._media_for_scene(content_type, visual_style, text, index)
            layout_variant = self._layout_variant_for_scene(content_type, visual_style, scene_type, text, index, edit_directive)
            energy_pattern = self._energy_pattern_for_scene(scene_type, layout_variant, text, index)
            scenes.append(
                {
                    "id": f"scene_{index + 1:02d}",
                    "duration": max(self._scene_duration_for_pace(pace, text), min_scene_seconds),
                    "voiceText": text,
                    "subtitleText": self._display_text_for_scene(text, step[0], index),
                    "intent": step[1],
                    "cta": self._cta_for_scene(index, scene_count, content_type),
                    "visual": {
                        "type": scene_type,
                        "headline": self._headline_for_scene(step[0], text, index),
                        "openingTitle": self._opening_title_for_scene(payload, project_title=project_title, text=text) if index == 0 else "",
                        "nodes": self._keywords_for_text(text, list(step[2])),
                        "layout": visual_style,
                        "layoutVariant": layout_variant,
                        "transition": "impact" if index == 0 and opening_effect == "impact" else self._transition_for_scene(scene_type, index),
                        "camera": "impact_zoom" if index == 0 and opening_effect == "impact" else self._camera_for_style(visual_style, pace),
                        "effect": "opening_impact" if index == 0 and opening_effect == "impact" else "",
                        "intensity": visual_intensity,
                        "energyPattern": energy_pattern,
                        "assetPrompt": self._asset_prompt_for_scene(content_type, visual_style, text, step[0], layout_variant),
                        "media": media,
                    },
                }
            )
        return scenes

    def _media_for_scene(self, content_type: str, visual_style: str, text: str, index: int) -> dict[str, Any]:
        theme_keywords = {
            "product_seed": ["product", "skincare", "beauty", "desk", "shopping"],
            "teaching": ["notebook", "diagram", "learning", "whiteboard"],
            "lifestyle": ["lifestyle", "home", "morning", "coffee"],
            "briefing": ["news", "city", "business", "data"],
            "creator_talk": ["studio", "creator", "microphone", "portrait"],
            "case_study": ["business", "analytics", "meeting", "chart"],
            "mood": ["soft light", "window", "healing", "calm"],
        }
        keyword = theme_keywords.get(content_type, ["abstract", "creative", "studio"])[index % len(theme_keywords.get(content_type, ["abstract"]))]
        return {
            "kind": "photo",
            "query": keyword,
            "src": self._stock_image_url(content_type, index),
            "blend": "overlay" if visual_style in {"premium_black_gold", "dark_editorial"} else "soft",
        }

    def _stock_image_url(self, content_type: str, index: int) -> str:
        pools = {
            "product_seed": [
                "https://images.unsplash.com/photo-1596462502278-27bfdc403348?auto=format&fit=crop&w=1280&q=85",
                "https://images.unsplash.com/photo-1522335789203-aabd1fc54bc9?auto=format&fit=crop&w=1280&q=85",
                "https://images.unsplash.com/photo-1556228578-8c89e6adf883?auto=format&fit=crop&w=1280&q=85",
                "https://images.unsplash.com/photo-1556228720-195a672e8a03?auto=format&fit=crop&w=1280&q=85",
            ],
            "teaching": [
                "https://images.unsplash.com/photo-1516321318423-f06f85e504b3?auto=format&fit=crop&w=1280&q=85",
                "https://images.unsplash.com/photo-1434030216411-0b793f4b4173?auto=format&fit=crop&w=1280&q=85",
                "https://images.unsplash.com/photo-1454165804606-c3d57bc86b40?auto=format&fit=crop&w=1280&q=85",
            ],
            "lifestyle": [
                "https://images.unsplash.com/photo-1500530855697-b586d89ba3ee?auto=format&fit=crop&w=1280&q=85",
                "https://images.unsplash.com/photo-1497215728101-856f4ea42174?auto=format&fit=crop&w=1280&q=85",
                "https://images.unsplash.com/photo-1511988617509-a57c8a288659?auto=format&fit=crop&w=1280&q=85",
            ],
            "briefing": [
                "https://images.unsplash.com/photo-1495020689067-958852a7765e?auto=format&fit=crop&w=1280&q=85",
                "https://images.unsplash.com/photo-1520607162513-77705c0f0d4a?auto=format&fit=crop&w=1280&q=85",
                "https://images.unsplash.com/photo-1551288049-bebda4e38f71?auto=format&fit=crop&w=1280&q=85",
            ],
            "creator_talk": [
                "https://images.unsplash.com/photo-1497366754035-f200968a6e72?auto=format&fit=crop&w=1280&q=85",
                "https://images.unsplash.com/photo-1516321497487-e288fb19713f?auto=format&fit=crop&w=1280&q=85",
            ],
            "case_study": [
                "https://images.unsplash.com/photo-1551288049-bebda4e38f71?auto=format&fit=crop&w=1280&q=85",
                "https://images.unsplash.com/photo-1460925895917-afdab827c52f?auto=format&fit=crop&w=1280&q=85",
            ],
        }
        selected = pools.get(content_type, [
            "https://images.unsplash.com/photo-1497366811353-6870744d04b2?auto=format&fit=crop&w=1280&q=85",
            "https://images.unsplash.com/photo-1500530855697-b586d89ba3ee?auto=format&fit=crop&w=1280&q=85",
        ])
        return selected[index % len(selected)]

    def _strengthen_opening_hook(self, text: str, content_type: str, payload: dict[str, Any]) -> str:
        cleaned = str(text or "").strip()
        custom = f"{payload.get('prompt') or ''} {payload.get('customPrompt') or ''}"
        if any(mark in cleaned for mark in ["?", "？", "！", "!"]) or "开头" in custom:
            return cleaned
        starters = {
            "product_seed": "别急着买，先看这个痛点：",
            "teaching": "很多新手卡住，其实只差这一步：",
            "lifestyle": "这个瞬间，可能你也经历过：",
            "briefing": "这件事真正值得关注的不是表面：",
            "creator_talk": "我先说结论，很多人都想反了：",
            "case_study": "这个案例最关键的转折点在这里：",
            "mood": "如果你最近很累，先听这句话：",
        }
        starter = starters.get(content_type, "先别划走，这个观点很重要：")
        return f"{starter}{cleaned}"

    def _normalize_draft_scenes(
        self,
        draft_scenes: list[dict[str, Any]],
        content_type: str,
        visual_style: str,
        pace: str,
    ) -> list[dict[str, Any]]:
        template = CONTENT_TEMPLATES.get(content_type, CONTENT_TEMPLATES["insight"])
        normalized: list[dict[str, Any]] = []
        for index, raw in enumerate(draft_scenes[:8]):
            visual = raw.get("visual") if isinstance(raw.get("visual"), dict) else {}
            text = str(raw.get("voiceText") or raw.get("subtitleText") or raw.get("text") or "").strip()
            if not text:
                continue
            step = template["steps"][min(index, len(template["steps"]) - 1)]
            scene_type = visual.get("type") or raw.get("sceneType") or template["sceneTypes"][index % len(template["sceneTypes"])]
            layout_variant = visual.get("layoutVariant") or self._layout_variant_for_scene(content_type, visual_style, scene_type, text, index, "")
            normalized.append(
                {
                    "id": raw.get("id") or f"scene_{index + 1:02d}",
                    "duration": raw.get("duration") or self._scene_duration_for_pace(pace, text),
                    "voiceText": text,
                    "subtitleText": self._display_text_for_scene(raw.get("subtitleText") or text, step[0], index),
                    "intent": raw.get("intent") or step[1],
                    "cta": raw.get("cta") or self._cta_for_scene(index, len(draft_scenes), content_type),
                    "visual": {
                        "type": scene_type,
                        "headline": visual.get("headline") or raw.get("title") or self._headline_for_scene(step[0], text, index),
                        "openingTitle": visual.get("openingTitle") or raw.get("openingTitle") or "",
                        "nodes": visual.get("nodes") or raw.get("keywords") or self._keywords_for_text(text, list(step[2])),
                        "layout": visual.get("layout") or visual_style,
                        "layoutVariant": layout_variant,
                        "transition": visual.get("transition") or self._transition_for_scene(scene_type, index),
                        "camera": visual.get("camera") or self._camera_for_style(visual_style, pace),
                        "effect": visual.get("effect") or "",
                        "intensity": visual.get("intensity") or "high",
                        "energyPattern": visual.get("energyPattern") or self._energy_pattern_for_scene(scene_type, layout_variant, text, index),
                        "assetPrompt": visual.get("assetPrompt") or self._asset_prompt_for_scene(content_type, visual_style, text, step[0], layout_variant),
                        "media": visual.get("media") if isinstance(visual.get("media"), dict) else None,
                    },
                }
            )
        return normalized or self._build_scenes("", {}, content_type, visual_style, pace)

    def _generate_cosyvoice_audio(
        self,
        project_json: dict[str, Any],
        task_dir: Path,
        log_path: str | None,
        payload: dict[str, Any],
    ) -> list[dict[str, Any]]:
        render_audio_dir = self.render_audio_root / f"job_{task_dir.name.replace('job_', '')}"
        render_audio_dir.mkdir(parents=True, exist_ok=True)
        backend_audio_dir = task_dir / "audio"
        backend_audio_dir.mkdir(parents=True, exist_ok=True)

        voice = self._resolve_cosyvoice_voice(
            str(payload.get("voiceId") or project_json.get("voice", {}).get("speaker") or "中文女")
        )
        audio_scenes: list[dict[str, Any]] = []
        for index, scene in enumerate(project_json.get("scenes") or []):
            text = str(scene.get("voiceText") or scene.get("subtitleText") or "").strip()
            if not text:
                raise RuntimeError(f"scene_{index + 1} 缺少可配音文本")

            filename = f"scene-{index + 1:02d}.wav"
            backend_audio_path = backend_audio_dir / filename
            render_audio_path = render_audio_dir / filename
            self._append_log(log_path, f"Open-source CosyVoice scene={index + 1} voice={voice} text={text[:80]}")
            seconds = self._generate_open_source_cosyvoice_audio(text, voice, backend_audio_path)
            if seconds <= 0 or not backend_audio_path.exists() or backend_audio_path.stat().st_size <= 0:
                raise RuntimeError(f"Open-source CosyVoice returned invalid audio for scene_{index + 1}")

            shutil.copyfile(backend_audio_path, render_audio_path)
            pause_frames = 2 if index < len(project_json.get("scenes") or []) - 1 else 4
            planned_seconds = float(scene.get("duration") or 0)
            max_hold_after_audio = 0.22 if index < len(project_json.get("scenes") or []) - 1 else 0.36
            duration_seconds = max(seconds + pause_frames / 30, min(planned_seconds, seconds + max_hold_after_audio))
            duration_frames = max(54, int(duration_seconds * 30 + 0.999))
            scene["duration"] = round(duration_seconds, 2)
            scene["durationFrames"] = duration_frames
            scene["audio"] = {
                "provider": "open_source_cosyvoice",
                "voice": voice,
                "path": str(backend_audio_path),
                "src": f"generated-audio/{render_audio_dir.name}/{filename}",
                "seconds": seconds,
                "durationInFrames": duration_frames,
                "text": text,
            }
            audio_scenes.append(
                {
                    "index": index,
                    "src": f"generated-audio/{render_audio_dir.name}/{filename}",
                    "seconds": seconds,
                    "durationInFrames": duration_frames,
                    "provider": "open_source_cosyvoice",
                }
            )

        project_json.setdefault("voice", {})["provider"] = "open_source_cosyvoice"
        project_json.setdefault("voice", {})["speaker"] = voice
        return audio_scenes

    def _generate_open_source_cosyvoice_audio(self, text: str, voice: str, output_path: Path) -> float:
        data = urllib.parse.urlencode({"tts_text": text, "spk_id": voice}).encode("utf-8")
        request = urllib.request.Request(
            f"{self.cosyvoice_url}/inference_sft",
            data=data,
            headers={"Content-Type": "application/x-www-form-urlencoded"},
            method="POST",
        )
        try:
            with urllib.request.urlopen(request, timeout=self.cosyvoice_timeout) as response:
                pcm = response.read()
        except urllib.error.HTTPError as exc:
            detail = exc.read().decode("utf-8", errors="ignore")
            raise RuntimeError(f"Open-source CosyVoice failed {exc.code}: {detail}") from exc
        except Exception as exc:
            raise RuntimeError(f"Open-source CosyVoice unavailable: {exc}") from exc

        pcm = self._trim_pcm_silence(pcm)
        if len(pcm) < 1024:
            raise RuntimeError("Open-source CosyVoice returned empty audio")
        if len(pcm) % 2:
            pcm = pcm[:-1]

        output_path.parent.mkdir(parents=True, exist_ok=True)
        with wave.open(str(output_path), "wb") as wav:
            wav.setnchannels(1)
            wav.setsampwidth(2)
            wav.setframerate(self.cosyvoice_sample_rate)
            wav.writeframes(pcm)
        return len(pcm) / (self.cosyvoice_sample_rate * 2)

    def _trim_pcm_silence(self, pcm: bytes, threshold: int = 260, keep_ms: int = 90) -> bytes:
        if len(pcm) < 4:
            return pcm
        samples = memoryview(pcm)
        frame_count = len(pcm) // 2

        def amp(i: int) -> int:
            lo = samples[i * 2]
            hi = samples[i * 2 + 1]
            value = int.from_bytes(bytes((lo, hi)), "little", signed=True)
            return abs(value)

        start = 0
        while start < frame_count and amp(start) < threshold:
            start += 1
        end = frame_count - 1
        while end > start and amp(end) < threshold:
            end -= 1
        keep = int(self.cosyvoice_sample_rate * keep_ms / 1000)
        start = max(0, start - keep)
        end = min(frame_count - 1, end + keep)
        return pcm[start * 2 : (end + 1) * 2]

    def _render_with_external_service(
        self,
        payload: dict[str, Any],
        audio_scenes: list[dict[str, Any]],
        scenes: list[dict[str, Any]],
        output_path: Path,
        log_path: str | None,
    ) -> dict[str, Any]:
        request_payload = {
            "script": payload.get("script") or "",
            "style": payload.get("visualStyle") or payload.get("style") or "dark_editorial",
            "contentType": payload.get("contentType") or payload.get("videoType") or "insight",
            "targetPlatform": payload.get("targetPlatform") or "douyin",
            "tone": payload.get("tone") or "professional",
            "pace": payload.get("pace") or "medium",
            "goal": payload.get("goal") or "",
            "density": 1,
            "audioScenes": audio_scenes,
            "scenes": [self._scene_for_render(scene) for scene in scenes],
            "bgmSrc": None,
        }
        body = json.dumps(request_payload, ensure_ascii=False).encode("utf-8")
        request = urllib.request.Request(
            f"{self.render_service_url}/api/render-project",
            data=body,
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        try:
            with urllib.request.urlopen(request, timeout=self.render_timeout) as response:
                result = json.loads(response.read().decode("utf-8"))
            if not result.get("ok") or not result.get("url"):
                return {"ok": False, "provider": "external_remotion", "message": result.get("message") or "Render failed"}
            source_url = f"{self.render_service_url}{result['url']}"
            self._download_file(source_url, output_path)
            self._append_log(log_path, f"外部 Remotion 渲染完成: {source_url}")
            return {
                "ok": True,
                "provider": "external_remotion_cosyvoice",
                "message": f"Rendered by {source_url}",
                "seconds": result.get("seconds"),
                "audioJobId": result.get("audioJobId"),
            }
        except urllib.error.HTTPError as exc:
            detail = ""
            try:
                detail_payload = json.loads(exc.read().decode("utf-8"))
                detail = str(detail_payload.get("message") or detail_payload)
            except Exception:
                detail = str(exc)
            return {"ok": False, "provider": "external_remotion", "message": detail or str(exc)}
        except urllib.error.URLError as exc:
            return {"ok": False, "provider": "external_remotion", "message": str(exc)}
        except Exception as exc:
            return {"ok": False, "provider": "external_remotion", "message": str(exc)}

    def _scene_for_render(self, scene: dict[str, Any]) -> dict[str, Any]:
        visual = scene.get("visual") if isinstance(scene.get("visual"), dict) else {}
        media = visual.get("media") if isinstance(visual.get("media"), dict) else {}
        audio = scene.get("audio") if isinstance(scene.get("audio"), dict) else {}
        return {
            "id": scene.get("id"),
            "voiceText": scene.get("voiceText"),
            "subtitleText": scene.get("subtitleText"),
            "displayText": scene.get("subtitleText"),
            "title": visual.get("headline") or scene.get("title"),
            "openingTitle": visual.get("openingTitle"),
            "mode": visual.get("type"),
            "keywords": visual.get("nodes") or [],
            "durationFrames": scene.get("durationFrames"),
            "audioSrc": audio.get("src"),
            "intent": scene.get("intent"),
            "cta": scene.get("cta"),
            "transition": visual.get("transition"),
            "camera": visual.get("camera"),
            "layout": visual.get("layout"),
            "layoutVariant": visual.get("layoutVariant"),
            "effect": visual.get("effect"),
            "intensity": visual.get("intensity"),
            "energyPattern": visual.get("energyPattern"),
            "assetPrompt": visual.get("assetPrompt"),
            "media": media,
        }

    def _download_file(self, source_url: str, output_path: Path) -> None:
        with urllib.request.urlopen(source_url, timeout=120) as response:
            output_path.write_bytes(response.read())

    def _probe_render_service(self) -> dict[str, Any]:
        try:
            with urllib.request.urlopen(f"{self.render_service_url}/api/health", timeout=2) as response:
                payload = json.loads(response.read().decode("utf-8"))
            return {"available": True, "status": payload}
        except Exception as exc:
            return {"available": False, "message": str(exc)}

    def _probe_cosyvoice_service(self) -> dict[str, Any]:
        try:
            with urllib.request.urlopen(f"{self.cosyvoice_url}/health", timeout=2) as response:
                payload = json.loads(response.read().decode("utf-8"))
            return {"available": True, "url": self.cosyvoice_url, "status": payload}
        except Exception as exc:
            return {"available": False, "url": self.cosyvoice_url, "message": str(exc)}

    def _apply_edit_to_project_json(self, project_json: dict[str, Any], message: str) -> dict[str, Any]:
        patch = self._parse_edit_intent(message)
        payload = self._payload_from_project_json(project_json)
        payload.update({k: v for k, v in patch.items() if k in {"contentType", "videoType", "visualStyle", "style", "pace", "tone", "subtitleMode", "sceneCount", "targetSeconds", "visualIntensity", "openingEffect"}})
        payload["customPrompt"] = "。".join(
            part for part in [payload.get("customPrompt") or "", f"用户修改优先级最高：{message.strip()}"] if part
        )
        payload["editDirective"] = message.strip()
        payload["scriptSource"] = project_json.get("scriptSource") or "user"
        payload["script"] = "。".join(scene.get("voiceText", "") for scene in project_json.get("scenes", []) if scene.get("voiceText"))
        regenerate_scenes = self._should_regenerate_scenes(message, patch)
        source_scenes = project_json.get("scenes") or []
        if patch.get("sceneType") and not regenerate_scenes:
            for scene in project_json.get("scenes", []):
                scene.setdefault("visual", {})["type"] = patch["sceneType"]
        if regenerate_scenes:
            payload.pop("draftScenes", None)
        else:
            payload["draftScenes"] = source_scenes
        edited = self._default_project_json(
            AiVideoProject(
                user_id=0,
                title=project_json.get("title") or "AI 视频项目",
                video_type=payload.get("contentType") or project_json.get("videoType") or "insight",
                aspect_ratio=project_json.get("aspectRatio") or "16:9",
            ),
            payload,
        )
        edited["prompt"] = project_json.get("prompt") or edited.get("prompt") or ""
        edited["customPrompt"] = payload.get("customPrompt") or ""
        edited.setdefault("director", {})["editDirective"] = message.strip()
        edited.setdefault("director", {})["userPriority"] = "edit_message"
        edited.setdefault("director", {})["regeneratedScenes"] = regenerate_scenes
        edited.setdefault("director", {})["appliedPatch"] = patch
        edited.setdefault("editHistory", project_json.get("editHistory", []))
        edited["editHistory"].append({"message": message, "patch": patch, "createdAt": datetime.utcnow().isoformat()})
        return edited

    def _payload_from_project_json(self, project_json: dict[str, Any]) -> dict[str, Any]:
        style = project_json.get("style") if isinstance(project_json.get("style"), dict) else {}
        voice = project_json.get("voice") if isinstance(project_json.get("voice"), dict) else {}
        return {
            "title": project_json.get("title") or "AI 视频项目",
            "script": "。".join(scene.get("voiceText", "") for scene in project_json.get("scenes", []) if scene.get("voiceText")),
            "requirements": project_json.get("requirements") or project_json.get("creativeBrief") or project_json.get("prompt") or "",
            "creativeBrief": project_json.get("creativeBrief") or project_json.get("requirements") or project_json.get("prompt") or "",
            "prompt": project_json.get("prompt") or project_json.get("creativeBrief") or project_json.get("requirements") or "",
            "scriptSource": project_json.get("scriptSource") or "user",
            "videoType": project_json.get("videoType") or "insight",
            "contentType": project_json.get("videoType") or "insight",
            "style": style.get("theme") or "dark_editorial",
            "visualStyle": style.get("theme") or "dark_editorial",
            "aspectRatio": project_json.get("aspectRatio") or "16:9",
            "voiceProvider": voice.get("provider") or "cosyvoice",
            "voiceId": voice.get("speaker") or "中文女",
            "subtitleMode": style.get("subtitleDensity") or "keywords",
            "targetPlatform": project_json.get("platform") or "douyin",
            "tone": style.get("tone") or "professional",
            "pace": self._pace_from_motion(style.get("motion")),
            "goal": project_json.get("goal") or "",
            "visualIntensity": style.get("visualIntensity") or self._default_visual_intensity(style.get("theme") or "dark_editorial", self._pace_from_motion(style.get("motion"))),
            "openingEffect": style.get("openingEffect") or self._default_opening_effect(style.get("theme") or "dark_editorial", self._pace_from_motion(style.get("motion"))),
            "customPrompt": project_json.get("customPrompt") or "",
        }

    def _parse_edit_intent(self, message: str) -> dict[str, Any]:
        text = (message or "").lower()
        patch: dict[str, Any] = {}
        content_matches = [
            ("带货", "product_seed"), ("种草", "product_seed"), ("电商", "product_seed"),
            ("教学", "teaching"), ("讲解", "teaching"), ("教程", "teaching"),
            ("观点", "insight"), ("知识", "insight"), ("认知", "insight"),
            ("生活", "lifestyle"), ("vlog", "lifestyle"),
            ("情绪", "mood"), ("治愈", "mood"),
            ("热点", "briefing"), ("快评", "briefing"), ("新闻", "briefing"),
            ("口播", "creator_talk"), ("个人ip", "creator_talk"), ("个人 ip", "creator_talk"),
            ("案例", "case_study"), ("复盘", "case_study"),
        ]
        for key, value in content_matches:
            if key in text:
                patch["contentType"] = value
                patch["videoType"] = value
                break
        style_matches = [
            ("黑金", "premium_black_gold"), ("高级", "premium_black_gold"),
            ("白板", "clean_explainer"), ("极简", "clean_explainer"),
            ("科技", "tech_blueprint"), ("蓝图", "tech_blueprint"),
            ("促销", "commerce_boost"), ("转化", "commerce_boost"),
            ("杂志", "lifestyle_magazine"),
            ("治愈", "warm_healing"),
            ("爆款", "viral_pop"), ("大字", "viral_pop"),
            ("数据", "data_report"),
            ("快讯", "news_flash"),
        ]
        for key, value in style_matches:
            if key in text:
                patch["visualStyle"] = value
                patch["style"] = value
                break
        if any(word in text for word in ["不要冲击", "别冲击", "别太冲", "柔和", "克制", "少动效", "少点动效", "别太花", "稳一点", "温和"]):
            patch["openingEffect"] = "soft"
            patch["visualIntensity"] = "medium"
        elif any(word in text for word in ["冲击", "抓人", "炸", "更强", "强节奏", "高能", "开场强"]):
            patch["openingEffect"] = "impact"
            patch["visualIntensity"] = "high"
        if any(word in text for word in ["快一点", "更快", "快节奏", "紧凑"]):
            patch["pace"] = "fast"
            patch.setdefault("visualIntensity", "high")
        elif any(word in text for word in ["慢一点", "更慢", "慢节奏", "舒缓"]):
            patch["pace"] = "slow"
            patch.setdefault("visualIntensity", "medium")
        if any(word in text for word in ["字幕少", "少一点字幕", "极简字幕"]):
            patch["subtitleMode"] = "minimal"
        elif any(word in text for word in ["完整字幕", "字幕全"]):
            patch["subtitleMode"] = "full"
        scene_type_matches = [
            ("对比", "compare_split"), ("时间线", "timeline"), ("图表", "data_report"),
            ("白板", "step_board"), ("金句", "quote_wall"), ("封面", "magazine_cover"),
            ("卖点", "benefit_stack"), ("cta", "cta_burst"), ("行动", "cta_burst"),
        ]
        for key, value in scene_type_matches:
            if key in text:
                patch["sceneType"] = value
                break
        match = re.search(r"(\d+)\s*(个|幕|段|分镜)", text)
        if match:
            patch["sceneCount"] = max(3, min(8, int(match.group(1))))
        seconds_match = re.search(r"(\d+)\s*(s|秒|秒钟)", text)
        if seconds_match:
            seconds = int(seconds_match.group(1))
            patch["targetSeconds"] = max(8, min(90, seconds))
            if seconds >= 30 and not patch.get("sceneCount"):
                patch["sceneCount"] = 5
        if any(word in text for word in ["重新生成", "重生成", "重新来", "重做", "再生成", "换一版", "重新拆", "重拆", "重新分镜", "不要沿用", "整体改"]):
            patch["regenerateScenes"] = True
        return patch

    def _should_regenerate_scenes(self, message: str, patch: dict[str, Any]) -> bool:
        if patch.get("regenerateScenes"):
            return True
        text = (message or "").lower()
        structural_keys = {"contentType", "videoType", "sceneCount", "targetSeconds"}
        if any(key in patch for key in structural_keys):
            return True
        return any(word in text for word in ["重新", "重做", "换一版", "整体", "不要沿用", "重新分镜", "重拆"])

    def _default_opening_effect(self, visual_style: str, pace: str) -> str:
        return "impact"

    def _default_visual_intensity(self, visual_style: str, pace: str) -> str:
        return "high"

    def _stable_pick(self, seed: str, options: list[str]) -> str:
        if not options:
            return ""
        total = sum(ord(char) for char in seed)
        return options[total % len(options)]

    def _layout_variant_for_scene(
        self,
        content_type: str,
        visual_style: str,
        scene_type: str,
        text: str,
        index: int,
        directive: str,
    ) -> str:
        if index == 0:
            options = ["center_burst", "media_hero", "kinetic_focus", "diagonal_impact"]
        elif scene_type in {"commerce_hook", "compare_split", "benefit_stack", "use_case", "cta_burst"}:
            options = ["media_product", "diagonal_split", "center_burst", "floating_tags", "text_left_media_right"]
        elif scene_type in {"question_board", "step_board", "diagram_flow", "example_card", "summary_cards"}:
            options = ["center_orbit", "diagram_stage", "text_left_media_right", "floating_tags"]
        elif scene_type in {"data_report", "metric_wall", "trend_line", "data_nodes"}:
            options = ["data_wall", "scan_dashboard", "center_orbit", "diagonal_split"]
        elif content_type in {"lifestyle", "mood"}:
            options = ["media_hero", "center_orbit", "text_left_media_right", "floating_tags"]
        else:
            options = ["center_burst", "media_hero", "diagonal_split", "center_orbit", "floating_tags"]
        return self._stable_pick(f"{content_type}|{visual_style}|{scene_type}|{index}|{text}|{directive}", options)

    def _energy_pattern_for_scene(self, scene_type: str, layout_variant: str, text: str, index: int) -> str:
        if layout_variant in {"center_burst", "kinetic_focus", "diagonal_impact"}:
            options = ["shockwave", "prism_rays", "glitch_slices"]
        elif layout_variant in {"media_hero", "media_product", "text_left_media_right"}:
            options = ["parallax_media", "light_sweep", "depth_scan"]
        elif layout_variant in {"data_wall", "scan_dashboard"}:
            options = ["data_scan", "ticker_bars", "metric_pulse"]
        else:
            options = ["orbit_rings", "floating_particles", "tag_burst"]
        return self._stable_pick(f"{scene_type}|{layout_variant}|{index}|{text}", options)

    def _asset_prompt_for_scene(
        self,
        content_type: str,
        visual_style: str,
        text: str,
        scene_label: str,
        layout_variant: str,
    ) -> str:
        topic = self._topic_from_prompt(text)
        style_hints = {
            "commerce_boost": "high-impact product advertising, glossy product surfaces, dramatic lighting",
            "viral_pop": "short-form viral visual, saturated colors, bold kinetic energy",
            "tech_blueprint": "futuristic interface, luminous data layers, blueprint depth",
            "data_report": "premium data visualization backdrop, metric dashboards, clean depth",
            "premium_black_gold": "luxury black-gold cinematic advertising, reflective highlights",
            "clean_explainer": "clean educational visual, clear diagrams, bright modern workspace",
        }
        return (
            f"{scene_label} visual for {content_type}: {topic}. "
            f"Layout: {layout_variant}. "
            f"Style: {style_hints.get(visual_style, 'cinematic editorial visual with strong depth and motion-ready composition')}. "
            "No text, no watermark, leave clean areas for animated typography."
        )

    def _opening_title_for_scene(self, payload: dict[str, Any], project_title: str, text: str) -> str:
        def usable(value: str) -> str:
            cleaned = self._display_text_for_scene(value, "", 0).strip()
            placeholders = {"ai 视频项目", "ai video", "scene 1", "scene 01", "主题开场", "痛点开场", "提出问题", "反常识开场"}
            if not cleaned or cleaned.lower() in placeholders:
                return ""
            if re.fullmatch(r"scene\s*\d+", cleaned.lower()):
                return ""
            return cleaned[:20]

        candidates = [
            str(project_title or ""),
            str(payload.get("title") or ""),
            str(payload.get("topic") or ""),
            str(payload.get("goal") or ""),
            str(payload.get("creativeBrief") or ""),
            self._topic_from_prompt(str(payload.get("script") or payload.get("prompt") or "")),
        ]
        for candidate in candidates:
            cleaned = usable(candidate)
            if cleaned:
                return cleaned
        keywords = self._keywords_for_text(text, [])
        if keywords:
            return " / ".join(keywords[:2])[:20]
        return usable(text) or "主题开场"

    def _normalize_prompt_payload(self, payload: dict[str, Any] | None) -> dict[str, Any]:
        normalized = dict(payload or {})
        user_script = str(normalized.get("script") or "").strip()
        requirements = str(
            normalized.get("requirements")
            or normalized.get("creativeBrief")
            or normalized.get("prompt")
            or normalized.get("customPrompt")
            or ""
        ).strip()
        if user_script:
            normalized["script"] = user_script
            normalized["scriptSource"] = "user"
        else:
            prompt_parts = self._split_prompt_parts(requirements)
            creative_brief = prompt_parts["creativeBrief"] or requirements
            normalized["script"] = prompt_parts["script"] or creative_brief
            normalized["scriptSource"] = "generated"
            requirements = creative_brief
        if requirements:
            normalized["requirements"] = requirements
            normalized["creativeBrief"] = requirements
            normalized.setdefault("prompt", requirements)
            normalized.setdefault("customPrompt", requirements)

        intent_text = " ".join(
            str(normalized.get(key) or "")
            for key in ("requirements", "creativeBrief", "prompt", "customPrompt", "goal")
        )
        inferred = self._parse_edit_intent(intent_text)

        if str(normalized.get("videoType") or "").strip().lower() == "auto":
            normalized.pop("videoType", None)
        if str(normalized.get("contentType") or "").strip().lower() == "auto":
            normalized.pop("contentType", None)
        if str(normalized.get("style") or "").strip().lower() == "auto":
            normalized.pop("style", None)
        if str(normalized.get("visualStyle") or "").strip().lower() == "auto":
            normalized.pop("visualStyle", None)

        for key in ("contentType", "videoType", "visualStyle", "style", "pace", "subtitleMode", "sceneCount", "targetSeconds"):
            if inferred.get(key) and not normalized.get(key):
                normalized[key] = inferred[key]

        return normalized

    def _split_prompt_parts(self, prompt: str) -> dict[str, str]:
        text = str(prompt or "").strip()
        if not text:
            return {"script": "", "creativeBrief": ""}
        raw_parts = [part.strip() for part in re.split(r"[。\n；;]", text) if part.strip()]
        script_parts: list[str] = []
        brief_parts: list[str] = []
        brief_markers = [
            "风格", "高级感", "黑金", "白板", "科技", "快讯", "小红书", "抖音", "视频号", "b站",
            "节奏", "快一点", "慢一点", "转场", "动效", "字幕", "30s", "30秒", "以上", "高清素材",
            "图片", "镜头", "开头抓人", "引导购买", "最后", "配音", "不要", "少一点",
        ]
        script_markers = ["文案：", "脚本：", "旁白：", "台词：", "内容："]
        for part in raw_parts:
            lowered = part.lower()
            marker_hit = next((marker for marker in script_markers if marker in part), None)
            if marker_hit:
                script_parts.append(part.split(marker_hit, 1)[-1].strip())
                continue
            if any(marker.lower() in lowered for marker in brief_markers):
                brief_parts.append(part)
            else:
                script_parts.append(part)
        if not script_parts:
            return {"script": "", "creativeBrief": text}
        return {"script": "。".join(script_parts), "creativeBrief": "。".join(brief_parts)}

    def _resolve_content_type(self, payload: dict[str, Any], fallback: str | None = None) -> str:
        explicit = str(payload.get("contentType") or payload.get("videoType") or fallback or "").strip()
        if explicit in CONTENT_TEMPLATES:
            return explicit
        custom = f"{payload.get('customPrompt') or ''} {payload.get('script') or ''}"
        inferred = self._parse_edit_intent(custom).get("contentType")
        return inferred or "insight"

    def _resolve_visual_style(self, payload: dict[str, Any], template: dict[str, Any]) -> str:
        explicit = str(payload.get("visualStyle") or payload.get("style") or "").strip()
        if explicit in STYLE_PRESETS:
            return explicit
        inferred = self._parse_edit_intent(f"{payload.get('customPrompt') or ''} {payload.get('goal') or ''}").get("visualStyle")
        return inferred or template.get("defaultStyle") or "dark_editorial"

    def _infer_scene_count(self, payload: dict[str, Any], template: dict[str, Any]) -> int:
        patch_count = self._parse_edit_intent(str(payload.get("customPrompt") or "")).get("sceneCount")
        if patch_count:
            return int(patch_count)
        platform = str(payload.get("targetPlatform") or "")
        if platform == "bilibili":
            return 5
        return min(5, max(3, len(template.get("steps") or [])))

    def _split_script(self, script: str, scene_count: int = 3, content_type: str = "insight", allow_prompt_expansion: bool = True) -> list[str]:
        normalized = " ".join(str(script or "").replace("\n", " ").split())
        if not normalized:
            return [self._fallback_sentence(i, content_type) for i in range(scene_count)]
        parts = [part.strip(" ，,、；;：:") for part in re.split(r"(?<=[。！？!?；;])\s*", normalized) if part.strip()]
        if allow_prompt_expansion and self._looks_like_generation_request(normalized) and "文案：" not in normalized and "旁白：" not in normalized and len(parts) < scene_count:
            return self._expand_prompt_to_scene_texts(normalized, content_type, scene_count)
        if len(parts) >= scene_count:
            return parts[:scene_count]
        if len(parts) == 1 and len(parts[0]) > 42:
            text = parts[0]
            if allow_prompt_expansion and self._looks_like_generation_request(text):
                parts = self._expand_prompt_to_scene_texts(text, content_type, scene_count)
            else:
                size = max(18, len(text) // scene_count)
                parts = [text[i : i + size] for i in range(0, len(text), size)][:scene_count]
        while len(parts) < scene_count:
            parts.append(self._contextual_fallback_sentence(len(parts), content_type, normalized))
        return parts[:scene_count]

    def _looks_like_generation_request(self, text: str) -> bool:
        return any(word in text for word in ["帮我", "生成", "做一条", "做一个", "视频", "短视频", "文案", "风格"])

    def _expand_prompt_to_scene_texts(self, prompt: str, content_type: str, scene_count: int) -> list[str]:
        topic = self._topic_from_prompt(prompt)
        pools = {
            "product_seed": [
                f"别急着买，先看清楚这个真实痛点：{topic}。",
                "真正打动用户的不是参数，而是它能解决熬夜、低效或选择困难这种具体问题。",
                "把使用前后的差别摆出来，让用户一眼看到为什么值得尝试。",
                "最后给一个明确行动理由：现在下单、收藏或咨询，都要有足够强的理由。",
            ],
            "teaching": [
                f"很多新手卡在这里：{topic}。",
                "先把问题拆小，再讲清楚判断标准。",
                "接着给出三个可以照着做的步骤。",
                "最后用一句话总结方法，让用户看完就能复用。",
            ],
            "lifestyle": [
                f"这个生活瞬间很适合被记录下来：{topic}。",
                "先给一个具体场景，让用户马上进入画面。",
                "再放大细节、动作和情绪，不要急着讲道理。",
                "结尾留一点共鸣，让人愿意收藏或留言。",
            ],
            "briefing": [
                f"这件事真正值得关注的不是表面：{topic}。",
                "先用一句话讲清楚发生了什么。",
                "再指出核心矛盾和可能带来的影响。",
                "最后给出明确判断，并抛出讨论问题。",
            ],
            "creator_talk": [
                f"我先说结论，很多人对这件事想反了：{topic}。",
                "用一个亲身经验或观察建立信任。",
                "给出清晰观点，不要只说情绪。",
                "结尾告诉用户为什么值得继续关注你。",
            ],
            "case_study": [
                f"这个案例的关键转折点在这里：{topic}。",
                "先交代背景和限制条件。",
                "再讲真正改变结果的决策。",
                "最后提炼成别人也能复用的方法。",
            ],
        }
        selected = pools.get(content_type, [
            f"先别划走，这个观点值得听完：{topic}。",
            "先抛出一个反常识判断，建立注意力。",
            "再解释背后的原因和例子。",
            "最后留下一个可以记住的结论。",
        ])
        while len(selected) < scene_count:
            selected.append(self._fallback_sentence(len(selected), content_type))
        return selected[:scene_count]

    def _topic_from_prompt(self, prompt: str) -> str:
        text = re.sub(
            r"帮我|生成|做一条|做一个|视频|短视频|文案|风格|高级感|开头抓人|最后引导购买|"
            r"小红书|种草|更|以上|强调|最后|引导|购买|配音|转场|动效|字幕|像|"
            r"\d+\s*(s|秒|秒钟)",
            "",
            prompt,
        )
        text = re.sub(r"[，。！？；;：:]+", " ", text)
        text = " ".join(text.split())
        return (text[:34] or prompt[:34]).strip()

    def _contextual_fallback_sentence(self, index: int, content_type: str, prompt: str) -> str:
        expanded = self._expand_prompt_to_scene_texts(prompt, content_type, index + 1)
        return expanded[index] if index < len(expanded) else self._fallback_sentence(index, content_type)

    def _fallback_sentence(self, index: int, content_type: str) -> str:
        defaults = {
            "product_seed": ["先指出用户最真实的痛点。", "再展示产品带来的改变。", "最后给出明确下单理由。"],
            "teaching": ["先提出一个具体问题。", "再拆成简单步骤。", "最后给出练习建议。"],
            "lifestyle": ["先打开一个日常瞬间。", "再放大细节和感受。", "最后留下温柔共鸣。"],
            "briefing": ["先讲清楚发生了什么。", "再指出核心矛盾。", "最后给出判断和讨论点。"],
        }
        pool = defaults.get(content_type, ["先抛出一个抓人的问题。", "再解释背后的原因。", "最后给出一个行动建议。"])
        return pool[index % len(pool)]

    def _headline_for_scene(self, fallback: str, text: str, index: int) -> str:
        if len(text) <= 14:
            return text.rstrip("。！？!")
        return fallback or f"Scene {index + 1}"

    def _display_text_for_scene(self, text: str, fallback: str, index: int) -> str:
        cleaned = " ".join(str(text or "").replace("\n", " ").split()).strip()
        if not cleaned:
            return fallback or f"Scene {index + 1}"
        cleaned = cleaned.strip(" .,!?:;，。！？；：、")
        parts = [
            part.strip(" .,!?:;，。！？；：、")
            for part in re.split(r"[\s，,。！？!、；;：:]+", cleaned)
            if part.strip(" .,!?:;，。！？；：、")
        ]
        preferred = [part for part in parts if 4 <= len(part) <= 18]
        if preferred:
            return preferred[0]
        source = parts[0] if parts else cleaned
        if len(source) <= 18:
            return source
        return source[:18].rstrip(" .,!?:;，。！？；：、") + "..."

    def _keywords_for_text(self, text: str, fallback: list[str]) -> list[str]:
        words = [
            word.strip(" .,!?:;，。！？；：、")
            for word in re.split(r"[\s，,。！？!、；;：:]+", str(text or ""))
            if len(word.strip(" .,!?:;，。！？；：、")) >= 2
        ]
        compact: list[str] = []
        for word in words:
            compact.append(word[:12] if len(word) > 12 else word)
        unique = list(dict.fromkeys(compact))
        return (unique[:4] or fallback[:4])[:4]

    def _cta_for_scene(self, index: int, count: int, content_type: str) -> str:
        if index != count - 1:
            return ""
        return {
            "product_seed": "立即下单",
            "creator_talk": "关注我，继续看下一条",
            "briefing": "你怎么看，评论区聊聊",
            "teaching": "收藏后跟着做一遍",
        }.get(content_type, "把这个方法用起来")

    def _transition_for_scene(self, scene_type: str, index: int) -> str:
        if scene_type in {"hook_flash", "breaking_headline", "cta_burst"}:
            return "flash"
        if scene_type in {"timeline", "diagram_flow", "decision_map"}:
            return "wipe"
        if scene_type in {"data_report", "metric_wall", "trend_line", "data_nodes"}:
            return "scan"
        if scene_type in {"compare_split", "contrast_cards", "conflict_map"}:
            return "split"
        if scene_type in {"quote_wall", "creator_caption", "big_subtitle"}:
            return "glitch"
        return ["push", "prism", "zoom"][index % 3]

    def _camera_for_style(self, visual_style: str, pace: str) -> str:
        if visual_style in {"lifestyle_magazine", "warm_healing"}:
            return "slow_pan"
        if pace == "fast":
            return "snap_zoom"
        if visual_style in {"tech_blueprint", "data_report"}:
            return "scan"
        return "cinematic_push"

    def _motion_for_pace(self, pace: str, style_preset: dict[str, Any]) -> str:
        if pace == "fast":
            return "snap"
        if pace == "slow":
            return "slow_breath"
        return str(style_preset.get("motion") or "cinematic")

    def _pace_from_motion(self, motion: str | None) -> str:
        if motion in {"snap", "fast_cut"}:
            return "fast"
        if motion in {"slow_breath", "slow_pan"}:
            return "slow"
        return "medium"

    def _scene_duration_for_pace(self, pace: str, text: str) -> int:
        base = {"fast": 2, "medium": 3, "slow": 4}.get(pace, 3)
        return max(base, min(7, base + len(text) // 48))

    def _build_srt(self, scenes: list[dict[str, Any]]) -> str:
        blocks: list[str] = []
        cursor = 0.0
        for index, scene in enumerate(scenes, start=1):
            start = cursor
            end = cursor + float(scene.get("duration") or 3)
            blocks.append(
                f"{index}\n{self._srt_time(start)} --> {self._srt_time(end)}\n{scene.get('subtitleText') or ''}\n"
            )
            cursor = end
        return "\n".join(blocks)

    def _srt_time(self, seconds: float) -> str:
        whole = int(seconds)
        millis = int((seconds - whole) * 1000)
        minutes, sec = divmod(whole, 60)
        hours, minutes = divmod(minutes, 60)
        return f"{hours:02d}:{minutes:02d}:{sec:02d},{millis:03d}"

    def _build_cover_svg(self, title: str, project_json: dict[str, Any] | None = None) -> str:
        safe = title.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
        style = (project_json or {}).get("style", {})
        accent = "#ff4a1c" if style.get("theme") != "clean_explainer" else "#111111"
        return f"""<svg xmlns="http://www.w3.org/2000/svg" width="1280" height="720" viewBox="0 0 1280 720">
<rect width="1280" height="720" fill="#050505"/>
<rect x="74" y="74" width="1132" height="572" rx="22" fill="#111111" stroke="{accent}" stroke-width="4"/>
<text x="116" y="340" fill="#f8fafc" font-size="58" font-family="Arial, sans-serif">{safe}</text>
<text x="116" y="420" fill="{accent}" font-size="30" font-family="Arial, sans-serif">AI Video Director Workspace</text>
</svg>"""

    def _draft_recommendations(self, project_json: dict[str, Any]) -> list[str]:
        style = project_json.get("style", {})
        return [
            f"当前使用「{style.get('label', style.get('theme'))}」视觉风格，可在每个分镜里单独切换画面类型。",
            f"已生成 {len(project_json.get('scenes') or [])} 个分镜，支持修改旁白、字幕、画面组件和 CTA。",
            "生成后可以继续用对话修改，例如：第二幕换成对比画面，整体更像小红书种草。",
        ]

    def _resolve_cosyvoice_voice(self, voice: str) -> str:
        normalized = voice.strip()
        female = "中文女"
        male = "中文男"
        mapping = {
            female: female,
            male: male,
            "女声": female,
            "元气女声": female,
            "男声": male,
            "稳重男声": male,
            "longanhuan": female,
            "longshuo_v3": male,
            "longanyang": male,
        }
        if not normalized or "?" in normalized or "\ufffd" in normalized:
            return female
        return mapping.get(normalized, female)

    def _derive_title(self, script: str) -> str:
        cleaned = " ".join(str(script or "").split())
        return cleaned[:24] or "AI 视频项目"

    def _update_job(self, db: Session, job: AiVideoJob, *, stage: str, status: str, progress: int) -> None:
        job.stage = stage
        job.status = status
        job.progress = progress
        job.updated_at = datetime.utcnow()
        db.commit()

    def _append_log(self, path: str | None, line: str) -> None:
        if not path:
            return
        Path(path).parent.mkdir(parents=True, exist_ok=True)
        with open(path, "a", encoding="utf-8") as handle:
            handle.write(f"{datetime.utcnow().isoformat()} {line}\n")
