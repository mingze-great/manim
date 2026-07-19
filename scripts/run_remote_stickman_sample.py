import json
from pathlib import Path

import requests


BASE_URL = "http://152.136.218.74:3003"
USERNAME = "stickman_test_user"
PASSWORD = "Stickman123"
PROJECT_ID = 1757


def main() -> int:
    session = requests.Session()
    login = session.post(
        f"{BASE_URL}/api/auth/login",
        data={"username": USERNAME, "password": PASSWORD},
        timeout=30,
    )
    login.raise_for_status()
    token = login.json()["access_token"]

    response = session.get(
        f"{BASE_URL}/api/tasks/{PROJECT_ID}/stickman-compose",
        headers={"Authorization": f"Bearer {token}"},
        stream=True,
        timeout=1800,
    )
    response.raise_for_status()

    video_url = None
    for raw_line in response.iter_lines(decode_unicode=True):
        if not raw_line or not raw_line.startswith("data: "):
            continue
        payload = json.loads(raw_line[6:])
        print(json.dumps(payload, ensure_ascii=False))
        if payload.get("type") == "success":
            video_url = payload.get("video_url")
            break
        if payload.get("type") == "error":
            raise RuntimeError(payload.get("content") or "remote sample generation failed")

    if not video_url:
        raise RuntimeError("remote compose did not return a video url")

    download_url = video_url if video_url.startswith("http") else f"{BASE_URL}{video_url}"
    target_dir = Path(__file__).resolve().parents[1] / "downloaded_test_videos"
    target_dir.mkdir(parents=True, exist_ok=True)
    target_path = target_dir / Path(video_url).name

    with session.get(download_url, headers={"Authorization": f"Bearer {token}"}, stream=True, timeout=1800) as download:
        download.raise_for_status()
        with open(target_path, "wb") as file:
            for chunk in download.iter_content(chunk_size=1024 * 1024):
                if chunk:
                    file.write(chunk)

    print(json.dumps({"downloaded_video": str(target_path), "video_url": video_url}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
