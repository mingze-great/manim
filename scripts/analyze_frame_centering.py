import json
import sys
from pathlib import Path

from PIL import Image, ImageChops


def diff_bbox(frame_path: Path, background_path: Path, ignore_bottom: int = 220):
    frame = Image.open(frame_path).convert("RGBA")
    background = Image.open(background_path).convert("RGBA")
    if frame.size != background.size:
        background = background.resize(frame.size, Image.Resampling.LANCZOS)

    # Ignore title and subtitle bands; focus on the central scene-image region.
    roi_left = int(frame.width * 0.2)
    roi_right = int(frame.width * 0.8)
    roi_top = int(frame.height * 0.18)
    roi_bottom = max(int(frame.height * 0.78), frame.height - ignore_bottom)
    roi_bottom = min(roi_bottom, frame.height)
    frame = frame.crop((roi_left, roi_top, roi_right, roi_bottom))
    background = background.crop((roi_left, roi_top, roi_right, roi_bottom))

    diff = ImageChops.difference(frame.convert("RGB"), background.convert("RGB"))
    gray = diff.convert("L")
    mask = gray.point(lambda value: 255 if value > 18 else 0)
    bbox = mask.getbbox()
    if not bbox:
        return None
    left, top, right, bottom = bbox
    left += roi_left
    right += roi_left
    top += roi_top
    bottom += roi_top
    center_x = round((left + right) / 2, 2)
    center_y = round((top + bottom) / 2, 2)
    target_x = Image.open(frame_path).size[0] / 2
    target_y = Image.open(frame_path).size[1] / 2
    return {
        "frame_size": list(Image.open(frame_path).size),
        "roi": [roi_left, roi_top, roi_right, roi_bottom],
        "bbox": [left, top, right, bottom],
        "center": [center_x, center_y],
        "target_center": [round(target_x, 2), round(target_y, 2)],
        "delta": [round(center_x - target_x, 2), round(center_y - target_y, 2)],
    }


def main():
    if len(sys.argv) < 3:
        raise SystemExit("usage: analyze_frame_centering.py <frame> <background>")
    frame_path = Path(sys.argv[1])
    background_path = Path(sys.argv[2])
    result = diff_bbox(frame_path, background_path)
    print(json.dumps(result, ensure_ascii=False))


if __name__ == "__main__":
    main()
