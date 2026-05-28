# V2 Deploy Flow

Current branch: `feature/prod-content-modules`

## Standard Flow

1. Commit code locally.
2. Keep work on `feature/prod-content-modules`.
3. Push with `python scripts/git_retry.py --repo E:\ai\agent -- push origin feature/prod-content-modules`.
4. If GitHub DNS fails, retry with `python scripts/git_retry.py --repo E:\ai\agent --resolve-github -- push origin feature/prod-content-modules`.
5. After GitHub is updated, reviewers can pull the branch for code review.
6. Deploy to `3002` with `docs/V2_3002_STANDARD_DEPLOY.md` only after the branch is pushed, unless this is an urgent production hotfix.

## Notes

- Prefer HTTPS remote plus `scripts/git_retry.py`; SSH can fail on this Windows host when `github.com` DNS is unstable.
- Direct deployment updates the server only; it does not update the remote branch.
- If review cannot see new code, check whether the latest commit exists on GitHub first.
