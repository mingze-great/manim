# 3003 SC1 Stickman Workflow Deployment - 2026-07-14

## Scope

- Standalone SC1 stickman workflow title renderer.
- Remotion composition: `Sc1StickmanVideo`.
- Target render service: `http://127.0.0.1:18787` on `152.136.218.74`.
- Remote deploy directory: `/opt/manim-v2-3003-snapshot`.
- Material library on remote: `/opt/manim_assets/sc1-outputs`.

## Source

- Branch: `codex/3003-standalone-stickman-workflow-20260712`
- Code commit pushed to GitHub: `aaaf4eb9`
- Files changed:
  - `video-render-service/remotion-mind-video/src/remotion/Sc1StickmanVideo.jsx`
  - `video-render-service/remotion-mind-video/scripts/generate-sc1-stickman-title.py`

## Deployment

- Remote GitHub fetch failed on 2026-07-14 because `github.com:443` timed out from the server.
- To avoid blocking validation, the two changed files were deployed by SFTP after backup.
- Remote HEAD remained `12734b29447216dfe19334f6ea1d678538a89ce2`.
- Remote effective state is therefore: `12734b29447216dfe19334f6ea1d678538a89ce2` plus SFTP-overlaid SC1 files from `aaaf4eb9`.

## Backup

- Backup directory: `/opt/backups/manim-v2-3003-sc1-20260714-091724`
- Backed up:
  - Previous `Sc1StickmanVideo.jsx`
  - Previous `generate-sc1-stickman-title.py` if present
  - Previous remote `git status`
  - Previous remote `git rev-parse HEAD`

## Validation

- Local generated video:
  - `E:\ai\agent_knowledge_ip_module_20260712\outputs\sc1-stickman-workflow\sc1-stickman-1783991335.mp4`
  - Duration: `66.389333s`
  - Video stream: H.264, 1920x1080, 30fps
  - Audio stream: AAC, 48kHz stereo
- Local frame validation:
  - `frame3-015.png`: first center image shifted left before second enters; no image/subtitle overlap.
  - `frame3-017.png`: two images visible side by side; no overlap with summary labels or subtitles.
  - `sc1-stickman-1783991335-contact.png`: all segment images render from the latest material library.
- Remote render service was restarted and health check passed:
  - service: `remotion-mind-video`
  - port: `18787`
  - `sc1MaterialLibraryPath`: `/opt/manim_assets/sc1-outputs`

## Notes

- DashScope CosyVoice model order remains:
  - `cosyvoice-v3.5-flash`
  - `cosyvoice-v3-plus`
  - `cosyvoice-v3-flash`
- `cosyvoice-v3.5-plus` is not used.
- Local preview audio fell back to Windows SAPI because DashScope returned `AllocationQuota.FreeTierOnly`.
- For production CosyVoice audio, disable free-tier-only mode in Alibaba DashScope console or provide a key with paid quota.

## Rollback

Restore the backed-up files and restart the render service:

```bash
cd /opt/manim-v2-3003-snapshot
cp /opt/backups/manim-v2-3003-sc1-20260714-091724/Sc1StickmanVideo.jsx \
  video-render-service/remotion-mind-video/src/remotion/Sc1StickmanVideo.jsx
if [ -f /opt/backups/manim-v2-3003-sc1-20260714-091724/generate-sc1-stickman-title.py ]; then
  cp /opt/backups/manim-v2-3003-sc1-20260714-091724/generate-sc1-stickman-title.py \
    video-render-service/remotion-mind-video/scripts/generate-sc1-stickman-title.py
else
  rm -f video-render-service/remotion-mind-video/scripts/generate-sc1-stickman-title.py
fi
pkill -f "video-render-service/remotion-mind-video.*node server.js" || true
cd video-render-service/remotion-mind-video
nohup node server.js > /tmp/remotion-mind-video-18787.log 2>&1 &
```
