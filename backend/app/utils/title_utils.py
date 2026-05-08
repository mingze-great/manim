def normalize_project_title(title: str | None) -> str:
    normalized = str(title or "").strip()
    for prefix in ("视频创作-", "视频讲解-", "数学可视化-"):
        if normalized.startswith(prefix):
            normalized = normalized[len(prefix):].strip()
    return normalized
