# 3003 Standalone Stickman Workflow Deployment - 2026-07-12

## Scope

Create and deploy a standalone SC1 stickman workflow entry outside AI Video Director. The user enters one topic and the system generates a finished horizontal stickman video.

## Source

- Local worktree: `E:\ai\agent_knowledge_ip_module_20260712`
- Branch: `codex/3003-standalone-stickman-workflow-20260712`
- Deployed HEAD: `47ee6be0eb80f3f94805f0d8fc48b77fc7106680`
- Runtime code commit: `3dd2223ebbf839a1093987389a852d802b8753fe`
- Material staging fix commit: `cc182010d0f194af5bf73a72bc4d2e2a7ee49480`
- Previous standalone module commit: `c85e767664c707bba4002619cc96b6e770aaa064`
- Previous deployed branch: `codex/3003-knowledge-ip-module-20260712`
- Previous deployed commit: `1ab199775445f10a49039ae64532a1d4fcab33d5`

## Target

- Server: `152.136.218.74`
- Deploy directory: `/opt/manim-v2-3003-snapshot`
- Frontend entry: `http://152.136.218.74:3003/stickman-workflow`
- Backend API: `/api/stickman-workflow/jobs`
- Render service: `http://127.0.0.1:18787`
- Material library: `/opt/manim_assets/sc1-sucai`
- Material count: `56` PNG files, about `91M`

## Backup

- Pre-deploy backup: `/opt/manim_backups/3003_before_standalone_stickman_20260712_214201`
- Bundle transport:
  - `/opt/manim_backups/standalone-stickman-workflow-20260712.bundle`
  - `/opt/manim_backups/standalone-stickman-full-20260712.bundle`

## Implementation Notes

- Added standalone frontend route `/stickman-workflow`.
- Added standalone backend router `/api/stickman-workflow`.
- Kept AI Video Director route separate; this module only wraps the SC1 topic workflow.
- Each generated scene gets two material-library images by default.
- Before rendering, selected SC1 material images are copied into Remotion public assets under `public/sc1-materials/job_xx/` so Chromium loads them reliably with `staticFile`.
- Remotion layout separates:
  - top title and keyword labels
  - middle two-image scene area
  - bottom horizon line and subtitle area
- Scene duration is driven by generated audio scene duration, so subtitles advance with the voice segment.

## Verification

Local:

- `python -m py_compile backend/app/services/ai_video.py backend/app/api/stickman_workflow.py backend/app/main.py`
- `node --check video-render-service/remotion-mind-video/server.js`
- `node --check video-render-service/remotion-mind-video/scripts/render-sc1-stickman-sample.js`
- `npm run build` in `frontend`
- `node scripts/render-sc1-stickman-sample.js stills`
- `node scripts/render-sc1-stickman-sample.js render 5` with temp redirected to `F:\ai\codex_tmp`

Remote:

- `npm run build` passed in `/opt/manim-v2-3003-snapshot/frontend`
- Backend py_compile passed with `/root/miniconda3/envs/manim311/bin/python3.11`
- `manim-v2-3003-backend.service`: active
- `manim-v2-3003-worker.service`: active
- `manim-v2-3003-ai-video-render.service`: active
- `curl http://127.0.0.1:8003/health`: healthy
- `curl http://127.0.0.1:18787/api/health`: ok and reports `/opt/manim_assets/sc1-sucai`
- `curl -I http://127.0.0.1:3003/stickman-workflow`: HTTP 200
- `curl -I http://127.0.0.1:18787/sc1-materials/1.png`: HTTP 200

End-to-end smoke:

- Endpoint: `POST http://152.136.218.74:8003/api/stickman-workflow/jobs`
- Topic: `喂警犬吃狗算什么行为`
- Successful job after material staging fix: `job_36`
- Project: `33`
- Completed at: `2026-07-12T14:21:04Z`
- Output URL: `/api/ai-video/files/36/output/video.mp4`
- Output file: `/opt/manim-v2-3003-snapshot/backend/storage/ai-video/tasks/job_36/output/video.mp4`
- Output duration: `32.192s`
- Output size: `2.79M`
- Frame checks at 4s and 12s confirmed:
  - two scene images are visible
  - labels stay above the scene
  - subtitles stay below the horizon line
  - scene images do not overlap subtitles

## Known Notes

- The current material library uses outline stickman PNGs, not the exact filled black silhouettes in the reference video. The layout and timing are matched; asset style is constrained by `E:\ai\cankao\sucai`.
- In-app browser screenshot verification was blocked on the local machine because the C drive had `0` free space and the browser plugin could not write runtime assets. HTTP route and end-to-end remote generation were verified instead.
- Remote disk remains tight. Before this deployment, old Remotion temporary renders and generated audio were cleaned to keep enough space for smoke generation.

## Rollback

Rollback to previous deployed standalone base:

```bash
cd /opt/manim-v2-3003-snapshot
git switch codex/3003-knowledge-ip-module-20260712
git reset --hard 1ab199775445f10a49039ae64532a1d4fcab33d5
systemctl restart manim-v2-3003-backend.service manim-v2-3003-worker.service manim-v2-3003-ai-video-render.service
```

Backup path for reference: `/opt/manim_backups/3003_before_standalone_stickman_20260712_214201`
