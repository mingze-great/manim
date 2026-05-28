# Git Transport Stability

## Current Recommendation

- Work on branch `feature/prod-content-modules`.
- Use HTTPS remote plus `scripts/git_retry.py` for GitHub operations.
- Avoid switching the remote back to `git@github.com:...` unless SSH DNS is known to work.

## Why

- The Windows host can fail normal DNS resolution for `github.com`.
- A direct push may fail with `Could not resolve host: github.com`.
- `scripts/git_retry.py` applies HTTP/1.1, single-request transport, retry/backoff, and Windows Git SSL backend compatibility.
- When DNS is blocked, add `--resolve-github` so the script resolves GitHub through DNS-over-HTTPS and passes the IP to Git via `http.curloptResolve`.

## Recommended Commands

```bash
python scripts/git_retry.py --repo E:\ai\agent -- ls-remote origin refs/heads/feature/prod-content-modules
python scripts/git_retry.py --repo E:\ai\agent -- fetch origin feature/prod-content-modules
python scripts/git_retry.py --repo E:\ai\agent -- push origin feature/prod-content-modules
```

## DNS Fallback Commands

```bash
python scripts/git_retry.py --repo E:\ai\agent --resolve-github -- ls-remote origin refs/heads/feature/prod-content-modules
python scripts/git_retry.py --repo E:\ai\agent --resolve-github -- fetch origin feature/prod-content-modules
python scripts/git_retry.py --repo E:\ai\agent --resolve-github -- push origin feature/prod-content-modules
```

## Fallback

If GitHub is still unreachable but production needs an urgent update on `3002`:

- Follow `docs/V2_3002_STANDARD_DEPLOY.md`.
- Treat direct deployment to `/opt/manim-v2` as a runtime hotfix only.
- Push the branch later when GitHub is reachable so code review can use the normal remote branch.

## Review Requirement

After every production-facing change:

1. Push the branch to GitHub.
2. Ask reviewers to `git fetch` / `git pull`.
3. If push fails, record the exact transport error and use the DNS fallback commands before direct deployment.
