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

import dashscope
from dashscope.audio.tts_v2 import SpeechSynthesizer
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
TTS_MODELS = ["cosyvoice-v3.5-flash", "cosyvoice-v3-plus", "cosyvoice-v3-flash"]
DEFAULT_VOICE = os.getenv("SC1_STICKMAN_VOICE", "longshuo_v3")
POWERSHELL = r"C:\Windows\System32\WindowsPowerShell\v1.0\powershell.exe"


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
    parts = [item.strip(" ，。！？；：、,.!?:;") for item in re.split(r"(?<=[。！？；!?;])\s*", text) if item.strip(" ，。！？；：、,.!?:;")]
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
        (["第一反应", "挑战", "脑洞"], "脑洞题开场"),
        (["行为", "动作", "做法"], "行为性质"),
        (["对象", "谁", "保护"], "对象边界"),
        (["风险", "后果", "影响"], "风险后果"),
        (["规则", "法律", "边界"], "规则边界"),
        (["结论", "答案", "所以"], "结论收束"),
        (["结构", "四层", "拆"], "结构判断"),
    ]
    for needles, label in rules:
        if any(needle in text for needle in needles):
            return label
    pieces = [item for item in re.split(r"[\s，。！？；：、,.!?:;]+", text) if 2 <= len(item) <= 7]
    return pieces[0] if pieces else ("前情提问" if index == 0 else "后续判断")


def build_scene_texts(title: str) -> list[tuple[str, str]]:
    topic = clean(title) or "沙雕法律竞赛题"
    return [
        (
            f"来挑战一道离谱但很容易答错的题：{topic}。第一反应先按住，不要急着站队。",
            "Try a weird question that is easy to answer wrong. Hold your first reaction.",
        ),
        (
            f"真正关键不是谁看起来更有道理，而是把{topic}里的行为、对象和后果分开看。",
            "The key is not who sounds right, but separating action, object and consequence.",
        ),
        (
            "第一步看行为指向谁：它影响的是普通场景，还是已经进入特殊规则保护的对象。",
            "Step one: identify who the action points to and what kind of object is involved.",
        ),
        (
            "第二步看有没有真实风险：只是想象中的尴尬，还是造成了可被评价的后果。",
            "Step two: check whether there is real risk or only imagined embarrassment.",
        ),
        (
            "第三步把事实放回规则边界：同一个动作，放在不同对象上，性质可能完全不同。",
            "Step three: put the fact back into the rule boundary. The same act can change nature.",
        ),
        (
            f"所以{topic}的答案不是背结论，而是按行为、对象、风险、边界四层拆。",
            "So the answer is not a slogan, but a four-layer analysis.",
        ),
        (
            "最后记住一句：越像段子的题，越要用结构判断，不然最容易被第一反应带跑。",
            "The more it sounds like a joke, the more you need structured judgment.",
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


def synthesize_audio(scenes: list[dict], job_id: str, voice: str = DEFAULT_VOICE) -> list[dict]:
    reuse_job = os.getenv("SC1_REUSE_AUDIO_JOB", "").strip()
    if reuse_job:
        audio_scenes = []
        reuse_dir = PUBLIC_AUDIO_DIR / reuse_job
        for index, scene in enumerate(scenes):
            audio_path = reuse_dir / f"scene-{index + 1:02d}.wav"
            if not audio_path.exists():
                raise FileNotFoundError(f"Reusable audio missing: {audio_path}")
            audio = AudioSegment.from_file(audio_path)
            seconds = max(len(audio) / 1000.0, 0.01)
            duration_frames = max(54, int(seconds * 30 + 3.999))
            scene["durationFrames"] = duration_frames
            scene["duration"] = round(duration_frames / 30, 2)
            scene["audioSrc"] = f"generated-audio/{reuse_job}/scene-{index + 1:02d}.wav"
            audio_scenes.append(
                {
                    "index": index,
                    "src": scene["audioSrc"],
                    "seconds": seconds,
                    "durationInFrames": duration_frames,
                    "provider": "reused_audio",
                    "sourceJobId": reuse_job,
                }
            )
        return audio_scenes

    api_key = os.getenv("STICKMAN_TTS_API_KEY") or os.getenv("DASHSCOPE_API_KEY") or os.getenv("IMAGE_API_KEY")
    if not api_key:
        raise RuntimeError("DASHSCOPE_API_KEY is required for DashScope CosyVoice TTS")
    dashscope.api_key = api_key
    dashscope.base_websocket_api_url = "wss://dashscope.aliyuncs.com/api-ws/v1/inference"
    job_dir = PUBLIC_AUDIO_DIR / job_id
    job_dir.mkdir(parents=True, exist_ok=True)
    audio_scenes = []
    for index, scene in enumerate(scenes):
        text = clean(scene["voiceText"])
        out_path = job_dir / f"scene-{index + 1:02d}.wav"
        last_error = None
        models_to_try = [] if os.getenv("SC1_SKIP_DASHSCOPE", "").strip() else TTS_MODELS
        for model in models_to_try:
            try:
                print(f"[sc1] tts scene={index + 1} model={model} voice={voice}")
                synthesizer = SpeechSynthesizer(model=model, voice=voice)
                audio_bytes = synthesizer.call(text)
                if not audio_bytes:
                    raise RuntimeError("empty audio")
                out_path.write_bytes(audio_bytes)
                audio = AudioSegment.from_file(out_path)
                if len(audio.raw_data) < 1024 or audio.rms <= 0:
                    raise RuntimeError("silent audio")
                seconds = max(len(audio) / 1000.0, 0.01)
                duration_frames = max(54, int(seconds * 30 + 3.999))
                scene["durationFrames"] = duration_frames
                scene["duration"] = round(duration_frames / 30, 2)
                scene["audioSrc"] = f"generated-audio/{job_id}/scene-{index + 1:02d}.wav"
                audio_scenes.append(
                    {
                        "index": index,
                        "src": scene["audioSrc"],
                        "seconds": seconds,
                        "durationInFrames": duration_frames,
                        "provider": "dashscope_cosyvoice",
                        "model": model,
                    }
                )
                break
            except Exception as exc:
                last_error = exc
                print(f"[sc1] tts failed scene={index + 1} model={model}: {exc}")
        else:
            print(f"[sc1] DashScope CosyVoice unavailable; falling back to Windows SAPI scene={index + 1}: {last_error}")
            text_path = job_dir / f"scene-{index + 1:02d}.txt"
            text_path.write_text(text, encoding="utf-8")
            subprocess.run(
                [
                    POWERSHELL,
                    "-NoProfile",
                    "-ExecutionPolicy",
                    "Bypass",
                    "-File",
                    str(PROJECT_ROOT / "scripts" / "sapi-tts.ps1"),
                    "-TextPath",
                    str(text_path),
                    "-OutPath",
                    str(out_path),
                    "-VoiceName",
                    "",
                    "-Rate",
                    "0",
                ],
                check=True,
                timeout=120,
            )
            audio = AudioSegment.from_file(out_path)
            if len(audio.raw_data) < 1024 or audio.rms <= 0:
                raise RuntimeError(f"SAPI fallback returned invalid audio for scene {index + 1}")
            seconds = max(len(audio) / 1000.0, 0.01)
            duration_frames = max(54, int(seconds * 30 + 3.999))
            scene["durationFrames"] = duration_frames
            scene["duration"] = round(duration_frames / 30, 2)
            scene["audioSrc"] = f"generated-audio/{job_id}/scene-{index + 1:02d}.wav"
            audio_scenes.append(
                {
                    "index": index,
                    "src": scene["audioSrc"],
                    "seconds": seconds,
                    "durationInFrames": duration_frames,
                    "provider": "sapi_fallback",
                    "dashscopeError": str(last_error),
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
    title = clean(" ".join(sys.argv[1:])) or "沙雕法律竞赛题"
    job_id = f"sc1-stickman-{int(time.time())}"
    print(f"[sc1] title={title}")
    print(f"[sc1] material_dir={MATERIAL_DIR}")
    print(f"[sc1] render_service={RENDER_SERVICE_URL}")
    materials = load_materials()
    scenes = build_scenes(title, materials)
    stage_materials(scenes)
    audio_scenes = synthesize_audio(scenes, job_id)
    result = render_video(title, scenes, audio_scenes, job_id)
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
