import base64
import json
import os
import re
import shutil
import subprocess
import tempfile
import uuid
from pathlib import Path
from urllib.parse import urlparse
from typing import Optional

import imageio_ffmpeg
import requests
from openai import OpenAI
from PIL import Image, ImageDraw, ImageFilter, ImageStat
from pydub import AudioSegment
import dashscope
from dashscope.audio.tts_v2 import SpeechSynthesizer
from dashscope.audio.tts import SpeechSynthesizer as SambertSpeechSynthesizer

from app.config import get_settings


class StickmanGenerator:
    def __init__(self):
        self.settings = get_settings()
        self.llm_api_key = self.settings.STICKMAN_LLM_API_KEY or self.settings.OPENAI_API_KEY or self.settings.DEEPSEEK_API_KEY or self.settings.DASHSCOPE_API_KEY
        self.llm_base_url = self.settings.STICKMAN_LLM_BASE_URL or self.settings.OPENAI_BASE_URL or self.settings.DEEPSEEK_BASE_URL or self.settings.DASHSCOPE_BASE_URL
        self.llm_model = self.settings.STICKMAN_LLM_MODEL or self.settings.OPENAI_MODEL or self.settings.DEEPSEEK_MODEL or self.settings.DASHSCOPE_CHAT_MODEL
        self.image_api_key = self.settings.STICKMAN_IMAGE_API_KEY or getattr(self.settings, "IMAGE_API_KEY", "") or self.settings.DASHSCOPE_API_KEY
        self.image_base_url = self.settings.STICKMAN_IMAGE_BASE_URL or getattr(self.settings, "IMAGE_BASE_URL", "")
        self.image_model = self.settings.STICKMAN_IMAGE_MODEL or getattr(self.settings, "IMAGE_MODEL", "wan2.7-image")
        self.image_models = [item.strip() for item in (self.settings.STICKMAN_IMAGE_MODELS or "").split(",") if item.strip()]
        if self.image_model and self.image_model not in self.image_models:
            self.image_models.insert(0, self.image_model)
        self.image_fallback_model = getattr(self.settings, "IMAGE_MODEL", "wan2.7-image") or "wan2.7-image"
        if self.image_fallback_model and self.image_fallback_model not in self.image_models:
            self.image_models.append(self.image_fallback_model)
        if "wan2.7-image" not in self.image_models:
            self.image_models.append("wan2.7-image")
        self.image_size = self.settings.STICKMAN_IMAGE_SIZE
        self.image_negative_prompt = self.settings.STICKMAN_IMAGE_NEGATIVE_PROMPT
        self.tts_api_key = self.settings.STICKMAN_TTS_API_KEY or getattr(self.settings, "IMAGE_API_KEY", "") or self.settings.DASHSCOPE_API_KEY
        self.tts_base_url = self.settings.STICKMAN_TTS_BASE_URL
        self.tts_model = self.settings.STICKMAN_TTS_MODEL
        self.tts_provider = self.settings.STICKMAN_TTS_PROVIDER
        self.tts_voice = self.settings.STICKMAN_TTS_VOICE
        self.tts_voice_library = self._load_tts_voice_library()
        self.ffmpeg_path = shutil.which("ffmpeg") or imageio_ffmpeg.get_ffmpeg_exe()
        AudioSegment.converter = self.ffmpeg_path
        dashscope.api_key = self.tts_api_key or self.settings.DASHSCOPE_API_KEY
        dashscope.base_websocket_api_url = 'wss://dashscope.aliyuncs.com/api-ws/v1/inference'
        self.llm_client = OpenAI(
            api_key=self.llm_api_key,
            base_url=self.llm_base_url,
        )

    def _load_tts_voice_library(self):
        raw = self.settings.STICKMAN_TTS_VOICE_LIBRARY or "[]"
        try:
            data = json.loads(raw)
            if isinstance(data, list):
                return data
        except Exception:
            pass
        return []

    def get_tts_voice_library(self):
        return self.tts_voice_library

    def _split_sentences(self, text: str) -> list[str]:
        parts = [item.strip() for item in re.split(r'(?<=[。！？!?])\s*', text or '') if item.strip()]
        return parts or ([text.strip()] if text and text.strip() else [])

    def _expand_storyboards_for_pacing(self, script_data: dict, topic: str):
        storyboards = script_data.get("storyboards") or []
        expanded = []
        for scene in storyboards:
            sentences = self._split_sentences(scene.get("narration", ""))
            if not sentences:
                expanded.append(scene)
                continue
            grouped = ["".join(sentences[i:i + 2]) for i in range(0, len(sentences), 2)]
            for idx, narration in enumerate(grouped, start=1):
                clone = dict(scene)
                clone["narration"] = narration
                if len(grouped) > 1:
                    clone["scene_title"] = f"{scene.get('scene_title', '分镜')}-{idx}"
                    clone["scene_description"] = f"{scene.get('scene_description', topic)}，画面聚焦第{idx}部分内容"
                expanded.append(clone)

        for index, scene in enumerate(expanded, start=1):
            scene["scene_id"] = index
            scene.setdefault("scene_title", f"第{index}幕")
            scene.setdefault("camera_type", self._camera_type_for_index(index))
            scene.setdefault("character_action", self._action_for_index(index))
            scene.setdefault("layout_hint", self._layout_for_index(index))
            scene.setdefault("visual_focus", (scene.get("keywords") or [topic])[0])

        script_data["storyboards"] = expanded
        script_data["script"] = "\n".join(scene.get("narration", "") for scene in expanded)
        return script_data

    def _require_config(self):
        missing = []
        if not self.llm_api_key:
            missing.append("STICKMAN_LLM_API_KEY")
        if not self.image_api_key:
            missing.append("STICKMAN_IMAGE_API_KEY")
        if not self.tts_api_key:
            missing.append("STICKMAN_TTS_API_KEY")
        if missing:
            raise RuntimeError("缺少火柴人模块配置: " + ", ".join(missing))

    def generate(
        self,
        topic: str,
        storyboard_count: int,
        progress_callback=None,
        aspect_ratio: str = "16:9",
        voice_source: str = "ai",
        voice_file_path: str | None = None,
        tts_provider: str | None = None,
        tts_voice: str | None = None,
        tts_rate: str | None = None,
        style_reference_image_path: str | None = None,
        style_reference_notes: str | None = None,
    ):
        self._require_config()
        storyboard_count = max(2, min(int(storyboard_count or 3), 20))

        def report(progress: int, message: str):
            if progress_callback:
                progress_callback(progress, message)

        report(5, "开始生成火柴人视频")
        script_data = self.generate_script_data(topic, storyboard_count)
        report(20, "脚本生成完成")

        with tempfile.TemporaryDirectory(prefix="stickman_") as temp_dir:
            image_dir = Path(temp_dir) / "images"
            audio_dir = Path(temp_dir) / "audio"
            clip_dir = Path(temp_dir) / "clips"
            image_dir.mkdir(parents=True, exist_ok=True)
            audio_dir.mkdir(parents=True, exist_ok=True)
            clip_dir.mkdir(parents=True, exist_ok=True)

            scenes = script_data["storyboards"]
            image_assets, generation_flags = self.generate_images(
                scenes,
                aspect_ratio,
                progress_callback=report,
                style_reference_image_path=style_reference_image_path,
                style_reference_notes=style_reference_notes,
            )
            image_paths = [item["image_path"] for item in image_assets]

            if voice_source in {"upload", "record"} and voice_file_path:
                audio_track = str(Path(temp_dir) / "user_voice.mp3")
                total_duration = self._prepare_reference_audio(voice_file_path, audio_track)
                report(65, "已使用用户音频")
                timeline = self._build_timeline_from_total_duration(total_duration, len(scenes))
                timeline = self._apply_scene_duration_ranges(timeline, scenes)
            else:
                audio_segments = []
                for index, scene in enumerate(scenes, start=1):
                    audio_path = audio_dir / f"scene_{index}.mp3"
                    duration = self._generate_audio(scene.get("narration", ""), str(audio_path), tts_provider, tts_voice, tts_rate)
                    audio_segments.append((str(audio_path), duration))
                    report(45 + int(index / len(scenes) * 20), f"配音生成中 ({index}/{len(scenes)})")
                timeline = self._build_timeline(audio_segments)
                timeline = self._apply_scene_duration_ranges(timeline, scenes)
                audio_track = str(Path(temp_dir) / "final_audio.mp3")
                self._concat_audio(audio_segments, audio_track)

            total_audio_duration = self._get_audio_duration(audio_track)
            timeline = self._ensure_timeline_covers_audio(timeline, total_audio_duration)

            report(68, "时间轴计算完成")

            clip_paths = []
            for index, (image_path, segment) in enumerate(zip(image_paths, timeline), start=1):
                clip_path = clip_dir / f"clip_{index}.mp4"
                self._create_image_clip(image_path, str(clip_path), segment["video_duration"])
                clip_paths.append(str(clip_path))
                report(70 + int(index / len(timeline) * 10), f"视频片段合成中 ({index}/{len(timeline)})")

            report(82, "音轨合成完成")

            merged_clip = str(Path(temp_dir) / "merged_video.mp4")
            self._concat_video_clips(clip_paths, merged_clip)
            report(90, "视频拼接完成")

            final_path = self._merge_video_and_audio(merged_clip, audio_track)
            report(100, "火柴人视频生成完成")

            return {
                "title": script_data.get("title") or topic,
                "script": script_data.get("script") or "",
                "storyboards": scenes,
                "image_assets": image_assets,
                "generation_flags": generation_flags,
                "duration": sum(item["video_duration"] for item in timeline),
                "video_path": final_path,
            }

    def compose_from_assets(
        self,
        topic: str,
        storyboards: list[dict],
        image_assets: list[dict],
        progress_callback=None,
        voice_source: str = "ai",
        voice_file_path: str | None = None,
        tts_provider: str | None = None,
        tts_voice: str | None = None,
        tts_rate: str | None = None,
    ):
        def report(progress: int, message: str):
            if progress_callback:
                progress_callback(progress, message)

        if not storyboards:
            raise RuntimeError("请先生成并确认分镜")
        if not image_assets:
            raise RuntimeError("请先生成并确认图片")

        report(5, "开始基于已确认素材合成视频")
        with tempfile.TemporaryDirectory(prefix="stickman_compose_") as temp_dir:
            audio_dir = Path(temp_dir) / "audio"
            clip_dir = Path(temp_dir) / "clips"
            audio_dir.mkdir(parents=True, exist_ok=True)
            clip_dir.mkdir(parents=True, exist_ok=True)

            image_paths = []
            for index, asset in enumerate(image_assets, start=1):
                image_path = asset.get("image_path")
                if not image_path or not os.path.exists(image_path):
                    raise RuntimeError(f"第 {index} 张分镜图片不存在，请重新生成图片")
                image_paths.append(str(image_path))
            report(20, "图片素材检查完成")

            if voice_source in {"upload", "record"} and voice_file_path:
                audio_track = str(Path(temp_dir) / "user_voice.mp3")
                total_duration = self._prepare_reference_audio(voice_file_path, audio_track)
                report(45, "已使用用户音频")
                timeline = self._build_timeline_from_total_duration(total_duration, len(storyboards))
                timeline = self._apply_scene_duration_ranges(timeline, storyboards)
            else:
                audio_segments = []
                for index, scene in enumerate(storyboards, start=1):
                    audio_path = audio_dir / f"scene_{index}.mp3"
                    duration = self._generate_audio(scene.get("narration", ""), str(audio_path), tts_provider, tts_voice, tts_rate)
                    audio_segments.append((str(audio_path), duration))
                    report(20 + int(index / len(storyboards) * 30), f"配音生成中 ({index}/{len(storyboards)})")
                timeline = self._build_timeline(audio_segments)
                timeline = self._apply_scene_duration_ranges(timeline, storyboards)
                audio_track = str(Path(temp_dir) / "final_audio.mp3")
                self._concat_audio(audio_segments, audio_track)

            total_audio_duration = self._get_audio_duration(audio_track)
            timeline = self._ensure_timeline_covers_audio(timeline, total_audio_duration)

            report(58, "时间轴计算完成")
            clip_paths = []
            for index, (image_path, segment) in enumerate(zip(image_paths, timeline), start=1):
                clip_path = clip_dir / f"clip_{index}.mp4"
                self._create_image_clip(image_path, str(clip_path), segment["video_duration"])
                clip_paths.append(str(clip_path))
                report(60 + int(index / len(timeline) * 20), f"视频片段合成中 ({index}/{len(timeline)})")

            merged_clip = str(Path(temp_dir) / "merged_video.mp4")
            self._concat_video_clips(clip_paths, merged_clip)
            report(88, "视频拼接完成")

            final_path = self._merge_video_and_audio(merged_clip, audio_track)
            report(100, "火柴人视频合成完成")
            return {
                "title": topic,
                "script": "\n".join(scene.get("narration", "") for scene in storyboards),
                "storyboards": storyboards,
                "image_assets": image_assets,
                "generation_flags": {"composed_from_assets": True},
                "duration": sum(item["video_duration"] for item in timeline),
                "video_path": final_path,
            }

    def generate_script_data(self, topic: str, storyboard_count: int):
        script_data = self._generate_script(topic, storyboard_count)
        script_data = self._expand_storyboards_for_pacing(script_data, topic)
        storyboards = script_data.get("storyboards") or []
        for index, scene in enumerate(storyboards, start=1):
            scene.setdefault("scene_title", f"第{index}幕")
            scene.setdefault("camera_type", self._camera_type_for_index(index))
            scene.setdefault("character_action", self._action_for_index(index))
            scene.setdefault("layout_hint", self._layout_for_index(index))
            scene.setdefault("visual_focus", (scene.get("keywords") or [topic])[0])
            scene.setdefault("duration_range", "2-4")
        return script_data

    def generate_images(self, storyboards: list[dict], aspect_ratio: str, project_id: Optional[int] = None, progress_callback=None, style_reference_image_path: Optional[str] = None, style_reference_notes: Optional[str] = None):
        assets = []
        flags = {"image_fallback_used": False, "fallback_count": 0, "image_provider_status": "model"}
        image_output_dir = self._get_image_output_dir(project_id)
        image_output_dir.mkdir(parents=True, exist_ok=True)
        style_hint = self._build_style_reference_hint(style_reference_image_path, style_reference_notes)

        for index, scene in enumerate(storyboards, start=1):
            image_path = image_output_dir / f"scene_{index}_{uuid.uuid4().hex[:8]}.png"
            prompt = self._build_image_prompt(scene, index, aspect_ratio, style_hint)
            image_result = self._generate_image(prompt, str(image_path), scene, aspect_ratio)
            assets.append({
                "scene_id": scene.get("scene_id", index),
                "prompt": prompt,
                "image_path": str(image_path),
                "image_url": f"/api/stickman-images/{image_path.name}",
                "used_fallback": image_result["used_fallback"],
                "image_source": image_result["image_source"],
                "model_used": image_result.get("model_used"),
                "error_summary": image_result.get("error_summary"),
            })
            if image_result["used_fallback"]:
                flags["image_fallback_used"] = True
                flags["fallback_count"] += 1
                flags["image_provider_status"] = "fallback"
            if image_result.get("error_summary"):
                flags[f"scene_{index}_error"] = image_result["error_summary"]
            if image_result.get("model_used"):
                flags[f"scene_{index}_model"] = image_result["model_used"]
            if progress_callback:
                progress_callback(20 + int(index / len(storyboards) * 25), f"图像生成中 ({index}/{len(storyboards)})")
        return assets, flags

    def regenerate_single_image(
        self,
        scene: dict,
        index: int,
        aspect_ratio: str,
        project_id: Optional[int] = None,
        prompt_override: Optional[str] = None,
        style_reference_image_path: Optional[str] = None,
        style_reference_notes: Optional[str] = None,
    ):
        image_output_dir = self._get_image_output_dir(project_id)
        image_output_dir.mkdir(parents=True, exist_ok=True)
        image_path = image_output_dir / f"scene_{index}_{uuid.uuid4().hex[:8]}.png"
        style_hint = self._build_style_reference_hint(style_reference_image_path, style_reference_notes)
        prompt = prompt_override or self._build_image_prompt(scene, index, aspect_ratio, style_hint)
        image_result = self._generate_image(prompt, str(image_path), scene, aspect_ratio)
        return {
            "scene_id": scene.get("scene_id", index),
            "prompt": prompt,
            "image_path": str(image_path),
            "image_url": f"/api/stickman-images/{image_path.name}",
            "used_fallback": image_result["used_fallback"],
            "image_source": image_result["image_source"],
            "model_used": image_result.get("model_used"),
            "error_summary": image_result.get("error_summary"),
        }, image_result["used_fallback"]

    def _get_image_output_dir(self, project_id: Optional[int] = None):
        backend_dir = Path(__file__).resolve().parents[2]
        base_dir = backend_dir / "uploads" / "stickman_images"
        if project_id is None:
            return base_dir / "temp"
        return base_dir / f"project_{project_id}"

    def _generate_script(self, topic: str, storyboard_count: int):
        prompt = (
            f'请为主题"{topic}"生成一个中文火柴人科普短视频脚本。'
            f"总共 {storyboard_count} 个分镜，每个分镜 1-2 句旁白。"
            "必须返回 JSON，不要输出解释。JSON 结构如下："
            '{"title":"视频标题","script":"完整脚本","storyboards":[{"scene_id":1,"scene_description":"场景描述","narration":"旁白文本","keywords":["关键词"]}]}'
        )

        response = self.llm_client.chat.completions.create(
            model=self.llm_model,
            messages=[
                {"role": "system", "content": "你是短视频脚本策划，擅长输出适合火柴人动画的分镜 JSON。"},
                {"role": "user", "content": prompt},
            ],
            temperature=0.7,
            max_tokens=2400,
        )
        content = response.choices[0].message.content or ""
        return self._extract_script_json(content, topic, storyboard_count)

    def _extract_script_json(self, content: str, topic: str, storyboard_count: int):
        match = re.search(r"\{[\s\S]*\}", content)
        if not match:
            return self._fallback_script(topic, storyboard_count, content)

        try:
            data = json.loads(match.group())
        except json.JSONDecodeError:
            return self._fallback_script(topic, storyboard_count, content)

        storyboards = data.get("storyboards") or []
        if not isinstance(storyboards, list) or not storyboards:
            return self._fallback_script(topic, storyboard_count, content)

        normalized = []
        for index, scene in enumerate(storyboards[:storyboard_count], start=1):
            normalized.append(
                {
                    "scene_id": index,
                    "scene_title": scene.get("scene_title") or f"第{index}幕",
                    "scene_description": scene.get("scene_description") or f"围绕{topic}的第{index}个场景",
                    "narration": scene.get("narration") or f"这是关于{topic}的第{index}个要点。",
                    "keywords": scene.get("keywords") or [],
                    "camera_type": scene.get("camera_type") or self._camera_type_for_index(index),
                    "character_action": scene.get("character_action") or self._action_for_index(index),
                    "layout_hint": scene.get("layout_hint") or self._layout_for_index(index),
                    "visual_focus": scene.get("visual_focus") or topic,
                    "duration_range": scene.get("duration_range") or "2-4",
                }
            )

        return {
            "title": data.get("title") or topic,
            "script": data.get("script") or "\n".join(item["narration"] for item in normalized),
            "storyboards": normalized,
        }

    def _fallback_script(self, topic: str, storyboard_count: int, raw_text: str):
        storyboards = []
        for index in range(1, storyboard_count + 1):
            storyboards.append(
                {
                    "scene_id": index,
                    "scene_title": f"第{index}幕",
                    "scene_description": f"火柴人围绕{topic}进行第{index}段讲解，画面简洁，重点突出。",
                    "narration": f"我们从第{index}个角度理解{topic}。",
                    "keywords": [topic],
                    "camera_type": self._camera_type_for_index(index),
                    "character_action": self._action_for_index(index),
                    "layout_hint": self._layout_for_index(index),
                    "visual_focus": topic,
                    "duration_range": "2-4",
                }
            )
        return {
            "title": topic,
            "script": raw_text or topic,
            "storyboards": storyboards,
        }

    def _build_image_prompt(self, scene: dict, index: int, aspect_ratio: str, style_hint: str = ""):
        keywords = ", ".join(scene.get("keywords") or [])
        layout_hint = "16:9 horizontal composition, cinematic wide shot, subject clearly visible, balanced left-right layout, safe margins for subtitles" if aspect_ratio == "16:9" else "clean composition"
        camera_type = scene.get("camera_type") or self._camera_type_for_index(index)
        character_action = scene.get("character_action") or self._action_for_index(index)
        layout_position = scene.get("layout_hint") or self._layout_for_index(index)
        visual_focus = scene.get("visual_focus") or keywords
        default_style_hint = "educational infographic scene, strong scene contrast, distinct composition from previous scenes, prop-based storytelling, clean professional illustration, varied props, strong silhouette separation"
        if style_hint:
            merged_style_hint = (
                "The uploaded reference image is the ONLY style guide for this frame. "
                "Fully inherit its palette, line quality, shading behavior, lighting mood, composition feeling, texture density and illustration medium. "
                "Keep the content as a stick-figure educational scene, but visually match the uploaded image as closely as possible. "
                "Do not use the default house style. Do not force white background or minimalist black-line style unless the reference image itself has that look. "
                f"{style_hint}"
            )
            base_prompt = "Create a stick-figure educational scene that follows the uploaded reference image style exactly in mood and rendering. "
        else:
            merged_style_hint = default_style_hint
            base_prompt = "Stick figure educational illustration, minimalist black line art, clean white background, simple composition, expressive gestures, high contrast, no text, no watermark, no speech bubbles. "
        return (
            base_prompt +
            f"{merged_style_hint}. "
            f"{layout_hint}. "
            "Do not render scene numbers, chapter labels, subtitles or any unrelated text in the image. "
            f"Camera: {camera_type}. Character action: {character_action}. Layout: {layout_position}. Visual focus: {visual_focus}. "
            f"Visual scene description: {scene.get('scene_description', '')}. "
            f"Focus keywords: {keywords}."
        )

    def _build_style_reference_hint(self, style_reference_image_path: Optional[str], style_reference_notes: Optional[str]):
        profile = self.extract_style_reference_profile(style_reference_image_path, style_reference_notes)
        if not profile:
            return style_reference_notes or ""
        return (
            "The uploaded reference image is mandatory style guidance. "
            "Keep the generated frame visually close to that reference in color, drawing language, composition feeling and mood. "
            f"{profile}"
        )

    def extract_style_reference_profile(self, style_reference_image_path: Optional[str], style_reference_notes: Optional[str] = None):
        hints = []
        if style_reference_image_path and os.path.exists(style_reference_image_path):
            try:
                image = Image.open(style_reference_image_path).convert("RGB")
                width, height = image.size
                aspect = round(width / height, 2) if height else 1

                small = image.resize((48, 48))
                colors = small.getcolors(48 * 48) or []
                colors = sorted(colors, reverse=True)[:4]
                palette = [f"rgb{color}" for _, color in colors]

                hsv_image = image.convert("HSV")
                hsv_stat = ImageStat.Stat(hsv_image)
                saturation = float(hsv_stat.mean[1]) if hsv_stat.mean else 0.0
                brightness = float(hsv_stat.mean[2]) if hsv_stat.mean else 0.0

                grayscale = image.convert("L")
                extrema = grayscale.getextrema()
                contrast = (int(extrema[1]) - int(extrema[0])) if extrema else 0
                edge_stat = ImageStat.Stat(grayscale.filter(ImageFilter.FIND_EDGES))
                edge_strength = float(edge_stat.mean[0]) if edge_stat.mean else 0.0

                if aspect > 1.4:
                    hints.append("wide cinematic framing")
                elif aspect < 0.8:
                    hints.append("tall poster-like framing")
                else:
                    hints.append("balanced editorial framing")

                if saturation > 120:
                    hints.append("vivid saturated palette")
                elif saturation > 70:
                    hints.append("moderately saturated clean palette")
                else:
                    hints.append("muted restrained palette")

                if brightness < 90:
                    hints.append("dark moody lighting")
                elif brightness > 170:
                    hints.append("bright airy lighting")
                else:
                    hints.append("soft neutral lighting")

                if contrast > 150:
                    hints.append("strong contrast and bold shapes")
                elif contrast > 90:
                    hints.append("clear contrast and readable subject separation")
                else:
                    hints.append("soft contrast and gentle tonal transitions")

                if edge_strength > 25:
                    hints.append("high texture density with detailed edges")
                else:
                    hints.append("clean large shapes with low visual clutter")

                hints.append(f"dominant palette {', '.join(palette)}")
                if aspect > 1.4:
                    hints.append("respect the same wide framing and horizontal scene balance")
                elif aspect < 0.8:
                    hints.append("respect the same tall framing and vertical emphasis")

                if edge_strength > 25:
                    hints.append("preserve strong edge definition and textured drawing feel")
                else:
                    hints.append("preserve smooth surfaces and simplified shape language")
            except Exception:
                pass

        if style_reference_notes:
            hints.append(style_reference_notes)

        return '; '.join(hints).strip()

    def _resolve_image_size(self, aspect_ratio: str):
        if aspect_ratio == "16:9":
            return "1664*928"
        if aspect_ratio == "9:16":
            return "928*1664"
        return self.image_size

    def _generate_image(self, prompt: str, save_path: str, scene: dict, aspect_ratio: str = "16:9"):
        last_error = None
        last_error_summary = None
        models_to_try = []
        for model in self.image_models:
            if model and model not in models_to_try:
                models_to_try.append(model)

        for model in models_to_try:
            try:
                response = requests.post(
                    self.image_base_url,
                    headers={
                        "Content-Type": "application/json",
                        "Authorization": f"Bearer {self.image_api_key}",
                    },
                    json={
                        "model": model,
                        "input": {
                            "messages": [
                                {
                                    "role": "user",
                                    "content": [{"text": prompt}],
                                }
                            ]
                        },
                        "parameters": {
                            "size": self._resolve_image_size(aspect_ratio),
                            "n": 1,
                            "watermark": False,
                            "prompt_extend": True,
                            "negative_prompt": self.image_negative_prompt,
                        },
                    },
                    timeout=120,
                )
                response.raise_for_status()
                result = response.json()
                image_url = self._extract_image_url(result)
                if not image_url:
                    raise RuntimeError(f"图像生成失败: {result}")

                image_response = requests.get(image_url, timeout=120)
                image_response.raise_for_status()
                with open(save_path, "wb") as file:
                    file.write(image_response.content)
                return {
                    "used_fallback": False,
                    "image_source": "model",
                    "model_used": model,
                    "error_summary": None,
                }
            except Exception as exc:
                last_error = exc
                last_error_summary = self._summarize_image_error(exc)

        try:
            raise last_error or RuntimeError("图像生成失败")
        except Exception:
            self._create_fallback_image(save_path, scene)
            return {
                "used_fallback": True,
                "image_source": "fallback",
                "model_used": None,
                "error_summary": last_error_summary or "图片模型不可用，已降级为占位图",
            }

    def _summarize_image_error(self, error: Exception):
        text = str(error)
        if "AllocationQuota.FreeTierOnly" in text or "free tier" in text.lower():
            return "当前开发环境图片模型免费额度已耗尽，已降级为占位图"
        if "403" in text:
            return "图片模型当前无权限或额度不足，已降级为占位图"
        if "401" in text:
            return "图片模型鉴权失败，已降级为占位图"
        if "timeout" in text.lower():
            return "图片模型响应超时，已降级为占位图"
        return f"图片生成失败，已降级为占位图: {text[:120]}"

    def _extract_image_url(self, result: dict):
        output = result.get("output") or {}
        results = output.get("results") or []
        if results and isinstance(results, list):
            first = results[0] or {}
            if first.get("url"):
                return first["url"]

        choices = output.get("choices") or []
        if choices and isinstance(choices, list):
            message = (choices[0] or {}).get("message") or {}
            content = message.get("content") or []
            for item in content:
                if isinstance(item, dict) and item.get("image"):
                    return item["image"]
                if isinstance(item, dict) and item.get("url"):
                    return item["url"]
        return None

    def _generate_audio(self, text: str, save_path: str, tts_provider: str | None = None, tts_voice: str | None = None, tts_rate: str | None = None):
        if not text.strip():
            silence = AudioSegment.silent(duration=1000)
            silence.export(save_path, format="mp3")
            return 1.0

        provider = (tts_provider or self.tts_provider or "dashscope_cosyvoice").strip()
        voice = (tts_voice or self.tts_voice or "longshuo_v3").strip()
        rate = (tts_rate or "+0%").strip()

        voice = self._normalize_tts_voice(provider, voice)

        if provider == "edge_tts":
            try:
                import edge_tts
                asyncio_run = __import__("asyncio").run
                async def _run_edge():
                    communicate = edge_tts.Communicate(text=text, voice=voice, rate=rate)
                    await communicate.save(save_path)
                asyncio_run(_run_edge())
                audio = AudioSegment.from_file(save_path)
                return max(len(audio) / 1000.0, 1.0)
            except Exception:
                provider = "dashscope_cosyvoice"
                voice = self._normalize_tts_voice(provider, voice)

        if provider == "dashscope_cosyvoice":
            try:
                synthesizer = SpeechSynthesizer(model=self.tts_model, voice=voice)
                audio_bytes = synthesizer.call(text)
                with open(save_path, 'wb') as file:
                    file.write(audio_bytes)
                audio = AudioSegment.from_file(save_path)
                if rate != "+0%":
                    factor = 1.0 + (float(rate.strip('%')) / 100.0)
                    factor = max(0.7, min(1.3, factor))
                    audio = audio._spawn(audio.raw_data, overrides={"frame_rate": int(audio.frame_rate * factor)}).set_frame_rate(audio.frame_rate)
                    audio.export(save_path, format="mp3")
                return max(len(audio) / 1000.0, 1.0)
            except Exception:
                provider = "dashscope_qwen"
                voice = "Cherry"

        if provider == "dashscope_sambert":
            try:
                result = SambertSpeechSynthesizer.call(model=voice, text=text, sample_rate=48000, format='wav')
                audio_data = result.get_audio_data() if hasattr(result, 'get_audio_data') else None
                if not audio_data:
                    raise RuntimeError('Sambert 未返回音频数据')
                with open(save_path, 'wb') as file:
                    file.write(audio_data)
                audio = AudioSegment.from_file(save_path)
                if rate != "+0%":
                    factor = 1.0 + (float(rate.strip('%')) / 100.0)
                    factor = max(0.7, min(1.3, factor))
                    audio = audio._spawn(audio.raw_data, overrides={"frame_rate": int(audio.frame_rate * factor)}).set_frame_rate(audio.frame_rate)
                    audio.export(save_path, format='mp3')
                else:
                    audio.export(save_path, format='mp3')
                return max(len(audio) / 1000.0, 1.0)
            except Exception:
                provider = "dashscope_qwen"
                voice = "Cherry"

        try:
            response = requests.post(
                self.tts_base_url,
                headers={
                    "Content-Type": "application/json",
                    "Authorization": f"Bearer {self.tts_api_key}",
                },
                json={
                    "model": self.tts_model,
                    "input": {
                        "text": text,
                        "voice": voice,
                        "language_type": "Chinese",
                    },
                },
                timeout=120,
            )
            response.raise_for_status()
            result = response.json()
            audio_url, audio_base64 = self._extract_audio_payload(result)

            if audio_url:
                self._download_and_convert_audio(audio_url, save_path)
            elif audio_base64:
                temp_path = save_path + ".raw"
                with open(temp_path, "wb") as file:
                    file.write(base64.b64decode(audio_base64))
                audio = AudioSegment.from_file(temp_path)
                audio.export(save_path, format="mp3")
                os.remove(temp_path)
            else:
                raise RuntimeError(f"语音合成失败: {result}")

            audio = AudioSegment.from_file(save_path)
            return max(len(audio) / 1000.0, 1.0)
        except Exception:
            duration = max(2.0, min(len(text) * 0.22, 10.0))
            silence = AudioSegment.silent(duration=int(duration * 1000))
            silence.export(save_path, format="mp3")
            return duration

    def _normalize_tts_voice(self, provider: str, voice: str):
        if provider == "dashscope_cosyvoice":
            mapping = {
                "zh-CN-YunxiNeural": "longshuo_v3",
                "zh-CN-YunjianNeural": "longanyang",
                "zh-CN-YunyangNeural": "longsanshu",
                "zh-CN-XiaoxiaoNeural": "longxiaochun_v2",
                "zh-CN-XiaoyiNeural": "longanhuan",
                "zh-CN-XiaochenNeural": "longanwen",
            }
            return mapping.get(voice, voice or "longshuo_v3")
        if provider == "dashscope_qwen":
            return voice if voice and not voice.startswith("zh-CN-") else "Cherry"
        return voice

    def _extract_audio_payload(self, result: dict):
        output = result.get("output") or {}
        if output.get("audio_url"):
            return output.get("audio_url"), None
        if output.get("audio") and isinstance(output.get("audio"), str):
            return None, output.get("audio")

        audio = output.get("audio") or {}
        if isinstance(audio, dict):
            if audio.get("url"):
                return audio.get("url"), None
            if audio.get("data"):
                return None, audio.get("data")
        return None, None

    def _download_and_convert_audio(self, url: str, save_path: str):
        suffix = Path(urlparse(url).path).suffix or ".wav"
        with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as temp_file:
            temp_path = temp_file.name

        try:
            audio_response = requests.get(url, timeout=120)
            audio_response.raise_for_status()
            with open(temp_path, "wb") as file:
                file.write(audio_response.content)
            audio = AudioSegment.from_file(temp_path)
            audio.export(save_path, format="mp3")
        finally:
            if os.path.exists(temp_path):
                os.remove(temp_path)

    def _create_fallback_image(self, save_path: str, scene: dict):
        image = Image.new("RGB", (1920, 1080), "white")
        draw = ImageDraw.Draw(image)

        scene_id = int(scene.get("scene_id", 1))
        position_cycle = [620, 960, 1300]
        head_x = position_cycle[(scene_id - 1) % len(position_cycle)]
        head_y = 240 + ((scene_id - 1) % 2) * 40
        draw.ellipse((head_x - 70, head_y - 70, head_x + 70, head_y + 70), outline="black", width=8)
        draw.line((head_x, head_y + 70, head_x, 560), fill="black", width=10)
        arm_offset = 220 if scene_id % 2 == 0 else 160
        draw.line((head_x, 380, head_x - arm_offset, 470), fill="black", width=10)
        draw.line((head_x, 380, head_x + arm_offset, 470), fill="black", width=10)
        draw.line((head_x, 560, head_x - 150, 780), fill="black", width=10)
        draw.line((head_x, 560, head_x + 150, 780), fill="black", width=10)

        draw.rectangle((100, 120, 1820, 760), outline="#e5e7eb", width=3)
        if scene_id % 3 == 1:
            draw.rectangle((200, 200, 480, 360), outline="#94a3b8", width=6)
        elif scene_id % 3 == 2:
            draw.ellipse((1320, 180, 1600, 420), outline="#f59e0b", width=6)
        else:
            draw.line((250, 650, 1650, 650), fill="#10b981", width=8)

        desc = scene.get("scene_description", "火柴人场景")[:80]
        narration = scene.get("narration", "")[:120]
        draw.rectangle((120, 820, 1800, 980), outline="#d9a066", width=4)
        draw.text((160, 850), f"Scene: {desc}", fill="black")
        draw.text((160, 900), f"Narration: {narration}", fill="#444444")
        image.save(save_path, format="PNG")

    def _camera_type_for_index(self, index: int):
        return ["wide shot", "medium shot", "close-up"][(index - 1) % 3]

    def _action_for_index(self, index: int):
        return ["pointing to a board", "walking while explaining", "raising one hand for emphasis"][(index - 1) % 3]

    def _layout_for_index(self, index: int):
        return ["subject on left, empty space on right", "subject centered", "subject on right, diagram on left"][(index - 1) % 3]

    def _prepare_reference_audio(self, source_path: str, output_path: str):
        audio = AudioSegment.from_file(source_path)
        audio = audio.set_channels(1).normalize()
        audio.export(output_path, format="mp3")
        return max(len(audio) / 1000.0, 1.0)

    def _get_audio_duration(self, audio_path: str):
        audio = AudioSegment.from_file(audio_path)
        return max(len(audio) / 1000.0, 1.0)

    def _build_timeline(self, audio_segments):
        timeline = []
        for index, (_, duration) in enumerate(audio_segments, start=1):
            pause_padding = 0.35 if index < len(audio_segments) else 0.9
            timeline.append({"video_duration": round(max(duration + pause_padding, 2.2), 2)})
        return timeline

    def _duration_bounds_from_scene(self, scene: dict):
        raw = str(scene.get("duration_range") or "2-4").strip()
        match = re.match(r"^(\d+(?:\.\d+)?)\s*-\s*(\d+(?:\.\d+)?)$", raw)
        if not match:
            return 2.0, 4.0
        low = float(match.group(1))
        high = float(match.group(2))
        if high < low:
            low, high = high, low
        return low, high

    def _apply_scene_duration_ranges(self, timeline, storyboards):
        adjusted = []
        for index, item in enumerate(timeline):
            scene = storyboards[index] if index < len(storyboards) else {}
            low, high = self._duration_bounds_from_scene(scene)
            adjusted.append({"video_duration": round(min(max(item["video_duration"], low), high), 2)})
        return adjusted

    def _build_timeline_from_total_duration(self, total_duration: float, scene_count: int):
        base_duration = max(total_duration / max(scene_count, 1), 2.2)
        return [{"video_duration": round(base_duration, 2)} for _ in range(scene_count)]

    def _ensure_timeline_covers_audio(self, timeline, total_audio_duration: float):
        if not timeline:
            return timeline
        total_video_duration = sum(item["video_duration"] for item in timeline)
        required_duration = total_audio_duration + 0.8
        if total_video_duration < required_duration:
            timeline[-1]["video_duration"] = round(timeline[-1]["video_duration"] + (required_duration - total_video_duration), 2)
        return timeline

    def _create_image_clip(self, image_path: str, output_path: str, duration: float):
        cmd = [
            "ffmpeg",
            "-y",
            "-loop",
            "1",
            "-i",
            image_path,
            "-t",
            str(duration),
            "-vf",
            "scale=1920:1080:force_original_aspect_ratio=increase,crop=1920:1080,zoompan=z='min(zoom+0.0008,1.06)':d=1:s=1920x1080:x='iw/2-(iw/zoom/2)':y='ih/2-(ih/zoom/2)',fps=25",
            "-c:v",
            "libx264",
            "-pix_fmt",
            "yuv420p",
            output_path,
        ]
        self._run_ffmpeg(cmd, "生成视频片段失败")

    def _concat_audio(self, audio_segments, output_path: str):
        combined = AudioSegment.empty()
        for index, (audio_path, _) in enumerate(audio_segments, start=1):
            combined += AudioSegment.from_file(audio_path)
            if index < len(audio_segments):
                combined += AudioSegment.silent(duration=350)
        combined.export(output_path, format="mp3")

    def _concat_video_clips(self, clip_paths, output_path: str):
        with tempfile.NamedTemporaryFile("w", suffix=".txt", delete=False, encoding="utf-8") as file:
            for clip_path in clip_paths:
                safe_path = clip_path.replace("'", "''")
                file.write(f"file '{safe_path}'\n")
            list_path = file.name

        try:
            cmd = [
                "ffmpeg",
                "-y",
                "-f",
                "concat",
                "-safe",
                "0",
                "-i",
                list_path,
                "-c",
                "copy",
                output_path,
            ]
            self._run_ffmpeg(cmd, "拼接视频片段失败")
        finally:
            if os.path.exists(list_path):
                os.remove(list_path)

    def _merge_video_and_audio(self, video_path: str, audio_path: str):
        backend_dir = Path(__file__).resolve().parents[2]
        videos_dir = backend_dir / "videos"
        videos_dir.mkdir(parents=True, exist_ok=True)
        final_name = f"stickman_{uuid.uuid4().hex[:12]}.mp4"
        final_path = videos_dir / final_name

        cmd = [
            "ffmpeg",
            "-y",
            "-i",
            video_path,
            "-i",
            audio_path,
            "-c:v",
            "copy",
            "-c:a",
            "aac",
            "-shortest",
            str(final_path),
        ]
        self._run_ffmpeg(cmd, "合成最终视频失败")
        return str(final_path)

    def _run_ffmpeg(self, cmd, error_message: str):
        run_cmd = [self.ffmpeg_path if cmd and cmd[0] == "ffmpeg" else cmd[0], *cmd[1:]]
        try:
            subprocess.run(run_cmd, capture_output=True, text=True, check=True)
        except FileNotFoundError as exc:
            raise RuntimeError("未检测到 ffmpeg，可安装系统 ffmpeg 或使用 imageio-ffmpeg") from exc
        except subprocess.CalledProcessError as exc:
            detail = exc.stderr or exc.stdout or str(exc)
            raise RuntimeError(f"{error_message}: {detail[:800]}") from exc
