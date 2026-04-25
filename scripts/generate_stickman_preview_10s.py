import json
import shutil
import sys
from pathlib import Path

sys.path.append(str(Path(__file__).resolve().parents[1] / "backend"))

from app.services.stickman_generator import StickmanGenerator


FULL_SCRIPT = (
    "很多焦虑，不是事情太多，而是大脑一直在预演失败。"
    "第一步，先停掉脑内预演，把注意力从结果拉回到眼前这一步。"
    "第二步，一次只做一件事，单点推进，比来回切换更能降低心理消耗。"
    "第三步，给每次行动一个收尾动作，让大脑感受到完成，而不是悬着。"
)


def main():
    generator = StickmanGenerator()
    script_data = generator.build_storyboards_from_script_text("心理知识分享", FULL_SCRIPT)
    storyboards = script_data["storyboards"]

    for scene in storyboards:
        scene["camera_track"] = "static"
        scene["motion_preset"] = "static"
        scene["foreground_subjects"] = generator._foreground_subjects_for_scene(scene, str(scene.get("visual_focus") or "主题"), int(scene.get("scene_id") or 1))
        scene["foreground_events"] = generator._foreground_events_for_scene(scene, int(scene.get("scene_id") or 1))
        scene["subtitle_lines"] = generator._subtitle_blueprint_for_scene(scene)

    assets, flags = generator.generate_images(storyboards, "16:9")

    output_dir = Path(__file__).resolve().parents[1] / "tmp_outputs"
    output_dir.mkdir(parents=True, exist_ok=True)

    result = generator.compose_from_assets(
        topic="心理知识分享",
        storyboards=storyboards,
        image_assets=assets,
        voice_source="ai",
        tts_provider="dashscope_cosyvoice",
        tts_voice="longanhuan",
        tts_rate="+15%",
    )

    final_path = output_dir / "stickman_preview_10s.mp4"
    shutil.copyfile(result["video_path"], final_path)
    print(json.dumps({
        "video": str(final_path),
        "first_scene_image": assets[0].get("scene_image_path") if assets else None,
        "duration": result["duration"],
        "storyboards": [
            {
                "scene_id": scene.get("scene_id"),
                "scene_title": scene.get("scene_title"),
                "scene_narration": scene.get("scene_narration") or scene.get("narration"),
                "start_time": scene.get("start_time"),
                "end_time": scene.get("end_time"),
            }
            for scene in result["storyboards"]
        ],
        "flags": flags,
    }, ensure_ascii=False))


if __name__ == "__main__":
    main()
