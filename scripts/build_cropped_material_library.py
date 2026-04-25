import json
import sys
from pathlib import Path

from PIL import Image


def non_white_bbox(image: Image.Image):
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


def build_cropped_material(source_path: Path, target_path: Path, output_size: int = 640):
    with Image.open(source_path).convert("RGB") as image:
        left, top, right, bottom = non_white_bbox(image)
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

        cropped = image.crop((crop_left, crop_top, crop_right, crop_bottom))
        canvas = Image.new("RGB", (output_size, output_size), (255, 255, 255))
        cropped.thumbnail((output_size, output_size), Image.Resampling.LANCZOS)
        x = (output_size - cropped.width) // 2
        y = (output_size - cropped.height) // 2
        canvas.paste(cropped, (x, y))
        canvas.save(target_path, format="PNG")


def main():
    source_dir = Path(sys.argv[1]) if len(sys.argv) > 1 else Path(r"E:\ai\cankao\sucai")
    target_dir = Path(sys.argv[2]) if len(sys.argv) > 2 else Path(r"E:\ai\cankao\sucai_cropped")
    source_manifest = source_dir / "materials.json"
    target_manifest = target_dir / "materials.json"

    target_dir.mkdir(parents=True, exist_ok=True)
    entries = json.loads(source_manifest.read_text(encoding="utf-8")) if source_manifest.exists() else []
    exported = []
    for entry in entries:
        if not isinstance(entry, dict):
            continue
        source_path = Path(str(entry.get("image_path") or "").strip())
        if not source_path.exists():
            file_name = str(entry.get("file_name") or "").strip()
            source_path = source_dir / file_name if file_name else source_path
        if not source_path.exists():
            continue
        target_path = target_dir / source_path.with_suffix(".png").name
        build_cropped_material(source_path, target_path)
        cloned = dict(entry)
        cloned["file_name"] = target_path.name
        cloned["image_path"] = str(target_path)
        exported.append(cloned)

    target_manifest.write_text(json.dumps(exported, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps({"count": len(exported), "manifest": str(target_manifest)}, ensure_ascii=False))


if __name__ == "__main__":
    main()
