from __future__ import annotations

import base64
import json
import mimetypes
import shutil
from datetime import datetime
from pathlib import Path
from typing import Any

from sqlalchemy.orm import Session

from app.models.material_library_generation import MaterialLibraryGeneration
from app.services.image_gen import image_gen_service
from app.services.stickman_workflow_assets import list_material_libraries, save_material_libraries


EMOTIONS = [
    ("calm", "neutral", 2, ["平静", "自省"], "安静整理自己的感受"),
    ("anxious", "negative", 4, ["焦虑", "等待"], "等待回应时不断放大不确定性"),
    ("sad", "negative", 4, ["失落", "被忽视"], "关系中的失落和委屈"),
    ("relief", "positive", 3, ["释怀", "松绑"], "把不属于自己的责任放下"),
    ("hopeful", "positive", 3, ["希望", "行动"], "看见可以开始改变的一小步"),
    ("tense", "negative", 5, ["冲突", "边界"], "关系拉扯中守住自己的边界"),
    ("supported", "positive", 3, ["支持", "共鸣"], "被理解和接住的安全感"),
    ("awkward", "neutral", 3, ["社交", "尴尬"], "不知道怎样回应的社交瞬间"),
    ("focused", "neutral", 3, ["专注", "拆解"], "把复杂问题拆开来看"),
    ("acceptance", "positive", 3, ["接纳", "自洽"], "允许真实的自己存在"),
    ("confidence", "positive", 4, ["自信", "成长"], "不再依赖外界证明自己"),
    ("fear", "negative", 5, ["恐惧", "警觉"], "面对风险时本能地拉响警报"),
]

SCENES = [
    ("self-reflection", "独处反思", "坐着思考并整理情绪", ["日记", "台灯"]),
    ("message-waiting", "等待消息", "看着手机等待回复", ["手机", "消息气泡"]),
    ("boundary", "关系边界", "伸手示意停止并保持距离", ["边界线"]),
    ("pressure-release", "释放压力", "深呼吸并放松肩膀", ["散开的线条"]),
    ("first-step", "迈出第一步", "向前迈出坚定的一步", ["脚印", "小路"]),
    ("comfort", "安慰陪伴", "两个人靠近并给予安慰", ["椅子", "纸巾"]),
    ("social-tension", "社交紧张", "在人群边缘局促站立", ["人群轮廓"]),
    ("helping-hand", "获得帮助", "接住对方伸出的手", ["手", "台阶"]),
    ("small-win", "小小胜利", "举手庆祝一次小进步", ["星星", "勾选框"]),
    ("repair", "关系修复", "两个人平静沟通", ["对话气泡"]),
    ("goodbye", "告别放下", "转身挥手告别", ["门", "远去小路"]),
    ("morning-reset", "重新开始", "在晨光中伸展身体", ["窗户", "太阳"]),
]

ROLES = [
    ["hook", "problem"],
    ["problem", "cause"],
    ["cause", "transition"],
    ["method", "transition"],
    ["method", "result"],
    ["result", "summary"],
]


def build_material_specs(count: int) -> list[dict[str, Any]]:
    total = max(2, min(200, int(count or 0)))
    specs: list[dict[str, Any]] = []
    for index in range(total):
        emotion, valence, intensity, concepts, meaning = EMOTIONS[index % len(EMOTIONS)]
        scene_key, scene_context, action, props = SCENES[index % len(SCENES)]
        roles = ROLES[index % len(ROLES)]
        subject_count = 2 if scene_key in {"comfort", "helping-hand", "repair"} else 1
        file_name = f"{index + 1}.png"
        prompt = (
            "严格参考上传图片的角色身份、线条、比例、配色和整体画风，生成同一素材系列的新场景。"
            f"场景是{scene_context}，角色动作是{action}，主要情绪为{emotion}。"
            "保持白色或透明的干净背景，只保留少量与语义相关的线稿道具；完整展示角色，不裁切身体，"
            "不要文字、边框、水印、logo、界面元素或复杂背景。1:1构图，主体居中，适合心理学短视频匹配。"
        )
        specs.append(
            {
                "file_name": file_name,
                "image_path": "",
                "image_type": "reference_style_interaction" if subject_count == 2 else "reference_style_character",
                "primary_subject": f"与参考图身份一致的角色，{scene_context}",
                "subject_count": subject_count,
                "clothing_outfit": "根据场景变化但保持角色身份一致的简洁服装",
                "clothing_keywords": ["简洁服装", "身份一致"],
                "pose_action": action,
                "props_objects": props,
                "scene_context": scene_context,
                "emotion_primary": emotion,
                "emotion_secondary": concepts,
                "emotion_valence": valence,
                "emotion_intensity": intensity,
                "psychology_concepts": concepts,
                "metaphor_meaning": meaning,
                "applicable_topics": [*concepts, scene_context],
                "storyboard_roles": roles,
                "usage_notes": f"适合表达{meaning}的文案分镜",
                "composition": "1:1居中完整角色，少量线稿道具，高留白",
                "subject_position": "center",
                "white_space_level": "high",
                "visual_complexity": "low",
                "style_tags": ["reference-consistent", "psychology-stickman", "white-background", scene_key],
                "search_keywords": [*concepts, scene_context, action, emotion, valence, *roles],
                "negative_keywords": ["文字", "水印", "边框", "复杂背景", "角色裁切", "身份漂移"],
                "prompt": prompt,
            }
        )
    return specs


def write_material_manifest(output_dir: Path, specs: list[dict[str, Any]]) -> Path:
    target = Path(output_dir).resolve()
    payload: list[dict[str, Any]] = []
    for raw in specs:
        item = dict(raw)
        image_path = target / str(item.get("file_name") or "")
        if not image_path.exists() or not image_path.is_file():
            raise ValueError(f"素材图片不存在: {image_path.name}")
        item["image_path"] = str(image_path)
        payload.append(item)
    manifest_path = target / "materials.json"
    manifest_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    return manifest_path


class MaterialLibraryGenerationService:
    def __init__(self, image_generator: Any = None, generated_image_root: Path | None = None):
        self.image_generator = image_generator or image_gen_service
        self.generated_image_root = Path(generated_image_root or Path(__file__).resolve().parents[2] / "uploads" / "article_images")

    def _reference_data_url(self, path: Path) -> str:
        mime = mimetypes.guess_type(path.name)[0] or "image/png"
        encoded = base64.b64encode(path.read_bytes()).decode("ascii")
        return f"data:{mime};base64,{encoded}"

    def _copy_generated_image(self, local_url: str, destination: Path) -> None:
        file_name = Path(str(local_url or "")).name
        source = (self.generated_image_root / file_name).resolve()
        root = self.generated_image_root.resolve()
        if source.parent != root or not source.exists() or not source.is_file():
            raise RuntimeError(f"生成图片本地文件不存在: {file_name}")
        shutil.copyfile(source, destination)

    async def _generate_range(self, db: Session, job: MaterialLibraryGeneration, start: int, end: int) -> None:
        output_dir = Path(job.output_dir).resolve()
        output_dir.mkdir(parents=True, exist_ok=True)
        reference_path = Path(job.reference_image_path).resolve()
        if not reference_path.exists():
            raise RuntimeError("参考图不存在")
        reference_images = [self._reference_data_url(reference_path)]
        specs = build_material_specs(job.target_count)
        for index in range(start, end):
            spec = specs[index]
            destination = output_dir / spec["file_name"]
            if not destination.exists():
                local_url, _public_url, _storage = await self.image_generator.generate_image(
                    spec["prompt"],
                    reference_images=reference_images,
                )
                self._copy_generated_image(local_url, destination)
            job.progress = max(job.progress or 0, int((index + 1) / max(1, job.target_count) * 100))
            job.message = f"已生成 {index + 1}/{job.target_count} 张素材"
            db.commit()

    async def generate_samples(self, db: Session, job: MaterialLibraryGeneration) -> None:
        job.status = "sampling"
        job.progress = 0
        job.error = None
        job.message = "正在生成两张风格样图"
        db.commit()
        try:
            await self._generate_range(db, job, 0, min(2, job.target_count))
            output_dir = Path(job.output_dir).resolve()
            sample_names = [f"{index}.png" for index in range(1, min(2, job.target_count) + 1)]
            job.sample_images_json = json.dumps(sample_names, ensure_ascii=False)
            job.status = "samples_ready"
            job.progress = 10
            job.message = "样图已生成，请确认风格后继续"
            db.commit()
        except Exception as exc:
            job.status = "failed"
            job.error = str(exc)
            job.message = "样图生成失败"
            db.commit()
            raise

    async def generate_batch(self, db: Session, job: MaterialLibraryGeneration) -> None:
        output_dir = Path(job.output_dir).resolve()
        if not (output_dir / "1.png").exists() or not (output_dir / "2.png").exists():
            raise RuntimeError("请先生成并确认两张样图")
        job.status = "generating"
        job.progress = max(10, job.progress or 0)
        job.error = None
        job.message = "正在批量生成素材库"
        db.commit()
        try:
            await self._generate_range(db, job, 2, job.target_count)
            manifest_path = write_material_manifest(output_dir, build_material_specs(job.target_count))
            job.manifest_path = str(manifest_path)
            job.status = "completed"
            job.progress = 100
            job.message = "素材库生成完成"
            job.completed_at = datetime.utcnow()
            db.commit()
            self.register_library(db, job)
        except Exception as exc:
            job.status = "failed"
            job.error = str(exc)
            job.message = "批量生成失败"
            db.commit()
            raise

    def register_library(self, db: Session, job: MaterialLibraryGeneration) -> None:
        output_dir = Path(job.output_dir).resolve()
        item = {
            "key": job.library_key,
            "name": job.library_name,
            "description": "由参考图自动生成的心理学火柴人素材库",
            "is_active": True,
            "is_visible": True,
            "sort_order": 20,
            "base_path": str(output_dir),
            "material_json_path": str(Path(job.manifest_path or output_dir / "materials.json")),
            "cover_image_path": str(output_dir / "1.png"),
            "cover_image_url": "",
            "image_count": int(job.target_count),
            "material_count": int(job.target_count),
            "source": "generated_reference",
        }
        libraries = list_material_libraries(db)
        existing_index = next((index for index, current in enumerate(libraries) if current.get("key") == job.library_key), -1)
        if existing_index >= 0:
            libraries[existing_index] = item
        else:
            libraries.append(item)
        save_material_libraries(db, libraries)


material_library_generation_service = MaterialLibraryGenerationService()
