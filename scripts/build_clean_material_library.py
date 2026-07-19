import json
import sys
from pathlib import Path

from PIL import Image, ImageDraw


def find_watermark_bbox(image: Image.Image):
    width, height = image.size
    x0 = int(width * 0.72)
    y0 = int(height * 0.80)
    pixels = image.load()
    left = width
    top = height
    right = -1
    bottom = -1
    for y in range(y0, height):
        for x in range(x0, width):
            r, g, b = pixels[x, y][:3]
            if not (r >= 248 and g >= 248 and b >= 248):
                left = min(left, x)
                top = min(top, y)
                right = max(right, x)
                bottom = max(bottom, y)
    if right < left or bottom < top:
        return None
    pad = 8
    return (
        max(left - pad, 0),
        max(top - pad, 0),
        min(right + pad + 1, width),
        min(bottom + pad + 1, height),
    )


def clean_material(source_path: Path, target_path: Path):
    image = Image.open(source_path).convert("RGB")
    bbox = find_watermark_bbox(image)
    if bbox:
        draw = ImageDraw.Draw(image)
        draw.rectangle(bbox, fill=(255, 255, 255))
    image.save(target_path, format="PNG")


def main():
    source_dir = Path(sys.argv[1]) if len(sys.argv) > 1 else Path(r"E:\ai\cankao\sucai_cropped")
    target_dir = Path(sys.argv[2]) if len(sys.argv) > 2 else Path(r"E:\ai\cankao\sucai_clean")
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
        target_path = target_dir / source_path.name
        clean_material(source_path, target_path)
        cloned = dict(entry)
        cloned["file_name"] = target_path.name
        cloned["image_path"] = str(target_path)
        exported.append(cloned)

    target_manifest.write_text(json.dumps(exported, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps({"count": len(exported), "manifest": str(target_manifest)}, ensure_ascii=False))


if __name__ == "__main__":
    main()
