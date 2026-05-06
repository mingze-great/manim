# V2 3002 Standard Deploy

适用场景：

- 本地有未提交改动
- 需要把当前 worktree 直接同步到 `3002`
- 目标机器：`152.136.218.74`
- 部署目录：`/opt/manim-v2`
- 后端服务：`manim-v2-backend.service`
- Worker：`manim-v2-worker.service`

## 固定原则

1. 先备份，再覆盖。
2. `3002` 只发布到 `/opt/manim-v2`。
3. 后端一律用 `tar.gz`，不要用 Windows `Compress-Archive` 生成 `zip`。
4. 原因：Windows `zip` 会把 `app\...` 作为文件名写进去，Linux 解压后目录结构会坏，服务会报 `ModuleNotFoundError: No module named 'app'`。
5. 前端也统一用 `tar.gz`，避免路径和换行问题。

## 当前快照

- 当前 3002 对应分支：`feature/stickman-v2-viral-hook-optimization-acceptance`
- 当前已部署提交：`d1b55e24` `fix: shorten storyboard and subtitle splitting`
- 说明：这版仅收紧了 `backend/app/services/stickman_generator_v2.py` 的分镜/字幕切分，保留去尾标点逻辑
- 最近一次远端备份：`/opt/manim-v2/backup_20260506_231958`
- 如需复现当前 3002，请直接拉取上述分支并切到该提交

## 本地前置检查

1. 后端至少过一次：
   - `python -m py_compile <changed_python_files>`
2. 前端至少过一次：
   - `npm run build`
3. 确认本地产物目录存在：
   - `backend/app`
   - `frontend/dist`

## 标准部署步骤

### 1. 生成时间戳

PowerShell:

```powershell
Get-Date -Format yyyyMMdd_HHmmss
```

下面示例把这个时间戳记为 `$TS`。

### 2. 本地打包

后端：

```powershell
tar -czf "E:\ai\agent_stickman_v2_viral_hook_acceptance\tmp\deploy_backend_app_$TS.tar.gz" -C "E:\ai\agent_stickman_v2_viral_hook_acceptance\backend" app
```

前端：

```powershell
tar -czf "E:\ai\agent_stickman_v2_viral_hook_acceptance\tmp\deploy_frontend_dist_$TS.tar.gz" -C "E:\ai\agent_stickman_v2_viral_hook_acceptance\frontend\dist" .
```

### 3. 远端整站备份

```powershell
python "E:\ai\agent_stickman_v2_viral_hook_acceptance\scripts\remote_exec.py" 152.136.218.74 "mkdir -p /opt/manim_backups/deploy_tmp && tar -czf /opt/manim_backups/manim-v2_$TS.tar.gz -C /opt manim-v2" --user root --password 010421 --timeout 1200 --retries 3 --retry-delay 8
```

### 4. 上传 tar 包

后端：

```powershell
python "E:\ai\agent_stickman_v2_viral_hook_acceptance\scripts\upload_file_remote.py" 152.136.218.74 "E:\ai\agent_stickman_v2_viral_hook_acceptance\tmp\deploy_backend_app_$TS.tar.gz" /opt/manim_backups/deploy_tmp/deploy_backend_app_$TS.tar.gz --user root --password 010421 --mkdirs --retries 5 --retry-delay 8
```

前端：

```powershell
python "E:\ai\agent_stickman_v2_viral_hook_acceptance\scripts\upload_file_remote.py" 152.136.218.74 "E:\ai\agent_stickman_v2_viral_hook_acceptance\tmp\deploy_frontend_dist_$TS.tar.gz" /opt/manim_backups/deploy_tmp/deploy_frontend_dist_$TS.tar.gz --user root --password 010421 --mkdirs --retries 5 --retry-delay 8
```

### 5. 远端覆盖脚本

本地临时生成一个 shell 脚本，内容固定如下：

```bash
#!/usr/bin/env bash
set -euo pipefail

find /opt/manim-v2/backend -maxdepth 1 -name 'app\*' -delete
find /opt/manim-v2/frontend/dist -maxdepth 1 -name '*\*' -delete

rm -rf /opt/manim-v2/backend/app
rm -rf /opt/manim-v2/frontend/dist/*

tar -xzf /opt/manim_backups/deploy_tmp/deploy_backend_app_$TS.tar.gz -C /opt/manim-v2/backend
tar -xzf /opt/manim_backups/deploy_tmp/deploy_frontend_dist_$TS.tar.gz -C /opt/manim-v2/frontend/dist

systemctl restart manim-v2-backend.service
systemctl restart manim-v2-worker.service

sleep 6

systemctl is-active manim-v2-backend.service
systemctl is-active manim-v2-worker.service
curl -fsS http://127.0.0.1:8002/health
```

说明：

- `find ... -name 'app\*' -delete` 是为了清理以前错误 zip 部署留下的脏文件。
- `frontend/dist/*` 清空后再解压，避免旧 bundle 残留。

### 6. 上传并执行远端脚本

上传：

```powershell
python "E:\ai\agent_stickman_v2_viral_hook_acceptance\scripts\upload_file_remote.py" 152.136.218.74 "<local_deploy_script_path>" /opt/manim_backups/deploy_tmp/deploy_remote_$TS.sh --user root --password 010421 --mkdirs --retries 5 --retry-delay 8
```

执行：

```powershell
python "E:\ai\agent_stickman_v2_viral_hook_acceptance\scripts\remote_exec.py" 152.136.218.74 "bash /opt/manim_backups/deploy_tmp/deploy_remote_$TS.sh" --user root --password 010421 --timeout 1200 --retries 3 --retry-delay 8
```

## 发布后验证

至少检查：

1. 服务状态：
   - `systemctl is-active manim-v2-backend.service`
   - `systemctl is-active manim-v2-worker.service`
2. 健康检查：
   - `curl -fsS http://127.0.0.1:8002/health`
3. 前端首页：
   - `curl -I http://127.0.0.1:3002/`
4. 如有前端变更，确认新 bundle 文件名已变化。

## 常见故障

### 1. `ModuleNotFoundError: No module named 'app'`

原因：

- 用了 Windows `zip`
- 远端出现了 `app\services\...` 这类错误文件名

处理：

1. 不再用 `zip`
2. 清理：
   - `find /opt/manim-v2/backend -maxdepth 1 -name 'app\*' -delete`
3. 重新用 `tar.gz` 解压 `backend/app`

### 2. 上传脚本执行时报 `No such file or directory`

不要猜路径，先查：

```powershell
python "E:\ai\agent_stickman_v2_viral_hook_acceptance\scripts\remote_exec.py" 152.136.218.74 "ls -lah /opt/manim_backups/deploy_tmp" --user root --password 010421
```

### 3. 页面还是旧的

先查：

1. `/opt/manim-v2/frontend/dist/assets` 下 bundle 名是否变化
2. `http://127.0.0.1:3002/` 返回的 `index.html` 是否是新的
3. 浏览器是否缓存

## 结论

后续 `3002` 本地直传部署统一按这份文档执行：

- 本地 `tar.gz`
- 远端整站备份
- 上传到 `/opt/manim_backups/deploy_tmp`
- 远端脚本覆盖
- 重启 backend/worker
- 健康检查
