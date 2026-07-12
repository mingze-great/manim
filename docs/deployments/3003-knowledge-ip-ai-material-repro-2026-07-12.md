# 3003 Knowledge IP Workflow Repro Runbook - 2026-07-12

## Deployment Summary

- Service: 3003 staging/test service only. Do not touch 3002.
- Deploy dir: `/opt/manim-v2-3003-snapshot`
- Git branch: `codex/3003-knowledge-ip-workflow-20260710`
- Commit before this sync: `34969c3d` (`fix: bust knowledge ip page cache`)
- Commit after this sync: run `git rev-parse --short HEAD` after commit.
- Backend service: `manim-v2-3003-backend`
- Backend health URL: `http://127.0.0.1:8003/health`
- Public page: `http://152.136.218.74:3003/`

## What This Sync Includes

This sync records the current 3003 Knowledge IP workflow source changes for AI material video generation. It does not change 3002.

### Source Files

- `backend/app/config.py`
- `backend/app/api/knowledge_ip.py`
- `docs/deployments/3003-knowledge-ip-ai-material-repro-2026-07-12.md`

### Runtime Config Keys

The backend now reads these settings from runtime environment / `.env`:

- `DASHSCOPE_VIDEO_BASE_URL`
- `DASHSCOPE_VIDEO_TASK_URL`
- `KNOWLEDGE_IP_VIDEO_MODEL`
- `KNOWLEDGE_IP_VIDEO_FALLBACK_MODELS`

Do not commit `.env`; it contains secrets.

### AI Material Generation Behavior

- Uses Bailian workspace video synthesis endpoint.
- Primary model: `happyhorse-1.0-t2v`
- Fallback order: `wan2.7-t2v`, `happyhorse-1.1-t2v`, `wan2.6-t2v`
- Each material segment tries the model order until one succeeds.
- Material segments run concurrently with max workers set to 2.
- If all AI material video generation fails, the job fails explicitly. It no longer silently uses fake material fallback.
- Error messages are ASCII-readable to avoid frontend question-mark mojibake.

## Current 3003 Runtime Env

Expected `.env` values in `/opt/manim-v2-3003-snapshot/.env`:

```bash
DASHSCOPE_VIDEO_BASE_URL=https://ws-ckc5fvl317n4h4af.cn-beijing.maas.aliyuncs.com/api/v1/services/aigc/video-generation/video-synthesis
DASHSCOPE_VIDEO_TASK_URL=https://ws-ckc5fvl317n4h4af.cn-beijing.maas.aliyuncs.com/api/v1/tasks/{task_id}
KNOWLEDGE_IP_VIDEO_MODEL=happyhorse-1.0-t2v
KNOWLEDGE_IP_VIDEO_FALLBACK_MODELS=wan2.7-t2v,happyhorse-1.1-t2v,wan2.6-t2v
```

## Reproduce Deployment

1. SSH to server.

```bash
ssh root@152.136.218.74
```

2. Enter deploy dir.

```bash
cd /opt/manim-v2-3003-snapshot
```

3. Check branch, commit and dirty state.

```bash
git branch --show-current
git rev-parse --short HEAD
git status --short
```

4. Check runtime video model config.

```bash
grep -E 'DASHSCOPE_VIDEO_BASE_URL|DASHSCOPE_VIDEO_TASK_URL|KNOWLEDGE_IP_VIDEO_MODEL|KNOWLEDGE_IP_VIDEO_FALLBACK_MODELS' .env
```

5. Restart backend after source/env changes.

```bash
systemctl restart manim-v2-3003-backend
```

6. Verify backend health.

```bash
curl -sS http://127.0.0.1:8003/health
```

7. Verify 3003 page response.

```bash
curl -I http://127.0.0.1:3003/
```

## Known Issue: T2V Quota

The Bailian API key and workspace endpoint are reachable. A test with `happyhorse-1.1-r2v` returned `PENDING`, so the key/workspace can submit at least one model class.

The following T2V models returned `403 AllocationQuota.FreeTierOnly` during testing:

- `happyhorse-1.0-t2v`
- `wan2.7-t2v`
- `wan2.7-t2v-2026-06-12`
- `wan2.7-t2v-2026-04-25`
- `happyhorse-1.1-t2v`
- `wan2.6-t2v`

Meaning: the free quota is exhausted, or Bailian console is set to free-tier-only / stop after free quota. Check the exact workspace, API key, model quota, and paid usage switch in Bailian console.

## Files Not To Commit

Do not commit runtime/generated files:

- `backend/storage/`
- `backend/uploads/`
- `video-render-service/remotion-mind-video/public/`
- `video-render-service/remotion-mind-video/renders/`
- `*.mp4`
- `*.wav`
- `.env`
- `frontend/tsconfig.tsbuildinfo`

## Rollback

To rollback 3003 source state:

```bash
cd /opt/manim-v2-3003-snapshot
git log --oneline -5
git checkout <target_commit_or_snapshot_branch>
systemctl restart manim-v2-3003-backend
curl -sS http://127.0.0.1:8003/health
```

Before rollback, check whether database, uploads, or running task storage also changed; Git does not fully manage runtime data.
