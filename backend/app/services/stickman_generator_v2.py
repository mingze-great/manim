import base64
import json
import logging
import os
import re
import shutil
import subprocess
import tempfile
import time
import uuid
from pathlib import Path
from urllib.parse import urlparse
from typing import Optional

import imageio_ffmpeg
import requests
from openai import OpenAI
from PIL import Image, ImageDraw, ImageFilter, ImageFont, ImageOps, ImageStat
from pydub import AudioSegment
from pydub.effects import compress_dynamic_range
from pydub.silence import detect_nonsilent
import dashscope
from dashscope.audio.tts_v2 import SpeechSynthesizer
from dashscope.audio.tts import SpeechSynthesizer as SambertSpeechSynthesizer

from app.config import get_settings
from app.services.stickman_v2_assets import normalize_scene_overlay_image


logger = logging.getLogger(__name__)


class StickmanGenerator:
    def __init__(self):
        self.settings = get_settings()
        self.llm_api_key = self.settings.STICKMAN_LLM_API_KEY or self.settings.DASHSCOPE_API_KEY or self.settings.OPENAI_API_KEY or self.settings.DEEPSEEK_API_KEY
        self.llm_base_url = self.settings.STICKMAN_LLM_BASE_URL or self.settings.DASHSCOPE_BASE_URL or self.settings.OPENAI_BASE_URL or self.settings.DEEPSEEK_BASE_URL
        self.llm_model = self.settings.STICKMAN_LLM_MODEL or self.settings.DASHSCOPE_CHAT_MODEL or self.settings.OPENAI_MODEL or self.settings.DEEPSEEK_MODEL
        self.llm_models = self._resolve_llm_models()
        self.image_api_key = self.settings.STICKMAN_IMAGE_API_KEY or getattr(self.settings, "IMAGE_API_KEY", "") or self.settings.DASHSCOPE_API_KEY
        self.image_base_url = self.settings.STICKMAN_IMAGE_BASE_URL or getattr(self.settings, "IMAGE_BASE_URL", "")
        self.image_model = self.settings.STICKMAN_IMAGE_MODEL or getattr(self.settings, "IMAGE_MODEL", "wan2.7-image")
        self.scene_image_model = self.settings.STICKMAN_SCENE_IMAGE_MODEL or self.image_model or "qwen-image-max-2025-12-30"
        self.scene_image_models = [item.strip() for item in (getattr(self.settings, "STICKMAN_SCENE_IMAGE_MODELS", "") or "").split(",") if item.strip()]
        if self.scene_image_model and self.scene_image_model not in self.scene_image_models:
            self.scene_image_models.insert(0, self.scene_image_model)
        self.scene_image_size = "1664*928"
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
        self.tts_fallback_models = [
            item.strip()
            for item in (getattr(self.settings, "STICKMAN_TTS_FALLBACK_MODELS", "") or "").split(",")
            if item.strip()
        ]
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
        self.background_asset_dir = Path(__file__).resolve().parents[1] / "assets" / "backgrounds"
        self.background_asset_dir.mkdir(parents=True, exist_ok=True)
        self.material_library_enabled = bool(getattr(self.settings, "STICKMAN_MATERIAL_LIBRARY_ENABLED", True))
        self.material_library_path = self._resolve_material_library_path()
        self.material_source_dir = self._resolve_material_source_dir()
        self.material_library = self._load_material_library()
        self.subtitle_translation_cache = {}
        self.direct_psychology_background = self._resolve_background_image_path()
        self.font_candidates = self._resolve_font_candidates()

    def _load_tts_voice_library(self):
        raw = self.settings.STICKMAN_TTS_VOICE_LIBRARY or "[]"
        try:
            data = json.loads(raw)
            if isinstance(data, list):
                return data
        except Exception:
            pass
        return []

    def _resolve_llm_models(self):
        candidates = [
            getattr(self.settings, "STICKMAN_LLM_MODEL", ""),
            getattr(self.settings, "DASHSCOPE_CHAT_MODEL", ""),
            getattr(self.settings, "DASHSCOPE_CHAT_FALLBACK_MODEL_1", ""),
            getattr(self.settings, "DASHSCOPE_CHAT_FALLBACK_MODEL_2", ""),
            getattr(self.settings, "OPENAI_MODEL", ""),
            getattr(self.settings, "DEEPSEEK_MODEL", ""),
            getattr(self.settings, "GLM_MODEL", ""),
        ]
        ordered = []
        seen = set()
        for candidate in candidates:
            value = str(candidate or "").strip()
            if value and value not in seen:
                ordered.append(value)
                seen.add(value)
        return ordered or [self.llm_model]

    def _chat_completion(self, messages: list[dict], temperature: float, max_tokens: int):
        last_error = None
        for model in self.llm_models:
            try:
                return self.llm_client.chat.completions.create(
                    model=model,
                    messages=messages,
                    temperature=temperature,
                    max_tokens=max_tokens,
                )
            except Exception as exc:
                last_error = exc
                continue
        raise last_error or RuntimeError("火柴人脚本模型不可用")

    def _resolve_material_library_path(self):
        configured = str(getattr(self.settings, "STICKMAN_MATERIAL_LIBRARY_PATH", "") or "").strip()
        candidates = [configured] if configured else []
        if os.name == "nt":
            candidates.append(r"E:\ai\cankao\sucai_clean_alpha\materials.json")
            candidates.append(r"E:\ai\cankao\sucai_clean\materials.json")
            candidates.append(r"E:\ai\cankao\sucai_cropped\materials.json")
            candidates.append(r"E:\ai\cankao\sucai\materials.json")
        else:
            candidates.append("/opt/manim-v2-material-library/materials.json")
            candidates.append("/opt/manim-v2-materials/materials.json")
        candidates.append(str(Path(__file__).resolve().parents[1] / "assets" / "materials" / "materials.json"))
        for candidate in candidates:
            if candidate and Path(candidate).exists():
                return Path(candidate)
        return Path(configured) if configured else Path(candidates[-1])

    def _resolve_background_image_path(self):
        configured = str(getattr(self.settings, "STICKMAN_V2_BACKGROUND_IMAGE_PATH", "") or "").strip()
        candidates = [configured] if configured else []
        if os.name == "nt":
            candidates.append(r"E:\ai\cankao\背景1.png")
        candidates.append(str(self.background_asset_dir / "psychology_reference_background.png"))
        for candidate in candidates:
            if candidate and Path(candidate).exists():
                return Path(candidate)
        return Path(configured) if configured else (self.background_asset_dir / "psychology_reference_background.png")

    def _resolve_font_candidates(self):
        configured = str(getattr(self.settings, "STICKMAN_V2_FONT_PATHS", "") or "").strip()
        candidates = [item.strip() for item in configured.split(",") if item.strip()]
        if os.name == "nt":
            candidates.extend([r"C:\Windows\Fonts\msyh.ttc", r"C:\Windows\Fonts\simhei.ttf", r"C:\Windows\Fonts\msyhbd.ttc"])
        else:
            candidates.extend([
                "/usr/share/fonts/truetype/noto/NotoSansCJK-Regular.ttc",
                "/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc",
                "/usr/share/fonts/truetype/wqy/wqy-zenhei.ttc",
                "/usr/share/fonts/truetype/arphic/ukai.ttc",
                "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
                "/usr/share/fonts/truetype/noto/NotoSansCJK-Bold.ttc",
                "/usr/share/fonts/opentype/noto/NotoSansCJK-Bold.ttc",
            ])
        seen = set()
        ordered = []
        for candidate in candidates:
            if candidate and candidate not in seen:
                ordered.append(candidate)
                seen.add(candidate)
        return ordered

    def _resolve_material_source_dir(self):
        configured = str(getattr(self.settings, "STICKMAN_MATERIAL_SOURCE_DIR", "") or "").strip()
        candidates = [configured] if configured else []
        if self.material_library_path and self.material_library_path.exists():
            candidates.append(str(self.material_library_path.parent))
        if os.name == "nt":
            candidates.append(r"E:\ai\cankao\sucai_clean_alpha")
            candidates.append(r"E:\ai\cankao\sucai_clean")
            candidates.append(r"E:\ai\cankao\sucai_cropped")
            candidates.append(r"E:\ai\cankao\sucai")
        else:
            candidates.append("/opt/manim-v2-material-library")
            candidates.append("/opt/manim-v2-materials")
        candidates.append(str(Path(__file__).resolve().parents[1] / "assets" / "materials"))
        for candidate in candidates:
            if candidate and Path(candidate).exists():
                return Path(candidate)
        return Path(configured) if configured else Path(candidates[-1])

    def _load_material_library(self):
        if not self.material_library_enabled:
            return []

        raw_entries = []
        if self.material_library_path and self.material_library_path.exists():
            try:
                payload = json.loads(self.material_library_path.read_text(encoding="utf-8"))
                if isinstance(payload, list):
                    raw_entries = payload
            except Exception:
                raw_entries = []

        if raw_entries:
            normalized = []
            for entry in raw_entries:
                normalized_entry = self._normalize_material_entry(entry)
                if normalized_entry:
                    normalized.append(normalized_entry)
            return normalized

        auto_entries = []
        source_dir = self.material_source_dir
        if source_dir and source_dir.exists():
            for image_path in sorted(source_dir.glob("*.png"), key=lambda item: (len(item.stem), item.stem)):
                auto_entries.append(self._normalize_material_entry({"file_name": image_path.name, "image_path": str(image_path)}))
        return [entry for entry in auto_entries if entry]

    def _normalize_material_entry(self, entry: dict, source_dir: Optional[Path] = None):
        if not isinstance(entry, dict):
            return None
        file_name = str(entry.get("file_name") or "").strip()
        image_path = str(entry.get("image_path") or "").strip()
        base_dir = source_dir or self.material_source_dir
        candidate = base_dir / file_name if file_name and base_dir else None
        if (not image_path or not Path(image_path).exists()) and candidate and candidate.exists():
            image_path = str(candidate)
        if not image_path or not Path(image_path).exists():
            return None

        normalized = dict(entry)
        normalized["file_name"] = file_name or Path(image_path).name
        normalized["image_path"] = image_path
        normalized["match_index"] = self._material_match_index(entry)
        normalized["has_semantic_metadata"] = any(
            entry.get(key)
            for key in [
                "emotion_primary",
                "emotion_secondary",
                "psychology_concepts",
                "applicable_topics",
                "storyboard_roles",
                "search_keywords",
                "usage_notes",
            ]
        )
        normalized["emotion_primary_norm"] = self._normalize_tag(entry.get("emotion_primary"))
        normalized["emotion_secondary_norm"] = {self._normalize_tag(item) for item in (entry.get("emotion_secondary") or []) if self._normalize_tag(item)}
        normalized["concepts_norm"] = {self._normalize_tag(item) for item in (entry.get("psychology_concepts") or []) if self._normalize_tag(item)}
        normalized["topics_norm"] = {self._normalize_tag(item) for item in (entry.get("applicable_topics") or []) if self._normalize_tag(item)}
        normalized["roles_norm"] = {self._normalize_tag(item) for item in (entry.get("storyboard_roles") or []) if self._normalize_tag(item)}
        normalized["negative_norm"] = {self._normalize_tag(item) for item in (entry.get("negative_keywords") or []) if self._normalize_tag(item)}
        return normalized

    def _load_material_library_from_paths(self, material_json_path: Optional[str], material_source_dir: Optional[str]):
        manifest_path = Path(str(material_json_path or "").strip()) if str(material_json_path or "").strip() else None
        source_dir = Path(str(material_source_dir or "").strip()) if str(material_source_dir or "").strip() else None
        if not manifest_path or not manifest_path.exists():
            return []
        try:
            payload = json.loads(manifest_path.read_text(encoding="utf-8"))
        except Exception:
            return []
        if not isinstance(payload, list):
            return []
        normalized = []
        for entry in payload:
            normalized_entry = self._normalize_material_entry(entry, source_dir=source_dir)
            if normalized_entry:
                normalized.append(normalized_entry)
        return normalized

    def _material_match_index(self, entry: dict):
        values = []
        for key in [
            "image_type",
            "primary_subject",
            "pose_action",
            "scene_context",
            "emotion_primary",
            "metaphor_meaning",
            "usage_notes",
            "composition",
        ]:
            values.append(entry.get(key))
        for key in [
            "emotion_secondary",
            "psychology_concepts",
            "applicable_topics",
            "storyboard_roles",
            "style_tags",
            "search_keywords",
            "props_objects",
        ]:
            values.extend(entry.get(key) or [])
        return self._extract_match_tokens(*values)

    def _clean_match_text(self, text: str):
        return re.sub(r"\s+", " ", re.sub(r"[^0-9a-zA-Z\u4e00-\u9fff]+", " ", str(text or "").lower())).strip()

    def _extract_match_tokens(self, *values):
        tokens = set()
        for value in values:
            if value is None:
                continue
            if isinstance(value, (list, tuple, set)):
                tokens.update(self._extract_match_tokens(*list(value)))
                continue
            cleaned = self._clean_match_text(str(value))
            if not cleaned:
                continue
            tokens.add(cleaned)
            for part in cleaned.split():
                if len(part) >= 2:
                    tokens.add(part)
        return tokens

    def _normalize_tag(self, value):
        cleaned = self._clean_match_text(str(value or ""))
        if not cleaned:
            return ""
        synonym_groups = {
            "happy": ["开心", "高兴", "喜悦", "庆祝", "成功", "轻松"],
            "sad": ["悲伤", "难过", "低落", "沮丧", "委屈", "无助"],
            "angry": ["愤怒", "生气", "暴躁", "爆发"],
            "anxious": ["焦虑", "不安", "紧张", "压力", "内耗"],
            "tired": ["疲惫", "累", "耗竭", "没力气", "乏力", "低能量"],
            "relaxed": ["放松", "恢复", "休息", "疗愈", "平静"],
            "confidence": ["自信", "笃定", "底气", "掌控感"],
            "focus": ["专注", "投入", "执行", "学习", "工作"],
            "shame": ["羞愧", "讨好", "退让", "压缩自己"],
            "cry": ["哭", "哭泣", "崩溃"],
            "phone": ["手机", "刷手机", "看手机"],
            "rest": ["睡觉", "休息", "躺平", "恢复"],
            "alone": ["独处", "一个人", "树下", "听歌"],
            "hook": ["hook", "开场"],
            "problem": ["problem", "问题"],
            "cause": ["cause", "原因"],
            "method": ["method", "方法"],
            "transition": ["transition", "转折"],
            "result": ["result", "结果"],
            "summary": ["summary", "总结"],
        }
        for canonical, aliases in synonym_groups.items():
            if cleaned == canonical or cleaned in aliases:
                return canonical
        return cleaned

    def _storyboard_role_from_scene(self, scene: dict, index: int, total: int):
        text = " ".join(
            [
                str(scene.get("scene_title") or ""),
                str(scene.get("scene_description") or ""),
                str(scene.get("narration") or ""),
                " ".join(str(item) for item in (scene.get("keywords") or [])),
            ]
        ).lower()
        if index == 1:
            return "hook"
        if any(word in text for word in ["所以", "因此", "因为", "根源", "原因"]):
            return "cause"
        if any(word in text for word in ["可以", "试着", "先", "然后", "步骤", "方法", "做法"]):
            return "method"
        if any(word in text for word in ["最后", "结果", "你会", "开始", "变得", "做到"]):
            return "result" if index >= max(total - 1, 1) else "transition"
        if index == total:
            return "summary"
        if index >= max(total - 1, 1):
            return "result"
        return "problem"

    def _scene_query_profile(self, scene: dict, index: int, total: int):
        narration = str(scene.get("narration") or "")
        description = str(scene.get("scene_description") or "")
        keywords = [str(item) for item in (scene.get("keywords") or []) if str(item).strip()]
        tokens = self._extract_match_tokens(scene.get("scene_title"), narration, description, keywords, scene.get("visual_focus"))
        normalized_tokens = {self._normalize_tag(token) for token in tokens if self._normalize_tag(token)}
        emotions = {token for token in normalized_tokens if token in {"happy", "sad", "angry", "anxious", "tired", "relaxed", "confidence", "focus", "shame", "cry"}}
        concepts = {
            token
            for token in normalized_tokens
            if token not in {"hook", "problem", "cause", "method", "transition", "result", "summary"}
        }
        role = self._storyboard_role_from_scene(scene, index, total)
        return {
            "tokens": tokens,
            "normalized_tokens": normalized_tokens,
            "emotions": emotions,
            "concepts": concepts,
            "role": role,
            "role_norm": self._normalize_tag(role),
        }

    def _score_material_for_scene(self, query: dict, material: dict):
        score = 0
        reasons = []

        concept_hits = sorted(query["concepts"] & material.get("concepts_norm", set()))
        if concept_hits:
            score += min(40, 20 + len(concept_hits) * 10)
            reasons.append(f"concept:{','.join(concept_hits[:3])}")

        emotion_hits = sorted(query["emotions"] & ({material.get('emotion_primary_norm')} | material.get("emotion_secondary_norm", set())))
        if emotion_hits:
            score += min(25, 15 + len(emotion_hits) * 5)
            reasons.append(f"emotion:{','.join(emotion_hits[:2])}")

        topic_hits = sorted(query["normalized_tokens"] & material.get("topics_norm", set()))
        if topic_hits:
            score += min(15, 8 + len(topic_hits) * 3)
            reasons.append(f"topic:{','.join(topic_hits[:2])}")

        if query["role_norm"] and query["role_norm"] in material.get("roles_norm", set()):
            score += 10
            reasons.append(f"role:{query['role_norm']}")

        token_hits = sorted(query["tokens"] & material.get("match_index", set()))
        if token_hits:
            score += min(10, len(token_hits) * 2)
            reasons.append(f"token:{','.join(token_hits[:3])}")

        negative_hits = sorted(query["normalized_tokens"] & material.get("negative_norm", set()))
        if negative_hits:
            score -= 35
            reasons.append(f"negative:{','.join(negative_hits[:2])}")

        if not score and query["role_norm"] in {"hook", "problem"} and material.get("emotion_primary_norm") in {"sad", "angry", "anxious", "tired", "shame", "cry"}:
            score += 6
            reasons.append("fallback:negative_scene")
        if not score and query["role_norm"] in {"result", "summary"} and material.get("emotion_primary_norm") in {"happy", "relaxed", "confidence"}:
            score += 6
            reasons.append("fallback:positive_scene")

        return score, reasons

    def _select_material_candidates(self, storyboards: list[dict]):
        if not self.material_library:
            return []

        scored_by_scene = []
        total = len(storyboards)
        for index, scene in enumerate(storyboards, start=1):
            query = self._scene_query_profile(scene, index, total)
            candidates = []
            for material in self.material_library:
                score, reasons = self._score_material_for_scene(query, material)
                candidates.append({
                    "material": material,
                    "score": score,
                    "reasons": reasons,
                    "query": query,
                })
            candidates.sort(key=lambda item: (-item["score"], item["material"].get("file_name") or ""))
            scored_by_scene.append({
                "scene_index": index,
                "scene": scene,
                "query": query,
                "candidates": candidates,
            })

        ordered = sorted(
            scored_by_scene,
            key=lambda item: (
                sum(1 for candidate in item["candidates"] if candidate["score"] > 0),
                -(item["candidates"][0]["score"] if item["candidates"] else 0),
            ),
        )
        used = set()
        selected = {}
        for item in ordered:
            chosen = next((candidate for candidate in item["candidates"] if candidate["material"]["file_name"] not in used), None)
            if not chosen:
                continue
            used.add(chosen["material"]["file_name"])
            selected[item["scene_index"]] = chosen

        return [selected.get(index) for index in range(1, total + 1)]

    def _prepare_material_frame(self, source_path: Path, target_path: Path, aspect_ratio: str):
        canvas_size = (1920, 1080) if aspect_ratio == "16:9" else (1080, 1920)
        canvas = Image.new("RGB", canvas_size, (255, 255, 255))
        with Image.open(source_path).convert("RGB") as image:
            image.thumbnail(canvas_size, Image.Resampling.LANCZOS)
            x = (canvas_size[0] - image.width) // 2
            y = (canvas_size[1] - image.height) // 2
            canvas.paste(image, (x, y))
        canvas.save(target_path, format="PNG")

    def _fixed_background_size(self, aspect_ratio: str):
        return (1920, 1080) if aspect_ratio == "16:9" else (1080, 1920)

    def _create_fixed_reference_background(self, save_path: str, aspect_ratio: str, scene: Optional[dict] = None, background_image_path: Optional[str] = None):
        width, height = self._fixed_background_size(aspect_ratio)
        preferred_background = Path(background_image_path) if background_image_path else self.direct_psychology_background
        if preferred_background.exists():
            with Image.open(preferred_background).convert("RGB") as image:
                if image.size == (width, height):
                    image.save(save_path, format="PNG")
                else:
                    image.resize((width, height), Image.Resampling.LANCZOS).save(save_path, format="PNG")
            return
        self._draw_psychology_cover_background(save_path, scene or {}, width, height)

    def _non_white_bbox(self, image: Image.Image):
        width, height = image.size
        pixels = image.load()
        left = width
        top = height
        right = -1
        bottom = -1
        for y in range(height):
            for x in range(width):
                r, g, b = pixels[x, y][:3]
                if not (r >= 245 and g >= 245 and b >= 245):
                    left = min(left, x)
                    top = min(top, y)
                    right = max(right, x)
                    bottom = max(bottom, y)
        if right < left or bottom < top:
            return 0, 0, width, height
        return left, top, right + 1, bottom + 1

    def _prepare_material_scene_image(self, source_path: Path, target_path: Path, output_size: int = 480):
        with Image.open(source_path).convert("RGB") as image:
            left, top, right, bottom = self._non_white_bbox(image)
            box_width = max(right - left, 1)
            box_height = max(bottom - top, 1)
            side = max(int(round(max(box_width, box_height) * 1.10)), 8)
            center_x = (left + right) / 2
            center_y = (top + bottom) / 2
            crop_left = int(round(center_x - side / 2))
            crop_top = int(round(center_y - side / 2))
            crop_right = crop_left + side
            crop_bottom = crop_top + side

            if crop_left < 0:
                crop_right -= crop_left
                crop_left = 0
            if crop_top < 0:
                crop_bottom -= crop_top
                crop_top = 0
            if crop_right > image.width:
                shift = crop_right - image.width
                crop_left = max(0, crop_left - shift)
                crop_right = image.width
            if crop_bottom > image.height:
                shift = crop_bottom - image.height
                crop_top = max(0, crop_top - shift)
                crop_bottom = image.height

            cropped = image.crop((crop_left, crop_top, crop_right, crop_bottom)).convert("RGBA")
            pixels = cropped.load()
            for y in range(cropped.height):
                for x in range(cropped.width):
                    r, g, b, a = pixels[x, y]
                    if r >= 245 and g >= 245 and b >= 245:
                        pixels[x, y] = (255, 255, 255, 0)

            bbox = cropped.getbbox()
            if bbox:
                cropped = cropped.crop(bbox)

            canvas = Image.new("RGBA", (output_size, output_size), (255, 255, 255, 0))
            cropped.thumbnail((output_size, output_size), Image.Resampling.LANCZOS)
            x = (output_size - cropped.width) // 2
            y = (output_size - cropped.height) // 2
            canvas.alpha_composite(cropped, (x, y))
            canvas.save(target_path, format="PNG")

    def _build_material_assets(self, storyboards: list[dict], image_output_dir: Path, aspect_ratio: str, material_library: Optional[list[dict]] = None):
        library = material_library if material_library is not None else self.material_library
        if not library:
            return [], {
                "material_library_used": False,
                "material_library_reason": "图片库为空，已回退模型生成",
            }

        if not any(item.get("has_semantic_metadata") for item in library):
            assets = []
            material_pool = library[:]
            for index, scene in enumerate(storyboards, start=1):
                material = material_pool[(index - 1) % len(material_pool)]
                source_path = Path(material["image_path"])
                scene["matched_material_file"] = material.get("file_name")
                scene["matched_material_score"] = 1
                scene["matched_material_reasons"] = ["fallback:sequential_material_library"]
                assets.append({
                    "scene_id": scene.get("scene_id", index),
                    "prompt": f"material_fallback:{material.get('file_name')}",
                    "scene_image_path": str(source_path),
                    "scene_image_url": None,
                    "used_fallback": False,
                    "image_source": "material_library",
                    "model_used": None,
                    "scene_image_source": "material_library",
                    "scene_image_model_used": None,
                    "material_file_name": material.get("file_name"),
                    "material_match_score": 1,
                    "material_match_reasons": ["fallback:sequential_material_library"],
                    "error_summary": "画面已准备完成。",
                })
            return assets, {
                "material_library_used": True,
                "material_library_count": len(library),
                "material_selection_unique": len(library) >= len(storyboards),
                "material_library_reason": "图片库缺少语义标签，已按顺序使用图片库",
            }

        original_library = self.material_library
        self.material_library = library
        try:
            selections = self._select_material_candidates(storyboards)
        finally:
            self.material_library = original_library
        if not selections or any(selection is None for selection in selections):
            return [], {
                "material_library_used": False,
                "material_library_reason": "图片匹配失败或数量不足",
            }

        if any((selection or {}).get("score", 0) <= 0 for selection in selections):
            return [], {
                "material_library_used": False,
                "material_library_reason": "当前分镜与图片语义匹配度不足，已回退模型生成",
            }

        assets = []
        for index, selection in enumerate(selections, start=1):
            material = selection["material"]
            source_path = Path(material["image_path"])
            scene = storyboards[index - 1]
            scene["matched_material_file"] = material.get("file_name")
            scene["matched_material_score"] = selection["score"]
            scene["matched_material_reasons"] = selection["reasons"]
            assets.append({
                "scene_id": scene.get("scene_id", index),
                "prompt": f"material_match:{material.get('file_name')}",
                "scene_image_path": str(source_path),
                "scene_image_url": None,
                "used_fallback": False,
                "image_source": "material_library",
                "model_used": None,
                "scene_image_source": "material_library",
                "scene_image_model_used": None,
                "material_file_name": material.get("file_name"),
                "material_match_score": selection["score"],
                "material_match_reasons": selection["reasons"],
                "error_summary": None,
            })
        return assets, {
            "material_library_used": True,
            "material_library_count": len(library),
            "material_selection_unique": True,
        }

    def get_tts_voice_library(self):
        return self.tts_voice_library

    def _strip_terminal_punctuation(self, text: str):
        return re.sub(r'[，。,.!?！？；;：:、…·~～）)】〕]+$', "", str(text or "").strip())

    def _sanitize_english_subtitle(self, text: str):
        cleaned = str(text or "").replace("|", " ").strip()
        cleaned = re.sub(r"\s+", " ", cleaned)
        cleaned = re.sub(r"^[\-–—|\s]+|[\-–—|\s]+$", "", cleaned)
        if not re.search(r"[A-Za-z]", cleaned):
            return ""
        return self._strip_terminal_punctuation(cleaned)

    def _fallback_translate_subtitle(self, text: str):
        text = str(text or "").strip()
        phrase_map = {
            "很多焦虑，不是事情太多，而是大脑一直在预演失败": "Anxiety is not from too much to do, but from replaying failure in your mind.",
            "第一步，先停掉脑内预演，把注意力从结果拉回到眼前这一步": "First, stop the mental rehearsal and bring your attention back to the step in front of you.",
            "第二步，一次只做一件事，单点推进，比来回切换更能降低心理消耗": "Second, do one thing at a time. Single-point progress drains less energy than constant switching.",
            "第三步，给每次行动一个收尾动作，让大脑感受到完成，而不是悬着": "Third, give every action a closing move so your brain can feel completion instead of hanging tension.",
        }
        normalized = self._strip_terminal_punctuation(text)
        if normalized in phrase_map:
            return phrase_map[normalized]
        if normalized.startswith("很多焦虑"):
            return "Anxiety is not caused by having too much to do"
        if "预演失败" in normalized:
            return "Your mind keeps rehearsing failure"
        if normalized.startswith("第一步"):
            return "Step one, stop the mental rehearsal"
        if "把注意力从结果拉回到眼前这一步" in normalized:
            return "Bring your attention back to the step in front of you"
        if normalized.startswith("第二步"):
            return "Step two, do one thing at a time"
        if "单点推进" in normalized or "来回切换" in normalized:
            return "Single-point progress reduces mental drain"
        if normalized.startswith("第三步"):
            return "Step three, give every action a closing move"
        if "让大脑感受到完成" in normalized or "不是悬着" in normalized:
            return "Let your brain feel completion instead of hanging tension"
        word_map = {
            "焦虑": "anxiety",
            "失败": "failure",
            "注意力": "attention",
            "结果": "result",
            "一步": "step",
            "一次": "one thing at a time",
            "行动": "action",
            "完成": "completion",
            "悬着": "hanging tension",
        }
        parts = [word_map.get(part, "") for part in re.split(r"[，。！？、\s]+", normalized) if part]
        english = " ".join(item for item in parts if item).strip()
        return english.capitalize() + ("." if english else "")

    def _translate_subtitle_to_english(self, text: str):
        text = str(text or "").strip()
        if not text:
            return ""
        cached = self.subtitle_translation_cache.get(text)
        if cached is not None:
            return cached
        english = ""
        try:
            response = self._chat_completion(
                messages=[
                    {"role": "system", "content": "Translate Chinese subtitles into concise natural English. Return only the English translation."},
                    {"role": "user", "content": text},
                ],
                temperature=0.1,
                max_tokens=80,
            )
            english = str(response.choices[0].message.content or "").strip()
            english = re.sub(r"^['\"\s]+|['\"\s]+$", "", english)
        except Exception:
            english = ""
        if not english:
            english = self._fallback_translate_subtitle(text)
        english = self._sanitize_english_subtitle(english)
        self.subtitle_translation_cache[text] = english
        return english

    def _split_sentences(self, text: str) -> list[str]:
        parts = [item.strip() for item in re.split(r'(?<=[。！？!?])\s*', text or '') if item.strip()]
        return parts or ([text.strip()] if text and text.strip() else [])

    def _normalize_locked_subtitle_text(self, text: str) -> str:
        cleaned = str(text or "").strip()
        return cleaned.replace("“", "").replace("”", "").replace("‘", "").replace("’", "").replace('"', "").replace("'", "").replace("*", "")

    def _normalize_storyboard_fragment(self, text: str) -> str:
        cleaned = self._normalize_locked_subtitle_text(text)
        cleaned = re.sub(r'^[，、；：:,.!?！？]+', '', cleaned)
        cleaned = self._strip_terminal_punctuation(cleaned) or cleaned
        return re.sub(r"\s+", "", cleaned).strip()

    def _split_enumeration_items(self, text: str) -> list[str]:
        raw = self._normalize_locked_subtitle_text(text)
        if "、" not in raw:
            return []
        items = [self._normalize_storyboard_fragment(item) for item in raw.split("、") if self._normalize_storyboard_fragment(item)]
        if len(items) < 2:
            return []
        if len(items) == 2 and items[1].startswith(items[0]):
            return [self._normalize_storyboard_fragment(raw)]
        if all(len(item) <= 10 for item in items):
            return items
        return []

    def _quote_spans(self, text: str) -> list[tuple[int, int]]:
        spans: list[tuple[int, int]] = []
        patterns = [
            r'“[^”]+”',
            r'‘[^’]+’',
            r'「[^」]+」',
            r'『[^』]+』',
            r'《[^》]+》',
            r'"[^"]+"',
            r"'[^']+'",
        ]
        for pattern in patterns:
            for match in re.finditer(pattern, text or ""):
                spans.append((match.start(), match.end()))
        return spans

    def _index_inside_quote_span(self, index: int, spans: list[tuple[int, int]]) -> bool:
        return any(start < index < end for start, end in spans)

    def _best_semantic_break_index(self, text: str, target: int, min_index: int, max_index: int) -> int:
        content = str(text or "").strip()
        if len(content) <= 1:
            return 0
        spans = self._quote_spans(content)
        candidates: list[tuple[int, int]] = []

        for match in re.finditer(r"[，；：、,;:]", content):
            split_at = match.end()
            if min_index <= split_at <= max_index and not self._index_inside_quote_span(split_at, spans):
                candidates.append((split_at, 0))

        before_cues = ["但是", "但", "所以", "于是", "然后", "而且", "并且", "不过", "可是", "如果", "当", "一到", "到了", "后来", "最后", "其实", "比如", "而是", "哪怕", "即使"]
        after_cues = ["的时候", "之后", "以后", "的话", "这种", "这个", "那个", "就是", "不是", "只要", "因为"]

        for cue in before_cues:
            start = 0
            while True:
                idx = content.find(cue, start)
                if idx < 0:
                    break
                if min_index <= idx <= max_index and not self._index_inside_quote_span(idx, spans):
                    candidates.append((idx, 1))
                start = idx + len(cue)

        for cue in after_cues:
            start = 0
            while True:
                idx = content.find(cue, start)
                if idx < 0:
                    break
                split_at = idx + len(cue)
                if min_index <= split_at <= max_index and not self._index_inside_quote_span(split_at, spans):
                    candidates.append((split_at, 2))
                start = idx + len(cue)

        if not candidates:
            return 0

        def score(item: tuple[int, int]) -> tuple[int, int, int]:
            split_at, priority = item
            previous = content[:split_at].strip()
            current = content[split_at:].strip()
            awkward = int(previous.endswith(("的", "了", "呢", "吗", "啊", "呀", "吧", "和", "跟", "与", "及", "并", "而", "但", "却", "就", "也", "还", "又", "再", "先")))
            awkward += int(current.startswith(("的", "了", "呢", "吗", "啊", "呀", "吧", "和", "跟", "与", "及", "并", "而", "但", "却", "就", "也", "还", "又", "再", "先")))
            return (abs(split_at - target), priority, awkward)

        return min(candidates, key=score)[0]

    def _semantic_split_long_text(self, text: str, preferred_max: int, hard_max: int, min_tail: int = 6) -> list[str]:
        remaining = self._normalize_locked_subtitle_text(text)
        if not remaining:
            return []
        segments: list[str] = []
        while len(remaining) > preferred_max:
            max_index = min(max(preferred_max + 4, preferred_max), min(hard_max, len(remaining) - min_tail))
            min_index = max(6, min(preferred_max - 4, max_index - 4))
            target = min(preferred_max, max_index)
            split_at = self._best_semantic_break_index(remaining, target, min_index, max_index)
            if not split_at:
                split_at = max_index
            piece = self._normalize_storyboard_fragment(remaining[:split_at])
            if not piece:
                break
            segments.append(piece)
            remaining = remaining[split_at:].strip()
        if remaining:
            tail = self._normalize_storyboard_fragment(remaining)
            if tail:
                segments.append(tail)
        return segments

    def _review_semantic_segments(self, segments: list[str], soft_limit: int = 18) -> list[str]:
        cleaned = [str(item or "").strip() for item in segments if str(item or "").strip()]
        if len(cleaned) <= 1:
            return cleaned

        quote_openers = ("“", "‘", "「", "『", "《")
        quote_closers = ("”", "’", "」", "』", "》")
        reviewed: list[str] = []

        def should_merge(previous: str, current: str) -> bool:
            combined = previous + current
            if len(combined) > soft_limit:
                return False
            if previous.endswith(quote_openers) or current.startswith(quote_closers):
                return True
            if current.startswith(previous):
                return True
            if len(previous) >= 2 and current.startswith(previous[-2:]):
                return True
            if previous.endswith(("，", "、", "；", ":", "：", "（", "(")):
                return True
            semantic_pairs = [
                ("完成", "永远比完美更重要"),
                ("怎么打破", "这个死循环"),
            ]
            return any(previous.endswith(left) and current.startswith(right) for left, right in semantic_pairs)

        for segment in cleaned:
            if not reviewed:
                reviewed.append(segment)
                continue
            previous = reviewed[-1]
            if should_merge(previous, segment):
                reviewed[-1] = previous + segment
                continue
            reviewed.append(segment)
        return reviewed

    def _split_script_for_storyboards(self, text: str) -> list[str]:
        raw = str(text or "")
        if not raw.strip():
            return []

        def split_long_chunk(chunk: str, max_chars: int = 16) -> list[str]:
            clean_chunk = self._normalize_storyboard_fragment(chunk)
            if not clean_chunk:
                return []
            if len(clean_chunk) <= max_chars:
                return [clean_chunk]
            if not re.search(r"[，；：,;:。！？!?]", clean_chunk):
                return self._semantic_split_long_text(clean_chunk, preferred_max=14, hard_max=16)
            pieces = []
            current = ""
            for char in clean_chunk:
                current += char
                if char in "。！？!?" and len(current) >= 8:
                    normalized = self._normalize_storyboard_fragment(current)
                    if normalized:
                        pieces.append(normalized)
                    current = ""
                    continue
                if len(current) >= max_chars and char in "，；：、,;:":
                    normalized = self._normalize_storyboard_fragment(current)
                    if normalized:
                        pieces.append(normalized)
                    current = ""
            if current.strip():
                normalized = self._normalize_storyboard_fragment(current)
                if normalized:
                    pieces.append(normalized)
            return pieces or ([clean_chunk] if clean_chunk else [])

        parts = [item.strip() for item in re.split(r"(?<=[。！？!?；;])\s*", raw) if item.strip()]
        refined = []
        for part in (parts or [raw.strip()]):
            clauses = [item.strip() for item in re.split(r"[，；：,;:]\s*", part) if item.strip()]
            if not clauses:
                refined.extend(split_long_chunk(part))
                continue
            for clause in clauses:
                refined.extend(split_long_chunk(clause))

        return [item for item in refined if item]
    def _expand_storyboards_for_pacing(self, script_data: dict, topic: str):
        storyboards = script_data.get("storyboards") or []
        expanded = []
        for scene in storyboards:
            sentences = self._split_sentences(scene.get("narration", ""))
            if not sentences:
                expanded.append(scene)
                continue
            for idx, narration in enumerate(sentences, start=1):
                clone = dict(scene)
                clone["narration"] = narration
                if len(sentences) > 1:
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
            scene.setdefault("motion_preset", self._motion_preset_for_scene(scene, index))
            scene.setdefault("transition_type", self._transition_type_for_index(index))

        script_data["storyboards"] = expanded
        script_data["script"] = "\n".join(scene.get("narration", "") for scene in expanded)
        return script_data

    def build_storyboards_from_script_text(self, topic: str, script_text: str, include_intro_scene: bool = False):
        sentences = self._split_script_for_storyboards(script_text)
        storyboards = []
        total = len(sentences)
        for index, narration in enumerate(sentences, start=1):
            focus = self._infer_scene_focus(narration, topic)
            scene = {
                "scene_id": index,
                "scene_title": self._scene_title_from_narration(narration, focus, index),
                "scene_description": f"围绕{focus}的心理学讲解画面，仅表达当前分镜内容。",
                "narration": narration,
                "scene_narration": narration,
                "keywords": [focus],
                "camera_type": self._camera_type_for_index(index),
                "character_action": self._action_for_index(index),
                "layout_hint": self._layout_for_index(index),
                "visual_focus": focus,
                "duration_range": self._duration_range_for_index(index, total),
                "camera_track": self._camera_track_for_index(index, total),
                "scene_energy": self._scene_energy_for_index(index, total),
                "performance_template": self._performance_template_for_index(index, total),
                "background_group": f"stage_{1 + ((index - 1) // 2)}",
                "palette_mode": "classic_stickman",
                "foreground_density": self._foreground_density_for_index(index),
            }
            scene["motion_preset"] = self._motion_preset_for_scene(scene, index)
            scene["transition_type"] = self._transition_type_for_index(index)
            scene["background_prompt"] = self._background_prompt_for_scene(scene, topic, index)
            scene["scene_image_prompt"] = self._scene_image_prompt_for_scene(scene, topic)
            scene["foreground_subjects"] = self._foreground_subjects_for_scene(scene, topic, index)
            scene["foreground_events"] = self._foreground_events_for_scene(scene, index)
            scene["subtitle_lines"] = [{
                "text": narration,
                "english": "",
            }]
            scene["emphasis_beats"] = self._emphasis_beats_for_scene(scene)
            storyboards.append(scene)
        sections = self._attach_sections(storyboards)
        storyboards = self._explode_storyboards_for_segments(storyboards, topic, include_intro_scene=include_intro_scene)
        return {
            "title": topic,
            "script": "\n".join(scene.get("scene_narration") or scene.get("narration") or "" for scene in storyboards),
            "storyboards": storyboards,
            "sections": sections,
        }

    def _infer_scene_focus(self, narration: str, topic: str):
        parts = [part for part in re.split(r"[，。！？、\s]+", str(narration or "")) if part]
        for part in parts:
            if len(part) >= 2:
                return part[:8]
        return str(topic or "主题")[:8]

    def _scene_title_from_narration(self, narration: str, focus: str, index: int):
        clean = re.sub(r"[。！？!?,，、；;：:]", "", str(narration or "")).strip()
        if clean:
            return clean[:10]
        return focus or f"第{index}幕"

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
        background_image_path: str | None = None,
        style_reference_image_path: str | None = None,
        style_reference_notes: str | None = None,
        opening_template_key: str | None = None,
        generation_flags: Optional[dict] = None,
        source_script: str | None = None,
    ):
        self._require_config()
        storyboard_count = max(2, min(int(storyboard_count or 3), 20))

        def report(progress: int, message: str):
            if progress_callback:
                progress_callback(progress, message)

        report(5, "开始生成视频讲解")
        if str(source_script or "").strip():
            script_data = self.build_storyboards_from_script_text(
                topic,
                str(source_script or ""),
                include_intro_scene=bool((generation_flags or {}).get("opening_intro_enabled", False)),
            )
            report(20, "文案拆分完成")
        else:
            script_data = self.generate_script_data(
                topic,
                storyboard_count,
                opening_template_key=opening_template_key,
                include_intro_scene=bool((generation_flags or {}).get("opening_intro_enabled", False)),
            )
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
                background_image_path=background_image_path,
                style_reference_image_path=style_reference_image_path,
                style_reference_notes=style_reference_notes,
                topic=topic,
                generation_flags=generation_flags,
            )
            if voice_source in {"upload", "record"} and voice_file_path:
                audio_track = str(Path(temp_dir) / "user_voice.mp3")
                total_duration = self._prepare_reference_audio(voice_file_path, audio_track)
                report(65, "已使用用户音频")
                timeline = self._build_timeline_from_total_duration(total_duration, len(scenes))
                audio_segments = None
            else:
                audio_segments = []
                for index, scene in enumerate(scenes, start=1):
                    audio_path = audio_dir / f"scene_{index}.mp3"
                    scene_provider, scene_voice, scene_rate = self._scene_tts_profile(
                        scene,
                        str(tts_provider or self.tts_provider or "dashscope_cosyvoice"),
                        str(tts_voice or self.tts_voice or "longshuo_v3"),
                        str(tts_rate or "+0%"),
                    )
                    duration = self._generate_audio(
                        scene.get("scene_narration") or scene.get("narration", ""),
                        str(audio_path),
                        scene_provider,
                        scene_voice,
                        scene_rate,
                    )
                    audio_segments.append((str(audio_path), duration))
                    report(45 + int(index / len(scenes) * 20), f"配音生成中 ({index}/{len(scenes)})")
                timeline = self._build_timeline(audio_segments)
                audio_track = str(Path(temp_dir) / "final_audio.mp3")
                self._concat_audio(audio_segments, audio_track)

            total_audio_duration = self._finalize_audio_track(audio_track)
            timeline = self._ensure_timeline_covers_audio(timeline, total_audio_duration)
            self._attach_scene_timing_metadata(scenes, timeline, audio_segments)
            self._attach_section_timing_metadata(scenes)
            self._attach_viral_package_metadata(scenes, generation_flags)

            report(68, "时间轴计算完成")

            clip_paths = []
            for index, (asset, segment) in enumerate(zip(image_assets, timeline), start=1):
                clip_path = clip_dir / f"clip_{index}.mp4"
                scene = scenes[index - 1] if index - 1 < len(scenes) else {}
                self._create_image_clip(str(asset["image_path"]), str(clip_path), segment["video_duration"], scene, index, asset)
                clip_paths.append(str(clip_path))
                report(70 + int(index / len(timeline) * 10), f"视频片段合成中 ({index}/{len(timeline)})")

            report(82, "音轨合成完成")

            merged_clip = str(Path(temp_dir) / "merged_video.mp4")
            self._concat_video_clips(clip_paths, timeline, scenes, merged_clip)
            report(90, "视频拼接完成")

            final_path = self._merge_video_and_audio(merged_clip, audio_track)
            report(100, "视频讲解生成完成")

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
        generation_flags: Optional[dict] = None,
        source_script: str | None = None,
    ):
        def report(progress: int, message: str):
            if progress_callback:
                progress_callback(progress, message)

        if not storyboards:
            raise RuntimeError("请先生成并确认分镜")
        if not image_assets:
            raise RuntimeError("请先生成并确认图片")

        report(5, "开始基于已确认内容合成视频")
        with tempfile.TemporaryDirectory(prefix="stickman_compose_") as temp_dir:
            audio_dir = Path(temp_dir) / "audio"
            clip_dir = Path(temp_dir) / "clips"
            audio_dir.mkdir(parents=True, exist_ok=True)
            clip_dir.mkdir(parents=True, exist_ok=True)

            for index, asset in enumerate(image_assets, start=1):
                image_path = asset.get("image_path")
                if not image_path or not os.path.exists(image_path):
                    raise RuntimeError(f"第 {index} 张分镜图片不存在，请重新生成图片")
            report(20, "图片检查完成")

            if voice_source in {"upload", "record"} and voice_file_path:
                audio_track = str(Path(temp_dir) / "user_voice.mp3")
                total_duration = self._prepare_reference_audio(voice_file_path, audio_track)
                report(45, "已使用用户音频")
                timeline = self._build_timeline_from_total_duration(total_duration, len(storyboards))
                audio_segments = None
            else:
                audio_segments = []
                for index, scene in enumerate(storyboards, start=1):
                    audio_path = audio_dir / f"scene_{index}.mp3"
                    scene_provider, scene_voice, scene_rate = self._scene_tts_profile(
                        scene,
                        str(tts_provider or self.tts_provider or "dashscope_cosyvoice"),
                        str(tts_voice or self.tts_voice or "longshuo_v3"),
                        str(tts_rate or "+0%"),
                    )
                    duration = self._generate_audio(
                        scene.get("scene_narration") or scene.get("narration", ""),
                        str(audio_path),
                        scene_provider,
                        scene_voice,
                        scene_rate,
                    )
                    audio_segments.append((str(audio_path), duration))
                    report(20 + int(index / len(storyboards) * 30), f"配音生成中 ({index}/{len(storyboards)})")
                timeline = self._build_timeline(audio_segments)
                audio_track = str(Path(temp_dir) / "final_audio.mp3")
                self._concat_audio(audio_segments, audio_track)

            total_audio_duration = self._finalize_audio_track(audio_track)
            timeline = self._ensure_timeline_covers_audio(timeline, total_audio_duration)
            self._attach_sections(storyboards)
            self._attach_scene_timing_metadata(storyboards, timeline, audio_segments)
            self._attach_section_timing_metadata(storyboards)
            generation_flags = self._resolve_viral_generation_flags(topic, generation_flags)
            self._attach_viral_package_metadata(storyboards, generation_flags)

            report(58, "时间轴计算完成")
            clip_paths = []
            for index, (asset, segment) in enumerate(zip(image_assets, timeline), start=1):
                clip_path = clip_dir / f"clip_{index}.mp4"
                scene = storyboards[index - 1] if index - 1 < len(storyboards) else {}
                self._create_image_clip(str(asset["image_path"]), str(clip_path), segment["video_duration"], scene, index, asset)
                clip_paths.append(str(clip_path))
                report(60 + int(index / len(timeline) * 20), f"视频片段合成中 ({index}/{len(timeline)})")

            merged_clip = str(Path(temp_dir) / "merged_video.mp4")
            self._concat_video_clips(clip_paths, timeline, storyboards, merged_clip)
            report(88, "视频拼接完成")

            final_path = self._merge_video_and_audio(merged_clip, audio_track)
            report(100, "视频讲解合成完成")
            return {
                "title": topic,
                "script": str(source_script or "").strip() or "\n".join(scene.get("scene_narration") or scene.get("narration", "") for scene in storyboards),
                "storyboards": storyboards,
                "image_assets": image_assets,
                "generation_flags": {**generation_flags, "composed_from_assets": True},
                "duration": sum(item["video_duration"] for item in timeline),
                "video_path": final_path,
            }

    def generate_script_data(self, topic: str, storyboard_count: int, opening_template_key: Optional[str] = None, include_intro_scene: bool = True):
        script_data = self._generate_script(topic, storyboard_count, opening_template_key=opening_template_key)
        script_data = self._expand_storyboards_for_pacing(script_data, topic)
        storyboards = script_data.get("storyboards") or []
        for index, scene in enumerate(storyboards, start=1):
            scene.setdefault("scene_title", f"第{index}幕")
            scene.setdefault("scene_narration", scene.get("narration") or "")
            scene.setdefault("camera_type", self._camera_type_for_index(index))
            scene.setdefault("character_action", self._action_for_index(index))
            scene.setdefault("layout_hint", self._layout_for_index(index))
            scene.setdefault("visual_focus", (scene.get("keywords") or [topic])[0])
            scene.setdefault("duration_range", self._duration_range_for_index(index, len(storyboards)))
            scene.setdefault("camera_track", self._camera_track_for_index(index, len(storyboards)))
            scene.setdefault("scene_energy", self._scene_energy_for_index(index, len(storyboards)))
            scene.setdefault("performance_template", self._performance_template_for_index(index, len(storyboards)))
            scene.setdefault("background_group", f"stage_{1 + ((index - 1) // 2)}")
            scene.setdefault("palette_mode", "classic_stickman")
            scene.setdefault("foreground_density", self._foreground_density_for_index(index))
            scene.setdefault("motion_preset", self._motion_preset_for_scene(scene, index))
            scene.setdefault("transition_type", self._transition_type_for_index(index))
            if index == 1:
                scene.setdefault("opening_template_key", opening_template_key or "hook_question")
            scene.setdefault("background_prompt", self._background_prompt_for_scene(scene, topic, index))
            scene.setdefault("scene_image_prompt", self._scene_image_prompt_for_scene(scene, topic))
            scene.setdefault("foreground_subjects", self._foreground_subjects_for_scene(scene, topic, index))
            scene.setdefault("foreground_events", self._foreground_events_for_scene(scene, index))
            scene.setdefault("subtitle_lines", self._subtitle_blueprint_for_scene(scene))
            scene.setdefault("emphasis_beats", self._emphasis_beats_for_scene(scene))
        sections = self._attach_sections(storyboards)
        script_data["sections"] = sections
        script_data["storyboards"] = self._explode_storyboards_for_segments(storyboards, topic, include_intro_scene=include_intro_scene)
        script_data["script"] = "\n".join(scene.get("scene_narration") or scene.get("narration") or "" for scene in script_data["storyboards"])
        return script_data

    def generate_images(self, storyboards: list[dict], aspect_ratio: str, project_id: Optional[int] = None, progress_callback=None, background_image_path: Optional[str] = None, style_reference_image_path: Optional[str] = None, style_reference_notes: Optional[str] = None, topic: Optional[str] = None, generation_flags: Optional[dict] = None):
        assets = []
        image_output_dir = self._get_image_output_dir(project_id)
        image_output_dir.mkdir(parents=True, exist_ok=True)
        fixed_background_path = image_output_dir / f"fixed_background_{uuid.uuid4().hex[:8]}.png"
        self._create_fixed_reference_background(str(fixed_background_path), aspect_ratio, storyboards[0] if storyboards else None, background_image_path)
        resolved_topic = str(topic or (storyboards[0].get("visual_focus") if storyboards else "") or "视频讲解").strip()
        generation_flags = self._resolve_viral_generation_flags(resolved_topic, generation_flags)
        active_material_library = self.material_library
        selected_scene_style = generation_flags.get("scene_style_library") if isinstance(generation_flags, dict) else None
        if isinstance(selected_scene_style, dict):
            override_library = self._load_material_library_from_paths(
                str(selected_scene_style.get("material_json_path") or ""),
                str(selected_scene_style.get("package_dir") or ""),
            )
            if override_library:
                active_material_library = override_library
        flags = {
            "image_fallback_used": False,
            "fallback_count": 0,
            "image_provider_status": "fixed_background",
            "default_style_reference": "psychology_reference_background",
            "dynamic_video_mode": "fixed_background_scene_overlay",
            "background_mode": "fixed_reference_background",
            "background_source": str(Path(background_image_path) if background_image_path else self.direct_psychology_background),
            "fixed_background_path": str(fixed_background_path),
        }
        flags.update(generation_flags)
        flags.update(self._generate_viral_package_assets(resolved_topic, image_output_dir, aspect_ratio, storyboards, generation_flags, progress_callback))

        material_assets, material_flags = self._build_material_assets(storyboards, image_output_dir, aspect_ratio, material_library=active_material_library)
        if not material_assets and active_material_library:
            material_assets = []
            for index, scene in enumerate(storyboards, start=1):
                material = active_material_library[(index - 1) % len(active_material_library)]
                source_path = Path(material["image_path"])
                scene["matched_material_file"] = material.get("file_name")
                scene["matched_material_score"] = 1
                scene["matched_material_reasons"] = ["forced:sequential_material_library"]
                material_assets.append({
                    "scene_id": scene.get("scene_id", index),
                    "prompt": f"material_forced:{material.get('file_name')}",
                    "scene_image_path": str(source_path),
                    "scene_image_url": None,
                    "used_fallback": False,
                    "image_source": "material_library",
                    "model_used": None,
                    "scene_image_source": "material_library",
                    "scene_image_model_used": None,
                    "material_file_name": material.get("file_name"),
                    "material_match_score": 1,
                    "material_match_reasons": ["forced:sequential_material_library"],
                    "error_summary": "画面已准备完成。",
                })
            material_flags = {
                "material_library_used": True,
                "material_library_count": len(active_material_library),
                "material_selection_unique": len(active_material_library) >= len(storyboards),
                "material_library_reason": "图片库已强制启用，当前按顺序使用图片库",
            }
        flags.update(material_flags)
        if material_assets:
            flags["image_provider_status"] = "material_library"
            flags["dynamic_video_mode"] = "fixed_background_material_overlay"
            for index, asset in enumerate(material_assets, start=1):
                assets.append({
                    "scene_id": asset.get("scene_id", index),
                    "prompt": asset.get("prompt"),
                    "image_path": str(fixed_background_path),
                    "image_url": f"/api/stickman-images/{fixed_background_path.name}",
                    "scene_image_path": asset.get("scene_image_path"),
                    "scene_image_url": asset.get("scene_image_url"),
                    "used_fallback": False,
                    "image_source": "fixed_background",
                    "model_used": None,
                    "scene_image_source": asset.get("scene_image_source", "material_library"),
                    "scene_image_model_used": None,
                    "material_file_name": asset.get("material_file_name"),
                    "material_match_score": asset.get("material_match_score"),
                    "material_match_reasons": asset.get("material_match_reasons"),
                    "error_summary": "画面已准备完成。",
                })
            if progress_callback:
                progress_callback(32, f"画面准备完成 ({len(assets)}/{len(storyboards)})")
            return assets, flags

        selected_scene_model = None
        for index, scene in enumerate(storyboards, start=1):
            prompt = self._resolved_scene_image_prompt(scene, str(scene.get("visual_focus") or scene.get("scene_title") or "主题"))
            scene_image_path = image_output_dir / f"scene_{index}_illustration_{uuid.uuid4().hex[:8]}.png"
            scene_with_model = dict(scene)
            if selected_scene_model:
                scene_with_model["scene_image_model_override"] = selected_scene_model
                scene_with_model["scene_image_lock_model"] = True
            illustration_result = self._generate_scene_illustration(prompt, str(scene_image_path), scene_with_model, aspect_ratio)
            selected_scene_model = selected_scene_model or illustration_result.get("model_used")
            assets.append({
                "scene_id": scene.get("scene_id", index),
                "prompt": prompt,
                "image_path": str(fixed_background_path),
                "image_url": f"/api/stickman-images/{fixed_background_path.name}",
                "scene_image_path": str(scene_image_path),
                "scene_image_url": f"/api/stickman-images/{scene_image_path.name}",
                "used_fallback": False,
                "image_source": "fixed_background",
                "model_used": None,
                "scene_image_source": illustration_result.get("image_source", "fallback"),
                "scene_image_model_used": illustration_result.get("model_used"),
                "error_summary": illustration_result.get("error_summary") or "画面已准备完成。",
            })
            if progress_callback:
                progress_callback(20 + int(index / len(storyboards) * 25), f"场景图生成中 ({index}/{len(storyboards)})")
            if index < len(storyboards) and self.settings.DASHSCOPE_API_KEY and self.image_base_url:
                time.sleep(2.0 if selected_scene_model else 1.2)
        return assets, flags

    def _resolve_viral_generation_flags(self, topic: str, generation_flags: Optional[dict] = None):
        raw = dict(generation_flags or {})
        opening_template = str(raw.get("opening_template_key") or "hook_question")
        title_mode = str(raw.get("viral_title_mode") or "hook_title")
        hook_template = str(raw.get("viral_hook_template_key") or ("big_number_flash" if opening_template == "big_number" else "shock_reveal"))
        outro_template = str(raw.get("viral_outro_template_key") or "quote_soft_cta")
        visual_style = str(raw.get("viral_visual_style") or "cinematic_clean")
        cta_mode = str(raw.get("viral_cta_mode") or "light_follow")
        title_text = str(raw.get("viral_title_text") or self._viral_title_text(topic, title_mode, opening_template)).strip()
        outro_text = str(raw.get("viral_outro_text") or self._viral_outro_text(topic, cta_mode)).strip()
        return {
            **raw,
            "viral_package_enabled": bool(raw.get("viral_package_enabled", True)),
            "viral_outro_enabled": bool(raw.get("viral_outro_enabled", False)),
            "viral_hook_template_key": hook_template,
            "viral_outro_template_key": outro_template,
            "viral_title_mode": title_mode,
            "viral_visual_style": visual_style,
            "viral_cta_mode": cta_mode,
            "viral_title_text": title_text,
            "viral_outro_text": outro_text,
        }

    def _viral_title_text(self, topic: str, title_mode: str, opening_template_key: str):
        clean_topic = str(topic or "视频讲解").strip() or "视频讲解"
        if title_mode == "raw_topic":
            return clean_topic
        if opening_template_key == "big_number":
            return f"3秒看懂{clean_topic}"
        if any(token in clean_topic for token in ["为什么", "为何", "怎么", "如何"]):
            return clean_topic
        return f"你真的懂{clean_topic}吗？"

    def _viral_outro_text(self, topic: str, cta_mode: str):
        clean_topic = str(topic or "这个主题").strip() or "这个主题"
        if cta_mode == "series_tease":
            return f"看懂{clean_topic}，下一步你会更知道该怎么做。"
        if cta_mode == "comment_prompt":
            return f"如果你也被{clean_topic}困住过，评论区聊聊。"
        return f"看懂{clean_topic}，才有机会真正改变自己。"

    def _hook_visual_prompt(self, topic: str, title_text: str, template_key: str, visual_style: str):
        mood = "high emotional contrast, social-media viral hook, cinematic opening frame"
        if template_key == "big_number_flash":
            hook_shape = "strong visual hierarchy, dramatic number-card composition, explosive contrast"
        elif template_key == "contrast_split":
            hook_shape = "before-after split composition, emotional contrast, left-right tension"
        else:
            hook_shape = "subject close-up, tension in composition, strong depth, suspenseful reveal"
        style_hint = {
            "cinematic_clean": "clean cinematic composition, premium lighting, crisp edges",
            "neon_punch": "neon accents, punchy highlights, fast short-video energy",
            "healing_film": "soft cinematic bloom, emotional but premium, warm controlled palette",
        }.get(visual_style, "clean cinematic composition, premium lighting")
        return (
            f"Short-video opening key art about {topic}. The poster must prominently render the exact Chinese title text: {title_text}. "
            f"{mood}. {hook_shape}. {style_hint}. "
            f"画面中必须清晰写出这句中文标题：{title_text}。标题需要像短视频海报大字一样吸睛、炫酷、高级，并与整体画面风格统一。 "
            "The title text must feel like a cool premium poster headline, visually integrated with the image style, bold, eye-catching, readable, and not inside any box or card. "
            "Do not add any extra Chinese or English text besides that exact title. No subtitles, no logos, no watermarks, no UI, no speech bubbles. "
            "Single striking visual moment suitable for a Douyin/TikTok viral intro frame. 16:9, high contrast, premium, clean, readable composition."
        )

    def _outro_visual_prompt(self, topic: str, outro_text: str, template_key: str, visual_style: str):
        ending_shape = "calm emotional release, visual closure, one strong final composition"
        if template_key == "reverse_summary":
            ending_shape = "from tension to relief, emotional resolution, stable final frame"
        style_hint = {
            "cinematic_clean": "clean cinematic composition, restrained premium ending",
            "neon_punch": "controlled highlight accents with a softer ending tone",
            "healing_film": "warm soft closing mood, emotional but not melodramatic",
        }.get(visual_style, "clean cinematic ending")
        return (
            f"Short-video ending key art about {topic}. Final takeaway concept: {outro_text}. "
            f"{ending_shape}. {style_hint}. "
            "Reserve a clean central-lower safe area for a final quote overlay, but do not render any text. "
            "No subtitles, no logos, no watermarks, no UI. Visually satisfying final frame for a viral short-video outro. 16:9."
        )

    def _wrap_text_for_font(self, draw: ImageDraw.ImageDraw, text: str, font: ImageFont.ImageFont, max_width: int):
        chars = list(str(text or "").strip()) or [" "]
        lines = []
        current = ""
        for char in chars:
            probe = current + char
            bbox = draw.textbbox((0, 0), probe, font=font)
            width = bbox[2] - bbox[0]
            if current and width > max_width:
                lines.append(current)
                current = char
            else:
                current = probe
        if current:
            lines.append(current)
        return lines[:3]

    def _fit_image_cover(self, image: Image.Image, target_width: int, target_height: int):
        width, height = image.size
        if width <= 0 or height <= 0:
            return image.resize((target_width, target_height), Image.Resampling.LANCZOS)
        scale = max(target_width / width, target_height / height)
        resized = image.resize((max(1, int(round(width * scale))), max(1, int(round(height * scale)))), Image.Resampling.LANCZOS)
        left = max((resized.width - target_width) // 2, 0)
        top = max((resized.height - target_height) // 2, 0)
        return resized.crop((left, top, left + target_width, top + target_height))

    def _normalize_package_image(self, image_path: str):
        if not image_path or not os.path.exists(image_path):
            return

        with Image.open(image_path).convert("RGBA") as source:
            canvas = self._fit_image_cover(source, 1920, 1080)
        canvas.save(image_path, format="PNG")

    def _create_viral_title_asset(self, save_path: str, title_text: str, kicker: str, style_key: str, accent_color: tuple[int, int, int], subtitle: str | None = None):
        canvas = Image.new("RGBA", (1920, 1080), (0, 0, 0, 0))
        draw = ImageDraw.Draw(canvas)
        title_font = self._load_font(108)
        subtitle_font = self._load_font(42)
        kicker_font = self._load_font(34)
        shadow = (0, 0, 0, 180)
        panel_fill = (255, 255, 255, 70)
        kicker_text = str(kicker or "爆款开头").strip()
        title = str(title_text or "主题标题").strip() or "主题标题"
        lines = self._wrap_text_for_font(draw, title, title_font, 1320)
        subtitle_text = str(subtitle or "").strip()
        top = 210 if style_key != "outro" else 530
        panel_width = 1450
        panel_left = (1920 - panel_width) // 2
        panel_height = 310 if subtitle_text else 250
        panel_top = top - 40
        draw.rounded_rectangle((panel_left, panel_top, panel_left + panel_width, panel_top + panel_height), radius=42, fill=panel_fill, outline=(*accent_color, 220), width=4)
        kicker_bbox = draw.textbbox((0, 0), kicker_text, font=kicker_font)
        kicker_w = kicker_bbox[2] - kicker_bbox[0]
        kicker_h = kicker_bbox[3] - kicker_bbox[1]
        kicker_left = panel_left + 48
        kicker_top = panel_top - 26
        draw.rounded_rectangle((kicker_left, kicker_top, kicker_left + kicker_w + 42, kicker_top + kicker_h + 18), radius=24, fill=(*accent_color, 245))
        draw.text((kicker_left + 21, kicker_top + 7), kicker_text, fill=(255, 255, 255, 255), font=kicker_font)
        y = top
        for line in lines:
            bbox = draw.textbbox((0, 0), line, font=title_font)
            width = bbox[2] - bbox[0]
            x = (1920 - width) / 2
            for dx, dy in [(-3, 0), (3, 0), (0, -3), (0, 3), (2, 2)]:
                draw.text((x + dx, y + dy), line, fill=shadow, font=title_font)
            draw.text((x, y), line, fill=(255, 255, 255, 255), font=title_font, stroke_width=2, stroke_fill=(*accent_color, 255))
            y += 122
        if subtitle_text:
            sub_lines = self._wrap_text_for_font(draw, subtitle_text, subtitle_font, 1200)
            for sub_line in sub_lines[:2]:
                bbox = draw.textbbox((0, 0), sub_line, font=subtitle_font)
                width = bbox[2] - bbox[0]
                x = (1920 - width) / 2
                draw.text((x, y + 12), sub_line, fill=(242, 242, 242, 240), font=subtitle_font)
                y += 54
        canvas.save(save_path, format="PNG")

    def _intro_narration_text(self, topic: str):
        clean_topic = str(topic or "这个主题").strip() or "这个主题"
        return f"今天我们要讲的是《{clean_topic}》"

    def _generate_viral_package_assets(self, topic: str, image_output_dir: Path, aspect_ratio: str, storyboards: list[dict], generation_flags: dict, progress_callback=None):
        if not generation_flags.get("viral_package_enabled", True):
            return generation_flags
        intro_enabled = bool(generation_flags.get("opening_intro_enabled", False))
        hook_template = str(generation_flags.get("viral_hook_template_key") or "shock_reveal")
        outro_template = str(generation_flags.get("viral_outro_template_key") or "quote_soft_cta")
        visual_style = str(generation_flags.get("viral_visual_style") or "cinematic_clean")
        title_text = str(generation_flags.get("viral_title_text") or topic)
        outro_text = str(generation_flags.get("viral_outro_text") or self._viral_outro_text(topic, str(generation_flags.get("viral_cta_mode") or "light_follow")))
        outro_enabled = bool(generation_flags.get("viral_outro_enabled", False))
        hook_package = None
        if intro_enabled:
            hook_image_path = image_output_dir / f"hook_package_{uuid.uuid4().hex[:8]}.png"
            hook_scene = dict(storyboards[0] if storyboards else {})
            hook_scene["scene_title"] = title_text
            hook_scene["visual_focus"] = topic
            hook_result = self._generate_image(self._hook_visual_prompt(topic, title_text, hook_template, visual_style), str(hook_image_path), hook_scene, aspect_ratio)
            self._normalize_package_image(str(hook_image_path))
            hook_package = {
                "template_key": hook_template,
                "title_text": title_text,
                "subtitle_text": "高能开场，快速切入核心观点",
                "image_path": str(hook_image_path),
                "image_url": f"/api/stickman-images/{hook_image_path.name}",
                "title_asset_path": None,
                "title_asset_url": None,
                "transition_in": "flash_cut",
                "transition_out": "smoothleft",
                "image_source": hook_result.get("image_source"),
                "image_model_used": hook_result.get("model_used"),
                "error_summary": hook_result.get("error_summary"),
            }
        outro_package = None
        if outro_enabled:
            outro_image_path = image_output_dir / f"outro_package_{uuid.uuid4().hex[:8]}.png"
            outro_title_path = image_output_dir / f"outro_title_{uuid.uuid4().hex[:8]}.png"
            outro_scene = dict(storyboards[-1] if storyboards else {})
            outro_scene["scene_title"] = outro_text
            outro_scene["visual_focus"] = topic
            outro_result = self._generate_image(self._outro_visual_prompt(topic, outro_text, outro_template, visual_style), str(outro_image_path), outro_scene, aspect_ratio)
            self._normalize_package_image(str(outro_image_path))
            self._create_viral_title_asset(str(outro_title_path), outro_text, "结尾收束", "outro", (245, 158, 11), subtitle="让用户记住这句，再离开")
            outro_package = {
                "template_key": outro_template,
                "title_text": outro_text,
                "subtitle_text": "轻收束，不突然切断",
                "image_path": str(outro_image_path),
                "image_url": f"/api/stickman-images/{outro_image_path.name}",
                "title_asset_path": str(outro_title_path),
                "title_asset_url": f"/api/stickman-images/{outro_title_path.name}",
                "transition_in": "fade",
                "transition_out": "fadeblack",
                "image_source": outro_result.get("image_source"),
                "image_model_used": outro_result.get("model_used"),
                "error_summary": outro_result.get("error_summary"),
            }
        if progress_callback:
            progress_callback(18, "开头与结尾包装已生成")
        payload = {**generation_flags}
        if hook_package:
            payload["viral_hook_package"] = hook_package
        else:
            payload.pop("viral_hook_package", None)
        if outro_package:
            payload["viral_outro_package"] = outro_package
        return payload

    def _attach_viral_package_metadata(self, storyboards: list[dict], generation_flags: Optional[dict]):
        if not storyboards or not generation_flags or not generation_flags.get("viral_package_enabled", True):
            return storyboards
        intro_enabled = bool(generation_flags.get("opening_intro_enabled", False))
        hook_package = generation_flags.get("viral_hook_package") or {}
        outro_package = generation_flags.get("viral_outro_package") or {}
        if intro_enabled and hook_package:
            storyboards[0]["viral_hook_package"] = hook_package
            storyboards[0]["transition_type"] = str(hook_package.get("transition_out") or storyboards[0].get("transition_type") or "smoothleft")
            if storyboards[0].get("viral_intro_scene") and len(storyboards) > 1:
                for scene in storyboards[1:]:
                    scene.pop("viral_hook_package", None)
        else:
            for scene in storyboards:
                scene.pop("viral_hook_package", None)
        if outro_package:
            storyboards[-1]["viral_outro_package"] = outro_package
        return storyboards

    def regenerate_single_image(
        self,
        scene: dict,
        index: int,
        aspect_ratio: str,
        project_id: Optional[int] = None,
        prompt_override: Optional[str] = None,
        background_image_path: Optional[str] = None,
        style_reference_image_path: Optional[str] = None,
        style_reference_notes: Optional[str] = None,
    ):
        image_output_dir = self._get_image_output_dir(project_id)
        image_output_dir.mkdir(parents=True, exist_ok=True)
        image_path = image_output_dir / f"fixed_background_{uuid.uuid4().hex[:8]}.png"
        prompt = prompt_override or self._resolved_scene_image_prompt(scene, str(scene.get("visual_focus") or scene.get("scene_title") or "主题"))
        self._create_fixed_reference_background(str(image_path), aspect_ratio, scene, background_image_path)
        scene_image_path = image_output_dir / f"scene_{index}_illustration_{uuid.uuid4().hex[:8]}.png"
        illustration_result = self._generate_scene_illustration(prompt, str(scene_image_path), scene, aspect_ratio)
        return {
            "scene_id": scene.get("scene_id", index),
            "prompt": prompt,
            "image_path": str(image_path),
            "image_url": f"/api/stickman-images/{image_path.name}",
            "scene_image_path": str(scene_image_path),
            "scene_image_url": f"/api/stickman-images/{scene_image_path.name}",
            "used_fallback": False,
            "image_source": "fixed_background",
            "model_used": None,
            "scene_image_source": illustration_result.get("image_source", "fallback"),
            "scene_image_model_used": illustration_result.get("model_used"),
            "error_summary": illustration_result.get("error_summary") or "预览图已生成，可继续下一步。",
        }, False

    def _get_image_output_dir(self, project_id: Optional[int] = None):
        backend_dir = Path(__file__).resolve().parents[2]
        base_dir = backend_dir / "uploads" / "stickman_images"
        if project_id is None:
            return base_dir / "temp"
        return base_dir / f"project_{project_id}"

    def _opening_template_instruction(self, opening_template_key: Optional[str]):
        if opening_template_key == "big_number":
            return "首幕必须使用爆点数字型开头：用明确数字、结果或反差抓住注意力。"
        return "首幕必须使用反问钩子型开头：用直接问题引发用户继续看下去。"

    def _generate_script(self, topic: str, storyboard_count: int, opening_template_key: Optional[str] = None):
        prompt = (
            f'请为主题"{topic}"生成一个中文火柴人科普短视频脚本。'
            f"总共 {storyboard_count} 个分镜，每个分镜 1-2 句旁白。"
            f"{self._opening_template_instruction(opening_template_key)}"
            "必须返回 JSON，不要输出解释。JSON 结构如下："
            '{"title":"视频标题","script":"完整脚本","storyboards":[{"scene_id":1,"scene_description":"场景描述","narration":"旁白文本","keywords":["关键词"]}]}'
        )

        response = self._chat_completion(
            messages=[
                {"role": "system", "content": "你是短视频脚本策划，擅长输出适合火柴人动画的分镜 JSON。"},
                {"role": "user", "content": prompt},
            ],
            temperature=0.7,
            max_tokens=2400,
        )
        content = response.choices[0].message.content or ""
        return self._extract_script_json(content, topic, storyboard_count, opening_template_key=opening_template_key)

    def _extract_script_json(self, content: str, topic: str, storyboard_count: int, opening_template_key: Optional[str] = None):
        match = re.search(r"\{[\s\S]*\}", content)
        if not match:
            return self._fallback_script(topic, storyboard_count, content, opening_template_key=opening_template_key)

        try:
            data = json.loads(match.group())
        except json.JSONDecodeError:
            return self._fallback_script(topic, storyboard_count, content, opening_template_key=opening_template_key)

        storyboards = data.get("storyboards") or []
        if not isinstance(storyboards, list) or not storyboards:
            return self._fallback_script(topic, storyboard_count, content, opening_template_key=opening_template_key)

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
                    "motion_preset": scene.get("motion_preset") or self._motion_preset_for_scene(scene, index),
                    "transition_type": scene.get("transition_type") or self._transition_type_for_index(index),
                    "opening_template_key": scene.get("opening_template_key") or (opening_template_key or "hook_question") if index == 1 else scene.get("opening_template_key"),
                }
            )

        return {
            "title": data.get("title") or topic,
            "script": data.get("script") or "\n".join(item["narration"] for item in normalized),
            "storyboards": normalized,
        }

    def _fallback_script(self, topic: str, storyboard_count: int, raw_text: str, opening_template_key: Optional[str] = None):
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
                    "motion_preset": self._motion_preset_for_index(index),
                    "transition_type": self._transition_type_for_index(index),
                    "opening_template_key": (opening_template_key or "hook_question") if index == 1 else None,
                }
            )
        return {
            "title": topic,
            "script": raw_text or topic,
            "storyboards": storyboards,
        }

    def _duration_range_for_index(self, index: int, total: int):
        return "2-5"

    def _camera_track_for_index(self, index: int, total: int):
        if index == 1:
            return "slow_push_center"
        if index == total:
            return "pull_out_soft"
        return ["micro_pan_right", "push_left_focus", "hold_then_push", "micro_pan_left"][(index - 2) % 4]

    def _scene_energy_for_index(self, index: int, total: int):
        if index == 1:
            return "viral"
        if index == total:
            return "normal"
        return "normal"

    def _performance_template_for_index(self, index: int, total: int):
        if index == 1:
            return "hook"
        if total >= 3 and index == total - 1:
            return "compare"
        if index == total:
            return "summary"
        return "explain"

    def _foreground_density_for_index(self, index: int):
        return "dense" if index == 1 else ("light" if index % 3 == 0 else "medium")

    def _background_prompt_for_scene(self, scene: dict, topic: str, index: int):
        title = str(scene.get("scene_title") or scene.get("visual_focus") or topic or "心理知识分享").strip()
        return (
            "一个极简风格的心理学主题PPT封面，浅灰色背景，带有柔和渐变（从上到下过渡），整体干净、留白充足、画面非常简洁，\n\n"
            "左上角：一个可替换的中文标题“{标题}”，黑色加粗字体，旁边搭配一个简洁的蓝色抽象小图标（扁平风、几何风），\n\n"
            "右上角：一行很小的浅灰色文字“心理知识分享 无不良引导”，细字体，右对齐，\n\n"
            "整体布局：居中、平衡、大量留白，视觉高级、克制，\n\n"
            "要求：不要底部进度条，不要字幕，不要底部任何文字，不要多余UI元素，\n\n"
            "风格：极简、高级感、类似苹果发布会Keynote风格、专业、冷静、干净、教育类视觉，\n\n"
            "画面比例：16:9，高清"
        ).replace("{标题}", title)

    def _resolved_background_prompt(self, scene: dict, topic: str):
        raw = str(scene.get("background_prompt") or self._background_prompt_for_scene(scene, topic, int(scene.get("scene_id") or 1)))
        title = str(scene.get("scene_title") or scene.get("visual_focus") or topic or "心理知识分享").strip()
        return raw.replace("{标题}", title)

    def _scene_image_prompt_for_scene(self, scene: dict, topic: str):
        text = str(scene.get("scene_narration") or scene.get("narration") or topic or "心理知识分享").strip()
        return (
            "极简心理主题图标插画，纯白背景（#FFFFFF），无边框、无阴影、无渐变、无背景元素，\n\n"
            "画面中央：只根据“{文案}”这一句内容生成一个抽象或具象的视觉表达（可以是小人、符号、简笔图形或隐喻图形），不要表现其他分镜内容，\n\n"
            "风格要求：\n"
            "- 极简设计（Minimalism）\n"
            "- 扁平化（Flat design）\n"
            "- 统一黑色线条（细线条，干净利落）\n"
            "- 可适当加入少量蓝色点缀（增强情绪表达）\n"
            "- 类似 Notion 插画 / 心理科普图标风格\n"
            "- 图形简洁、可读性强\n\n"
            "构图：\n"
            "- 单个主体\n"
            "- 居中\n"
            "- 四周留白充足\n"
            "- 不要复杂背景\n\n"
            "严格限制：\n"
            "不要阴影，不要渐变，不要透视，不要背景物体，不要地面，不要边框，不要UI，不要文字，不要水印\n\n"
            "输出：高清，矢量风，适合叠加在任意背景上（无违和）"
        ).replace("{文案}", text)

    def _resolved_scene_image_prompt(self, scene: dict, topic: str):
        raw = str(scene.get("scene_image_prompt") or self._scene_image_prompt_for_scene(scene, topic))
        text = str(scene.get("scene_narration") or scene.get("narration") or topic or "心理知识分享").strip()
        return raw.replace("{文案}", text)

    def _stage_groups_from_storyboards(self, storyboards: list[dict]):
        grouped = {}
        for scene in storyboards:
            key = str(scene.get("background_group") or "stage_1")
            grouped.setdefault(key, []).append(scene)
        return grouped

    def _subtitle_blueprint_for_scene(self, scene: dict):
        text = str(scene.get("scene_narration") or scene.get("narration", "")).strip()
        if not text:
            return []
        lines = self._subtitle_segments_from_text(text)
        result = []
        for line in lines:
            clean_text = self._strip_terminal_punctuation(line)
            result.append({
                "text": clean_text,
                "english": self._sanitize_english_subtitle(self._translate_subtitle_to_english(clean_text)),
            })
        return result
    def _emphasis_beats_for_scene(self, scene: dict):
        keywords = [str(item).strip() for item in (scene.get("keywords") or []) if str(item).strip()]
        text = str(scene.get("narration") or "")
        candidates = keywords[:2] or [part for part in re.split(r"[，。！？、\s]+", text) if part][:2]
        return candidates

    def _section_icon_for_index(self, index: int, total: int):
        if total <= 1:
            return "summary"
        if index == 1:
            return "question"
        if index >= total:
            return "summary"
        return "method"

    def _balanced_section_sizes(self, total: int):
        total = max(int(total or 0), 0)
        if total <= 0:
            return []
        if total <= 3:
            return [1] * total
        section_count = min(4, max(2, total // 2))
        while section_count > 1 and (total / section_count) < 2:
            section_count -= 1
        base = total // section_count
        remainder = total % section_count
        return [base + (1 if index < remainder else 0) for index in range(section_count)]

    def _section_title_from_texts(self, texts: list[str], fallback: str):
        combined = "，".join(str(text or "").strip() for text in texts if str(text or "").strip())
        if not combined:
            return fallback[:8]

        normalized = self._strip_terminal_punctuation(combined)
        normalized = re.sub(r"[\"'“”‘’《》【】()（）]", "", normalized)
        normalized = re.sub(r"\s+", "", normalized)
        candidates = []

        if "为什么" in normalized:
            tail = normalized.split("为什么", 1)[1]
            tail = re.split(r"[，。！？；：]", tail)[0]
            tail = tail[:5]
            if tail:
                candidates.append(f"为什么{tail}"[:8])
        for marker in ("别再", "不要再", "一定要", "千万别", "其实", "原来", "关键是"):
            if marker in normalized:
                tail = normalized.split(marker, 1)[1]
                tail = re.split(r"[，。！？；：]", tail)[0]
                tail = tail[: max(0, 8 - len(marker))]
                if tail:
                    candidates.append(f"{marker}{tail}"[:8])

        chunks = [chunk for chunk in re.split(r"[，。！？；：、]", normalized) if chunk]
        for chunk in chunks:
            clean = re.sub(r"^(所以|然后|就是|如果|因为|但是|而且|其实|我们|你要|你会|这个|那个)", "", chunk)
            clean = clean[:8]
            if 3 <= len(clean) <= 8:
                candidates.append(clean)
        for chunk in chunks:
            if 3 <= len(chunk) <= 8:
                candidates.append(chunk[:8])

        seen = set()
        for candidate in candidates:
            title = self._strip_terminal_punctuation(candidate).strip()
            if 2 <= len(title) <= 8 and title not in seen:
                seen.add(title)
                return title
        return fallback[:8]

    def _clean_section_title(self, title: str, fallback: str):
        clean = re.sub(r"[\s\-:：，。！？!?,；;、'\"“”‘’()（）【】《》]", "", str(title or "").strip())
        clean = clean[:8]
        if 2 <= len(clean) <= 8:
            return clean
        return fallback[:8]

    def _generate_section_titles(self, section_text_groups: list[list[str]]):
        if not section_text_groups:
            return []

        fallback_titles = [
            self._section_title_from_texts(group, fallback=f"第{index}部分")
            for index, group in enumerate(section_text_groups, start=1)
        ]
        numbered_sections = []
        for index, group in enumerate(section_text_groups, start=1):
            combined = "\n".join(f"- {str(text or '').strip()}" for text in group if str(text or '').strip())
            if combined:
                numbered_sections.append(f"第{index}部分：\n{combined}")
        if not numbered_sections:
            return fallback_titles

        try:
            response = self._chat_completion(
                messages=[
                    {
                        "role": "system",
                        "content": (
                            "你是短视频分段标题助手。"
                            "请根据每一部分的内容，总结一个4到8个汉字的进度条标题。"
                            "标题必须概括这部分含义，不能直接照抄开头几个字，"
                            "不要带标点，不要编号，不要解释。"
                            "只返回 JSON 数组字符串。"
                        ),
                    },
                    {
                        "role": "user",
                        "content": (
                            "请给下面每个部分各写一个短标题，按顺序返回 JSON 数组。\n\n"
                            + "\n\n".join(numbered_sections)
                        ),
                    },
                ],
                temperature=0.2,
                max_tokens=220,
            )
            content = (response.choices[0].message.content or "").strip()
            match = re.search(r"\[[\s\S]*\]", content)
            payload = json.loads(match.group(0) if match else content)
            if isinstance(payload, list):
                titles = []
                for index, fallback in enumerate(fallback_titles):
                    candidate = payload[index] if index < len(payload) else fallback
                    titles.append(self._clean_section_title(str(candidate or ""), fallback))
                if len(titles) == len(fallback_titles):
                    return titles
        except Exception:
            pass
        return fallback_titles

    def _attach_sections(self, storyboards: list[dict]):
        total = len(storyboards)
        sizes = self._balanced_section_sizes(total)
        sections = []
        section_groups = []
        cursor = 0
        for _, size in enumerate(sizes, start=1):
            group = storyboards[cursor:cursor + size]
            if not group:
                continue
            section_groups.append([
                [str(item.get("scene_narration") or item.get("narration") or "").strip() for item in group],
                group,
            ])
            cursor += len(group)

        titles = self._generate_section_titles([texts for texts, _ in section_groups])

        cursor = 0
        for section_index, size in enumerate(sizes, start=1):
            group = storyboards[cursor:cursor + size]
            if not group:
                continue
            section_title = titles[len(sections)] if len(sections) < len(titles) else self._section_title_from_texts(
                [str(item.get("scene_narration") or item.get("narration") or "").strip() for item in group],
                fallback=f"第{section_index}部分",
            )
            icon_key = self._section_icon_for_index(section_index, len(sizes))
            section = {
                "section_id": len(sections) + 1,
                "title": section_title,
                "icon_key": icon_key,
                "start_scene_index": cursor + 1,
                "end_scene_index": cursor + len(group),
            }
            sections.append(section)
            for scene in group:
                scene["section_id"] = section["section_id"]
                scene["section_title"] = section_title
                scene["section_icon_key"] = icon_key
            cursor += len(group)
        return sections

    def _explode_storyboards_for_segments(self, storyboards: list[dict], topic: str, include_intro_scene: bool = True):
        exploded = []
        for scene in storyboards:
            clone = dict(scene)
            subtitle_lines = list(scene.get("subtitle_lines") or self._subtitle_blueprint_for_scene(scene))
            full_text = self._normalize_storyboard_fragment(scene.get("scene_narration") or scene.get("narration") or topic)
            if not subtitle_lines and full_text:
                subtitle_lines = [{"text": full_text, "english": ""}]
            clone["segment_index_within_scene"] = 1
            clone["source_scene_id"] = scene.get("scene_id")
            clone["scene_narration"] = full_text
            clone["narration"] = full_text
            clone["scene_title"] = str(scene.get("section_title") or scene.get("scene_title") or f"第{scene.get('scene_id')}幕")
            clone["subtitle_lines"] = subtitle_lines
            clone["visual_focus"] = self._infer_scene_focus(full_text, topic)
            clone["scene_description"] = f"围绕{full_text[:14]}的讲解画面，仅表达当前分镜内容。"
            clone["scene_image_prompt"] = self._scene_image_prompt_for_scene(clone, topic)
            clone["foreground_subjects"] = self._foreground_subjects_for_scene(clone, topic, len(exploded) + 1)
            clone["foreground_events"] = self._foreground_events_for_scene(clone, len(exploded) + 1)
            exploded.append(clone)
        if exploded and include_intro_scene:
            intro_scene = dict(exploded[0])
            intro_text = self._intro_narration_text(topic)
            intro_scene["scene_narration"] = intro_text
            intro_scene["narration"] = intro_text
            intro_scene["scene_title"] = str(topic or intro_scene.get("scene_title") or "主题").strip() or "主题"
            intro_scene["scene_description"] = f"以主题《{str(topic or '').strip() or '主题'}》为核心的开场海报画面，仅用于吸引注意并引出主题。"
            intro_scene["visual_focus"] = str(topic or intro_scene.get("visual_focus") or "主题").strip() or "主题"
            intro_scene["foreground_subjects"] = []
            intro_scene["foreground_events"] = []
            intro_scene["subtitle_lines"] = [{
                "text": intro_text,
                "english": self._sanitize_english_subtitle(self._translate_subtitle_to_english(intro_text)),
            }]
            intro_scene["viral_intro_scene"] = True
            intro_scene["opening_intro_scene"] = True
            intro_scene["performance_template"] = "opening_intro"
            intro_scene["transition_type"] = "fade"
            exploded.insert(0, intro_scene)
        for index, scene in enumerate(exploded, start=1):
            scene["scene_id"] = index
        return exploded

    def _foreground_subjects_for_scene(self, scene: dict, topic: str, index: int):
        focus = str(scene.get("visual_focus") or topic).strip() or topic
        return [
            {"key": f"scene_image_{index}", "kind": "scene_illustration", "label": focus[:8]},
        ]

    def _foreground_events_for_scene(self, scene: dict, index: int):
        return [
            {"target": f"scene_image_{index}", "animation": "center_fade", "start": 0.0, "duration": 4.2, "x_ratio": 0.5, "y_ratio": 0.5},
        ]

    def _default_style_reference_profile(self):
        return "classic stickman explainer style, clean white background, black line figure, simple props, layered overlays, readable lower third subtitles"

    def _load_font(self, size: int):
        for candidate in self.font_candidates:
            if os.path.exists(candidate):
                try:
                    return ImageFont.truetype(candidate, size=size)
                except Exception:
                    pass
        return ImageFont.load_default()

    def _draw_psychology_cover_background(self, save_path: str, scene: dict, width: int, height: int):
        image = Image.new("RGB", (width, height), (255, 255, 255))
        draw = ImageDraw.Draw(image)
        for y in range(height):
            ratio = y / max(height - 1, 1)
            shade = int(248 - ratio * 10)
            draw.line((0, y, width, y), fill=(shade, shade, shade))

        title = str(scene.get("scene_title") or scene.get("visual_focus") or "心理知识分享").strip()
        title_font = self._load_font(78)
        tag_font = self._load_font(22)
        icon_blue = (59, 130, 246)
        text_black = (18, 18, 18)
        light_gray = (170, 170, 170)

        title_x = int(width * 0.11)
        title_y = int(height * 0.18)

        # small abstract blue icon
        icon_x = title_x - 4
        icon_y = title_y + 20
        draw.rounded_rectangle((icon_x, icon_y, icon_x + 18, icon_y + 76), radius=8, fill=icon_blue)
        draw.rounded_rectangle((icon_x + 26, icon_y + 24, icon_x + 82, icon_y + 42), radius=9, fill=icon_blue)
        draw.ellipse((icon_x + 48, icon_y - 6, icon_x + 84, icon_y + 30), fill=icon_blue)

        draw.text((title_x + 110, title_y), title, fill=text_black, font=title_font)

        corner_text = "心理知识分享 无不良引导"
        bbox = draw.textbbox((0, 0), corner_text, font=tag_font)
        corner_w = bbox[2] - bbox[0]
        draw.text((width - int(width * 0.11) - corner_w, int(height * 0.12)), corner_text, fill=light_gray, font=tag_font)

        image.save(save_path, format="PNG")

    def _warm_palette_for_scene(self, scene: dict):
        mode = str(scene.get("palette_mode") or "classic_stickman")
        if mode == "classic_stickman_soft":
            return {
                "bg": (250, 250, 250),
                "surface": (242, 242, 242),
                "surface_alt": (215, 215, 215),
                "accent": (40, 40, 40),
                "accent_soft": (120, 120, 120),
                "text": (18, 18, 18),
                "shadow": (90, 90, 90),
            }
        return {
            "bg": (255, 255, 255),
            "surface": (246, 246, 246),
            "surface_alt": (210, 210, 210),
            "accent": (28, 28, 28),
            "accent_soft": (125, 125, 125),
            "text": (20, 20, 20),
            "shadow": (96, 96, 96),
        }

    def _create_stage_background(self, save_path: str, aspect_ratio: str, scenes: list[dict], style_reference_image_path: Optional[str], style_reference_notes: Optional[str]):
        width, height = (1920, 1080) if aspect_ratio == "16:9" else (1080, 1920)
        scene = scenes[0] if scenes else {}
        resolved_prompt = self._resolved_background_prompt(scene, str(scene.get("visual_focus") or scene.get("scene_title") or "心理知识分享"))
        if "心理学主题PPT封面" in resolved_prompt or "心理知识分享 无不良引导" in resolved_prompt:
            if self.direct_psychology_background.exists():
                shutil.copyfile(self.direct_psychology_background, save_path)
                return
            self._draw_psychology_cover_background(save_path, scene, width, height)
            return
        palette = self._warm_palette_for_scene(scene)
        image = Image.new("RGB", (width, height), palette["bg"])
        draw = ImageDraw.Draw(image)
        draw.line((0, int(height * 0.76), width, int(height * 0.76)), fill=palette["surface_alt"], width=4)
        draw.line((int(width * 0.17), int(height * 0.24), int(width * 0.17), int(height * 0.66)), fill=palette["surface_alt"], width=5)
        draw.line((int(width * 0.17), int(height * 0.24), int(width * 0.83), int(height * 0.24)), fill=palette["surface_alt"], width=5)
        draw.line((int(width * 0.83), int(height * 0.24), int(width * 0.83), int(height * 0.66)), fill=palette["surface_alt"], width=5)
        draw.line((int(width * 0.17), int(height * 0.66), int(width * 0.83), int(height * 0.66)), fill=palette["surface_alt"], width=5)
        draw.line((140, 170, 240, 250), fill=palette["surface_alt"], width=4)
        draw.line((240, 170, 140, 250), fill=palette["surface_alt"], width=4)
        draw.ellipse((width - 290, 120, width - 160, 250), outline=palette["surface_alt"], width=4)
        draw.line((width - 225, 250, width - 225, 360), fill=palette["surface_alt"], width=4)
        draw.line((width - 225, 285, width - 285, 335), fill=palette["surface_alt"], width=4)
        draw.line((width - 225, 285, width - 165, 335), fill=palette["surface_alt"], width=4)
        draw.line((width - 225, 360, width - 275, 455), fill=palette["surface_alt"], width=4)
        draw.line((width - 225, 360, width - 180, 455), fill=palette["surface_alt"], width=4)
        image.save(save_path, format="PNG")

    def _build_image_prompt(self, scene: dict, index: int, aspect_ratio: str, style_hint: str = ""):
        keywords = ", ".join(scene.get("keywords") or [])
        layout_hint = "16:9 horizontal composition, cinematic wide shot, subject clearly visible, balanced left-right layout, safe margins for subtitles" if aspect_ratio == "16:9" else "clean composition"
        camera_type = scene.get("camera_type") or self._camera_type_for_index(index)
        character_action = scene.get("character_action") or self._action_for_index(index)
        layout_position = scene.get("layout_hint") or self._layout_for_index(index)
        visual_focus = scene.get("visual_focus") or keywords
        background_prompt = self._resolved_background_prompt(scene, visual_focus or "")
        default_style_hint = (
            "classic black line stickman style, clean white background, stable scene composition, layered foreground overlays, low-clutter center area, "
            f"short-video visual rhythm, {self._default_style_reference_profile()}"
        )
        if style_hint:
            merged_style_hint = (
                "The uploaded reference image is the ONLY style guide for this frame. "
                "Fully inherit its palette, line quality, shading behavior, lighting mood, composition feeling, texture density and illustration medium. "
                "Keep the content as a stick-figure educational scene, but visually match the uploaded image as closely as possible. "
                "Do not use the default house style. Do not force white background or minimalist black-line style unless the reference image itself has that look. "
                f"{style_hint}"
            )
            base_prompt = "Create a classic stickman explainer background that follows the uploaded reference image style exactly in mood and rendering. "
        else:
            merged_style_hint = default_style_hint
            base_prompt = "Create a classic 16:9 stickman explainer background with white background, black line drawing, simple props, stable composition, and no baked text or UI cards. "
        return (
            base_prompt +
            f"{merged_style_hint}. "
            f"{layout_hint}. "
            "Do not render scene numbers, chapter labels, subtitles, white cards, speech bubbles or any unrelated text in the image. "
            f"Camera: {camera_type}. Character action: {character_action}. Layout: {layout_position}. Visual focus: {visual_focus}. "
            f"Background scene description: {background_prompt}. "
            "Leave most of the narrative elements for transparent animated foreground overlays in the final video. "
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

    def _subtitle_segments_from_text(self, text: str):
        raw = str(text or "")
        if not raw.strip():
            return []

        def split_long_clause(clause: str):
            clause = self._normalize_storyboard_fragment(clause)
            if not clause:
                return []
            if len(clause) <= 16:
                return [clause]
            if not re.search(r"[，,、。！？!?；;：:]", clause):
                return self._semantic_split_long_text(clause, preferred_max=14, hard_max=16)

            comma_parts = [item.strip() for item in re.split(r"(?<=[，,、])\s*", clause) if item.strip()]
            if len(comma_parts) > 1:
                return [self._normalize_storyboard_fragment(part) for part in comma_parts if self._normalize_storyboard_fragment(part)]

            return [clause]

        parts = [item.strip() for item in re.split(r"(?<=[。！？!?；;])\s*", raw) if item.strip()]
        refined = []
        for part in (parts or [raw.strip()]):
            clauses = [item.strip() for item in re.split(r"[，；：,;:]\s*", part) if item.strip()]
            if not clauses:
                refined.extend(split_long_clause(part))
                continue
            for clause in clauses:
                refined.extend(split_long_clause(clause))
        return [item for item in refined if item]
    def _split_chinese_subtitle_lines(self, text: str):
        cleaned = re.sub(r"\s+", "", str(text or "").strip())
        if not cleaned:
            return [" "]
        if len(cleaned) <= 18:
            return [self._strip_terminal_punctuation(cleaned) or cleaned]

        target = max(8, min((len(cleaned) + 1) // 2, 14))
        split_at = self._best_semantic_break_index(cleaned, target, 8, min(18, len(cleaned) - 4))
        if not split_at:
            split_at = target
        numeral_chars = "一二三四五六七八九十百千万0123456789两几多半"
        if 1 <= split_at < len(cleaned):
            while split_at > 8 and split_at < len(cleaned) and cleaned[split_at - 1] in numeral_chars and cleaned[split_at] not in "，。！？；：、】【）》〕】」』,.!?;:" and cleaned[split_at] not in numeral_chars:
                split_at -= 1
            while split_at < min(18, len(cleaned) - 4) and cleaned[split_at - 1] not in "，。！？；：、】【）》〕】」』,.!?;:" and cleaned[split_at] in numeral_chars:
                split_at += 1
        first = cleaned[:split_at].strip()
        second = cleaned[split_at:].strip()
        if second and re.match(r"^[，。！？；：、】【）》〕】」』,.!?;:]", second):
            first += second[0]
            second = second[1:].strip()
        lines = [self._strip_terminal_punctuation(line) or line for line in [first, second] if line]
        return lines or [self._strip_terminal_punctuation(cleaned) or cleaned]

    def _render_centered_chinese_lines(self, draw: ImageDraw.ImageDraw, lines: list[str], font: ImageFont.ImageFont, canvas_width: int, start_y: int, line_height: int, fill, stroke_width: int = 0, stroke_fill=None):
        y = start_y
        for line in lines:
            chars = list(str(line or "").strip()) or [" "]
            cell_width = line_height
            total_width = cell_width * len(chars)
            start_x = (canvas_width - total_width) / 2
            for index, char in enumerate(chars):
                bbox = draw.textbbox((0, 0), char, font=font)
                char_width = bbox[2] - bbox[0]
                x = start_x + index * cell_width + (cell_width - char_width) / 2
                draw.text((x, y), char, fill=fill, font=font, stroke_width=stroke_width, stroke_fill=stroke_fill)
            y += line_height
        return y

    def _wrap_english_subtitle_lines(self, draw: ImageDraw.ImageDraw, text: str, font: ImageFont.ImageFont, max_width: int, max_lines: int = 2):
        cleaned = self._sanitize_english_subtitle(text)
        if not cleaned:
            return []
        words = [word for word in cleaned.split(" ") if word]
        if not words:
            return []

        lines = []
        current = words[0]
        for word in words[1:]:
            candidate = f"{current} {word}"
            bbox = draw.textbbox((0, 0), candidate, font=font)
            if current and (bbox[2] - bbox[0]) > max_width:
                lines.append(current)
                current = word
            else:
                current = candidate
        if current:
            lines.append(current)

        if len(lines) <= max_lines:
            return lines

        collapsed = lines[:max_lines - 1]
        collapsed.append(" ".join(lines[max_lines - 1:]))
        return collapsed

    def _hook_package_title_end(self, duration: float):
        duration = max(float(duration or 0.0), 0.5)
        return min(duration, max(1.35, duration * 0.58))

    def _outro_package_title_start(self, duration: float):
        duration = max(float(duration or 0.0), 0.5)
        return max(0.0, duration - 0.86)

    def _subtitle_timing_window(self, scene: dict, duration: float):
        start_at = 0.0
        end_at = max(float(duration or 0.0), 0.2)

        hook = scene.get("viral_hook_package") or {}
        if hook and not scene.get("viral_intro_scene"):
            hook_title_end = self._hook_package_title_end(end_at)
            start_at = min(end_at - 0.2, hook_title_end + 0.08)

        outro = scene.get("viral_outro_package") or {}
        if outro:
            outro_title_start = self._outro_package_title_start(end_at)
            end_at = max(start_at + 0.2, outro_title_start - 0.08)

        return round(max(start_at, 0.0), 2), round(max(end_at, start_at + 0.2), 2)

    def _timed_subtitles_for_scene(self, scene: dict, duration: float):
        existing = scene.get("subtitle_segments") or []
        window_start, window_end = self._subtitle_timing_window(scene, duration)
        subtitle_lead = 0.0
        if existing:
            return [
                {
                    "text": str(item.get("text") or ""),
                    "english": str(item.get("english") or ""),
                    "start": max(window_start, float(item.get("start", 0.0))),
                    "end": min(float(item.get("end", duration)), window_end),
                }
                for item in existing
                if str(item.get("text") or "").strip() and min(float(item.get("end", duration)), window_end) > max(window_start, float(item.get("start", 0.0)))
            ]
        lines = list(scene.get("subtitle_lines") or self._subtitle_blueprint_for_scene(scene))
        if not lines:
            return []
        audio_duration = float(scene.get("audio_duration") or 0.0)
        audio_lead = float(scene.get("audio_lead") or 0.18)
        effective_duration = min(window_end, audio_lead + audio_duration + 0.06) if audio_duration > 0 else window_end
        safe_duration = max(min(window_end, effective_duration) - window_start, 0.2)
        if len(lines) == 1:
            item = lines[0]
            return [{
                "text": self._strip_terminal_punctuation(str(item.get("text") or "")),
                "english": self._sanitize_english_subtitle(str(item.get("english") or "")),
                "start": window_start,
                "end": round(window_start + safe_duration, 2),
            }]
        weights = [max(len(str(item.get("text") or "").strip()), 1) for item in lines]
        total_weight = max(sum(weights), 1)
        timed = []
        cursor = window_start
        for index, item in enumerate(lines):
            slice_duration = safe_duration * (weights[index] / total_weight)
            lead = min(0.16, max(slice_duration * 0.22, 0.06))
            start = round(max(window_start, cursor - lead), 2)
            end = round(min(window_end, cursor + slice_duration), 2)
            timed.append({
                "text": self._strip_terminal_punctuation(str(item.get("text") or "")),
                "english": self._sanitize_english_subtitle(str(item.get("english") or "")),
                "start": start,
                "end": max(end, start + 0.2),
            })
            cursor = timed[-1]["end"]
        if timed:
            timed[-1]["end"] = round(window_end, 2)
        return timed

    def _create_foreground_asset(self, save_path: str, subject: dict, palette: dict):
        kind = str(subject.get("kind") or "keyword_text")
        size_map = {
            "scene_illustration": (640, 640),
            "host_marker": (420, 540),
            "keyword_text": (760, 220),
            "number_badge": (340, 340),
            "focus_ring": (360, 360),
            "underline": (560, 80),
            "compare_divider": (180, 520),
            "spotlight": (640, 360),
            "arrow": (480, 180),
        }
        width, height = size_map.get(kind, (520, 220))
        canvas = Image.new("RGBA", (width, height), (0, 0, 0, 0))
        draw = ImageDraw.Draw(canvas)
        label = str(subject.get("label") or "").strip()[:16]
        font_large = self._load_font(72)
        font_mid = self._load_font(46)

        if kind == "scene_illustration":
            draw.ellipse((180, 82, 460, 362), outline=palette["text"], width=8)
            draw.line((320, 360, 320, 528), fill=palette["text"], width=8)
            draw.line((320, 408, 226, 462), fill=palette["text"], width=7)
            draw.line((320, 408, 418, 450), fill=palette["text"], width=7)
            draw.line((320, 528, 248, 610), fill=palette["text"], width=7)
            draw.line((320, 528, 392, 610), fill=palette["text"], width=7)
            draw.ellipse((430, 120, 560, 250), outline=(59, 130, 246), width=6)
            draw.line((492, 252, 492, 330), fill=(59, 130, 246), width=6)
            draw.line((492, 278, 452, 315), fill=(59, 130, 246), width=5)
            draw.line((492, 278, 534, 312), fill=(59, 130, 246), width=5)
        elif kind == "host_marker":
            draw.ellipse((98, 40, 250, 190), fill=(255, 248, 240, 235), outline=palette["text"], width=6)
            draw.line((174, 192, 174, 362), fill=palette["text"], width=8)
            draw.line((174, 240, 92, 292), fill=palette["text"], width=7)
            draw.line((174, 240, 262, 282), fill=palette["text"], width=7)
            draw.line((174, 362, 118, 476), fill=palette["text"], width=7)
            draw.line((174, 362, 240, 472), fill=palette["text"], width=7)
            draw.rounded_rectangle((218, 170, 408, 260), radius=34, fill=palette["accent"], outline=palette["shadow"], width=3)
            draw.text((250, 190), "讲", font=font_large, fill=(255, 248, 239))
        elif kind == "keyword_text":
            draw.rounded_rectangle((24, 22, width - 24, height - 28), radius=48, fill=(255, 248, 240, 238), outline=palette["surface_alt"], width=4)
            draw.rounded_rectangle((44, 44, width - 44, height - 48), radius=40, outline=palette["accent_soft"], width=3)
            bbox = draw.textbbox((0, 0), label, font=font_large)
            draw.text(((width - (bbox[2] - bbox[0])) / 2, 58), label, font=font_large, fill=palette["text"])
        elif kind == "number_badge":
            draw.ellipse((26, 26, width - 26, height - 26), fill=palette["accent"], outline=palette["shadow"], width=5)
            bbox = draw.textbbox((0, 0), label, font=font_mid)
            draw.text(((width - (bbox[2] - bbox[0])) / 2, (height - 56) / 2), label, font=font_mid, fill=(255, 249, 242))
        elif kind == "focus_ring":
            draw.ellipse((32, 32, width - 32, height - 32), outline=palette["accent"], width=14)
            draw.ellipse((78, 78, width - 78, height - 78), outline=(255, 248, 240, 210), width=7)
        elif kind == "underline":
            draw.rounded_rectangle((30, 20, width - 30, 56), radius=18, fill=palette["accent"])
            draw.rounded_rectangle((100, 10, width - 100, 70), radius=20, outline=palette["accent_soft"], width=3)
        elif kind == "compare_divider":
            draw.rounded_rectangle((80, 24, 100, height - 24), radius=10, fill=palette["accent"])
            draw.polygon([(90, 0), (120, 48), (60, 48)], fill=palette["accent_soft"])
            draw.polygon([(90, height), (120, height - 48), (60, height - 48)], fill=palette["accent_soft"])
        elif kind == "spotlight":
            draw.ellipse((20, 60, width - 20, height - 60), fill=(255, 250, 243, 95), outline=(255, 244, 230, 0))
            draw.ellipse((100, 120, width - 100, height - 120), fill=(255, 247, 238, 135))
        else:
            draw.line((40, height // 2, width - 120, height // 2), fill=palette["accent"], width=14)
            draw.polygon([(width - 120, height // 2), (width - 180, height // 2 - 36), (width - 180, height // 2 + 36)], fill=palette["accent"])

        canvas.save(save_path, format="PNG")

    def _remove_white_background(self, image_path: str):
        image = Image.open(image_path).convert("RGBA")
        pixels = image.load()
        width, height = image.size
        for x in range(width):
            for y in range(height):
                r, g, b, a = pixels[x, y]
                if r >= 245 and g >= 245 and b >= 245:
                    pixels[x, y] = (255, 255, 255, 0)
        image.save(image_path, format="PNG")

    def _normalize_scene_illustration(self, image_path: str):
        image = Image.open(image_path).convert("RGBA")
        canvas = Image.new("RGBA", (420, 420), (0, 0, 0, 0))
        image.thumbnail((320, 320))
        x = (420 - image.width) // 2
        y = (420 - image.height) // 2
        canvas.alpha_composite(image, (x, y))
        canvas.save(image_path, format="PNG")

    def _scene_frame_size(self, aspect_ratio: str):
        if aspect_ratio == "9:16":
            return 928, 1664
        return 1664, 928

    def _normalize_scene_frame(self, image_path: str, aspect_ratio: str, background_color=(8, 20, 58)):
        target_size = self._scene_frame_size(aspect_ratio)
        image = Image.open(image_path).convert("RGBA")
        image = self._crop_dark_frame_edges(image)
        background = Image.new("RGBA", image.size, (*background_color, 255))
        background.alpha_composite(image)
        fitted = ImageOps.fit(background.convert("RGB"), target_size, method=Image.Resampling.LANCZOS, centering=(0.5, 0.5))
        fitted.save(image_path, format="PNG")

    def _crop_dark_frame_edges(self, image: Image.Image):
        rgb = image.convert("RGB")
        width, height = rgb.size
        left = 0
        right = width - 1
        top = 0
        bottom = height - 1

        def row_is_dark(y: int):
            stat = ImageStat.Stat(rgb.crop((0, y, width, y + 1)))
            return sum(stat.mean) / 3 < 16

        def col_is_dark(x: int):
            stat = ImageStat.Stat(rgb.crop((x, 0, x + 1, height)))
            return sum(stat.mean) / 3 < 16

        while top < bottom and row_is_dark(top):
            top += 1
        while bottom > top and row_is_dark(bottom):
            bottom -= 1
        while left < right and col_is_dark(left):
            left += 1
        while right > left and col_is_dark(right):
            right -= 1

        if left == 0 and right == width - 1 and top == 0 and bottom == height - 1:
            return image
        cropped = image.crop((left, top, right + 1, bottom + 1))
        return cropped if cropped.width > 0 and cropped.height > 0 else image

    def _create_scene_frame_fallback(self, save_path: str, scene: dict, aspect_ratio: str):
        width, height = self._scene_frame_size(aspect_ratio)
        canvas = Image.new("RGB", (width, height), (8, 20, 58))
        draw = ImageDraw.Draw(canvas)
        title_font = self._load_font(64 if aspect_ratio == "16:9" else 56)
        body_font = self._load_font(36 if aspect_ratio == "16:9" else 34)
        accent = (82, 196, 255)
        text = str(scene.get("visual_focus") or scene.get("scene_title") or "重点")[:18]
        subtitle = str(scene.get("scene_description") or "").strip()[:32]
        draw.rectangle((0, int(height * 0.78), width, height), fill=(5, 12, 36))
        draw.ellipse((int(width * 0.10), int(height * 0.16), int(width * 0.34), int(height * 0.60)), outline=(255, 255, 255), width=8)
        draw.line((int(width * 0.22), int(height * 0.43), int(width * 0.22), int(height * 0.72)), fill=(255, 255, 255), width=8)
        draw.line((int(width * 0.22), int(height * 0.52), int(width * 0.15), int(height * 0.61)), fill=(255, 255, 255), width=7)
        draw.line((int(width * 0.22), int(height * 0.52), int(width * 0.31), int(height * 0.59)), fill=(255, 255, 255), width=7)
        draw.line((int(width * 0.22), int(height * 0.72), int(width * 0.16), int(height * 0.85)), fill=(255, 255, 255), width=7)
        draw.line((int(width * 0.22), int(height * 0.72), int(width * 0.29), int(height * 0.84)), fill=(255, 255, 255), width=7)
        card = (int(width * 0.42), int(height * 0.18), int(width * 0.90), int(height * 0.62))
        draw.rounded_rectangle(card, radius=28, fill=(10, 32, 86), outline=accent, width=4)
        draw.text((card[0] + 44, card[1] + 44), text, fill=(255, 255, 255), font=title_font)
        if subtitle:
            draw.text((card[0] + 44, card[1] + 148), subtitle, fill=(214, 233, 255), font=body_font)
        draw.line((card[0] + 44, card[1] + 128, card[0] + 220, card[1] + 128), fill=accent, width=5)
        canvas.save(save_path, format="PNG")

    def _create_scene_image_fallback(self, save_path: str, scene: dict):
        palette = self._warm_palette_for_scene(scene)
        self._create_foreground_asset(save_path, {"kind": "scene_illustration", "label": str(scene.get("visual_focus") or "主题")[:8]}, palette)

    def _generate_scene_illustration(self, prompt: str, save_path: str, scene: dict, aspect_ratio: str = "16:9"):
        model_override = str(scene.get("scene_image_model_override") or "").strip()
        lock_model = bool(scene.get("scene_image_lock_model"))
        previous_override = getattr(self, "_scene_image_model_override", "")
        previous_lock = getattr(self, "_scene_image_lock_model", False)
        self._scene_image_model_override = model_override
        self._scene_image_lock_model = lock_model
        if self.settings.DASHSCOPE_API_KEY and self.image_base_url:
            try:
                result = self._generate_scene_image_via_dashscope(prompt, save_path, aspect_ratio)
                if scene.get("scene_image_mode") == "full_frame":
                    self._normalize_scene_frame(save_path, aspect_ratio)
                else:
                    self._remove_white_background(save_path)
                    self._normalize_scene_illustration(save_path)
                result["image_source"] = result.get("image_source") or "model"
                return result
            except Exception:
                if scene.get("scene_image_mode") == "full_frame":
                    raise
            finally:
                self._scene_image_model_override = previous_override
                self._scene_image_lock_model = previous_lock
        else:
            self._scene_image_model_override = previous_override
            self._scene_image_lock_model = previous_lock
        if scene.get("scene_image_mode") == "full_frame":
            self._create_scene_frame_fallback(save_path, scene, aspect_ratio)
        else:
            self._create_scene_image_fallback(save_path, scene)
        return {
            "used_fallback": True,
            "image_source": "fallback",
            "model_used": None,
            "error_summary": "场景插画生成失败，已使用本地极简火柴人插画降级。",
        }

    def _generate_scene_image_via_dashscope(self, prompt: str, save_path: str, aspect_ratio: str = "16:9"):
        last_error = None
        models_to_try = [item for item in self.scene_image_models if item]
        model_override = str(getattr(self, "_scene_image_model_override", "") or "").strip()
        lock_model = bool(getattr(self, "_scene_image_lock_model", False))
        if model_override:
            if lock_model:
                models_to_try = [model_override]
            else:
                models_to_try = [model_override, *[item for item in models_to_try if item != model_override]]
        if not models_to_try:
            models_to_try = [self.scene_image_model]
        for model_index, model in enumerate(models_to_try):
            max_attempts = 6 if lock_model else 4
            for attempt in range(max_attempts):
                try:
                    response = requests.post(
                        self.image_base_url,
                        headers={
                            "Content-Type": "application/json",
                            "Authorization": f"Bearer {self.settings.DASHSCOPE_API_KEY}",
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
                                "prompt_extend": False,
                                "size": self._resolve_scene_image_size(aspect_ratio),
                            },
                        },
                        timeout=120,
                    )
                    response.raise_for_status()
                    result = response.json()
                    image_url = self._extract_image_url(result)
                    if not image_url:
                        raise RuntimeError(f"场景图生成失败: {result}")
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
                    if attempt < (max_attempts - 1) and self._is_retryable_scene_image_error(exc):
                        time.sleep((4.0 if lock_model else 1.2) * (attempt + 1))
                        continue
                    break
            if model_index < len(models_to_try) - 1:
                time.sleep(0.8)
        raise last_error or RuntimeError("场景图生成失败")

    def _resolve_scene_image_size(self, aspect_ratio: str):
        if aspect_ratio == "9:16":
            return "928*1664"
        return "1664*928"

    def _is_retryable_scene_image_error(self, error: Exception):
        text = str(error).lower()
        return any(token in text for token in ["429", "too many requests", "connection reset", "connection aborted", "10054", "timed out", "timeout"])

    def _create_subtitle_asset(self, save_path: str, subtitle: dict | str, palette: dict):
        if isinstance(subtitle, dict):
            chinese = str(subtitle.get("text") or "").strip() or " "
            english = self._sanitize_english_subtitle(str(subtitle.get("english") or ""))
        else:
            chinese = str(subtitle or "").strip() or " "
            english = self._sanitize_english_subtitle(self._translate_subtitle_to_english(chinese))
        zh_font = self._load_font(56)
        en_font = self._load_font(32)
        probe = Image.new("RGBA", (1680, 220), (0, 0, 0, 0))
        probe_draw = ImageDraw.Draw(probe)
        zh_lines = self._split_chinese_subtitle_lines(chinese)
        en_lines = self._wrap_english_subtitle_lines(probe_draw, english, en_font, 1320) if english else []
        canvas_height = 24 + len(zh_lines) * 62 + (12 if en_lines else 0) + len(en_lines) * 40
        canvas = Image.new("RGBA", (1680, max(canvas_height, 132)), (0, 0, 0, 0))
        draw = ImageDraw.Draw(canvas)
        y = self._render_centered_chinese_lines(draw, zh_lines, zh_font, 1680, 0, 62, (0, 0, 0, 255))
        if en_lines:
            y += 8
            for line in en_lines:
                bbox = draw.textbbox((0, 0), line, font=en_font)
                text_width = bbox[2] - bbox[0]
                draw.text(((1680 - text_width) / 2, y), line, fill=(0, 0, 0, 255), font=en_font)
                y += 40
        canvas.save(save_path, format="PNG")

    def _create_progress_bar_asset(self, save_path: str, scene: dict):
        sections = list(scene.get("sections_meta") or [])
        canvas = Image.new("RGBA", (1680, 120), (0, 0, 0, 0))
        draw = ImageDraw.Draw(canvas)
        title_font = self._load_font(28)
        bar_y = 78
        bar_left = 120
        bar_width = 1440
        bar_height = 14
        draw.rounded_rectangle((bar_left, bar_y, bar_left + bar_width, bar_y + bar_height), radius=7, fill=(255, 255, 255, 185))
        current_section = int(scene.get("section_id") or 1)
        for section in sections:
            start_ratio = float(section.get("start_ratio", 0.0))
            end_ratio = float(section.get("end_ratio", start_ratio))
            left = bar_left + int(bar_width * start_ratio)
            right = bar_left + int(bar_width * end_ratio)
            color = (59, 130, 246, 240) if int(section.get("section_id") or 0) <= current_section else (210, 210, 210, 180)
            draw.rounded_rectangle((left, bar_y, max(right, left + 8), bar_y + bar_height), radius=7, fill=color)
            label = str(section.get("title") or "")[:8]
            bbox = draw.textbbox((0, 0), label, font=title_font)
            label_w = bbox[2] - bbox[0]
            label_x = max(0, min(1680 - label_w, left + max((right - left - label_w) // 2, 0)))
            draw.text((label_x, 24), label, fill=(18, 18, 18, 255), font=title_font)
        canvas.save(save_path, format="PNG")

    def _create_progress_marker_asset(self, save_path: str):
        canvas = Image.new("RGBA", (46, 46), (0, 0, 0, 0))
        draw = ImageDraw.Draw(canvas)
        draw.ellipse((5, 5, 41, 41), fill=(245, 158, 11, 255), outline=(255, 255, 255, 255), width=3)
        draw.ellipse((16, 16, 30, 30), fill=(255, 255, 255, 255))
        canvas.save(save_path, format="PNG")

    def _create_fixed_bottom_panel_asset(self, save_path: str, sections: list[dict]):
        canvas = Image.new("RGBA", (1920, 1080), (0, 0, 0, 0))
        draw = ImageDraw.Draw(canvas)

        progress_bar_y = 1036
        label_y = 1050
        bar_left = 90
        bar_right = 1830
        bar_width = bar_right - bar_left

        # Keep the progress UI lightweight: a single thin bottom track plus section labels.
        draw.rounded_rectangle((bar_left, progress_bar_y, bar_right, progress_bar_y + 10), radius=5, fill=(220, 220, 220, 120))

        label_font = self._load_font(18)
        previous_end = -9999
        for index, section in enumerate(sections, start=1):
            start_ratio = float(section.get("start_ratio", 0.0))
            end_ratio = float(section.get("end_ratio", start_ratio))
            left = int(bar_left + bar_width * start_ratio)
            right = int(bar_left + bar_width * end_ratio)
            center_x = int((left + right) / 2)
            if index < len(sections):
                draw.line((right, progress_bar_y - 2, right, 1071), fill=(235, 235, 235, 110), width=2)
            label = str(section.get("title") or "内容")[:8]
            bbox = draw.textbbox((0, 0), label, font=label_font)
            text_width = bbox[2] - bbox[0]
            text_x = center_x - text_width / 2
            text_y = label_y - 20 if text_x < previous_end + 16 else label_y
            draw.text((text_x, text_y), label, fill=(0, 0, 0, 255), font=label_font)
            previous_end = max(previous_end, text_x + text_width)
        canvas.save(save_path, format="PNG")

    def _section_progress_position_expr(self, overlay: dict, width: int):
        sections = list(overlay.get("sections_meta") or [])
        scene_start_time = float(overlay.get("scene_start_time") or 0.0)
        bar_left = 90
        bar_width = 1740
        total_end = bar_left + bar_width - width / 2
        if not sections:
            duration = max(float(overlay.get("end", 0.3)) - float(overlay.get("start", 0.0)), 0.3)
            return f"{bar_left} + ({bar_width}) * t / {duration:.3f} - w/2"

        global_t = f"({scene_start_time:.3f}+t)"
        expr = f"{total_end:.3f}"
        for section in reversed(sections):
            start_time = float(section.get("start_time", 0.0))
            end_time = float(section.get("end_time", start_time))
            start_ratio = float(section.get("start_ratio", 0.0))
            end_ratio = float(section.get("end_ratio", start_ratio))
            left = bar_left + bar_width * start_ratio
            right = bar_left + bar_width * end_ratio
            section_duration = max(end_time - start_time, 0.05)
            pixels_per_second = (right - left) / section_duration
            section_expr = f"{left:.3f}+(({global_t})-{start_time:.3f})*{pixels_per_second:.6f}-w/2"
            expr = f"if(lte({global_t},{end_time:.3f}),{section_expr},{expr})"
        return expr

    def _create_fixed_subtitle_asset(self, save_path: str, subtitle: dict | str):
        if isinstance(subtitle, dict):
            chinese = str(subtitle.get("text") or "").strip() or " "
            english = self._sanitize_english_subtitle(str(subtitle.get("english") or ""))
        else:
            chinese = str(subtitle or "").strip() or " "
            english = self._sanitize_english_subtitle(self._translate_subtitle_to_english(chinese))

        zh_font = self._load_font(54)
        en_font = self._load_font(28)
        probe = Image.new("RGBA", (1920, 240), (0, 0, 0, 0))
        probe_draw = ImageDraw.Draw(probe)
        zh_lines = self._split_chinese_subtitle_lines(chinese)
        en_lines = self._wrap_english_subtitle_lines(probe_draw, english, en_font, 1500) if english else []
        canvas_height = 20 + len(zh_lines) * 58 + (10 if en_lines else 0) + len(en_lines) * 34 + 12
        canvas = Image.new("RGBA", (1920, max(148, canvas_height)), (0, 0, 0, 0))
        draw = ImageDraw.Draw(canvas)

        y = self._render_centered_chinese_lines(draw, zh_lines, zh_font, 1920, 0, 58, (22, 22, 22, 255), stroke_width=1, stroke_fill=(255, 255, 255, 150))
        if en_lines:
            y += 2
            for line in en_lines:
                bbox = draw.textbbox((0, 0), line, font=en_font)
                text_width = bbox[2] - bbox[0]
                draw.text(((1920 - text_width) / 2, y), line, fill=(42, 42, 42, 235), font=en_font, stroke_width=1, stroke_fill=(255, 255, 255, 190))
                y += 34
        canvas.save(save_path, format="PNG")

    def _build_fixed_bottom_overlays(self, storyboards: list[dict], total_duration: float, asset_dir: Path):
        asset_dir.mkdir(parents=True, exist_ok=True)
        overlays = []
        sections = list((storyboards[0].get("sections_meta") if storyboards else []) or [])

        panel_path = asset_dir / "bottom_panel.png"
        self._create_fixed_bottom_panel_asset(str(panel_path), sections)
        overlays.append({
            "path": str(panel_path),
            "start": 0.0,
            "end": float(total_duration),
            "animation": "fixed_bottom_panel",
        })

        marker_path = asset_dir / "progress_marker.png"
        self._create_progress_marker_asset(str(marker_path))
        overlays.append({
            "path": str(marker_path),
            "start": 0.0,
            "end": float(total_duration),
            "x_ratio": 0.0,
            "x_end_ratio": 1.0,
            "animation": "global_progress_marker",
        })

        subtitle_offset = 0
        for scene in storyboards:
            scene_start = float(scene.get("start_time") or 0.0)
            for subtitle in self._timed_subtitles_for_scene(scene, float(scene.get("scene_duration") or 0.0)):
                subtitle_path = asset_dir / f"subtitle_global_{subtitle_offset}.png"
                self._create_fixed_subtitle_asset(str(subtitle_path), subtitle)
                overlays.append({
                    "path": str(subtitle_path),
                    "start": round(scene_start + float(subtitle.get("start") or 0.0), 2),
                    "end": round(scene_start + float(subtitle.get("end") or 0.0), 2),
                    "animation": "fixed_subtitle",
                })
                subtitle_offset += 1
        return overlays

    def _build_scene_overlays(self, scene: dict, duration: float, asset_dir: Path, asset: Optional[dict] = None):
        asset_dir.mkdir(parents=True, exist_ok=True)
        subject_map = {str(item.get("key")): item for item in (scene.get("foreground_subjects") or []) if item.get("key")}
        palette = self._warm_palette_for_scene(scene)
        overlays = []
        overlays.extend(self._build_viral_package_overlays(scene, duration))
        if scene.get("sections_meta"):
            panel_path = asset_dir / "bottom_panel.png"
            marker_path = asset_dir / "progress_marker.png"
            self._create_fixed_bottom_panel_asset(str(panel_path), list(scene.get("sections_meta") or []))
            self._create_progress_marker_asset(str(marker_path))
            overlays.append({
                "path": str(panel_path),
                "start": 0.0,
                "end": float(duration),
                "animation": "fixed_bottom_panel",
                "fade_in": 0.0,
                "fade_out": 0.0,
            })
            overlays.append({
                "path": str(marker_path),
                "start": 0.0,
                "end": float(duration),
                "sections_meta": list(scene.get("sections_meta") or []),
                "scene_start_time": float(scene.get("start_time") or 0.0),
                "animation": "global_progress_marker",
                "fade_in": 0.0,
                "fade_out": 0.0,
            })
        for index, event in enumerate((scene.get("foreground_events") or [])[:6]):
            subject = subject_map.get(str(event.get("target") or ""))
            if not subject:
                continue
            subject_key = str(subject.get("key") or "")
            if subject_key.startswith("scene_image_") and asset and asset.get("scene_image_path") and os.path.exists(str(asset.get("scene_image_path"))):
                source_overlay_path = Path(str(asset.get("scene_image_path")))
                overlay_path = asset_dir / f"scene_overlay_{index}.png"
                normalize_scene_overlay_image(str(source_overlay_path), str(overlay_path))
            else:
                overlay_path = asset_dir / f"fg_{index}.png"
                self._create_foreground_asset(str(overlay_path), subject, palette)
            event_start = max(float(event.get("start", 0.0)), 0.0)
            if scene.get("viral_hook_package") and subject_key.startswith("scene_image_"):
                event_start = max(event_start, self._hook_package_title_end(duration) + 0.05)
            overlay_end = float(duration)
            if not subject_key.startswith("scene_image_"):
                overlay_end = min(float(duration), max(event_start + max(float(event.get("duration", 0.4)), 0.25) + 1.0, event_start + 0.45))
            overlays.append({
                "path": str(overlay_path),
                "start": event_start,
                "end": overlay_end,
                "x_ratio": float(event.get("x_ratio", 0.58)),
                "y_ratio": float(event.get("y_ratio", 0.42)),
                "animation": str(event.get("animation") or "fade_in"),
            })
        for index, subtitle in enumerate(self._timed_subtitles_for_scene(scene, duration), start=len(overlays)):
            overlay_path = asset_dir / f"subtitle_{index}.png"
            self._create_fixed_subtitle_asset(str(overlay_path), subtitle)
            overlays.append({
                "path": str(overlay_path),
                "start": float(subtitle["start"]),
                "end": float(subtitle["end"]),
                "animation": "fixed_subtitle",
                "fade_in": 0.0,
                "fade_out": 0.0,
            })
        return overlays

    def _build_viral_package_overlays(self, scene: dict, duration: float):
        overlays = []
        hook = scene.get("viral_hook_package") or {}
        outro = scene.get("viral_outro_package") or {}
        duration = max(float(duration or 0.0), 0.5)
        if hook:
            image_path = str(hook.get("image_path") or "")
            title_path = str(hook.get("title_asset_path") or "")
            if image_path and os.path.exists(image_path):
                image_end = duration if scene.get("viral_intro_scene") else min(duration, 0.92)
                overlays.append({
                    "path": image_path,
                    "start": 0.0,
                    "end": image_end,
                    "animation": "fullscreen_hook",
                    "fade_in": 0.0,
                    "fade_out": 0.18 if scene.get("viral_intro_scene") else 0.14,
                })
            if title_path and os.path.exists(title_path):
                title_start = 0.06 if scene.get("viral_intro_scene") else 0.12
                title_end = duration if scene.get("viral_intro_scene") else self._hook_package_title_end(duration)
                overlays.append({
                    "path": title_path,
                    "start": title_start,
                    "end": title_end,
                    "animation": "center_bounce",
                    "fade_in": 0.08,
                    "fade_out": 0.08 if scene.get("viral_intro_scene") else 0.14,
                })
        if outro:
            image_path = str(outro.get("image_path") or "")
            title_path = str(outro.get("title_asset_path") or "")
            if image_path and os.path.exists(image_path):
                overlays.append({
                    "path": image_path,
                    "start": max(0.0, duration - 1.0),
                    "end": duration,
                    "animation": "fullscreen_outro",
                    "fade_in": 0.12,
                    "fade_out": 0.0,
                })
            if title_path and os.path.exists(title_path):
                overlays.append({
                    "path": title_path,
                    "start": self._outro_package_title_start(duration),
                    "end": duration,
                    "animation": "center_fade",
                    "fade_in": 0.10,
                    "fade_out": 0.0,
                })
        return overlays

    def _overlay_position_expr(self, overlay_path: str, overlay: dict):
        animation = str(overlay.get("animation") or "fade_in")
        start = float(overlay.get("start", 0.0))
        x_ratio = float(overlay.get("x_ratio", 0.5))
        y_ratio = float(overlay.get("y_ratio", 0.5))
        with Image.open(overlay_path) as image:
            width, height = image.size
        fixed_x = max(0, min(1920 - width, int(1920 * x_ratio) - width // 2))
        fixed_y = max(0, min(1080 - height, int(1080 * y_ratio) - height // 2))
        if animation == "progress_bar":
            return "(W-w)/2", "min(H-h-8, 952)"
        if animation == "progress_marker":
            end_ratio = float(overlay.get("x_end_ratio", x_ratio))
            bar_left = 120
            bar_width = 1440
            start_x = bar_left + int(bar_width * x_ratio) - width // 2
            end_x = bar_left + int(bar_width * end_ratio) - width // 2
            end_time = max(float(overlay.get("end", start + 0.3)), start + 0.3)
            return f"if(lt(t,{end_time:.2f}),{start_x}+({end_x}-{start_x})*(t-{start:.2f})/{max(end_time-start,0.3):.3f},{end_x})", "min(H-h-8, 948)"
        if animation == "center_fade":
            return "(W-w)/2", "(H-h)/2"
        if animation == "center_zoom_in":
            return f"if(lt(t,{start + 0.26:.2f}),(W-w)/2+80-80*(t-{start:.2f})/0.26,(W-w)/2)", f"if(lt(t,{start + 0.26:.2f}),(H-h)/2+50-50*(t-{start:.2f})/0.26,(H-h)/2)"
        if animation == "center_slide_up":
            return "(W-w)/2", f"if(lt(t,{start + 0.30:.2f}),(H-h)/2+140-140*(t-{start:.2f})/0.30,(H-h)/2)"
        if animation == "center_bounce":
            return f"if(lt(t,{start + 0.18:.2f}),(W-w)/2+34-34*(t-{start:.2f})/0.18,if(lt(t,{start + 0.34:.2f}),(W-w)/2-12+12*(t-{start + 0.18:.2f})/0.16,(W-w)/2))", f"if(lt(t,{start + 0.18:.2f}),(H-h)/2+46-46*(t-{start:.2f})/0.18,if(lt(t,{start + 0.34:.2f}),(H-h)/2-10+10*(t-{start + 0.18:.2f})/0.16,(H-h)/2))"
        if animation == "slide_left_fade":
            return f"if(lt(t,{start:.2f}),1920+w,if(lt(t,{start + 0.32:.2f}),1920+w-(1920+w-{fixed_x})*(t-{start:.2f})/0.32,{fixed_x}))", str(fixed_y)
        if animation == "slide_up_fade":
            return str(fixed_x), f"if(lt(t,{start:.2f}),1080+h,if(lt(t,{start + 0.28:.2f}),1080+h-(1080+h-{fixed_y})*(t-{start:.2f})/0.28,{fixed_y}))"
        if animation == "subtitle":
            return "(W-w)/2", "min(760,H-h-44)"
        if animation == "fixed_bottom_panel":
            return "0", "0"
        if animation == "fixed_subtitle":
            return "0", "822"
        if animation == "global_progress_marker":
            return self._section_progress_position_expr(overlay, width), "1018"
        if animation in {"fullscreen_hook", "fullscreen_outro"}:
            return "0", "0"
        return str(fixed_x), str(fixed_y)

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
        voice = (tts_voice or self.tts_voice or "longanyang").strip()
        rate = (tts_rate or "+15%").strip()

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
                return self._export_tts_audio(audio, save_path, provider=provider, voice=voice)
            except Exception:
                provider = "dashscope_cosyvoice"
                voice = self._normalize_tts_voice(provider, voice)

        if provider == "dashscope_cosyvoice":
            errors = []
            for model in self._resolve_cosyvoice_models(voice):
                try:
                    logger.warning("Trying CosyVoice model provider=%s voice=%s model=%s", provider, voice, model)
                    synthesizer = SpeechSynthesizer(model=model, voice=voice)
                    audio_bytes = synthesizer.call(text)
                    if not audio_bytes:
                        raise RuntimeError("CosyVoice 未返回音频数据")
                    with open(save_path, 'wb') as file:
                        file.write(audio_bytes)
                    audio = AudioSegment.from_file(save_path)
                    if not self._audio_has_signal(audio):
                        raise RuntimeError("CosyVoice returned silent audio")
                    if rate != "+0%":
                        factor = 1.0 + (float(rate.strip('%')) / 100.0)
                        factor = max(0.7, min(1.3, factor))
                        audio = audio._spawn(audio.raw_data, overrides={"frame_rate": int(audio.frame_rate * factor)}).set_frame_rate(audio.frame_rate)
                    if errors:
                        logger.warning("CosyVoice fallback succeeded provider=%s voice=%s model=%s previous_errors=%s", provider, voice, model, " | ".join(errors))
                    return self._export_tts_audio(audio, save_path, provider=provider, voice=voice)
                except Exception as exc:
                    self._raise_if_tts_quota_exhausted(exc)
                    errors.append(f"{model}: {str(exc)[:160]}")
                    logger.warning("CosyVoice model failed provider=%s voice=%s model=%s error=%s", provider, voice, model, str(exc)[:500])
                    continue
            raise RuntimeError(f"所选音色生成失败: provider={provider}, voice={voice}, errors={' | '.join(errors)}")

        if provider == "edge_tts":
            try:
                import edge_tts
                asyncio_run = __import__("asyncio").run
                async def _run_edge_fallback():
                    communicate = edge_tts.Communicate(text=text, voice=voice or "zh-CN-YunjianNeural", rate=rate)
                    await communicate.save(save_path)
                asyncio_run(_run_edge_fallback())
                audio = AudioSegment.from_file(save_path)
                return self._export_tts_audio(audio, save_path, provider=provider, voice=voice)
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
                if not self._audio_has_signal(audio):
                    raise RuntimeError('Sambert returned silent audio')
                if rate != "+0%":
                    factor = 1.0 + (float(rate.strip('%')) / 100.0)
                    factor = max(0.7, min(1.3, factor))
                    audio = audio._spawn(audio.raw_data, overrides={"frame_rate": int(audio.frame_rate * factor)}).set_frame_rate(audio.frame_rate)
                return self._export_tts_audio(audio, save_path, provider=provider, voice=voice)
            except Exception as exc:
                self._raise_if_tts_quota_exhausted(exc)
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
            if not self._audio_has_signal(audio):
                raise RuntimeError('Generic TTS returned silent audio')
            return self._export_tts_audio(audio, save_path, provider=provider, voice=voice)
        except Exception as exc:
            raise RuntimeError(self._summarize_tts_error(exc)) from exc

    def _raise_if_tts_quota_exhausted(self, error: Exception):
        text = str(error)
        if "AllocationQuota.FreeTierOnly" in text or "free tier" in text.lower() or "quota" in text.lower():
            raise RuntimeError("当前语音配音额度已用尽，配音失败，请稍后重试") from error

    def _summarize_tts_error(self, error: Exception):
        text = str(error)
        if "AllocationQuota.FreeTierOnly" in text or "free tier" in text.lower() or "quota" in text.lower():
            return "当前语音配音额度已用尽，配音失败，请稍后重试"
        if "403" in text:
            return "当前语音配音服务无权限或额度不足，配音失败"
        if "401" in text:
            return "当前语音配音服务鉴权失败，配音失败"
        if "timeout" in text.lower():
            return "当前语音配音服务超时，配音失败，请稍后重试"
        return f"语音配音失败: {text[:160]}"

    def _normalize_tts_voice(self, provider: str, voice: str):
        if provider == "dashscope_cosyvoice":
            mapping = {
                "zh-CN-YunxiNeural": "longshuo_v3",
                "zh-CN-YunjianNeural": "longanyang",
                "zh-CN-YunyangNeural": "longsanshu",
                "zh-CN-XiaoxiaoNeural": "longxiaochun_v2",
                "zh-CN-XiaoyiNeural": "longanhuan",
                "zh-CN-XiaochenNeural": "longanwen",
                "longanlang": "longanlang_v3",
                "longanwen": "longanwen_v3",
                "longanyun": "longanyun_v3",
                "longxiaochun": "longxiaochun_v3",
                "longsanshu": "longsanshu_v3",
            }
            return mapping.get(voice, voice or "longanyang")
        if provider == "dashscope_qwen":
            return voice if voice and not voice.startswith("zh-CN-") else "Cherry"
        return voice

    def _resolve_cosyvoice_models(self, voice: str):
        preferred = "cosyvoice-v3.5-plus" if voice.startswith("cosyvoice-v3.5-plus-") else "cosyvoice-v3-flash"
        ordered = []
        seen = set()
        for candidate in [preferred, *self.tts_fallback_models]:
            model = str(candidate or "").strip()
            if model and model not in seen:
                ordered.append(model)
                seen.add(model)
        return ordered or ["cosyvoice-v3.5-plus"]

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

    def _audio_has_signal(self, audio: AudioSegment):
        return bool(len(audio)) and int(audio.rms or 0) > 0

    def _tts_export_preroll_ms(self):
        return 40

    def _tts_concat_lead_ms(self):
        return 60

    def _tts_concat_pause_ms(self, is_last: bool):
        return 180 if is_last else 140

    def _postprocess_tts_audio(self, audio: AudioSegment, provider: str, voice: str):
        processed = audio.set_channels(1)
        voice_key = str(voice or "").strip()
        cloned_voice = provider == "dashscope_cosyvoice" and voice_key.startswith("cosyvoice-v3.5-plus-")

        # Clone voices often sound stiff at sentence edges; trim the clicky boundary
        # and add a slightly softer fade-in/fade-out to smooth transitions.
        if cloned_voice and len(processed) > 120:
            processed = processed[20:max(20, len(processed) - 28)]
            processed = processed.fade_in(26).fade_out(42)
        try:
            if cloned_voice:
                processed = processed.high_pass_filter(110).low_pass_filter(7200)
                processed = compress_dynamic_range(processed, threshold=-24.0, ratio=3.2, attack=5, release=70)
            else:
                processed = processed.high_pass_filter(80).low_pass_filter(8000)
                processed = compress_dynamic_range(processed, threshold=-22.0, ratio=2.4, attack=6, release=80)
        except Exception:
            pass

        try:
            ranges = detect_nonsilent(processed, min_silence_len=220, silence_thresh=-43 if cloned_voice else -45)
            if ranges:
                start = max(ranges[0][0] - 25, 0)
                end = min(ranges[-1][1] + 45, len(processed))
                processed = processed[start:end]
        except Exception:
            pass

        try:
            processed = processed.normalize()
        except Exception:
            pass
        return processed.set_frame_rate(24000)

    def _export_tts_audio(self, audio: AudioSegment, save_path: str, preroll_ms: int | None = None, provider: str = "", voice: str = ""):
        processed = self._postprocess_tts_audio(audio, provider, voice)
        if preroll_ms is None:
            preroll_ms = self._tts_export_preroll_ms()
        final_audio = AudioSegment.silent(duration=max(preroll_ms, 0)) + processed
        final_audio.export(save_path, format="mp3")
        return max(len(final_audio) / 1000.0, 1.0)

    def _scene_tts_profile(self, scene: dict, provider: str, voice: str, rate: str):
        return provider, voice, rate

    def _finalize_audio_track(self, audio_path: str):
        audio = AudioSegment.from_file(audio_path)
        if len(audio) > 300:
            audio = audio.fade_out(min(120, len(audio) // 8))
        audio.export(audio_path, format="mp3")
        return max(len(audio) / 1000.0, 1.0)

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
        self._create_stage_background(save_path, "16:9", [scene], None, None)

    def _camera_type_for_index(self, index: int):
        return ["wide shot", "medium shot", "close-up"][(index - 1) % 3]

    def _action_for_index(self, index: int):
        return ["pointing to a board", "walking while explaining", "raising one hand for emphasis"][(index - 1) % 3]

    def _layout_for_index(self, index: int):
        return ["subject on left, empty space on right", "subject centered", "subject on right, diagram on left"][(index - 1) % 3]

    def _motion_preset_for_index(self, index: int):
        return ["slow_push_center", "micro_pan_right", "push_left_focus", "hold_then_push", "push_right_focus", "pull_out_soft"][(index - 1) % 6]

    def _motion_preset_for_scene(self, scene: dict, index: int):
        preset = str(scene.get("motion_preset") or "").strip().lower()
        if preset in {"auto", "", "none"}:
            track = str(scene.get("camera_track") or self._camera_track_for_index(index, max(index, 2))).lower()
            if track in {"static", "slow_push_center", "micro_pan_right", "push_left_focus", "hold_then_push", "push_right_focus", "pull_out_soft", "micro_pan_left"}:
                return track
            return self._motion_preset_for_index(index)
        allowed = {"static", "slow_push_center", "micro_pan_right", "push_left_focus", "hold_then_push", "push_right_focus", "pull_out_soft", "micro_pan_left"}
        return preset if preset in allowed else self._motion_preset_for_index(index)

    def _transition_type_for_index(self, index: int):
        return ["fade", "smoothleft", "fade", "smoothright"][(index - 1) % 4]

    def _transition_type_for_scene(self, scene: dict, index: int):
        transition = str(scene.get("transition_type") or "").strip().lower()
        allowed = {"fade", "fadeblack", "smoothleft", "smoothright", "circleopen", "circleclose"}
        if transition in {"", "auto", "none"}:
            return self._transition_type_for_index(index)
        return transition if transition in allowed else self._transition_type_for_index(index)

    def _anchor_from_layout(self, layout_hint: str | None):
        text = str(layout_hint or "").lower()
        if "subject on left" in text or ("left" in text and "right" in text):
            return 0.18
        if "subject on right" in text:
            return 0.82
        if "left" in text:
            return 0.25
        if "right" in text:
            return 0.75
        return 0.5

    def _vertical_anchor_from_camera(self, camera_type: str | None, motion_preset: str):
        camera = str(camera_type or "").lower()
        if motion_preset == "static":
            return 0.5
        if motion_preset in {"micro_pan_left", "micro_pan_right", "pull_out_soft"}:
            return 0.32
        if motion_preset in {"slow_push_center", "push_left_focus", "push_right_focus", "hold_then_push"}:
            return 0.68
        if "close" in camera:
            return 0.42
        if "wide" in camera:
            return 0.5
        return 0.48

    def _clamp_ratio(self, value: float, low: float = 0.0, high: float = 1.0):
        return max(low, min(high, value))

    def _motion_spec_for_scene(self, scene: dict, index: int, duration: float):
        preset = self._motion_preset_for_scene(scene, index)
        anchor_x = self._anchor_from_layout(scene.get("layout_hint"))
        anchor_y = self._vertical_anchor_from_camera(scene.get("camera_type"), preset)
        base_zoom = 1.0
        scene_duration = max(float(duration or 2.5), 1.5)

        spec_map = {
            "static": {
                "zoom": (1.0, 1.0, 1.0),
                "x": (anchor_x, anchor_x, anchor_x),
                "y": (anchor_y, anchor_y, anchor_y),
            },
            "slow_push_center": {
                "zoom": (base_zoom, 1.04, 1.08 if scene_duration > 2.6 else 1.06),
                "x": (anchor_x, anchor_x, anchor_x),
                "y": (anchor_y, anchor_y, anchor_y),
            },
            "pull_out_soft": {
                "zoom": (1.08, 1.04, 1.0),
                "x": (anchor_x, anchor_x, anchor_x),
                "y": (anchor_y, anchor_y, anchor_y),
            },
            "micro_pan_left": {
                "zoom": (1.03, 1.04, 1.05),
                "x": (anchor_x, anchor_x, anchor_x),
                "y": (anchor_y, anchor_y, anchor_y),
            },
            "micro_pan_right": {
                "zoom": (1.03, 1.04, 1.05),
                "x": (anchor_x, anchor_x, anchor_x),
                "y": (anchor_y, anchor_y, anchor_y),
            },
            "push_left_focus": {
                "zoom": (1.02, 1.06, 1.1 if scene_duration > 2.6 else 1.08),
                "x": (anchor_x, anchor_x, anchor_x),
                "y": (anchor_y, anchor_y, anchor_y),
            },
            "push_right_focus": {
                "zoom": (1.02, 1.06, 1.1 if scene_duration > 2.6 else 1.08),
                "x": (anchor_x, anchor_x, anchor_x),
                "y": (anchor_y, anchor_y, anchor_y),
            },
            "hold_then_push": {
                "zoom": (1.0, 1.02, 1.08),
                "x": (anchor_x, anchor_x, anchor_x),
                "y": (anchor_y, anchor_y, anchor_y),
            },
        }
        return {"preset": preset, **spec_map.get(preset, spec_map["static"])}

    def _linear_expr(self, first: float, third: float, frames: int):
        end_frames = max(frames - 1, 1)
        return f"{first:.4f}+({third:.4f}-{first:.4f})*on/{end_frames}"

    def _piecewise_expr(self, first: float, second: float, third: float, frames: int):
        midpoint = max(frames // 2, 1)
        end_frames = max(frames - midpoint, 1)
        return (
            f"if(lte(on,{midpoint}),"
            f"{first:.4f}+({second:.4f}-{first:.4f})*on/{midpoint},"
            f"{second:.4f}+({third:.4f}-{second:.4f})*(on-{midpoint})/{end_frames})"
        )

    def _transition_duration_for_pair(self, current_duration: float, next_duration: float):
        return round(max(0.18, min(0.45, current_duration * 0.18, next_duration * 0.18)), 2)

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
        segment_count = len(audio_segments or [])
        for index, (_, duration) in enumerate(audio_segments, start=1):
            lead_padding = self._tts_concat_lead_ms() / 1000.0
            pause_padding = self._tts_concat_pause_ms(index >= segment_count) / 1000.0
            padded_duration = float(duration or 0.0) + lead_padding + pause_padding
            timeline.append({"video_duration": round(max(padded_duration, 0.75), 3)})
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
        return [{"video_duration": round(max(float(item.get("video_duration", 0.0)), 0.3), 2)} for item in timeline]

    def _build_timeline_from_total_duration(self, total_duration: float, scene_count: int):
        base_duration = max(total_duration / max(scene_count, 1), 0.3)
        return [{"video_duration": round(base_duration, 2)} for _ in range(scene_count)]

    def _ensure_timeline_covers_audio(self, timeline, total_audio_duration: float):
        if not timeline:
            return timeline
        total_video_duration = sum(item["video_duration"] for item in timeline)
        delta = round(float(total_audio_duration) - float(total_video_duration), 3)
        if abs(delta) >= 0.001:
            timeline[-1]["video_duration"] = round(max(0.3, float(timeline[-1]["video_duration"]) + delta), 3)
        return timeline

    def _attach_scene_timing_metadata(self, storyboards: list[dict], timeline: list[dict], audio_segments=None):
        elapsed = 0.0
        for index, scene in enumerate(storyboards):
            segment = timeline[index] if index < len(timeline) else {"video_duration": 2.0}
            scene_duration = float(segment.get("video_duration", 2.0))
            audio_duration = 0.0
            if audio_segments and index < len(audio_segments):
                audio_duration = float(audio_segments[index][1] or 0.0)
            scene["audio_lead"] = round(self._tts_concat_lead_ms() / 1000.0, 3)
            scene["audio_pause"] = round(self._tts_concat_pause_ms(index >= len(storyboards) - 1) / 1000.0, 3)
            scene["scene_duration"] = round(scene_duration, 2)
            scene["audio_duration"] = round(audio_duration, 2)
            scene["start_time"] = round(elapsed, 2)
            scene["end_time"] = round(elapsed + scene_duration, 2)
            scene["subtitle_segments"] = self._timed_subtitles_for_scene(scene, scene_duration)
            elapsed += scene_duration
        return storyboards

    def _attach_section_timing_metadata(self, storyboards: list[dict]):
        if not storyboards:
            return []
        total_duration = max(float(storyboards[-1].get("end_time") or 0.0), 0.1)
        sections = []
        current = None
        for scene in storyboards:
            section_id = int(scene.get("section_id") or 0) or (len(sections) + 1)
            title = str(scene.get("section_title") or "内容")
            icon_key = str(scene.get("section_icon_key") or "section")
            if current is None or current["section_id"] != section_id:
                current = {
                    "section_id": section_id,
                    "title": title,
                    "icon_key": icon_key,
                    "start_time": float(scene.get("start_time") or 0.0),
                    "end_time": float(scene.get("end_time") or 0.0),
                }
                sections.append(current)
            else:
                current["end_time"] = float(scene.get("end_time") or current["end_time"])
        for section in sections:
            section["start_ratio"] = round(float(section["start_time"]) / total_duration, 4)
            section["end_ratio"] = round(float(section["end_time"]) / total_duration, 4)
        for scene in storyboards:
            scene["sections_meta"] = sections
            scene["video_progress_start_ratio"] = round(float(scene.get("start_time") or 0.0) / total_duration, 4)
            scene["video_progress_end_ratio"] = round(float(scene.get("end_time") or 0.0) / total_duration, 4)
        return sections

    def _create_image_clip(self, image_path: str, output_path: str, duration: float, scene: Optional[dict] = None, index: int = 1, asset: Optional[dict] = None):
        fps = 25
        scene = scene or {}
        frames = max(int(round(float(duration) * fps)), 2)
        if asset and str(asset.get("image_source") or "") == "fixed_background":
            filter_expr = f"scale=1920:1080,fps={fps},trim=duration={float(duration):.3f}"
        else:
            spec = self._motion_spec_for_scene(scene, index, duration)
            zoom_expr = self._linear_expr(spec["zoom"][0], spec["zoom"][2], frames)
            x_expr = "(iw-iw/zoom)/2"
            y_expr = "(ih-ih/zoom)/2"
            filter_expr = (
                "scale=2200:1238,"
                f"zoompan=z='{zoom_expr}':x='{x_expr}':y='{y_expr}':d=1:s=1920x1080:fps={fps},"
                f"trim=duration={float(duration):.3f},fps={fps}"
            )
        overlay_dir = Path(output_path).with_suffix("")
        overlays = self._build_scene_overlays(scene, duration, overlay_dir, asset)
        cmd = ["ffmpeg", "-y", "-loop", "1", "-i", image_path]
        for overlay in overlays:
            cmd.extend(["-loop", "1", "-i", overlay["path"]])
        cmd.extend(["-t", str(duration)])
        if overlays:
            filter_parts = [f"[0:v]{filter_expr}[base0]"]
            current_label = "[base0]"
            for overlay_index, overlay in enumerate(overlays, start=1):
                x_overlay, y_overlay = self._overlay_position_expr(overlay["path"], overlay)
                fade_in = max(float(overlay.get("fade_in", 0.14)), 0.0)
                fade_out = max(float(overlay.get("fade_out", 0.16)), 0.0)
                overlay_label = f"[ov{overlay_index}]"
                output_label = f"[base{overlay_index}]"
                overlay_filter = f"[{overlay_index}:v]format=rgba"
                if fade_in > 0:
                    overlay_filter += f",fade=t=in:st={float(overlay['start']):.2f}:d={fade_in:.2f}:alpha=1"
                if fade_out > 0:
                    fade_out_start = max(float(overlay["end"]) - fade_out, float(overlay["start"]))
                    overlay_filter += f",fade=t=out:st={fade_out_start:.2f}:d={fade_out:.2f}:alpha=1"
                animation = str(overlay.get("animation") or "")
                if animation in {"keyword_punch", "number_burst", "bounce_settle", "focus_ring_ping", "arrow_draw", "underline_wipe"}:
                    overlay_filter += ",setpts=PTS-STARTPTS"
                filter_parts.append(f"{overlay_filter}{overlay_label}")
                filter_parts.append(
                    f"{current_label}{overlay_label}overlay=x='{x_overlay}':y='{y_overlay}':enable='between(t,{float(overlay['start']):.2f},{float(overlay['end']):.2f})'{output_label}"
                )
                current_label = output_label
            cmd.extend(["-filter_complex", ";".join(filter_parts), "-map", current_label])
        else:
            cmd.extend(["-vf", filter_expr])
        cmd.extend([
            "-c:v",
            "libx264",
            "-threads",
            "2",
            "-preset",
            "veryfast",
            "-pix_fmt",
            "yuv420p",
            "-r",
            str(fps),
            output_path,
        ])
        self._run_ffmpeg(cmd, "生成视频片段失败")

    def _concat_audio(self, audio_segments, output_path: str):
        combined = AudioSegment.empty()
        total = len(audio_segments or [])
        for index, (audio_path, _) in enumerate(audio_segments, start=1):
            combined += AudioSegment.silent(duration=self._tts_concat_lead_ms())
            combined += AudioSegment.from_file(audio_path)
            combined += AudioSegment.silent(duration=self._tts_concat_pause_ms(index >= total))
        combined.export(output_path, format="mp3")

    def _concat_video_clips(self, clip_paths, timeline, storyboards, output_path: str):
        if not clip_paths:
            raise RuntimeError("没有可拼接的视频片段")
        if len(clip_paths) == 1:
            shutil.copyfile(clip_paths[0], output_path)
            return

        cmd = ["ffmpeg", "-y"]
        for clip_path in clip_paths:
            cmd.extend(["-i", clip_path])

        concat_inputs = "".join(f"[{index}:v]" for index in range(len(clip_paths)))

        cmd.extend([
            "-filter_complex",
            f"{concat_inputs}concat=n={len(clip_paths)}:v=1:a=0[outv]",
            "-map",
            "[outv]",
            "-c:v",
            "libx264",
            "-threads",
            "2",
            "-preset",
            "veryfast",
            "-pix_fmt",
            "yuv420p",
            output_path,
        ])
        self._run_ffmpeg(cmd, "拼接视频片段失败")

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
