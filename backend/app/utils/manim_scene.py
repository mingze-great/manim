import re


SCENE_BASE_CLASSES = {
    "Scene",
    "MovingCameraScene",
    "ThreeDScene",
    "ZoomedScene",
    "GraphScene",
    "LinearTransformationScene",
    "VectorScene",
}

SCENE_CLASS_PATTERN = re.compile(
    r"class\s+([A-Za-z_]\w*)\s*\(\s*([A-Za-z_]\w*)\s*\)"
)


def extract_scene_name(code: str, default: str = "SceneName") -> str:
    for match in SCENE_CLASS_PATTERN.finditer(code or ""):
        class_name, base_name = match.groups()
        if base_name in SCENE_BASE_CLASSES:
            return class_name
    return default


def force_intro_title(code: str, title: str | None) -> str:
    safe_title = (title or "").strip()
    if not code or not safe_title:
        return code

    escaped_title = safe_title.replace("\\", "\\\\").replace('"', '\\"')
    replacement = f'INTRO_TITLE = "{escaped_title}"'

    if re.search(r"^INTRO_TITLE\s*=", code, flags=re.MULTILINE):
        return re.sub(
            r"^INTRO_TITLE\s*=\s*([\"']).*?\1",
            replacement,
            code,
            count=1,
            flags=re.MULTILINE,
        )

    lines = code.splitlines()
    insert_at = 0
    for index, line in enumerate(lines):
        stripped = line.strip()
        if stripped.startswith("from ") or stripped.startswith("import "):
            insert_at = index + 1
            continue
        if stripped == "":
            continue
        break

    lines.insert(insert_at, replacement)
    return "\n".join(lines)
