# 3003 SC1 Topic Workflow Deployment - 2026-07-12

## Scope

Deploy the isolated SC1 stickman knowledge-IP workflow so a user can enter one topic and generate a finished MP4 from the 3003 AI video page.

## Source

- Local worktree: `E:\ai\agent_knowledge_ip_module_20260712`
- Branch: `codex/3003-knowledge-ip-module-20260712`
- Code commit deployed first: `b3c5054962d43248d09519cf9436484771540ed7`
- Base branch: `codex/3003-knowledge-ip-workflow-20260710`
- Base commit: `3a21d68a0faa02dd380cd1b9d75d82fbf6c110e5`

## Target

- Server: `152.136.218.74`
- Deploy directory: `/opt/manim-v2-3003-snapshot`
- Frontend: `3003`
- Backend: `8003`
- Render service: `18787`
- Services:
  - `manim-v2-3003-backend.service`
  - `manim-v2-3003-worker.service`
  - `manim-v2-3003-ai-video-render.service`

## Backup And Transport

- Pre-deploy backup: `/opt/manim_backups/3003_before_sc1_topic_workflow_20260712_2025`
- Bundle transport path: `/opt/manim_backups/sc1-topic-workflow-20260712.bundle`
- Smoke-test DB backups:
  - `/opt/manim_backups/manim.db.before_sc1_smoke_20260712_205103`
  - `/opt/manim_backups/manim.db.before_sc1_smoke_20260712_205132`

GitHub fetch was intermittently unavailable from the server, so deployment used a local git bundle.

## Deployment Actions

1. Created isolated local worktree and branch from `origin/codex/3003-knowledge-ip-workflow-20260710@3a21d68a`.
2. Added reusable Remotion composition `Sc1StickmanVideo`.
3. Registered selectable render composition in the Remotion render service.
4. Added backend AI video style/type support:
   - `knowledge_ip_stickman`
   - `sc1_stickman`
5. Added topic expansion so short user input becomes a multi-scene SC1 script.
6. Added AI video frontend option for the SC1 stickman workflow.
7. Built frontend on the server.
8. Restarted backend, worker, and render services.
9. Created a short-lived smoke account `codex_sc1_smoke_20260712` after backing up the SQLite DB.

## Verification

Local verification before deployment:

- `python -m py_compile backend/app/services/ai_video.py`
- `node --check video-render-service/remotion-mind-video/server.js`
- `node --check video-render-service/remotion-mind-video/scripts/render-sc1-stickman-sample.js`
- `npm run build` in `frontend`
- `node scripts/render-sc1-stickman-sample.js stills`
- `node scripts/render-sc1-stickman-sample.js render 5`

Remote verification after deployment:

- `npm run build` passed in `/opt/manim-v2-3003-snapshot/frontend`
- `/root/miniconda3/envs/manim311/bin/python3.11 -m py_compile backend/app/services/ai_video.py` passed
- `manim-v2-3003-backend.service`: active
- `manim-v2-3003-worker.service`: active
- `manim-v2-3003-ai-video-render.service`: active
- `curl http://127.0.0.1:8003/health`: healthy
- `curl -I http://127.0.0.1:3003/ai-video/create`: HTTP 200
- `curl http://127.0.0.1:18787/api/health`: ok

End-to-end smoke test:

- Endpoint: `POST http://152.136.218.74:8003/api/ai-video/jobs`
- Topic: `喂警犬吃狗算什么行为`
- Payload type/style: `knowledge_ip_stickman` / `sc1_stickman`
- Job: `job_34`
- Project: `31`
- Created: `2026-07-12T12:52:10Z`
- Completed: `2026-07-12T13:00:33Z`
- Output URL: `/api/ai-video/files/34/output/video.mp4`
- Output file: `/opt/manim-v2-3003-snapshot/backend/storage/ai-video/tasks/job_34/output/video.mp4`
- Output size: `5.0M`
- Output duration: `22.55s`

## Known Notes

- The Coze YAML was used only as workflow reference. Runtime generation does not depend on Coze.
- The uploaded reference video was used as a visual target, but exact recreation of proprietary or platform-only transition internals is approximated in Remotion.
- The center scene slide transition is implemented as a reusable Remotion scene transition, not as a Coze/CutCap transfer.
- Text in the center scene is derived from the topic/script so it can be reused for arbitrary themes.
- Server disk is tight after smoke verification: `/` had about `1.4G` free. Runtime output cleanup should be scheduled before heavy batch testing.

## Rollback

Rollback branch and commit:

- Branch: `codex/3003-knowledge-ip-workflow-20260710`
- Commit: `3a21d68a0faa02dd380cd1b9d75d82fbf6c110e5`

Rollback aids:

- Pre-deploy backup: `/opt/manim_backups/3003_before_sc1_topic_workflow_20260712_2025`
- Smoke-test DB backup before account creation: `/opt/manim_backups/manim.db.before_sc1_smoke_20260712_205132`

Suggested rollback command:

```bash
cd /opt/manim-v2-3003-snapshot
git switch codex/3003-knowledge-ip-workflow-20260710
git reset --hard 3a21d68a0faa02dd380cd1b9d75d82fbf6c110e5
systemctl restart manim-v2-3003-backend.service manim-v2-3003-worker.service manim-v2-3003-ai-video-render.service
```

