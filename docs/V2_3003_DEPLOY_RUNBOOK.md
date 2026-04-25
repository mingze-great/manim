# V2 3003 Deploy Runbook

## Target

- Branch: `feature/v2-ui-mobile-ux-recover-3003`
- Frontend: `3003`
- Backend: `8003`
- Deploy root: `/opt/manim-v2-3003-snapshot`

## What This Runbook Guarantees

Following this runbook should reproduce the current `3003` behavior using:

1. Git branch content
2. Standardized nginx config
3. Standardized backend/worker services
4. Shared template preview video directory

## One-Time Server Setup

1. Ensure these binaries exist:
- `git`
- `npm`
- `/root/miniconda3/envs/manim311/bin/python3.11`
- `nginx`

2. Ensure Redis is running.

3. Ensure shared template example directory is allowed:
- `/opt/manim/shared/videos/template_examples`

## Required Files In Repo

- `deploy/manim-v2-3003.conf`
- `deploy/manim-v2-3003-backend.service`
- `deploy/manim-v2-3003-worker.service`
- `deploy/env.backend.3003.example`
- `deploy/env.frontend.3003.example`
- `deploy/sync-template-example-videos.sh`
- `deploy/deploy-v2-3003.sh`

## Deployment Steps

```bash
git clone --branch feature/v2-ui-mobile-ux-recover-3003 --single-branch https://github.com/mingze-great/manim.git /opt/manim-v2-3003-snapshot
cd /opt/manim-v2-3003-snapshot
bash deploy/deploy-v2-3003.sh
```

## Environment Notes

### Backend

Copy and customize:

- `deploy/env.backend.3003.example` -> `backend/.env`

Minimum required overrides:

- `PORT=8003`
- `CELERY_QUEUE=manim_v2_3003`
- `NEW_SERVER_URL=http://<host>:3003`
- your production/shared database and model credentials

### Frontend

Deployment script copies:

- `deploy/env.frontend.3003.example` -> `frontend/.env.production.local`

Current expected values:

- `VITE_API_BASE_URL=/api`
- `VITE_LEGACY_APP_URL=http://manim.asia`

## Template Preview Videos

### Shared Directory

- `/opt/manim/shared/videos/template_examples`

### Rule

Template preview videos must be treated as shared v2 assets, not per-port assets.

### Why

This ensures template preview works across:

- `3002/8002`
- `3003/8003`
- future v2 ports

### Sync

Deployment script runs:

- `deploy/sync-template-example-videos.sh`

This copies existing historical template preview videos from common old directories into the shared directory.

## Validation Checklist

1. Health
- `curl http://127.0.0.1:8003/health`

2. Frontend
- `http://<host>:3003`

3. Login
- `POST http://<host>:3003/api/auth/login`

4. Streaming chat
- Enter a visual project chat page and confirm incremental SSE output

5. Template preview video
- Open Admin Templates and preview an uploaded example video
- Confirm `HEAD http://<host>:3003/api/videos/template_examples/<filename>` returns `200`

6. Cross-port check
- Confirm the same preview video also works from `3002`

## Important Limitation

Git alone does not store the actual preview mp4 files.

To fully reproduce current behavior on a new server, you need both:

1. this branch
2. the shared template preview video directory populated with the actual mp4 files
