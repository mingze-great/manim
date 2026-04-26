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
from PIL import Image, ImageDraw, ImageFilter, ImageFont, ImageStat
from pydub import AudioSegment
import dashscope
from dashscope.audio.tts_v2 import SpeechSynthesizer
from dashscope.audio.tts import SpeechSynthesizer as SambertSpeechSynthesizer

from app.config import get_settings


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
        self.scene_image_model = "z-image-turbo"
        self.scene_image_size = "1120*1440"
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
            candidates.extend([r"C:\Windows\Fonts\msyh.ttc", r"C:\Windows\Fonts\simhei.ttf"])
        else:
            candidates.extend([
                "/usr/share/fonts/truetype/noto/NotoSansCJK-Regular.ttc",
                "/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc",
                "/usr/share/fonts/truetype/wqy/wqy-zenhei.ttc",
                "/usr/share/fonts/truetype/arphic/ukai.ttc",
                "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
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

    def _normalize_material_entry(self, entry: dict):
        if not isinstance(entry, dict):
            return None
        file_name = str(entry.get("file_name") or "").strip()
        image_path = str(entry.get("image_path") or "").strip()
        if not image_path and file_name and self.material_source_dir:
            candidate = self.material_source_dir / file_name
            if candidate.exists():
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

    def _build_material_assets(self, storyboards: list[dict], image_output_dir: Path, aspect_ratio: str):
        if not self.material_library:
            return [], {
                "material_library_used": False,
                "material_library_reason": "素材库为空，已回退模型生成",
            }

        if not any(item.get("has_semantic_metadata") for item in self.material_library):
            assets = []
            material_pool = self.material_library[:]
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
                    "error_summary": "素材库缺少语义标签，已按素材库顺序生成场景前景。",
                })
            return assets, {
                "material_library_used": True,
                "material_library_count": len(self.material_library),
                "material_selection_unique": len(self.material_library) >= len(storyboards),
                "material_library_reason": "素材库缺少语义标签，已按顺序使用素材库",
            }

        selections = self._select_material_candidates(storyboards)
        if not selections or any(selection is None for selection in selections):
            return [], {
                "material_library_used": False,
                "material_library_reason": "素材匹配失败或素材数量不足",
            }

        if any((selection or {}).get("score", 0) <= 0 for selection in selections):
            return [], {
                "material_library_used": False,
                "material_library_reason": "当前分镜与素材语义匹配度不足，已回退模型生成",
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
            "material_library_count": len(self.material_library),
            "material_selection_unique": True,
        }

    def get_tts_voice_library(self):
        return self.tts_voice_library

    def _strip_terminal_punctuation(self, text: str):
        return re.sub(r"[，。,.!?！？；;：:]+$", "", str(text or "").strip())

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

    def _split_script_for_storyboards(self, text: str) -> list[str]:
        sentences = self._split_sentences(text)
        refined = []
        for sentence in sentences:
            estimate = min(len(sentence) * 0.22, 10.0)
            if estimate <= 4.8:
                refined.append(sentence)
                continue
            clauses = [item.strip() for item in re.split(r'(?<=[，；：,;])\s*', sentence) if item.strip()]
            if len(clauses) <= 1:
                refined.append(sentence)
                continue
            current = ""
            for clause in clauses:
                candidate = f"{current}{clause}"
                candidate_estimate = min(len(candidate) * 0.22, 10.0)
                if current and candidate_estimate > 4.8:
                    refined.append(current)
                    current = clause
                else:
                    current = candidate
            if current:
                refined.append(current)
        return refined or ([text.strip()] if text and text.strip() else [])

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

    def build_storyboards_from_script_text(self, topic: str, script_text: str):
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
            scene["subtitle_lines"] = self._subtitle_blueprint_for_scene(scene)
            scene["emphasis_beats"] = self._emphasis_beats_for_scene(scene)
            storyboards.append(scene)
        sections = self._attach_sections(storyboards)
        storyboards = self._explode_storyboards_for_segments(storyboards, topic)
        return {
            "title": topic,
            "script": "\n".join(sentences),
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
    ):
        self._require_config()
        storyboard_count = max(2, min(int(storyboard_count or 3), 20))

        def report(progress: int, message: str):
            if progress_callback:
                progress_callback(progress, message)

        report(5, "开始生成火柴人视频")
        script_data = self.generate_script_data(topic, storyboard_count, opening_template_key=opening_template_key)
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

            for index, asset in enumerate(image_assets, start=1):
                image_path = asset.get("image_path")
                if not image_path or not os.path.exists(image_path):
                    raise RuntimeError(f"第 {index} 张分镜图片不存在，请重新生成图片")
            report(20, "图片素材检查完成")

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
            self._attach_scene_timing_metadata(storyboards, timeline, audio_segments)
            self._attach_section_timing_metadata(storyboards)

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

    def generate_script_data(self, topic: str, storyboard_count: int, opening_template_key: Optional[str] = None):
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
        script_data["storyboards"] = self._explode_storyboards_for_segments(storyboards, topic)
        script_data["script"] = "\n".join(scene.get("scene_narration") or scene.get("narration") or "" for scene in script_data["storyboards"])
        return script_data

    def generate_images(self, storyboards: list[dict], aspect_ratio: str, project_id: Optional[int] = None, progress_callback=None, background_image_path: Optional[str] = None, style_reference_image_path: Optional[str] = None, style_reference_notes: Optional[str] = None):
        assets = []
        image_output_dir = self._get_image_output_dir(project_id)
        image_output_dir.mkdir(parents=True, exist_ok=True)
        fixed_background_path = image_output_dir / f"fixed_background_{uuid.uuid4().hex[:8]}.png"
        self._create_fixed_reference_background(str(fixed_background_path), aspect_ratio, storyboards[0] if storyboards else None, background_image_path)
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

        material_assets, material_flags = self._build_material_assets(storyboards, image_output_dir, aspect_ratio)
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
                    "error_summary": "已使用固定背景，素材人物会以居中场景图形式叠加出现。",
                })
            if progress_callback:
                progress_callback(32, f"素材匹配完成 ({len(assets)}/{len(storyboards)})")
            return assets, flags

        for index, scene in enumerate(storyboards, start=1):
            prompt = self._resolved_scene_image_prompt(scene, str(scene.get("visual_focus") or scene.get("scene_title") or "主题"))
            scene_image_path = image_output_dir / f"scene_{index}_illustration_{uuid.uuid4().hex[:8]}.png"
            illustration_result = self._generate_scene_illustration(prompt, str(scene_image_path), scene)
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
                "error_summary": illustration_result.get("error_summary") or "当前场景使用固定背景，动态讲解元素会在视频合成阶段居中叠加。",
            })
            if progress_callback:
                progress_callback(20 + int(index / len(storyboards) * 25), f"场景图生成中 ({index}/{len(storyboards)})")
        return assets, flags

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
        illustration_result = self._generate_scene_illustration(prompt, str(scene_image_path), scene)
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
            "error_summary": illustration_result.get("error_summary") or "预览图展示的是固定背景，真正的动态场景图会在视频合成阶段居中叠加。",
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

    def _section_title_for_scene(self, scene: dict, index: int, total: int):
        role = str(scene.get("performance_template") or scene.get("opening_template_key") or "").strip().lower()
        if role in {"hook", "problem"}:
            return "问题切入", "question"
        if role in {"cause", "compare"}:
            return "原因分析", "cause"
        if role in {"method", "explain"}:
            return "应对方法", "method"
        if role in {"result", "summary", "transition"} or index >= total:
            return "总结收束", "summary"
        if total <= 3:
            return ("问题切入", "question") if index == 1 else ("应对方法", "method")
        if index <= max(1, total // 3):
            return "问题切入", "question"
        if index <= max(2, total * 2 // 3):
            return "应对方法", "method"
        return "总结收束", "summary"

    def _attach_sections(self, storyboards: list[dict]):
        total = len(storyboards)
        sections = []
        last_key = None
        for index, scene in enumerate(storyboards, start=1):
            title, icon_key = self._section_title_for_scene(scene, index, total)
            key = (title, icon_key)
            if key != last_key:
                sections.append({
                    "section_id": len(sections) + 1,
                    "title": title,
                    "icon_key": icon_key,
                    "start_scene_index": index,
                    "end_scene_index": index,
                })
                last_key = key
            else:
                sections[-1]["end_scene_index"] = index
            scene["section_id"] = sections[-1]["section_id"]
            scene["section_title"] = title
            scene["section_icon_key"] = icon_key
        return sections

    def _explode_storyboards_for_segments(self, storyboards: list[dict], topic: str):
        exploded = []
        for scene in storyboards:
            subtitle_lines = list(scene.get("subtitle_lines") or self._subtitle_blueprint_for_scene(scene))
            if not subtitle_lines:
                subtitle_lines = [{"text": str(scene.get("scene_narration") or scene.get("narration") or topic).strip()}]
            for seg_index, subtitle in enumerate(subtitle_lines, start=1):
                text = str(subtitle.get("text") or "").strip() or str(scene.get("scene_narration") or scene.get("narration") or topic).strip()
                clone = dict(scene)
                clone["segment_index_within_scene"] = seg_index
                clone["source_scene_id"] = scene.get("scene_id")
                clone["scene_narration"] = text
                clone["narration"] = text
                clone["scene_title"] = str(scene.get("section_title") or scene.get("scene_title") or f"第{scene.get('scene_id')}幕")
                clone["subtitle_lines"] = [{
                    "text": text,
                    "english": str(subtitle.get("english") or "").strip(),
                }]
                clone["visual_focus"] = self._infer_scene_focus(text, topic)
                clone["scene_description"] = f"围绕{text[:14]}的单句讲解画面，仅表达当前字幕段内容。"
                clone["scene_image_prompt"] = self._scene_image_prompt_for_scene(clone, topic)
                clone["foreground_subjects"] = self._foreground_subjects_for_scene(clone, topic, len(exploded) + 1)
                clone["foreground_events"] = self._foreground_events_for_scene(clone, len(exploded) + 1)
                exploded.append(clone)
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
            clause = clause.strip()
            if not clause:
                return []
            if len(clause) <= 18:
                return [clause]

            comma_parts = [item.strip() for item in re.split(r"(?<=[，,、])\s*", clause) if item.strip()]
            if len(comma_parts) > 1:
                merged = []
                current = ""
                for part in comma_parts:
                    candidate = f"{current}{part}" if current else part
                    if current and len(candidate) > 18:
                        merged.append(current)
                        current = part
                    else:
                        current = candidate
                if current:
                    merged.append(current)
                return merged

            pieces = []
            current = clause
            while len(current) > 18:
                cut = current.rfind("，", 0, 18)
                if cut <= 0:
                    cut = current.rfind(",", 0, 18)
                if cut <= 0:
                    cut = current.rfind("、", 0, 18)
                if cut <= 0:
                    cut = 16
                pieces.append(current[:cut + 1].strip())
                current = current[cut + 1:].strip()
            if current:
                pieces.append(current)
            return [item for item in pieces if item]

        parts = [item.strip() for item in re.split(r"(?<=[。！？!?；;])\s*", raw) if item.strip()]
        refined = []
        for part in (parts or [raw.strip()]):
            refined.extend(split_long_clause(part))
        return refined or [raw.strip()]

    def _timed_subtitles_for_scene(self, scene: dict, duration: float):
        existing = scene.get("subtitle_segments") or []
        subtitle_lead = 0.10
        if existing:
            return [
                {
                    "text": str(item.get("text") or ""),
                    "english": str(item.get("english") or ""),
                    "start": max(0.0, float(item.get("start", 0.0)) - subtitle_lead),
                    "end": float(item.get("end", duration)),
                }
                for item in existing
                if str(item.get("text") or "").strip()
            ]
        lines = list(scene.get("subtitle_lines") or self._subtitle_blueprint_for_scene(scene))
        if not lines:
            return []
        start_at = 0.0
        audio_duration = float(scene.get("audio_duration") or 0.0)
        effective_duration = min(duration, audio_duration + 0.06) if audio_duration > 0 else duration
        safe_duration = max(min(duration, effective_duration), 0.2)
        if len(lines) == 1:
            item = lines[0]
            return [{
                "text": self._strip_terminal_punctuation(str(item.get("text") or "")),
                "english": self._sanitize_english_subtitle(str(item.get("english") or "")),
                "start": 0.0,
                "end": round(safe_duration, 2),
            }]
        segment = safe_duration / max(len(lines), 1)
        timed = []
        for index, item in enumerate(lines):
            start = round(max(0.0, start_at + index * segment - subtitle_lead), 2)
            end = round(min(duration, start_at + (index + 1) * segment), 2)
            timed.append({
                "text": self._strip_terminal_punctuation(str(item.get("text") or "")),
                "english": self._sanitize_english_subtitle(str(item.get("english") or "")),
                "start": start,
                "end": max(end, start + 0.2),
            })
        if timed:
            timed[-1]["end"] = round(duration, 2)
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

    def _create_scene_image_fallback(self, save_path: str, scene: dict):
        palette = self._warm_palette_for_scene(scene)
        self._create_foreground_asset(save_path, {"kind": "scene_illustration", "label": str(scene.get("visual_focus") or "主题")[:8]}, palette)

    def _generate_scene_illustration(self, prompt: str, save_path: str, scene: dict):
        if self.settings.DASHSCOPE_API_KEY and self.image_base_url:
            try:
                result = self._generate_scene_image_via_dashscope(prompt, save_path)
                self._remove_white_background(save_path)
                self._normalize_scene_illustration(save_path)
                result["image_source"] = result.get("image_source") or "model"
                return result
            except Exception:
                pass
        self._create_scene_image_fallback(save_path, scene)
        return {
            "used_fallback": True,
            "image_source": "fallback",
            "model_used": None,
            "error_summary": "场景插画生成失败，已使用本地极简火柴人插画降级。",
        }

    def _generate_scene_image_via_dashscope(self, prompt: str, save_path: str):
        response = requests.post(
            self.image_base_url,
            headers={
                "Content-Type": "application/json",
                "Authorization": f"Bearer {self.settings.DASHSCOPE_API_KEY}",
            },
            json={
                "model": self.scene_image_model,
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
                    "size": self.scene_image_size,
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
            "model_used": self.scene_image_model,
            "error_summary": None,
        }

    def _create_subtitle_asset(self, save_path: str, subtitle: dict | str, palette: dict):
        if isinstance(subtitle, dict):
            chinese = str(subtitle.get("text") or "").strip() or " "
            english = self._sanitize_english_subtitle(str(subtitle.get("english") or ""))
        else:
            chinese = str(subtitle or "").strip() or " "
            english = self._sanitize_english_subtitle(self._translate_subtitle_to_english(chinese))
        zh_lines = [chinese[i:i + 14] for i in range(0, len(chinese), 14)] or [chinese]
        en_lines = [english[i:i + 28] for i in range(0, len(english), 28)] if english else []
        zh_font = self._load_font(56)
        en_font = self._load_font(32)
        canvas_height = 24 + len(zh_lines) * 62 + (12 if en_lines else 0) + len(en_lines) * 40
        canvas = Image.new("RGBA", (1680, max(canvas_height, 132)), (0, 0, 0, 0))
        draw = ImageDraw.Draw(canvas)
        y = 0
        for line in zh_lines:
            bbox = draw.textbbox((0, 0), line, font=zh_font)
            text_width = bbox[2] - bbox[0]
            draw.text(((1680 - text_width) / 2, y), line, fill=(0, 0, 0, 255), font=zh_font)
            y += 62
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
        draw.rounded_rectangle((bar_left, progress_bar_y, bar_right, progress_bar_y + 10), radius=5, fill=(220, 220, 220, 225))

        label_font = self._load_font(20)
        for index, section in enumerate(sections, start=1):
            start_ratio = float(section.get("start_ratio", 0.0))
            end_ratio = float(section.get("end_ratio", start_ratio))
            left = int(bar_left + bar_width * start_ratio)
            right = int(bar_left + bar_width * end_ratio)
            center_x = int((left + right) / 2)
            if index < len(sections):
                draw.line((right, progress_bar_y - 2, right, 1071), fill=(235, 235, 235, 165), width=2)
            label = str(section.get("title") or "内容")[:12]
            bbox = draw.textbbox((0, 0), label, font=label_font)
            text_width = bbox[2] - bbox[0]
            draw.text((center_x - text_width / 2, label_y), label, fill=(235, 235, 235, 235), font=label_font)
        canvas.save(save_path, format="PNG")

    def _create_fixed_subtitle_asset(self, save_path: str, subtitle: dict | str):
        if isinstance(subtitle, dict):
            chinese = str(subtitle.get("text") or "").strip() or " "
            english = self._sanitize_english_subtitle(str(subtitle.get("english") or ""))
        else:
            chinese = str(subtitle or "").strip() or " "
            english = self._sanitize_english_subtitle(self._translate_subtitle_to_english(chinese))

        zh_lines = [chinese[i:i + 14] for i in range(0, len(chinese), 14)] or [chinese]
        en_lines = [english[i:i + 28] for i in range(0, len(english), 28)] if english else []
        canvas = Image.new("RGBA", (1920, 132), (0, 0, 0, 0))
        draw = ImageDraw.Draw(canvas)
        zh_font = self._load_font(54)
        en_font = self._load_font(28)

        y = 0
        for line in zh_lines:
            bbox = draw.textbbox((0, 0), line, font=zh_font)
            text_width = bbox[2] - bbox[0]
            draw.text(((1920 - text_width) / 2, y), line, fill=(22, 22, 22, 255), font=zh_font, stroke_width=2, stroke_fill=(255, 255, 255, 220))
            y += 58
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
                "x_ratio": float(scene.get("video_progress_start_ratio", 0.0)),
                "x_end_ratio": float(scene.get("video_progress_end_ratio", 0.0)),
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
                overlay_path = Path(str(asset.get("scene_image_path")))
            else:
                overlay_path = asset_dir / f"fg_{index}.png"
                self._create_foreground_asset(str(overlay_path), subject, palette)
            overlays.append({
                "path": str(overlay_path),
                "start": max(float(event.get("start", 0.0)), 0.0),
                "end": min(float(duration), max(float(event.get("start", 0.0)) + max(float(event.get("duration", 0.4)), 0.25) + 1.0, 0.45)),
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
            return "0", "900-h"
        if animation == "global_progress_marker":
            bar_left = 90
            bar_width = 1740
            end_time = max(float(overlay.get("end", start + 0.3)), start + 0.3)
            return f"if(lt(t,{end_time:.2f}),{bar_left}+({bar_width})*(t-{start:.2f})/{max(end_time-start,0.3):.3f}-w/2,{bar_left + bar_width}-w/2)", "1018"
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
                return max(len(audio) / 1000.0, 1.0)
            except Exception:
                provider = "dashscope_cosyvoice"
                voice = self._normalize_tts_voice(provider, voice)

        if provider == "dashscope_cosyvoice":
            try:
                model = self.tts_model or "cosyvoice-v3-plus"
                synthesizer = SpeechSynthesizer(model=model, voice=voice)
                audio_bytes = synthesizer.call(text)
                with open(save_path, 'wb') as file:
                    file.write(audio_bytes)
                audio = AudioSegment.from_file(save_path)
                if not self._audio_has_signal(audio):
                    raise RuntimeError("CosyVoice returned silent audio")
                if rate != "+0%":
                    factor = 1.0 + (float(rate.strip('%')) / 100.0)
                    factor = max(0.7, min(1.3, factor))
                    audio = audio._spawn(audio.raw_data, overrides={"frame_rate": int(audio.frame_rate * factor)}).set_frame_rate(audio.frame_rate)
                    audio.export(save_path, format="mp3")
                return max(len(audio) / 1000.0, 1.0)
            except Exception:
                provider = "dashscope_sambert"
                voice = "sambert-zhiming-v1"

        if provider == "edge_tts":
            try:
                import edge_tts
                asyncio_run = __import__("asyncio").run
                async def _run_edge_fallback():
                    communicate = edge_tts.Communicate(text=text, voice=voice or "zh-CN-YunjianNeural", rate=rate)
                    await communicate.save(save_path)
                asyncio_run(_run_edge_fallback())
                audio = AudioSegment.from_file(save_path)
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
                if not self._audio_has_signal(audio):
                    raise RuntimeError('Sambert returned silent audio')
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
            if not self._audio_has_signal(audio):
                raise RuntimeError('Generic TTS returned silent audio')
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
                "zoom": (base_zoom, 1.1, 1.18 if scene_duration > 3.2 else 1.14),
                "x": (self._clamp_ratio(anchor_x - 0.05), anchor_x, self._clamp_ratio(anchor_x + 0.03)),
                "y": (anchor_y + 0.03, anchor_y, anchor_y - 0.02),
            },
            "pull_out_soft": {
                "zoom": (1.16, 1.08, 1.0),
                "x": (anchor_x, self._clamp_ratio(anchor_x - 0.04), self._clamp_ratio(anchor_x + 0.03)),
                "y": (anchor_y, anchor_y - 0.02, anchor_y + 0.02),
            },
            "micro_pan_left": {
                "zoom": (1.06, 1.1, 1.14),
                "x": (self._clamp_ratio(anchor_x + 0.18), self._clamp_ratio(anchor_x + 0.07), self._clamp_ratio(anchor_x - 0.05)),
                "y": (anchor_y, anchor_y - 0.012, anchor_y),
            },
            "micro_pan_right": {
                "zoom": (1.06, 1.1, 1.14),
                "x": (self._clamp_ratio(anchor_x - 0.18), self._clamp_ratio(anchor_x - 0.07), self._clamp_ratio(anchor_x + 0.05)),
                "y": (anchor_y, anchor_y + 0.012, anchor_y),
            },
            "push_left_focus": {
                "zoom": (1.04, 1.14, 1.22 if scene_duration > 3.0 else 1.18),
                "x": (self._clamp_ratio(anchor_x - 0.16), self._clamp_ratio(anchor_x - 0.07), anchor_x),
                "y": (anchor_y + 0.03, anchor_y, self._clamp_ratio(anchor_y - 0.04)),
            },
            "push_right_focus": {
                "zoom": (1.04, 1.14, 1.22 if scene_duration > 3.0 else 1.18),
                "x": (self._clamp_ratio(anchor_x + 0.16), self._clamp_ratio(anchor_x + 0.07), anchor_x),
                "y": (anchor_y + 0.03, anchor_y, self._clamp_ratio(anchor_y - 0.04)),
            },
            "hold_then_push": {
                "zoom": (1.0, 1.02, 1.16),
                "x": (anchor_x, self._clamp_ratio(anchor_x - 0.02), self._clamp_ratio(anchor_x + 0.03)),
                "y": (anchor_y, anchor_y, self._clamp_ratio(anchor_y - 0.03)),
            },
        }
        return {"preset": preset, **spec_map.get(preset, spec_map["static"])}

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
        for _, duration in audio_segments:
            timeline.append({"video_duration": round(max(float(duration or 0.0), 0.3), 2)})
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
        required_duration = total_audio_duration + 0.02
        if total_video_duration < required_duration:
            timeline[-1]["video_duration"] = round(timeline[-1]["video_duration"] + (required_duration - total_video_duration), 2)
        return timeline

    def _attach_scene_timing_metadata(self, storyboards: list[dict], timeline: list[dict], audio_segments=None):
        elapsed = 0.0
        for index, scene in enumerate(storyboards):
            segment = timeline[index] if index < len(timeline) else {"video_duration": 2.0}
            scene_duration = float(segment.get("video_duration", 2.0))
            audio_duration = 0.0
            if audio_segments and index < len(audio_segments):
                audio_duration = float(audio_segments[index][1] or 0.0)
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
            zoom_expr = self._piecewise_expr(*spec["zoom"], frames)
            x_progress = self._piecewise_expr(*spec["x"], frames)
            y_progress = self._piecewise_expr(*spec["y"], frames)
            x_expr = f"(iw-iw/zoom)*({x_progress})"
            y_expr = f"(ih-ih/zoom)*({y_progress})"
            filter_expr = (
                "scale=2400:1350:force_original_aspect_ratio=increase,"
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
        for audio_path, _ in audio_segments:
            combined += AudioSegment.from_file(audio_path)
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
        cmd.extend([
            "-filter_complex",
            f"{''.join(f'[{index}:v]' for index in range(len(clip_paths)))}concat=n={len(clip_paths)}:v=1:a=0[vout]",
            "-map",
            "[vout]",
            "-c:v",
            "libx264",
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
