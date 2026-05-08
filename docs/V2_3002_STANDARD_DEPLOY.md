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
- 当前已发布的远程复现基线：`repro/3002-12fbd6a6` @ `12fbd6a6` `fix: align acceptance deploy with local media flow`
- 当前本地冻结的完整 3002 发布快照：`12fbd6a6` `fix: align acceptance deploy with local media flow`
- 目标 repro 分支名：`repro/3002-12fbd6a6`
- 关键说明：
  - `2b714c21` 引入“最终文案多行时，每行锁成一个分镜”
  - `9d2458c8` 在其基础上补齐运行依赖，形成可运行基准
  - `ef0b0bdf` 恢复最新增强讲解独立流前后端
  - `2d02dfc6` 增加“可选英文字幕”能力，当前 3002 后端源码停在这版
  - `2267ee1f`、`105c9739` 为当前 3002 前端新增的英文字幕状态与进度反馈
  - `c0e7a83c` 修正增强讲解英文字幕同步时序、后台用户列表兼容与标题强约束
  - `12fbd6a6` 补齐本地媒体链路、权限拆分、下载与标准讲解音色试听等当前运行态改动
- 当前 3002 关键行为：
  - 最终文案区多行文本优先按“每行一个分镜”处理
  - 对话默认风格仍为 `classic`
- 当前 3002 实际运行态说明：
  - 服务器目录：`/opt/manim-v2`
  - 当前线上运行效果对应的本地冻结快照：`12fbd6a6`
  - 该快照已在本地通过后端编译与前端构建校验，并已通过 tar 直传方式部署到 `3002`
- 当前推进状态：
  - `12fbd6a6` 已在本地通过 `python -m py_compile backend/app/api/admin.py backend/app/api/projects.py backend/app/api/tasks.py backend/app/config.py backend/app/models/user.py backend/app/schemas/user.py backend/app/services/background_task.py backend/app/services/chat.py backend/app/services/manim.py backend/app/services/stickman_generator.py backend/app/tasks/render.py backend/app/utils/cos_storage.py`
  - `12fbd6a6` 已在本地通过 `frontend/npm run build`
  - `feature/stickman-v2-viral-hook-optimization-acceptance` 已推送到远端最新提交 `f9ee4155`
  - `repro/3002-12fbd6a6` 已成功发布到 GitHub，指向冻结运行态提交 `12fbd6a6`
  - `3003` 已使用 `12fbd6a6` 对应部署包完成复现，运行目录仍为 `/opt/manim-v2-3003-snapshot`
  - `3003` 本次整站备份：`/opt/manim_backups/manim-v2-3003-snapshot_20260507_235051.tar.gz`
  - `3003` 本次源码快照留档：`/opt/manim_backups/releases/manim-v2-3003-12fbd6a6`
  - 服务器到 GitHub 的直接 `git clone/fetch` 仍有 TLS 波动，所以本次 `3003` 先通过 bundle + tar 包完成落地
- 最近一次远端备份：`/opt/manim_backups/backup_20260507_*.tar.gz` 与目录内 `backup_*`
- 当前服务器新版目录保留的非代码脏数据仅包括：
  - `.env.development`
  - `.env.example`
  - `.env.production`
  - `frontend/tsconfig.tsbuildinfo`
  - `backend/uploads/`
- 如需严格复现“当前 3002 最新运行态”，直接拉取 `repro/3002-12fbd6a6`；如服务器侧 GitHub TLS 暂时不稳定，再按本文档备用方案使用 bundle 或 tar 包落地

## 磁盘与队列

- 2026-05-07 已处理生产服务器磁盘满问题
- 根因：`/opt/manim_backups`、历史 snapshot/backups 过大，导致根分区曾达到 `100%`
- 影响：Redis 出现 `MISCONF`，Celery worker 无法写入队列，进而影响思维可视化等异步任务
- 当前结果：根分区已恢复到可用空间，Redis/worker 已恢复正常

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
