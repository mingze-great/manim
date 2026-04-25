# V2 Rollback Info

## Current Deployed Service

1. Branch
- `feature/v2-ui-mobile-ux-recover`

2. Local HEAD
- `06d902f20638dcaaf0c34566297cc0e47f9d8749`
- Commit message: `chore: ignore one-off deployment utilities`

3. Frontend Service
- Port: `3002`
- Deploy directory: `/opt/manim-v2/frontend/dist`

4. Backend Service
- Port: `8002`

5. Site Config
- Config file: `manim-v2.conf`
- `/api` proxy target: `http://localhost:8002`

## Remote Status

1. Current branch remote
- `origin/feature/v2-ui-mobile-ux-recover` does not exist yet

2. Safe remote baseline
- Branch: `origin/feature/v2-mobile-admin-ux-optimization`
- Commit: `06d902f20638dcaaf0c34566297cc0e47f9d8749`

## Rollback Notes

1. The currently deployed v2 service is based on `feature/v2-ui-mobile-ux-recover`.
2. The currently deployed live state is not yet represented by a single remote commit.
3. The reliable rollback anchor is `origin/feature/v2-mobile-admin-ux-optimization@06d902f20638dcaaf0c34566297cc0e47f9d8749`.
4. If a future push or deploy is incorrect, rebuild and redeploy from that baseline or from a new clean recovery branch created from it.

## One-line Record

- `feature/v2-ui-mobile-ux-recover` / `06d902f20638dcaaf0c34566297cc0e47f9d8749` / frontend `3002` / backend `8002` / `/opt/manim-v2/frontend/dist` / `manim-v2.conf`
