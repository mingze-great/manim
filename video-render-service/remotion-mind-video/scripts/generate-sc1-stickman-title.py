import hashlib
import json
import os
import re
import shutil
import subprocess
import sys
import time
import urllib.request
from pathlib import Path

from pydub import AudioSegment


PROJECT_ROOT = Path(__file__).resolve().parents[1]
REPO_ROOT = PROJECT_ROOT.parents[1]
MATERIAL_DIR = Path(
    os.getenv(
        "SC1_MATERIAL_LIBRARY_PATH",
        r"C:\Users\Administrator\Documents\Codex\2026-07-13\e-ai-cankao-sucai\outputs"
        if os.name == "nt"
        else "/opt/manim_assets/sc1-outputs",
    )
)
RENDER_SERVICE_URL = os.getenv("AI_VIDEO_RENDER_SERVICE_URL", "http://127.0.0.1:18787").rstrip("/")
PUBLIC_AUDIO_DIR = PROJECT_ROOT / "public" / "generated-audio"
PUBLIC_MATERIAL_DIR = PROJECT_ROOT / "public" / "sc1-materials"
OUTPUT_DIR = REPO_ROOT / "outputs" / "sc1-stickman-workflow"
DEFAULT_TOPIC = "为什么你越努力越焦虑"
DEFAULT_REFERENCE_VIDEO = (
    r"F:\ai\火柴人工作流\SC1全赛道高级版火柴人\20250901-15010d17-fc2d-4eb8-8983-77b4139cf8ea.mov"
    if os.name == "nt"
    else "/opt/manim_assets/sc1-reference/20250901-15010d17-fc2d-4eb8-8983-77b4139cf8ea.mov"
)
REFERENCE_VIDEO = Path(os.getenv("SC1_VOICE_REFERENCE_VIDEO", DEFAULT_REFERENCE_VIDEO))
REFERENCE_AUDIO = Path(os.getenv("SC1_VOICE_REFERENCE_AUDIO", ""))
TTS_ENGINE = os.getenv("SC1_TTS_ENGINE", "indextts2").strip().lower()
INDEXTTS2_REPO_VALUE = os.getenv("SC1_INDEXTTS2_REPO", "").strip()
INDEXTTS2_REPO = Path(INDEXTTS2_REPO_VALUE) if INDEXTTS2_REPO_VALUE else None
INDEXTTS2_MODEL_DIR = os.getenv("SC1_INDEXTTS2_MODEL_DIR", "checkpoints").strip()


def load_env_file() -> None:
    for name in [".env.production", ".env.development", ".env"]:
        path = REPO_ROOT / name
        if not path.exists():
            continue
        for raw in path.read_text(encoding="utf-8", errors="ignore").splitlines():
            line = raw.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            key, value = line.split("=", 1)
            os.environ.setdefault(key.strip(), value.strip().strip('"').strip("'"))


def clean(value: str) -> str:
    return re.sub(r"\s+", " ", str(value or "")).strip()


def material_manifest_path() -> Path:
    if MATERIAL_DIR.is_file():
        return MATERIAL_DIR
    for name in ["materials.generated.json", "materials.json"]:
        candidate = MATERIAL_DIR / name
        if candidate.exists():
            return candidate
    raise FileNotFoundError(f"SC1 material manifest not found under {MATERIAL_DIR}")


def load_materials() -> list[dict]:
    manifest = material_manifest_path()
    payload = json.loads(manifest.read_text(encoding="utf-8-sig", errors="replace"))
    items = payload if isinstance(payload, list) else []
    materials = []
    for item in items:
        file_name = Path(str(item.get("file_name") or item.get("fileName") or "")).name
        if not file_name:
            continue
        parts = []
        for key in [
            "primary_subject",
            "pose_action",
            "scene_context",
            "emotion_primary",
            "emotion_valence",
            "metaphor_meaning",
            "usage_notes",
            "composition",
            "subject_position",
        ]:
            if item.get(key):
                parts.append(str(item.get(key)))
        for key in [
            "props_objects",
            "emotion_secondary",
            "psychology_concepts",
            "applicable_topics",
            "storyboard_roles",
            "style_tags",
            "search_keywords",
        ]:
            values = item.get(key)
            if isinstance(values, list):
                parts.extend(str(value) for value in values if value)
        materials.append(
            {
                "fileName": file_name,
                "searchText": " ".join(parts).lower(),
                "roles": [str(value).lower() for value in item.get("storyboard_roles", []) if value],
            }
        )
    if not materials:
        raise RuntimeError(f"No usable materials in {manifest}")
    return materials


def tokens_for(text: str) -> list[str]:
    source = clean(text).lower()
    tokens: list[str] = re.findall(r"[a-z0-9][a-z0-9_-]{1,}", source)
    concept_map = [
        (["焦虑", "紧张", "不安", "困住"], ["anxiety", "stress", "worry", "panic"]),
        (["努力", "自律", "硬扛", "用力"], ["perfectionism", "over-control", "burnout", "pressure"]),
        (["崩溃", "耗尽", "累", "消耗"], ["burnout", "depleted", "emotional exhaustion"]),
        (["情绪", "逃避", "内耗"], ["emotion", "rumination", "avoidance", "self-soothing"]),
        (["目标", "完成", "掌控"], ["focus", "flow", "control", "growth"]),
        (["边界", "拒绝", "停一下"], ["boundary", "self-compassion", "self-soothing"]),
        (["评委", "标准", "不满意"], ["shame", "spotlight", "perfectionism", "black-white thinking"]),
        (["重新出发", "变强", "修复"], ["growth", "confidence", "repair", "inner strength"]),
    ]
    for needles, additions in concept_map:
        if any(needle in source for needle in needles):
            tokens.extend(additions)
    for phrase in re.findall(r"[\u4e00-\u9fff]{2,}", source):
        tokens.append(phrase)
        if len(phrase) > 4:
            tokens.extend([phrase[:4], phrase[-4:]])
        for size in (2, 3):
            tokens.extend(phrase[index : index + size] for index in range(0, max(0, len(phrase) - size + 1)))
    result = []
    seen = set()
    for token in tokens:
        if token and token not in seen:
            seen.add(token)
            result.append(token)
    return result[:80]


def select_material(materials: list[dict], text: str, scene_index: int, slot: int, selected: set[str]) -> dict:
    role_hints = ["hook", "problem", "cause"] if slot == 0 else ["method", "transition", "result", "summary"]
    best = None
    best_score = -9999.0
    for material in materials:
        file_name = material["fileName"]
        if file_name in selected:
            continue
        corpus = material["searchText"]
        score = 0.0
        for token in tokens_for(text):
            if token in corpus:
                score += min(12.0, 3.0 + len(token))
        score += sum(7.0 for hint in role_hints if hint in corpus or hint in material["roles"])
        digest = hashlib.sha1(f"{text}-{scene_index}-{slot}-{file_name}".encode("utf-8")).hexdigest()
        score += (int(digest[:4], 16) % 100) / 1000
        if score > best_score:
            best = material
            best_score = score
    if best is None:
        best = materials[(scene_index * 2 + slot) % len(materials)]
        best_score = 0.0
    selected.add(best["fileName"])
    return {**best, "score": best_score}


def split_cues(text: str) -> list[str]:
    parts = [item.strip(" ，。！？；：、,.!?:;") for item in re.split(r"(?<=[。！？；!?;.])\s*", text) if item.strip(" ，。！？；：、,.!?:;")]
    if len(parts) >= 2:
        return parts[:3]
    if len(text) <= 24:
        return [text]
    midpoint = len(text) // 2
    split_at = midpoint
    for radius in range(0, min(16, midpoint)):
        for candidate in (midpoint + radius, midpoint - radius):
            if 0 < candidate < len(text) and text[candidate] in "，、；：,;: ":
                split_at = candidate + 1
                break
        if split_at != midpoint:
            break
    return [text[:split_at].strip(" ，。！？；：、,.!?:;"), text[split_at:].strip(" ，。！？；：、,.!?:;")]


def summary_label(text: str, index: int) -> str:
    rules = [
        (["第一反应", "按住", "站队"], "按住第一反应"),
        (["挑战", "脑洞", "答错"], "脑洞题开场"),
        (["行为", "动作", "做法"], "行为性质"),
        (["对象", "谁", "保护"], "对象边界"),
        (["风险", "后果", "影响"], "风险后果"),
        (["规则", "法律", "边界"], "规则边界"),
        (["结论", "答案", "所以"], "结论收束"),
        (["结构", "四层", "拆"], "结构判断"),
        (["焦虑", "困住", "骂自己"], "情绪困住"),
        (["努力", "自律", "用力"], "努力误区"),
        (["忙碌", "逃避", "情绪"], "逃避情绪"),
        (["压力", "评委", "消耗"], "压力来源"),
        (["目标", "掌控感", "完成"], "掌控感"),
        (["停一下", "重新出发", "硬扛"], "重新出发"),
    ]
    for needles, label in rules:
        if any(needle in text for needle in needles):
            return label
    pieces = [item for item in re.split(r"[\s，。！？；：、,.!?:;]+", text) if 2 <= len(item) <= 7]
    return pieces[0] if pieces else ("前情提问" if index == 0 else "后续判断")


def build_scene_texts(title: str) -> list[tuple[str, str]]:
    topic = clean(title) or DEFAULT_TOPIC
    return [
        (
            f"如果你最近总被{topic}困住，先别急着骂自己。真正的问题，可能从来不是你不够努力。",
            "If this keeps trapping you, do not blame yourself first. The real issue may not be effort.",
        ),
        (
            f"很多人一听到{topic}，第一反应就是加倍自律。可越用力，越容易把自己推到崩溃边缘。",
            "Many people try harder first. But pushing harder can move you closer to breaking down.",
        ),
        (
            "第一步，先看你是在解决问题，还是在用忙碌逃避情绪。两者看起来很像，结果完全不同。",
            "Step one: check whether you are solving the problem or escaping emotion through busyness.",
        ),
        (
            "第二步，看压力到底来自现实，还是来自脑子里那个永远不满意的评委。后者最会消耗人。",
            "Step two: see whether pressure comes from reality or from the judge inside your head.",
        ),
        (
            "第三步，把目标拆小到今天能完成的一件事。不是降低标准，而是让大脑重新获得掌控感。",
            "Step three: shrink the goal into one thing you can finish today to regain control.",
        ),
        (
            f"所以{topic}的破局点，不是再逼自己一把，而是把努力、情绪、目标和边界重新分开。",
            "So the breakthrough is not forcing yourself harder, but separating effort, emotion, goals and boundaries.",
        ),
        (
            "最后记住一句：真正能让人变强的，不是硬扛，而是知道什么时候停一下，再重新出发。",
            "Remember this: strength is not only endurance. It is knowing when to pause and restart.",
        ),
    ]


def build_scenes(title: str, materials: list[dict]) -> list[dict]:
    selected: set[str] = set()
    scenes = []
    modes = ["judge", "casefile", "police", "execution", "desk", "chase", "judge"]
    for scene_index, (text, english) in enumerate(build_scene_texts(title)):
        cues = split_cues(text)
        english_parts = split_cues(english)
        layout_mode = "pair_left_right" if scene_index % 2 == 0 else "center_shift_pair"
        first_text = " ".join(cues[: max(1, (len(cues) + 1) // 2)])
        second_text = " ".join(cues[max(1, (len(cues) + 1) // 2) :]) or cues[-1]
        images = []
        for slot, image_text in enumerate([first_text, second_text]):
            material = select_material(materials, f"{title} {image_text}", scene_index, slot, selected)
            images.append(
                {
                    "src": f"sc1-materials/{material['fileName']}",
                    "fileName": material["fileName"],
                    "segmentIndex": slot,
                    "segmentText": image_text,
                    "summaryLabel": summary_label(image_text, slot),
                    "enterDirection": "center" if layout_mode == "center_shift_pair" and slot == 0 else ("right" if slot else "left"),
                    "layoutMode": layout_mode,
                    "matchScore": round(float(material["score"]), 2),
                }
            )
        caption_cues = []
        for cue_index, cue in enumerate(cues):
            caption_cues.append(
                {
                    "text": cue,
                    "englishText": english_parts[min(cue_index, len(english_parts) - 1)] if english_parts else english,
                    "summaryLabel": summary_label(cue, cue_index),
                }
            )
        scenes.append(
            {
                "id": f"sc1-title-{scene_index + 1:02d}",
                "title": summary_label(text, scene_index),
                "subtitleText": text,
                "voiceText": text,
                "englishText": english,
                "keywords": [summary_label(cue, cue_index) for cue_index, cue in enumerate(cues)][:3],
                "mode": modes[scene_index % len(modes)],
                "layoutMode": layout_mode,
                "segments": [
                    {
                        "text": text,
                        "subtitleText": text,
                        "englishText": english,
                        "summaryLabel": summary_label(text, 0),
                        "summaryLabels": [summary_label(cue, cue_index) for cue_index, cue in enumerate(cues)],
                        "layoutMode": layout_mode,
                        "captionCues": caption_cues,
                        "startRatio": 0,
                        "endRatio": 1,
                    }
                ],
                "assetImages": images,
            }
        )
    return scenes


def validate_audio_file(path: Path, label: str, min_seconds: float = 0.1) -> dict:
    if not path.exists():
        raise FileNotFoundError(f"{label} audio missing: {path}")
    audio = AudioSegment.from_file(path)
    seconds = max(len(audio) / 1000.0, 0.0)
    if seconds < min_seconds:
        raise RuntimeError(f"{label} audio too short: {seconds:.3f}s at {path}")
    if len(audio.raw_data) < 1024 or audio.rms <= 0:
        raise RuntimeError(f"{label} audio is silent or invalid: {path}")
    return {
        "seconds": seconds,
        "rms": audio.rms,
        "channels": audio.channels,
        "frameRate": audio.frame_rate,
    }


def extract_reference_voice(job_dir: Path) -> Path:
    staged = job_dir / "reference-voice.wav"
    configured_audio = os.getenv("SC1_VOICE_REFERENCE_AUDIO", "").strip()
    if configured_audio:
        source_audio = Path(configured_audio)
        validate_audio_file(source_audio, "configured reference voice", min_seconds=1.0)
        if source_audio.resolve() != staged.resolve():
            shutil.copyfile(source_audio, staged)
        validate_audio_file(staged, "staged reference voice", min_seconds=1.0)
        return staged

    if not REFERENCE_VIDEO.exists():
        raise FileNotFoundError(
            "SC1 voice reference video not found. Set SC1_VOICE_REFERENCE_VIDEO or "
            f"SC1_VOICE_REFERENCE_AUDIO. Current path: {REFERENCE_VIDEO}"
        )
    start = os.getenv("SC1_VOICE_REFERENCE_START", "0").strip() or "0"
    seconds = os.getenv("SC1_VOICE_REFERENCE_SECONDS", "24").strip() or "24"
    subprocess.run(
        [
            "ffmpeg",
            "-y",
            "-ss",
            start,
            "-t",
            seconds,
            "-i",
            str(REFERENCE_VIDEO),
            "-vn",
            "-ac",
            "1",
            "-ar",
            "16000",
            "-af",
            "highpass=f=80,lowpass=f=7600,loudnorm=I=-18:LRA=11:TP=-1.5",
            str(staged),
        ],
        check=True,
        timeout=180,
    )
    validate_audio_file(staged, "extracted reference voice", min_seconds=3.0)
    return staged


def run_indextts2_batch(job_dir: Path, jobs: list[dict], reference_audio: Path) -> None:
    if TTS_ENGINE != "indextts2":
        raise RuntimeError(f"Unsupported SC1_TTS_ENGINE={TTS_ENGINE!r}; this workflow currently requires indextts2")
    if INDEXTTS2_REPO is None or not INDEXTTS2_REPO.exists():
        raise RuntimeError(
            "IndexTTS2 is not installed/configured. Clone the IndexTTS repo and set SC1_INDEXTTS2_REPO, "
            "then set SC1_INDEXTTS2_MODEL_DIR to the downloaded IndexTTS2 checkpoints directory. "
            f"Current SC1_INDEXTTS2_REPO={INDEXTTS2_REPO_VALUE or '<empty>'}"
        )

    helper = PROJECT_ROOT / "scripts" / "indextts2_batch.py"
    manifest = job_dir / "indextts2-jobs.json"
    manifest.write_text(
        json.dumps(
            {
                "referenceAudio": str(reference_audio),
                "modelDir": INDEXTTS2_MODEL_DIR,
                "jobs": jobs,
            },
            ensure_ascii=False,
            indent=2,
        ),
        encoding="utf-8",
    )
    env = os.environ.copy()
    env["PYTHONPATH"] = str(INDEXTTS2_REPO) + os.pathsep + env.get("PYTHONPATH", "")
    python_bin = os.getenv("SC1_INDEXTTS2_PYTHON", sys.executable)
    subprocess.run(
        [python_bin, str(helper), "--manifest", str(manifest)],
        cwd=str(INDEXTTS2_REPO),
        env=env,
        check=True,
        timeout=int(os.getenv("SC1_INDEXTTS2_TIMEOUT", "3600")),
    )


def synthesize_audio(scenes: list[dict], job_id: str) -> list[dict]:
    def scene_cues(scene: dict) -> list[dict]:
        segments = scene.get("segments") if isinstance(scene.get("segments"), list) else []
        if not segments:
            return []
        cues = segments[0].get("captionCues") if isinstance(segments[0].get("captionCues"), list) else []
        return cues

    def apply_audio_clips(scene: dict, clips: list[dict]) -> None:
        cursor = 0
        audio_clips = []
        for cue, clip in zip(scene_cues(scene), clips):
            duration_frames = max(12, int(float(clip["seconds"]) * 30 + 3.999))
            cue["startFrame"] = cursor
            cue["endFrame"] = cursor + duration_frames
            audio_clips.append(
                {
                    "src": clip["src"],
                    "startFrame": cursor,
                    "endFrame": cursor + duration_frames,
                    "durationInFrames": duration_frames,
                    "seconds": clip["seconds"],
                    "provider": clip["provider"],
                    **({"model": clip["model"]} if clip.get("model") else {}),
                }
            )
            cursor += duration_frames
        scene["durationFrames"] = max(54, cursor)
        scene["duration"] = round(scene["durationFrames"] / 30, 2)
        scene["audioClips"] = audio_clips
        scene.pop("audioSrc", None)

    reuse_job = os.getenv("SC1_REUSE_AUDIO_JOB", "").strip()
    if reuse_job:
        audio_scenes = []
        reuse_dir = PUBLIC_AUDIO_DIR / reuse_job
        for index, scene in enumerate(scenes):
            clips = []
            for cue_index, _cue in enumerate(scene_cues(scene)):
                audio_path = reuse_dir / f"scene-{index + 1:02d}-cue-{cue_index + 1:02d}.wav"
                if not audio_path.exists():
                    raise FileNotFoundError(f"Reusable cue audio missing: {audio_path}")
                audio = AudioSegment.from_file(audio_path)
                clips.append(
                    {
                        "src": f"generated-audio/{reuse_job}/{audio_path.name}",
                        "seconds": max(len(audio) / 1000.0, 0.01),
                        "provider": "reused_audio",
                    }
                )
            apply_audio_clips(scene, clips)
            audio_scenes.append(
                {
                    "index": index,
                    "seconds": sum(clip["seconds"] for clip in clips),
                    "durationInFrames": scene["durationFrames"],
                    "provider": "reused_audio",
                    "sourceJobId": reuse_job,
                }
            )
        return audio_scenes

    job_dir = PUBLIC_AUDIO_DIR / job_id
    job_dir.mkdir(parents=True, exist_ok=True)
    reference_audio = extract_reference_voice(job_dir)
    print(f"[sc1] reference_voice={reference_audio}")

    tts_jobs = []
    for index, scene in enumerate(scenes):
        for cue_index, cue in enumerate(scene_cues(scene)):
            out_path = job_dir / f"scene-{index + 1:02d}-cue-{cue_index + 1:02d}.wav"
            tts_jobs.append(
                {
                    "sceneIndex": index,
                    "cueIndex": cue_index,
                    "label": f"scene={index + 1} cue={cue_index + 1}",
                    "text": clean(cue.get("text") or scene["voiceText"]),
                    "outputPath": str(out_path),
                }
            )
    run_indextts2_batch(job_dir, tts_jobs, reference_audio)

    audio_scenes = []
    for index, scene in enumerate(scenes):
        clips = []
        for cue_index, cue in enumerate(scene_cues(scene)):
            out_path = job_dir / f"scene-{index + 1:02d}-cue-{cue_index + 1:02d}.wav"
            stats = validate_audio_file(out_path, f"IndexTTS2 scene={index + 1} cue={cue_index + 1}")
            clips.append(
                {
                    "src": f"generated-audio/{job_id}/{out_path.name}",
                    "seconds": stats["seconds"],
                    "provider": "indextts2_open_source",
                    "engine": "indextts2",
                    "referenceAudio": f"generated-audio/{job_id}/{reference_audio.name}",
                    "rms": stats["rms"],
                }
            )
        apply_audio_clips(scene, clips)
        audio_scenes.append(
            {
                "index": index,
                "seconds": sum(clip["seconds"] for clip in clips),
                "durationInFrames": scene["durationFrames"],
                "provider": "indextts2_open_source" if clips else "none",
                "engine": "indextts2",
            }
        )
    return audio_scenes


def stage_materials(scenes: list[dict]) -> None:
    source_root = MATERIAL_DIR.parent if MATERIAL_DIR.is_file() else MATERIAL_DIR
    PUBLIC_MATERIAL_DIR.mkdir(parents=True, exist_ok=True)
    for scene in scenes:
        for image in scene.get("assetImages") or []:
            file_name = Path(str(image.get("fileName") or "")).name
            if not file_name:
                continue
            source = source_root / file_name
            if not source.exists():
                raise FileNotFoundError(f"Selected material missing: {source}")
            shutil.copyfile(source, PUBLIC_MATERIAL_DIR / file_name)


def render_video(title: str, scenes: list[dict], audio_scenes: list[dict], job_id: str) -> dict:
    payload = {
        "title": title,
        "script": "",
        "style": "sc1_stickman",
        "contentType": "knowledge_ip_stickman",
        "targetPlatform": "douyin",
        "tone": "sharp",
        "pace": "medium",
        "goal": "standalone_sc1_stickman_workflow",
        "density": 1,
        "audioScenes": audio_scenes,
        "scenes": scenes,
        "bgmSrc": None,
        "renderComposition": "Sc1StickmanVideo",
    }
    data = json.dumps(payload, ensure_ascii=False).encode("utf-8")
    request = urllib.request.Request(
        f"{RENDER_SERVICE_URL}/api/render-project",
        data=data,
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    with urllib.request.urlopen(request, timeout=900) as response:
        result = json.loads(response.read().decode("utf-8"))
    if not result.get("ok"):
        raise RuntimeError(result.get("message") or result)
    render_path = PROJECT_ROOT / "renders" / result["filename"]
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    output_path = OUTPUT_DIR / f"{job_id}.mp4"
    shutil.copyfile(render_path, output_path)
    project_json = OUTPUT_DIR / f"{job_id}.json"
    project_json.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    return {**result, "renderPath": str(render_path), "outputPath": str(output_path), "projectJson": str(project_json)}


def main() -> int:
    load_env_file()
    title = clean(" ".join(sys.argv[1:])) or DEFAULT_TOPIC
    job_id = f"sc1-stickman-{int(time.time())}"
    print(f"[sc1] title={title}")
    print(f"[sc1] material_dir={MATERIAL_DIR}")
    print(f"[sc1] render_service={RENDER_SERVICE_URL}")
    if os.getenv("SC1_VALIDATE_REFERENCE_AUDIO_ONLY", "").strip():
        job_dir = PUBLIC_AUDIO_DIR / job_id
        job_dir.mkdir(parents=True, exist_ok=True)
        reference_audio = extract_reference_voice(job_dir)
        stats = validate_audio_file(reference_audio, "reference voice", min_seconds=3.0)
        print(json.dumps({"ok": True, "referenceAudio": str(reference_audio), **stats}, ensure_ascii=False, indent=2))
        return 0
    materials = load_materials()
    scenes = build_scenes(title, materials)
    stage_materials(scenes)
    audio_scenes = synthesize_audio(scenes, job_id)
    result = render_video(title, scenes, audio_scenes, job_id)
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
