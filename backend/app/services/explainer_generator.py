import json
import re
import tempfile
from pathlib import Path
from typing import Optional

from PIL import Image, ImageDraw

from app.services.stickman_generator_v2 import StickmanGenerator as StickmanGeneratorV2


class ExplainerGenerator:
    def __init__(self):
        self.engine = StickmanGeneratorV2()
        self.background_dir = Path(__file__).resolve().parents[2] / "uploads" / "explainer_backgrounds"
        self.background_dir.mkdir(parents=True, exist_ok=True)

    def generate_storyboard_data(
        self,
        source_text: str,
        storyboard_count: int,
        opening_hook_mode: str | None = None,
        visual_style_key: str | None = None,
        target_duration: int | None = None,
    ):
        normalized_count = max(8, min(int(storyboard_count or 10), 15))
        hook_mode = str(opening_hook_mode or "hook_question").strip() or "hook_question"
        style_key = str(visual_style_key or "deep_blue_emotional").strip() or "deep_blue_emotional"
        target_duration = max(25, min(int(target_duration or 45), 180))
        script_data = self._generate_script(source_text, normalized_count, hook_mode, style_key, target_duration)
        title = str(script_data.get("title") or self._fallback_title(source_text)).strip()
        storyboards = []
        for index, scene in enumerate(script_data.get("storyboards") or [], start=1):
            storyboards.append(self._normalize_scene(scene, index, title, normalized_count, hook_mode))
        return {
            "title": title,
            "script": "\n".join(scene.get("narration_text") or "" for scene in storyboards),
            "storyboards": storyboards,
            "generation_flags": {
                "visual_style_key": style_key,
                "opening_hook_mode": hook_mode,
                "scene_count": len(storyboards),
                "target_duration": target_duration,
                "has_voice": True,
                "has_music": False,
                "subtitle_mode": "short_punch",
                "hook_title": script_data.get("hook_title") or title,
                "hook_subtitle": script_data.get("hook_subtitle") or (storyboards[0].get("subtitle_text") if storyboards else ""),
                "hook_conflict_point": script_data.get("hook_conflict_point") or "",
                "ending_payoff": script_data.get("ending_payoff") or (storyboards[-1].get("punch_phrase") if storyboards else ""),
            },
        }

    def generate(
        self,
        source_text: str,
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
        opening_hook_mode: str | None = None,
        visual_style_key: str | None = None,
        target_duration: int | None = None,
    ):
        def report(progress: int, message: str):
            if progress_callback:
                progress_callback(progress, message)

        report(5, "开始生成讲解型视频")
        script_bundle = self.generate_storyboard_data(source_text, storyboard_count, opening_hook_mode, visual_style_key, target_duration)
        report(20, "脚本生成完成")
        engine_storyboards = self._to_engine_storyboards(script_bundle["storyboards"], script_bundle["title"], script_bundle["generation_flags"])
        effective_background_path = background_image_path or self._ensure_default_background(script_bundle["title"], script_bundle["generation_flags"])
        with tempfile.TemporaryDirectory(prefix="explainer_") as _:
            image_assets, image_flags = self._generate_engine_images(
                engine_storyboards,
                aspect_ratio,
                None,
                report,
                effective_background_path,
                style_reference_image_path,
                style_reference_notes,
            )
            result = self._compose_engine_without_section_panels(
                script_bundle["title"],
                engine_storyboards,
                image_assets,
                report,
                voice_source,
                voice_file_path,
                tts_provider,
                tts_voice,
                tts_rate,
            )
        merged_flags = {**script_bundle["generation_flags"], **(image_flags or {}), **(result.get("generation_flags") or {}), "module_type": "explainer"}
        synced_storyboards = self._sync_storyboards_with_assets(script_bundle["storyboards"], image_assets)
        report(100, "讲解型视频生成完成")
        return {
            "title": script_bundle["title"],
            "script": result.get("script") or script_bundle["script"],
            "storyboards": synced_storyboards,
            "image_assets": image_assets,
            "generation_flags": merged_flags,
            "duration": result.get("duration") or 0,
            "video_path": result["video_path"],
        }

    def generate_images(
        self,
        source_text: str,
        storyboards: list[dict],
        aspect_ratio: str,
        project_id: Optional[int] = None,
        progress_callback=None,
        background_image_path: Optional[str] = None,
        style_reference_image_path: Optional[str] = None,
        style_reference_notes: Optional[str] = None,
        generation_flags: Optional[dict] = None,
    ):
        topic = self._fallback_title(source_text)
        engine_storyboards = self._to_engine_storyboards(storyboards, topic, generation_flags or {})
        effective_background_path = background_image_path or self._ensure_default_background(topic, generation_flags or {})
        assets, flags = self._generate_engine_images(
            engine_storyboards,
            aspect_ratio,
            project_id,
            progress_callback,
            effective_background_path,
            style_reference_image_path,
            style_reference_notes,
        )
        synced_storyboards = self._sync_storyboards_with_assets(storyboards, assets)
        merged_flags = {**(generation_flags or {}), **flags, "module_type": "explainer"}
        return synced_storyboards, assets, merged_flags

    def regenerate_single_image(
        self,
        source_text: str,
        storyboards: list[dict],
        scene_index: int,
        aspect_ratio: str,
        project_id: Optional[int] = None,
        prompt_override: Optional[str] = None,
        background_image_path: Optional[str] = None,
        style_reference_image_path: Optional[str] = None,
        style_reference_notes: Optional[str] = None,
        generation_flags: Optional[dict] = None,
    ):
        topic = self._fallback_title(source_text)
        engine_storyboards = self._to_engine_storyboards(storyboards, topic, generation_flags or {})
        effective_background_path = background_image_path or self._ensure_default_background(topic, generation_flags or {})
        asset, used_fallback = self.engine.regenerate_single_image(
            engine_storyboards[scene_index],
            scene_index + 1,
            aspect_ratio,
            project_id,
            prompt_override,
            effective_background_path,
            style_reference_image_path,
            style_reference_notes,
        )
        scene = dict(storyboards[scene_index])
        scene["image_url"] = asset.get("scene_image_url") or asset.get("image_url")
        scene["visual_prompt"] = asset.get("prompt")
        return scene, asset, used_fallback

    def compose_from_assets(
        self,
        source_text: str,
        storyboards: list[dict],
        image_assets: list[dict],
        progress_callback=None,
        voice_source: str = "ai",
        voice_file_path: str | None = None,
        tts_provider: str | None = None,
        tts_voice: str | None = None,
        tts_rate: str | None = None,
        generation_flags: Optional[dict] = None,
    ):
        topic = self._fallback_title(source_text)
        engine_storyboards = self._to_engine_storyboards(storyboards, topic, generation_flags or {})
        result = self._compose_engine_without_section_panels(
            topic,
            engine_storyboards,
            image_assets,
            progress_callback,
            voice_source,
            voice_file_path,
            tts_provider,
            tts_voice,
            tts_rate,
        )
        return {
            **result,
            "storyboards": self._sync_storyboards_with_assets(storyboards, image_assets),
            "generation_flags": {**(generation_flags or {}), **(result.get("generation_flags") or {}), "module_type": "explainer"},
        }

    def _generate_script(self, source_text: str, storyboard_count: int, hook_mode: str, style_key: str, target_duration: int):
        prompt = (
            f'请为主题或原始文案“{source_text}”生成一个中文抖音风格讲解型视频脚本。'
            f'总共生成 {storyboard_count} 个分镜，目标总时长约 {target_duration} 秒。'
            '要求：前3秒必须抓人；每镜头只表达一个点；文案要像短视频口播；字幕要短句；结尾必须有收束或拔高。'
            f'开头模式：{hook_mode}。视觉风格：{style_key}。'
            '必须返回 JSON，不要输出解释。结构如下：'
            '{"title":"视频标题","hook_title":"开头主标题","hook_subtitle":"开头副标题","hook_conflict_point":"冲突点","ending_payoff":"结尾收束句","storyboards":[{"scene_title":"第一幕","hook_level":"high","narration_text":"配音文案","subtitle_text":"字幕短句","visual_description":"画面描述","camera_motion":"slow_zoom_in","transition_type":"fade","emotion_tone":"tense","duration":3.0,"attention_goal":"hook","punch_phrase":"击中句","beat_type":"hook","keywords":["关键词1","关键词2"]}]}'
        )
        try:
            response = self.engine._chat_completion(
                messages=[
                    {"role": "system", "content": "你是擅长抖音爆款讲解视频的中文短视频编导，擅长输出高留存、高节奏的分镜 JSON。"},
                    {"role": "user", "content": prompt},
                ],
                temperature=0.85,
                max_tokens=3200,
            )
            content = response.choices[0].message.content or ""
            return self._extract_script_json(content, source_text, storyboard_count, hook_mode)
        except Exception:
            return self._fallback_script(source_text, storyboard_count, hook_mode)

    def _extract_script_json(self, content: str, source_text: str, storyboard_count: int, hook_mode: str):
        match = re.search(r"\{[\s\S]*\}", content)
        if not match:
            return self._fallback_script(source_text, storyboard_count, hook_mode)
        try:
            data = json.loads(match.group())
        except json.JSONDecodeError:
            return self._fallback_script(source_text, storyboard_count, hook_mode)
        storyboards = data.get("storyboards") or []
        if not isinstance(storyboards, list) or not storyboards:
            return self._fallback_script(source_text, storyboard_count, hook_mode)
        return {
            "title": data.get("title") or self._fallback_title(source_text),
            "hook_title": data.get("hook_title") or data.get("title") or self._fallback_title(source_text),
            "hook_subtitle": data.get("hook_subtitle") or "",
            "hook_conflict_point": data.get("hook_conflict_point") or "",
            "ending_payoff": data.get("ending_payoff") or "",
            "storyboards": storyboards[:storyboard_count],
        }

    def _fallback_script(self, source_text: str, storyboard_count: int, hook_mode: str):
        topic = self._fallback_title(source_text)
        hook_phrase = self._first_hook_phrase(topic)
        payoff_phrase = self._payoff_phrase(topic)
        storyboards = []
        for index in range(1, storyboard_count + 1):
            beat_type = "hook" if index == 1 else "payoff" if index == storyboard_count else "expand"
            subtitle = hook_phrase if index == 1 else payoff_phrase if index == storyboard_count else f"{topic}第{index}点"
            narration = (
                f"{hook_phrase}，很多人不是不会表达，而是太习惯先压住自己。" if index == 1
                else f"{payoff_phrase}。你真正要做的，不是继续忍，而是把自己放回重要位置。" if index == storyboard_count
                else f"{topic}的第{index}个关键点。"
            )
            storyboards.append({
                "scene_title": f"第{index}幕",
                "hook_level": "high" if index == 1 else "medium",
                "narration_text": narration,
                "subtitle_text": subtitle,
                "visual_description": f"围绕{topic}的第{index}个讲解画面，构图清晰，适合字幕叠加。",
                "camera_motion": "slow_zoom_in" if index % 2 else "pan_right",
                "transition_type": "fade",
                "emotion_tone": "tense" if index == 1 else "calm",
                "duration": 3.5,
                "attention_goal": beat_type,
                "punch_phrase": subtitle,
                "beat_type": beat_type,
                "keywords": [topic],
                "opening_template_key": hook_mode if index == 1 else "standard_scene",
            })
        return {
            "title": topic,
            "hook_title": topic,
            "hook_subtitle": "前3秒抓住注意力",
            "hook_conflict_point": topic,
            "ending_payoff": f"这就是{topic}真正值得记住的一点。",
            "storyboards": storyboards,
        }

    def _normalize_scene(self, scene: dict, index: int, title: str, total: int, hook_mode: str):
        beat_type = str(scene.get("beat_type") or ("hook" if index == 1 else "payoff" if index >= total else "expand")).strip().lower()
        attention_goal = str(scene.get("attention_goal") or beat_type).strip().lower()
        subtitle_text = str(scene.get("subtitle_text") or scene.get("narration_text") or scene.get("narration") or "").strip()
        narration_text = str(scene.get("narration_text") or scene.get("narration") or subtitle_text).strip()
        camera_motion = str(scene.get("camera_motion") or scene.get("motion_preset") or ("slow_zoom_in" if index % 2 else "pan_right")).strip()
        duration = float(scene.get("duration") or 3.5)
        duration = max(2.0, min(duration, 5.5))
        normalized = {
            "scene_index": index,
            "scene_title": str(scene.get("scene_title") or f"第{index}幕").strip(),
            "hook_level": str(scene.get("hook_level") or ("high" if index == 1 else "medium")).strip().lower(),
            "narration_text": narration_text,
            "subtitle_text": subtitle_text,
            "visual_description": str(scene.get("visual_description") or scene.get("scene_description") or f"围绕{title}的第{index}个讲解画面").strip(),
            "camera_motion": camera_motion,
            "transition_type": str(scene.get("transition_type") or "fade").strip().lower(),
            "emotion_tone": str(scene.get("emotion_tone") or ("tense" if index == 1 else "calm")).strip().lower(),
            "duration": duration,
            "image_url": scene.get("image_url"),
            "attention_goal": attention_goal,
            "punch_phrase": str(scene.get("punch_phrase") or (self._first_hook_phrase(title) if index == 1 else subtitle_text[:20])).strip(),
            "energy_level": str(scene.get("energy_level") or ("high" if index <= 2 else "medium" if index < total else "high")).strip().lower(),
            "beat_type": beat_type,
            "keywords": scene.get("keywords") or [title[:8]],
            "opening_template_key": str(scene.get("opening_template_key") or (hook_mode if index == 1 else "standard_scene")),
        }
        return normalized

    def _to_engine_storyboards(self, storyboards: list[dict], topic: str, generation_flags: dict):
        opening_template_key = str(generation_flags.get("opening_hook_mode") or generation_flags.get("opening_template_key") or "hook_question")
        mapped = []
        total = len(storyboards)
        for index, scene in enumerate(storyboards, start=1):
            narration = str(scene.get("narration_text") or scene.get("subtitle_text") or "").strip()
            subtitle_text = str(scene.get("subtitle_text") or narration).strip()
            mapped_scene = {
                "scene_id": index,
                "scene_title": scene.get("scene_title") or f"第{index}幕",
                "scene_description": scene.get("visual_description") or f"围绕{topic}的第{index}个画面",
                "narration": narration,
                "scene_narration": narration,
                "keywords": scene.get("keywords") or [topic],
                "visual_focus": (scene.get("keywords") or [topic])[0],
                "duration_range": self._duration_range_from_scene(scene),
                "camera_type": self._camera_type_from_motion(str(scene.get("camera_motion") or "")),
                "character_action": self._action_from_emotion(str(scene.get("emotion_tone") or "")),
                "layout_hint": self._layout_hint_from_attention(str(scene.get("attention_goal") or "")),
                "motion_preset": self._motion_preset_from_camera_motion(str(scene.get("camera_motion") or "")),
                "transition_type": str(scene.get("transition_type") or "fade"),
                "opening_template_key": opening_template_key if index == 1 else "standard_scene",
                "camera_track": "fast_intro" if index <= 2 else "steady_explain",
                "scene_energy": scene.get("energy_level") or ("high" if index <= 2 else "medium"),
                "performance_template": scene.get("beat_type") or "expand",
                "background_group": f"stage_{1 + ((index - 1) // 2)}",
                "palette_mode": "classic_stickman",
                "foreground_density": "dense" if index <= 2 else "medium",
                "subtitle_lines": [{"text": part} for part in self._subtitle_segments_from_text(subtitle_text)],
                "emphasis_beats": [scene.get("punch_phrase") or subtitle_text[:16]],
            }
            mapped_scene["background_prompt"] = self.engine._background_prompt_for_scene(mapped_scene, topic, index)
            mapped_scene["scene_image_prompt"] = self._scene_image_prompt_for_scene(scene, topic, total, generation_flags)
            mapped_scene["foreground_subjects"] = self._foreground_subjects_for_scene(scene, index, total)
            mapped_scene["foreground_events"] = self._foreground_events_for_scene(scene, index, total)
            mapped.append(mapped_scene)
        return mapped

    def _foreground_subjects_for_scene(self, scene: dict, index: int, total: int):
        focus = str(scene.get("punch_phrase") or scene.get("subtitle_text") or scene.get("scene_title") or "重点")[:14]
        subjects = [
            {"key": "hero_figure", "kind": "scene_illustration", "label": focus},
            {"key": "hook_text", "kind": "keyword_text", "label": focus},
        ]
        beat_type = str(scene.get("beat_type") or "expand")
        if index == 1 or beat_type == "hook":
            subjects.append({"key": "focus_ring", "kind": "focus_ring", "label": "focus"})
            subjects.append({"key": "host_marker", "kind": "host_marker", "label": "讲"})
        elif beat_type == "payoff" or index == total:
            subjects.append({"key": "underline", "kind": "underline", "label": "收束"})
        return subjects

    def _foreground_events_for_scene(self, scene: dict, index: int, total: int):
        beat_type = str(scene.get("beat_type") or "expand")
        if index == 1 or beat_type == "hook":
            return [
                {"target": "hook_text", "animation": "center_zoom_in", "start": 0.0, "duration": 1.2, "x_ratio": 0.5, "y_ratio": 0.20},
                {"target": "hero_figure", "animation": "center_bounce", "start": 0.18, "duration": 1.0, "x_ratio": 0.5, "y_ratio": 0.46},
                {"target": "focus_ring", "animation": "center_fade", "start": 0.28, "duration": 0.8, "x_ratio": 0.5, "y_ratio": 0.46},
                {"target": "host_marker", "animation": "slide_up_fade", "start": 0.52, "duration": 0.8, "x_ratio": 0.20, "y_ratio": 0.48},
            ]
        if beat_type == "payoff" or index == total:
            return [
                {"target": "hero_figure", "animation": "center_fade", "start": 0.0, "duration": 1.2, "x_ratio": 0.5, "y_ratio": 0.43},
                {"target": "hook_text", "animation": "center_slide_up", "start": 0.15, "duration": 1.0, "x_ratio": 0.5, "y_ratio": 0.18},
                {"target": "underline", "animation": "center_fade", "start": 0.5, "duration": 0.8, "x_ratio": 0.5, "y_ratio": 0.28},
            ]
        return [
            {"target": "hero_figure", "animation": "center_fade", "start": 0.0, "duration": 1.0, "x_ratio": 0.5, "y_ratio": 0.43},
            {"target": "hook_text", "animation": "center_slide_up", "start": 0.22, "duration": 0.8, "x_ratio": 0.5, "y_ratio": 0.18},
        ]

    def _scene_image_prompt_for_scene(self, scene: dict, topic: str, total: int, generation_flags: dict):
        style_key = str(generation_flags.get("visual_style_key") or "deep_blue_emotional")
        visual = str(scene.get("visual_description") or topic)
        emotion = str(scene.get("emotion_tone") or "calm")
        beat = str(scene.get("beat_type") or "expand")
        focus = str(scene.get("punch_phrase") or scene.get("subtitle_text") or topic)
        return (
            "Create a Chinese short-video explainer scene in a viral Douyin style. "
            "Deep blue background, white line-art characters and props, selective bright accent colors, strong focal hierarchy, editorial composition, readable subtitle-safe bottom area, no baked subtitles, no text inside image. "
            f"Style key: {style_key}. Beat type: {beat}. Emotion: {emotion}. Topic: {topic}. Core focus: {focus}. Visual description: {visual}. "
            "The frame should feel emotionally charged, concise, modern, and optimized for the first-screen attention of a short video."
        )

    def _sync_storyboards_with_assets(self, storyboards: list[dict], image_assets: list[dict]):
        synced = []
        for index, scene in enumerate(storyboards):
            clone = dict(scene)
            asset = image_assets[index] if index < len(image_assets) else {}
            clone["image_url"] = asset.get("scene_image_url") or asset.get("image_url")
            clone["visual_prompt"] = asset.get("prompt")
            synced.append(clone)
        return synced

    def _subtitle_segments_from_text(self, text: str):
        raw = str(text or "").strip()
        if not raw:
            return []
        parts = [item.strip() for item in re.split(r"[，。！？；;]", raw) if item.strip()]
        if not parts:
            return [raw]
        return parts[:2] if len(parts) > 2 and len(raw) < 28 else parts

    def _duration_range_from_scene(self, scene: dict):
        duration = float(scene.get("duration") or 3.5)
        if duration <= 2.5:
            return "2-3"
        if duration <= 4.0:
            return "3-4"
        return "4-5"

    def _camera_type_from_motion(self, camera_motion: str):
        text = camera_motion.lower()
        if "zoom" in text:
            return "close-up"
        if "pan" in text:
            return "medium shot"
        return "wide shot"

    def _action_from_emotion(self, emotion: str):
        text = emotion.lower()
        if text in {"tense", "angry", "sad", "conflicted"}:
            return "raising one hand for emphasis"
        if text in {"warm", "hopeful", "calm"}:
            return "walking while explaining"
        return "pointing to a board"

    def _layout_hint_from_attention(self, attention_goal: str):
        text = attention_goal.lower()
        if text == "hook":
            return "subject centered"
        if text in {"payoff", "summary"}:
            return "subject on right, diagram on left"
        return "subject on left, empty space on right"

    def _motion_preset_from_camera_motion(self, camera_motion: str):
        mapping = {
            "slow_zoom_in": "push_in",
            "slow_zoom_out": "pull_out",
            "pan_left": "pan_left",
            "pan_right": "pan_right",
            "parallax_light": "focus_subject",
            "fade": "focus_subject",
        }
        return mapping.get(camera_motion.lower(), "push_in")

    def _fallback_title(self, source_text: str):
        cleaned = re.sub(r"\s+", " ", str(source_text or "")).strip()
        if not cleaned:
            return "讲解型视频"
        return cleaned.split("\n")[0][:24]

    def _generate_engine_images(self, storyboards, aspect_ratio, project_id=None, progress_callback=None, background_image_path=None, style_reference_image_path=None, style_reference_notes=None):
        original_enabled = getattr(self.engine, "material_library_enabled", False)
        original_library = getattr(self.engine, "material_library", [])
        try:
            self.engine.material_library_enabled = False
            self.engine.material_library = []
            return self.engine.generate_images(
                storyboards,
                aspect_ratio,
                project_id,
                progress_callback,
                background_image_path,
                style_reference_image_path,
                style_reference_notes,
            )
        finally:
            self.engine.material_library_enabled = original_enabled
            self.engine.material_library = original_library

    def _compose_engine_without_section_panels(self, topic, storyboards, image_assets, progress_callback=None, voice_source="ai", voice_file_path=None, tts_provider=None, tts_voice=None, tts_rate=None):
        original = self.engine._attach_section_timing_metadata

        def lightweight_attach(items):
            for item in items or []:
                item.pop("sections_meta", None)
                item.pop("video_progress_start_ratio", None)
                item.pop("video_progress_end_ratio", None)
            return []

        try:
            self.engine._attach_section_timing_metadata = lightweight_attach
            return self.engine.compose_from_assets(topic, storyboards, image_assets, progress_callback, voice_source, voice_file_path, tts_provider, tts_voice, tts_rate)
        finally:
            self.engine._attach_section_timing_metadata = original

    def _ensure_default_background(self, title: str, generation_flags: dict):
        style_key = str(generation_flags.get("visual_style_key") or "deep_blue_emotional")
        file_name = f"explainer_{style_key}.png"
        save_path = self.background_dir / file_name
        if save_path.exists():
            return str(save_path)
        width, height = 1920, 1080
        image = Image.new("RGB", (width, height), (8, 20, 58))
        draw = ImageDraw.Draw(image)
        title_font = self.engine._load_font(54)
        meta_font = self.engine._load_font(28)
        accent = (82, 196, 255) if style_key == "deep_blue_emotional" else (255, 193, 7)
        draw.rectangle((0, int(height * 0.78), width, height), fill=(5, 12, 36))
        draw.ellipse((90, 90, 310, 310), outline=(255, 255, 255), width=4)
        draw.ellipse((width - 360, 110, width - 160, 310), outline=accent, width=4)
        draw.line((180, 180, width - 260, 180), fill=(255, 255, 255), width=2)
        draw.line((120, 720, width - 120, 720), fill=(255, 255, 255), width=3)
        draw.rounded_rectangle((120, 760, width - 120, 950), radius=24, outline=(255, 255, 255), width=2)
        draw.rounded_rectangle((140, 120, 640, 220), radius=18, fill=(255, 255, 255))
        draw.text((180, 142), title[:18], fill=(8, 20, 58), font=title_font)
        draw.text((width - 320, 146), "讲解型视频", fill=(255, 255, 255), font=meta_font)
        image.save(save_path, format="PNG")
        return str(save_path)

    def _first_hook_phrase(self, topic: str):
        clean = str(topic or "").replace("为什么", "").replace("？", "").replace("?", "").strip()
        if clean:
            return f"越{clean[:10]} 越容易委屈自己"
        return "你越懂事 越容易委屈自己"

    def _payoff_phrase(self, topic: str):
        clean = str(topic or "").strip()
        return f"{clean[:10]}的关键，不是忍下去，而是看见自己" if clean else "真正的改变，从把自己放回重要位置开始"
