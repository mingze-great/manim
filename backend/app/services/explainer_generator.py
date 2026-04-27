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
        normalized_count = max(3, min(int(storyboard_count or 6), 10))
        hook_mode = str(opening_hook_mode or "hook_question").strip() or "hook_question"
        style_key = str(visual_style_key or "deep_blue_emotional").strip() or "deep_blue_emotional"
        target_duration = self._resolve_target_duration(source_text, normalized_count, target_duration)
        script_data = self._generate_script(source_text, normalized_count, hook_mode, style_key, target_duration)
        title = str(script_data.get("title") or self._fallback_title(source_text)).strip()
        storyboards = []
        for index, scene in enumerate(script_data.get("storyboards") or [], start=1):
            storyboards.append(self._normalize_scene(scene, index, title, normalized_count, hook_mode))
        if storyboards:
            storyboards[0] = self._strengthen_first_scene(storyboards[0], title)
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
        engine_storyboards = self._to_engine_storyboards(script_bundle["storyboards"], script_bundle["title"], {**script_bundle["generation_flags"], "aspect_ratio": aspect_ratio})
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
        engine_storyboards = self._to_engine_storyboards(storyboards, topic, {**(generation_flags or {}), "aspect_ratio": aspect_ratio})
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
        engine_storyboards = self._to_engine_storyboards(storyboards, topic, {**(generation_flags or {}), "aspect_ratio": aspect_ratio})
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
        asset = {
            **asset,
            "image_path": asset.get("scene_image_path") or asset.get("image_path"),
            "image_url": asset.get("scene_image_url") or asset.get("image_url"),
            "image_source": asset.get("scene_image_source") or asset.get("image_source"),
            "model_used": asset.get("scene_image_model_used") or asset.get("model_used"),
        }
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
            f'请为主题或原始文案“{source_text}”生成一个中文高留存讲解型视频脚本。'
            f'总共生成 {storyboard_count} 个分镜，目标总时长约 {target_duration} 秒。'
            '要求：前3秒必须抓人；开头第一句必须像真实短视频爆款开场，先打中痛点再抛出反差；每镜头只表达一个点；文案要像短视频口播；字幕要短句；结尾必须有收束或拔高。'
            f'开头模式：{hook_mode}。视觉风格：{style_key}。'
            '首幕禁止空泛表达，禁止“今天聊聊”“很多人都这样”这类弱开场。首幕字幕必须在12字内，最好带反差、提问或情绪刺点。'
            '必须返回 JSON，不要输出解释。结构如下：'
            '{"title":"视频标题","hook_title":"开头主标题","hook_subtitle":"开头副标题","hook_conflict_point":"冲突点","ending_payoff":"结尾收束句","storyboards":[{"scene_title":"第一幕","hook_level":"high","narration_text":"配音文案","subtitle_text":"字幕短句","visual_description":"画面描述","camera_motion":"slow_zoom_in","transition_type":"fade","emotion_tone":"tense","duration":3.0,"attention_goal":"hook","punch_phrase":"击中句","beat_type":"hook","keywords":["关键词1","关键词2"]}]}'
        )
        try:
            response = self.engine._chat_completion(
                messages=[
                    {"role": "system", "content": "你是擅长中文高留存讲解视频的短视频编导，擅长输出高节奏、强钩子的分镜 JSON。"},
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
        middle_lines = [
            "你怕气氛变僵，所以总是先忍。",
            "你把别人的感受排前面，自己的情绪却没人接住。",
            "你越会体谅别人，别人越容易默认你没事。",
            "委屈攒久了，最后伤到的只会是你自己。",
            "真正要改的，不是脾气，是你总把自己放最后。",
            "你不是脆弱，你只是太久没站在自己这边了。",
        ]
        visual_lines = [
            "一个人站在画面中央，肩膀微缩，周围留白很大，压抑感明显。",
            "两个人在对话，一方欲言又止，空气像被按住一样僵住。",
            "主人公把别人推到前景中央，自己被挤到角落里，情绪被忽略。",
            "表面上还在微笑配合，胸口却像压着一块石头。",
            "主人公慢慢站直，看向前方，情绪从委屈转向清醒。",
            "画面里的人终于把手收回自己胸前，像是在重新站回自己这边。",
        ]
        storyboards = []
        for index in range(1, storyboard_count + 1):
            beat_type = "hook" if index == 1 else "payoff" if index == storyboard_count else "expand"
            middle_line = middle_lines[(index - 2) % len(middle_lines)] if 1 < index < storyboard_count else ""
            visual_line = visual_lines[(index - 1) % len(visual_lines)]
            subtitle = hook_phrase if index == 1 else payoff_phrase if index == storyboard_count else middle_line
            narration = (
                self._first_hook_narration(topic) if index == 1
                else f"{payoff_phrase}。你真正要做的，不是继续忍，而是把自己放回重要位置。" if index == storyboard_count
                else middle_line
            )
            storyboards.append({
                "scene_title": f"第{index}幕",
                "hook_level": "high" if index == 1 else "medium",
                "narration_text": narration,
                "subtitle_text": subtitle,
                "visual_description": visual_line,
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
            "hook_title": self._first_hook_phrase(topic),
            "hook_subtitle": "你总在先委屈自己",
            "hook_conflict_point": topic,
            "ending_payoff": f"这就是{topic}真正值得记住的一点。",
            "storyboards": storyboards,
        }

    def _resolve_target_duration(self, source_text: str, storyboard_count: int, target_duration: int | None):
        if target_duration is not None:
            return max(12, min(int(target_duration), 180))
        text = re.sub(r"\s+", "", str(source_text or ""))
        estimated_by_text = max(16, min(len(text) // 6, 90)) if text else 0
        estimated_by_scenes = storyboard_count * 4
        return max(18, min(max(estimated_by_text, estimated_by_scenes), 90))

    def _strengthen_first_scene(self, scene: dict, title: str):
        boosted = dict(scene)
        hook_phrase = self._first_hook_phrase(title)
        hook_narration = self._first_hook_narration(title)
        boosted["hook_level"] = "high"
        boosted["beat_type"] = "hook"
        boosted["attention_goal"] = "hook"
        boosted["energy_level"] = "high"
        boosted["duration"] = min(max(float(boosted.get("duration") or 0), 2.4), 2.8)
        subtitle_text = str(boosted.get("subtitle_text") or "").strip()
        if not subtitle_text or len(subtitle_text) > 16 or "第1" in subtitle_text:
            boosted["subtitle_text"] = hook_phrase
        narration_text = str(boosted.get("narration_text") or "").strip()
        if not narration_text or len(narration_text) < 18 or "很多人" in narration_text[:8]:
            boosted["narration_text"] = hook_narration
        punch_phrase = str(boosted.get("punch_phrase") or "").strip()
        if not punch_phrase or len(punch_phrase) > 16:
            boosted["punch_phrase"] = hook_phrase
        return boosted

    def _normalize_scene(self, scene: dict, index: int, title: str, total: int, hook_mode: str):
        beat_type = str(scene.get("beat_type") or ("hook" if index == 1 else "payoff" if index >= total else "expand")).strip().lower()
        attention_goal = str(scene.get("attention_goal") or beat_type).strip().lower()
        subtitle_text = str(scene.get("subtitle_text") or scene.get("narration_text") or scene.get("narration") or "").strip()
        narration_text = str(scene.get("narration_text") or scene.get("narration") or subtitle_text).strip()
        narration_text = self._compress_scene_narration(narration_text, index, total, title)
        subtitle_text = narration_text
        camera_motion = self._stable_camera_motion(scene, index)
        duration = float(scene.get("duration") or 2.6)
        duration = max(1.8, min(duration, 2.8))
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
            subtitle_text = narration
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
                "subtitle_lines": [{"text": part} for part in self._subtitle_segments_from_text(narration)],
                "emphasis_beats": [scene.get("punch_phrase") or subtitle_text[:16]],
                "foreground_subjects": [],
                "foreground_events": [],
                "scene_image_mode": "full_frame",
                "scene_image_aspect_ratio": generation_flags.get("aspect_ratio") or "16:9",
            }
            mapped_scene["background_prompt"] = self.engine._background_prompt_for_scene(mapped_scene, topic, index)
            mapped_scene["scene_image_prompt"] = self._scene_image_prompt_for_scene(scene, topic, total, generation_flags)
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
        aspect_ratio = str(generation_flags.get("aspect_ratio") or "16:9")
        visual = self._sanitize_image_instruction_text(str(scene.get("visual_description") or topic))
        emotion = str(scene.get("emotion_tone") or "calm")
        beat = str(scene.get("beat_type") or "expand")
        focus = self._sanitize_image_instruction_text(str(scene.get("punch_phrase") or scene.get("subtitle_text") or topic))
        frame_instruction = "16:9 horizontal full-bleed composition" if aspect_ratio == "16:9" else "9:16 vertical full-bleed composition"
        return (
            "Create a Chinese explainer scene illustration. "
            f"Use a {frame_instruction}. The image must fully cover the frame edge to edge with no black borders, no empty padding, no transparent background, and no letterboxing. "
            "Deep blue background, white line-art characters and props, selective bright accent colors, strong focal hierarchy, editorial composition, readable subtitle-safe bottom area. "
            "Keep one strictly consistent illustration style across all scenes in the same video: same line quality, same character design, same palette, same visual language. "
            "Generate the image according to the meaning of the current storyboard narration and visual description. Match the scene content to the narration, not to a platform or product interface. Use one single continuous scene, not a collage, not a moodboard, not a storyboard grid, not multiple panels, not split screen, not a comic page. "
            "Absolutely do not render any readable text inside the image: no Chinese characters, no English words, no numbers, no labels, no subtitles, no title cards, no posters, no signs, no speech bubbles, no chat bubbles, no handwritten notes, no UI text, no captions. If the model tends to add text, replace it with abstract shapes or leave the area blank. Avoid obvious logos, watermarks, platform symbols, phone app interfaces, dashboards, laptops, tablets, charts, and commercial UI unless the visual description explicitly requires them. "
            f"Style key: {style_key}. Beat type: {beat}. Emotion: {emotion}. Topic: {topic}. Core focus: {focus}. Visual description: {visual}. "
            "The frame should feel emotionally charged, concise, modern, cover the whole screen, and remain visually clean and consistent with the other scenes."
        )

    def _sanitize_image_instruction_text(self, text: str):
        cleaned = str(text or "")
        cleaned = re.sub(r"[‘’'\"]([^‘’'\"]{1,20})[‘’'\"]", "", cleaned)
        cleaned = cleaned.replace("‘", "").replace("’", "").replace('"', "")
        cleaned = re.sub(r"\s+", " ", cleaned).strip(" ，。！？；、")
        return cleaned

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

    def _compress_scene_narration(self, text: str, index: int, total: int, title: str):
        raw = re.sub(r"\s+", " ", str(text or "")).strip()
        if not raw:
            return self._first_hook_narration(title) if index == 1 else f"{title[:10]}，先别再往心里压。"
        max_len = 20 if index == 1 else 22
        if len(raw) <= max_len:
            return raw
        clauses = [item.strip() for item in re.split(r"(?<=[，。！？!?；;])\s*", raw) if item.strip()]
        compact = ""
        for clause in clauses:
            if len(compact + clause) > max_len and compact:
                break
            compact += clause
        compact = compact or raw[:max_len]
        return compact.rstrip("，。！？；;、,")

    def _duration_range_from_scene(self, scene: dict):
        duration = float(scene.get("duration") or 3.5)
        if duration <= 3.0:
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

    def _stable_camera_motion(self, scene: dict, index: int):
        raw = str(scene.get("camera_motion") or scene.get("motion_preset") or "").strip().lower()
        if raw == "slow_zoom_out":
            return "slow_zoom_out"
        if raw in {"pan_left", "pan_right", "parallax_light", "fade", ""}:
            return "slow_zoom_in" if index % 2 else "slow_zoom_out"
        return "slow_zoom_in"

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
            assets, flags = self.engine.generate_images(
                storyboards,
                aspect_ratio,
                project_id,
                progress_callback,
                background_image_path,
                style_reference_image_path,
                style_reference_notes,
            )
            normalized_assets = []
            ai_scene_count = 0
            fallback_scene_count = 0
            for asset in assets or []:
                clone = dict(asset)
                scene_image_path = clone.get("scene_image_path")
                scene_image_url = clone.get("scene_image_url")
                scene_image_source = clone.get("scene_image_source")
                if scene_image_path:
                    clone["image_path"] = scene_image_path
                if scene_image_url:
                    clone["image_url"] = scene_image_url
                if scene_image_source:
                    clone["image_source"] = scene_image_source
                if clone.get("scene_image_model_used"):
                    clone["model_used"] = clone.get("scene_image_model_used")
                if clone.get("image_source") == "model":
                    ai_scene_count += 1
                else:
                    fallback_scene_count += 1
                normalized_assets.append(clone)
            normalized_flags = {
                **(flags or {}),
                "image_provider_status": "scene_images" if ai_scene_count else "scene_fallback",
                "dynamic_video_mode": "per_scene_ai_image_motion",
                "background_mode": "per_scene_images",
                "scene_ai_image_count": ai_scene_count,
                "scene_fallback_count": fallback_scene_count,
            }
            return normalized_assets, normalized_flags
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
        self.background_dir.mkdir(parents=True, exist_ok=True)
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
        if "懂事" in clean and "委屈" in clean:
            return "懂事，怎么成了你的软肋？"
        if clean:
            return f"{clean[:10]}，为什么总先伤你自己？"
        return "你越懂事 越容易委屈自己"

    def _first_hook_narration(self, topic: str):
        clean = str(topic or "").strip()
        if "懂事" in clean and "委屈" in clean:
            return "越懂事的人，越习惯先委屈自己。最难受时，你还先体谅别人。"
        hook_phrase = self._first_hook_phrase(topic)
        return f"{hook_phrase}。你总把自己放到最后。"

    def _payoff_phrase(self, topic: str):
        clean = str(topic or "").strip()
        return f"{clean[:10]}的关键，不是忍下去，而是看见自己" if clean else "真正的改变，从把自己放回重要位置开始"
