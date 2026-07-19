import json
import sys
from pathlib import Path

import numpy as np
from PIL import Image


def load_rgba(path: Path):
    return Image.open(path).convert("RGBA")


def visible_bbox(image: Image.Image):
    alpha = image.getchannel("A")
    bbox = alpha.getbbox()
    return bbox or (0, 0, image.width, image.height)


def crop_template(image: Image.Image):
    left, top, right, bottom = visible_bbox(image)
    cropped = image.crop((left, top, right, bottom))
    return cropped, (left, top, right, bottom)


def score_position(frame_rgb, template_rgb, mask, x, y):
    h, w = template_rgb.shape[:2]
    region = frame_rgb[y:y + h, x:x + w]
    if region.shape[0] != h or region.shape[1] != w:
        return None
    diff = np.abs(region.astype(np.int16) - template_rgb.astype(np.int16))
    weighted = diff * mask[:, :, None]
    denom = max(mask.sum() * 3, 1)
    return float(weighted.sum() / denom)


def locate_template(frame_path: Path, template_path: Path):
    frame = load_rgba(frame_path)
    template, _ = crop_template(load_rgba(template_path))
    frame_rgb = np.array(frame.convert("RGB"))
    template_rgba = np.array(template)
    template_rgb = template_rgba[:, :, :3]
    mask = (template_rgba[:, :, 3] > 0).astype(np.float32)
    h, w = template_rgb.shape[:2]

    # Search around the center first; this is enough for our generated layout.
    x_start = max(0, frame.width // 2 - 500)
    x_end = min(frame.width - w, frame.width // 2 + 500)
    y_start = max(0, frame.height // 2 - 380)
    y_end = min(frame.height - h, frame.height // 2 + 280)

    best = None
    for y in range(y_start, y_end + 1, 16):
        for x in range(x_start, x_end + 1, 16):
            score = score_position(frame_rgb, template_rgb, mask, x, y)
            if score is None:
                continue
            if best is None or score < best["score"]:
                best = {"x": x, "y": y, "score": score}

    if best is None:
        return None

    fine_x_start = max(x_start, best["x"] - 24)
    fine_x_end = min(x_end, best["x"] + 24)
    fine_y_start = max(y_start, best["y"] - 24)
    fine_y_end = min(y_end, best["y"] + 24)

    for y in range(fine_y_start, fine_y_end + 1, 2):
        for x in range(fine_x_start, fine_x_end + 1, 2):
            score = score_position(frame_rgb, template_rgb, mask, x, y)
            if score is None:
                continue
            if score < best["score"]:
                best = {"x": x, "y": y, "score": score}

    bbox = [best["x"], best["y"], best["x"] + w, best["y"] + h]
    center_x = round(best["x"] + w / 2, 2)
    center_y = round(best["y"] + h / 2, 2)
    target_x = frame.width / 2
    target_y = frame.height / 2
    return {
        "frame_size": [frame.width, frame.height],
        "template_size": [w, h],
        "bbox": bbox,
        "center": [center_x, center_y],
        "target_center": [round(target_x, 2), round(target_y, 2)],
        "delta": [round(center_x - target_x, 2), round(center_y - target_y, 2)],
        "score": round(best["score"], 4),
    }


def main():
    if len(sys.argv) < 3:
        raise SystemExit("usage: match_scene_template.py <frame> <template>")
    result = locate_template(Path(sys.argv[1]), Path(sys.argv[2]))
    print(json.dumps(result, ensure_ascii=False))


if __name__ == "__main__":
    main()
