# V2 3003 Remote Redeploy Verification

## Goal

Verify that pulling branch `feature/v2-ui-mobile-ux-recover-3003` and running the standard deployment flow can reproduce the current `3003/8003` behavior.

## Branch

- `feature/v2-ui-mobile-ux-recover-3003`

## Deploy Root

- `/opt/manim-v2-3003-snapshot`

## Standard Command

```bash
cd /opt/manim-v2-3003-snapshot
bash deploy/deploy-v2-3003.sh
```

## What The Script Preserves

The deployment script now preserves existing server-local env files before `git clean` and restores them after checkout:

- `backend/.env`
- `frontend/.env.production.local`

This avoids wiping production/test credentials and port-specific environment values.

## Validation Checklist

1. Frontend root
- `http://<host>:3003`

2. Login
- `POST http://<host>:3003/api/auth/login`

3. Streaming chat
- Enter a visual project chat page
- Confirm incremental SSE output instead of waiting for the whole response

4. Template preview video
- Confirm preview works in Admin Templates
- Confirm a sample URL like below returns `200`:
- `http://<host>:3003/api/videos/template_examples/template_21_1775727198.mp4`

5. Cross-port consistency
- Confirm the same template preview URL also works on `3002`

## Notes

Git does not contain the actual preview mp4 assets. Reproducing current `3003` behavior also requires the shared directory to be populated:

- `/opt/manim/shared/videos/template_examples`

This is handled by:

- `deploy/sync-template-example-videos.sh`
