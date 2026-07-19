import json
import time
from datetime import datetime
from pathlib import Path

import requests


BASE_URL = "http://152.136.218.74:3003"
USERNAME = "stickman_test_user"
PASSWORD = "Stickman123"
TITLE_PREFIX = "[viral-smoke]"
THEME = "为什么你越想改变，越容易拖延"
STORYBOARD_COUNT = 4

GENERATION_FLAGS = {
    "workflow_variant": "v2_viral_package",
    "viral_package_enabled": True,
    "viral_hook_template_key": "shock_reveal",
    "viral_outro_template_key": "quote_soft_cta",
    "viral_title_mode": "hook_title",
    "viral_visual_style": "cinematic_clean",
    "viral_cta_mode": "light_follow",
    "viral_title_text": "你越想彻底改变，越容易卡住",
    "viral_outro_text": "先做最小一步，拖延就会先松开一点",
    "opening_template_key": "hook_question",
}


def _headers(token: str) -> dict:
    return {"Authorization": f"Bearer {token}"}


def _parse_sse(response: requests.Response):
    for raw_line in response.iter_lines(decode_unicode=True):
        if not raw_line or not raw_line.startswith("data: "):
            continue
        yield json.loads(raw_line[6:])


def _delete_old_smoke_projects(session: requests.Session, token: str) -> None:
    response = session.get(f"{BASE_URL}/api/projects", headers=_headers(token), timeout=30)
    response.raise_for_status()
    projects = response.json()
    smoke_ids = [project["id"] for project in projects if str(project.get("title") or "").startswith(TITLE_PREFIX)]
    for project_id in smoke_ids:
        delete_response = session.delete(
            f"{BASE_URL}/api/projects/{project_id}",
            headers=_headers(token),
            timeout=30,
        )
        delete_response.raise_for_status()


def _create_project(session: requests.Session, token: str) -> dict:
    title = f"{TITLE_PREFIX} {datetime.now().strftime('%Y%m%d-%H%M%S')}"
    payload = {
        "title": title,
        "theme": THEME,
        "module_type": "stickman",
        "stickman_variant": "v2",
        "storyboard_count": STORYBOARD_COUNT,
        "aspect_ratio": "16:9",
        "generation_mode": "one_click",
        "voice_source": "ai",
        "tts_provider": "dashscope_cosyvoice",
        "tts_voice": "longanhuan",
        "tts_rate": "+8%",
    }
    response = session.post(f"{BASE_URL}/api/projects", json=payload, headers=_headers(token), timeout=60)
    if response.status_code == 400 and "作品数量已达上限" in response.text:
        _delete_old_smoke_projects(session, token)
        response = session.post(f"{BASE_URL}/api/projects", json=payload, headers=_headers(token), timeout=60)
    response.raise_for_status()
    return response.json()


def _update_generation_flags(session: requests.Session, token: str, project_id: int) -> dict:
    payload = {"generation_flags": json.dumps(GENERATION_FLAGS, ensure_ascii=False)}
    response = session.put(
        f"{BASE_URL}/api/projects/{project_id}",
        json=payload,
        headers=_headers(token),
        timeout=60,
    )
    response.raise_for_status()
    return response.json()


def _run_one_click_generation(session: requests.Session, token: str, project_id: int) -> str:
    response = session.get(
        f"{BASE_URL}/api/tasks/{project_id}/stickman-generate",
        headers=_headers(token),
        stream=True,
        timeout=7200,
    )
    response.raise_for_status()
    video_url = ""
    for payload in _parse_sse(response):
        print(json.dumps(payload, ensure_ascii=False))
        if payload.get("type") == "error":
            raise RuntimeError(payload.get("content") or "stickman v2 viral smoke test failed")
        if payload.get("type") == "success":
            video_url = str(payload.get("video_url") or "")
            break
    if not video_url:
        raise RuntimeError("stickman generate stream finished without video_url")
    return video_url


def _fetch_project(session: requests.Session, token: str, project_id: int) -> dict:
    response = session.get(f"{BASE_URL}/api/projects/{project_id}", headers=_headers(token), timeout=60)
    response.raise_for_status()
    return response.json()


def _download_video(session: requests.Session, token: str, video_url: str, output_dir: Path) -> Path:
    download_url = video_url if video_url.startswith("http") else f"{BASE_URL}{video_url}"
    output_dir.mkdir(parents=True, exist_ok=True)
    target_path = output_dir / Path(video_url).name
    with session.get(download_url, headers=_headers(token), stream=True, timeout=7200) as response:
        response.raise_for_status()
        with open(target_path, "wb") as file:
            for chunk in response.iter_content(chunk_size=1024 * 1024):
                if chunk:
                    file.write(chunk)
    return target_path


def main() -> int:
    session = requests.Session()
    login = session.post(
        f"{BASE_URL}/api/auth/login",
        data={"username": USERNAME, "password": PASSWORD},
        timeout=30,
    )
    login.raise_for_status()
    token = login.json()["access_token"]

    project = _create_project(session, token)
    project_id = int(project["id"])
    print(json.dumps({"project_id": project_id, "title": project.get("title")}, ensure_ascii=False))

    _update_generation_flags(session, token, project_id)
    video_url = _run_one_click_generation(session, token, project_id)
    project_snapshot = _fetch_project(session, token, project_id)

    output_dir = Path(__file__).resolve().parents[1] / "downloaded_test_videos" / f"project_{project_id}"
    video_path = _download_video(session, token, video_url, output_dir)
    snapshot_path = output_dir / "project_snapshot.json"
    snapshot_path.write_text(json.dumps(project_snapshot, ensure_ascii=False, indent=2), encoding="utf-8")

    print(json.dumps({
        "project_id": project_id,
        "video_url": video_url,
        "video_path": str(video_path),
        "snapshot_path": str(snapshot_path),
        "generation_flags": GENERATION_FLAGS,
    }, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
