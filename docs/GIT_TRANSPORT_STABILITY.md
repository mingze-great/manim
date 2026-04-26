# Git Transport Stability

## What Was Failing

- Local GitHub HTTPS access was intermittent.
- `git ls-remote` and `git remote show origin` sometimes failed with `Could not connect to server`, timeout, or TLS reset style errors.
- Local `api.github.com:443` was reachable while `github.com:443` intermittently failed.
- Remote SSH execution to `152.136.218.74` also intermittently timed out before command execution.

## What Changed

### `scripts/remote_exec.py`

- Added retry/backoff.
- Added configurable SSH port.
- Added configurable connect timeout.
- Added SSH keepalive.
- Returns the actual remote exit code.

### `scripts/upload_file_remote.py`

- Added retry/backoff.
- Added configurable SSH port.
- Added configurable connect timeout.
- Added SSH keepalive.
- Added optional `--mkdirs` to create missing remote parent directories.

### `scripts/git_retry.py`

- Wraps `git` with retry/backoff for transient transport failures.
- Uses per-command GitHub HTTPS workarounds without changing git config:
  - `-c http.version=HTTP/1.1`
  - `-c http.maxRequests=1`
- Retries only when stderr/stdout matches transient network/TLS failure patterns.

## Why This Approach

- It avoids changing global or repo git config.
- It works with the current HTTPS remote and credential manager setup.
- It hardens the two unstable links we actually observed:
  - local machine -> GitHub
  - local machine -> deployment server

## Usage

### Safer Git fetch/ls-remote/push

```bash
python scripts/git_retry.py --repo E:\ai\agent_stickman_3003_upgrade -- ls-remote origin refs/heads/feature/stickman-v2-on-3003
python scripts/git_retry.py --repo E:\ai\agent_stickman_3003_upgrade -- fetch origin feature/stickman-v2-on-3003
python scripts/git_retry.py --repo E:\ai\agent_stickman_3003_upgrade -- push origin HEAD:feature/stickman-v2-on-3003
```

### Safer remote command execution

```bash
python scripts/remote_exec.py 152.136.218.74 "git -C /opt/manim-v2-3003-snapshot rev-parse HEAD" --user root --password <password> --retries 5 --retry-delay 8
```

### Safer remote upload

```bash
python scripts/upload_file_remote.py 152.136.218.74 local.zip /tmp/local.zip --user root --password <password> --retries 5 --retry-delay 8 --mkdirs
```

## Important Limitation

- GitHub SSH over `443` is reachable from this machine, but current GitHub SSH authentication is not configured here.
- Both checks currently return `Permission denied (publickey)`:
  - `ssh -T -p 443 git@ssh.github.com`
  - `ssh -T git@github.com`
- So the practical short-term fix is resilient HTTPS, not switching remotes to SSH.
