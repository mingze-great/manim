# 项目状态

## 当前任务
在不影响现有 3003 服务和 `codex/3003-standalone-stickman-workflow-20260712` 分支的前提下，基于独立 3004 工作区开发合作者分佣、邀请码自动开通、`/stickman-workflow` 专用素材库管理、火柴人生成高级控制和 3004 隔离部署能力。

## 当前重点
- 当前工作区：`C:\Users\Administrator\Documents\Codex\2026-07-18\300\work\3004-partner-stickman-worktree`
- 当前分支：`codex/3004-partner-stickman-platform-20260724`
- 基线提交：`afb7a9d9832331060a916e96de9712fb8dd6c820`
- 基线提交时间：`2026-07-24T22:15:50+08:00`
- 基线提交信息：`docs: add skill selection levels`
- 3004 远程目标目录：`/opt/manim-v2-3004-snapshot`
- 3004 目标前端端口：`3004`
- 3004 目标后端端口：`8004`
- 3004 目标 Remotion 渲染端口：`18788`
- 3004 目标 Celery 队列：`manim_v2_3004`
- 当前部署前源提交：`4db089f2a8ea8cf6b61ec45b8fb4a710e3e6b84f`
- 当前部署前源提交时间：`2026-07-25 00:04:13 +08:00`
- 当前部署前源提交信息：`feat: add partner and stickman workflow UI`
- 当前已部署提交：`8e776f5bb7fa79a33710910b759476f9822ad08d`
- 当前已部署提交时间：`2026-07-25T01:59:59+08:00`
- 当前已部署提交信息：`chore: tune 3004 cosyvoice fallback config`
- 当前待部署客户端修复提交：`2afc707db4994aba5cde21c2c8ee5987f8e9a107`
- 当前待部署客户端修复：`backend/app/services/ai_video.py` 将开源 CosyVoice zero-shot 改为受控 `curl --max-time` 下载 PCM，避免 Python `requests` 等待流关闭导致 worker 卡住。
- 状态更新时间：`2026-07-25 02:12:30 +08:00`

## 已完成
- 已确认现有 3003 分支保持不动，3004 使用独立 git worktree。
- 已创建 3004 专用分支 `codex/3004-partner-stickman-platform-20260724`。
- 已确认 `/stickman-workflow` 当前只把 `materialLibrary` 作为字符串传给 AI video job。
- 已确认现有后台 zip 上传接口属于 `/admin/stickman-v2/scene-style-libraries`，不是 `/stickman-workflow` 专用素材库管理。
- 已决定新增 `stickman-workflow` 专用素材库管理，不混用 `stickman_v2` 配置。
- 已完成新 worktree 基线检查：`python -m py_compile backend/app/api/stickman_workflow.py backend/app/services/stickman_v2_assets.py backend/app/models/user.py backend/app/models/subscription.py` 通过，`git diff --check` 通过。
- 已新增 3004 专用 nginx、systemd、环境示例和部署脚本，目标路径和服务均指向 3004。
- 已新增合作者、推荐码、邀请码和佣金台账基础模型。
- 已扩展用户和订单模型，支持推荐归因与佣金状态。
- 已为新增用户/订单字段补充启动迁移逻辑。
- 已通过 TDD 验证：`pytest backend/tests/test_partner_models_import.py -q` 通过。
- 已新增合作者服务层、合作者工作台 API、后台 partner/invite/commission API 和兑换码开通接口。
- 已接入注册推荐码归因和支付成功佣金台账记录。
- 已通过 TDD 验证：`pytest backend/tests/test_partner_program_service.py backend/tests/test_partner_models_import.py -q` 通过。
- 已新增 `/stickman-workflow` 专用素材库服务，使用独立配置 key 和独立上传目录。
- 已新增后台 `/admin/stickman-workflow/material-libraries` 系列接口，避免误用 `stickman-v2` 配置。
- 已新增用户端 `/stickman-workflow/config`，返回素材库、声音和能力配置。
- 已将 `/stickman-workflow/jobs` 的素材库选择改为先校验专用素材库，再传递素材库路径和 manifest。
- 已通过 TDD 验证：`pytest backend/tests/test_stickman_workflow_assets.py backend/tests/test_partner_program_service.py backend/tests/test_partner_models_import.py -q` 通过。
- 已新增火柴人工作流时长预估和互斥校验服务。
- 已扩展 `/stickman-workflow/jobs` 支持 `scriptMode`、`customScript`、`targetSeconds`、`backgroundMode`、`backgroundTemplate`、`uploadedBackgroundUrl` 和 `imageMode`。
- 已强制自定义文案和目标时长互斥，并限制普通用户默认不能使用实时生图模式。
- 已通过 TDD 验证：`pytest backend/tests/test_stickman_workflow_limits.py backend/tests/test_stickman_workflow_assets.py backend/tests/test_partner_program_service.py backend/tests/test_partner_models_import.py -q` 通过。
- 已新增前端 `/partner` 合作者工作台入口，合作者和管理员可查看推荐用户、订单、佣金，并生成兑换码。
- 已新增后台 `/admin/partners` 合作者管理页，支持创建合作者、筛选推荐用户、查看佣金台账、生成后台兑换码。
- 已新增后台 `/admin/stickman-workflow-libraries`，专门管理 `/stickman-workflow` 素材库 zip，明确不使用 `stickman-v2` 的素材库接口。
- 已扩展 `/stickman-workflow` 前端高级控制：自定义文案、目标时长、画面模式、背景模式、声音和专用素材库选择；默认仍可只输入标题生成。
- 已修正合作者 profile 返回真实 `referral_code`，前端复制推广链接时不再用 profile id 拼假码。
- 已完成本地验证：
  - `npm run build` 通过，Vite 仅提示既有大 chunk 警告。
  - `pytest backend/tests/test_partner_models_import.py backend/tests/test_partner_program_service.py backend/tests/test_stickman_workflow_assets.py backend/tests/test_stickman_workflow_limits.py -q` 通过，结果 `7 passed`。
  - `python -m py_compile backend/app/models/partner.py backend/app/services/partner_program.py backend/app/services/stickman_workflow_assets.py backend/app/services/stickman_workflow_limits.py backend/app/api/partner.py backend/app/api/stickman_workflow.py backend/app/api/admin.py backend/app/api/payment.py backend/app/main.py` 通过。
  - `git diff --check` 通过，仅有 CRLF/LF 替换提示。
- 已提交前端阶段：`4db089f2a8ea8cf6b61ec45b8fb4a710e3e6b84f`（`feat: add partner and stickman workflow UI`）。
- 部署前准备：下一步推送 `codex/3004-partner-stickman-platform-20260724` 到远程，并执行 3004 专用部署脚本。
- 已提交部署前状态记录：`51ccd96fcbb7d9028c5ee880a7423b38b3977e19`（`docs: record 3004 deployment preflight`）。
- 已通过归档快照方式部署到 `/opt/manim-v2-3004-snapshot`，部署标记文件 `.deployed-ref` 记录分支 `codex/3004-partner-stickman-platform-20260724` 和提交 `51ccd96fcbb7d9028c5ee880a7423b38b3977e19`。
- 已验证 3004 三个服务 active：`manim-v2-3004-backend.service`、`manim-v2-3004-worker.service`、`manim-v2-3004-ai-video-render.service`；`http://127.0.0.1:8004/health` 返回 healthy；`http://127.0.0.1:3004/` 返回 200。
- 已验证 3003 前端仍返回 200，3003 backend/worker active；3003 render 服务当时为 `activating`，未修改或重启 3003。
- 已创建 3004 平台验证任务 `job_1`，标题为“为什么你越想证明自己，越容易陷入内耗”。
- `job_1` 失败根因已定位：SC1 场景图传给 Remotion 的 URL 为相对 `/sc1-materials/...`，被 Remotion 解析为 `http://localhost:3000/public/sc1-materials/...`，导致渲染取图失败。
- 当前修复：`backend/app/services/ai_video.py` 改为用 `SC1_MATERIAL_PUBLIC_BASE_URL` 生成绝对素材 URL，并让默认值跟随 `AI_VIDEO_RENDER_SERVICE_URL`；3004 backend/worker service 显式设置到 `http://127.0.0.1:18788`。
- 当前修复已通过本地验证：
  - 新增回归测试 `backend/tests/test_ai_video_sc1_material_urls.py`，先复现失败，再修复通过。
  - `pytest backend/tests/test_ai_video_sc1_material_urls.py backend/tests/test_partner_models_import.py backend/tests/test_partner_program_service.py backend/tests/test_stickman_workflow_assets.py backend/tests/test_stickman_workflow_limits.py -q` 通过，结果 `8 passed`。
  - `python -m py_compile backend/app/services/ai_video.py backend/app/api/stickman_workflow.py backend/app/api/partner.py backend/app/api/admin.py backend/app/main.py` 通过。
  - `git diff --check` 通过，仅有 CRLF/LF 替换提示。
- 已提交并部署 SC1 素材 URL 修复：`8ef8e7628b61f65d16fc4b435ce41b2948bb5954`（`fix: use render service urls for sc1 materials`）。
- 3004 远程部署标记 `/opt/manim-v2-3004-snapshot/.deployed-ref` 已记录分支 `codex/3004-partner-stickman-platform-20260724`、提交 `8ef8e7628b61f65d16fc4b435ce41b2948bb5954`、部署时间 `2026-07-25 00:40:50 +0800`。
- 已验证 3004 后端、worker、Remotion 渲染服务均为 active；`http://127.0.0.1:8004/health` 和 `http://127.0.0.1:18788/api/health` 正常。
- 已定位并处理 3004 登录 500 的环境问题：远程根分区 40G 已满，SQLite 写入审计日志失败，报错 `sqlite3.OperationalError: database or disk is full`。
- 已仅清理可再生临时文件和日志：`/tmp/3003-deploy-worktree.tar.gz`、`/tmp/sc1-outputs-20260713_233032.tar.gz`、`/tmp/manim-v2-3004-snapshot-*.tar`、`/tmp/remotion-webpack-bundle-*`、`/root/.npm/_cacache`、`/root/.cache/whisper`，并将 journal vacuum 到约 200M；未修改、重启或删除 3003 部署代码。
- 清理后远程根分区恢复到约 1.2G 可用，3004 登录和 `/api/stickman-workflow/config` 恢复 200。
- 已创建 3004 平台验证任务 `job_5`，标题为“为什么你越想证明自己，越容易陷入内耗”，使用 `dayun_manbo` 声音和 `sc1_outputs` 素材库。
- `job_5` 失败根因已定位：Dayun Manbo TTS 接口返回 `HTTP Error 429: Too Many Requests`，任务在 `tts_generating` 阶段失败。
- 当前待提交修复：`backend/app/services/ai_video.py` 在 `dayun_manbo` provider 遇到请求失败/限流时，自动降级到现有开源 CosyVoice zero-shot 参考音色路径继续生成音频，不再让整条任务失败。
- 已新增回归测试：`backend/tests/test_ai_video_sc1_material_urls.py::test_dayun_manbo_tts_rate_limit_falls_back_to_open_source_cosyvoice`。
- 当前待提交修复已通过本地验证：
  - `PYTHONPATH=backend pytest backend/tests/test_ai_video_sc1_material_urls.py backend/tests/test_partner_models_import.py backend/tests/test_partner_program_service.py backend/tests/test_stickman_workflow_assets.py backend/tests/test_stickman_workflow_limits.py -q` 通过，结果 `9 passed`，仅有本地 ffmpeg path warning。
  - `python -m py_compile backend/app/services/ai_video.py backend/app/api/stickman_workflow.py backend/app/api/partner.py backend/app/api/admin.py backend/app/main.py` 通过。
  - `git diff --check` 通过。
- 已确认远程 3004 部署标记为 `codex/3004-partner-stickman-platform-20260724@c696bd4633c2e07c57a785833508e7f47a6033ac`，3004 backend、worker、Remotion 服务 active，3003 未修改、未重启。
- 已定位 `job_6` 后续 TTS 失败链路：Dayun 远程请求仍 429；开源 CosyVoice SFT 因无 speaker 不可用；zero-shot 依赖参考音频和较长生成时间。
- 已用远程 CosyVoice zero-shot 直接验证 `dayun_tools_manbo_tts_test.mp3` 可作为 prompt 产出音频，探针输出 `/tmp/cosy_dayun_probe_py.pcm` 为 `158720` 字节。
- 已同步并部署 3004 配置提交 `8e776f5bb7fa79a33710910b759476f9822ad08d`：backend/worker 显式设置 `AI_VIDEO_COSYVOICE_TIMEOUT=180`，并将 zero-shot prompt 固定为 `/opt/manim-v2-3004-snapshot/outputs/dayun_tools_manbo_tts_test.mp3`。
- 已创建 3004 平台验证任务 `job_7`；任务进入第一个 cue 的 open-source CosyVoice fallback 后未推进。CosyVoice 日志显示 `POST /inference_zero_shot HTTP/1.1 200 OK` 且后续吐出音频 blob，但 job 目录未写入音频文件，根因进一步收敛为 Python 客户端等待流关闭。
- 已新增回归测试 `test_open_source_cosyvoice_accepts_valid_pcm_when_stream_times_out`，覆盖 curl 返回 timeout 但已写出有效 PCM 时仍接受音频，避免任务卡死；相关测试 `10 passed`。

## 当前问题
- 3004 已部署到 `8e776f5bb7fa79a33710910b759476f9822ad08d`；`job_7` 显示配置已生效，但 Python `requests` 客户端仍会等 CosyVoice zero-shot 流关闭，导致 worker 停在 `tts_generating`。
- 当前待部署客户端修复已本地验证通过；下一步需要同步 `backend/app/services/ai_video.py` 和测试/状态文件到 3004，并重启 3004 backend/worker 后创建 `job_8` 验证。
- 3004 还没有完成“成功成片 + 下载 MP4 + 音视频流检查 + 抽帧确认”的最终验收。
- 远程磁盘空间仍偏紧（清理后约 1.2G 可用），若 Remotion 渲染再次因空间不足失败，需要优先清理 3004 可再生构建缓存或旧备份，仍不能影响 3003 运行数据。
- 参考图生成完整素材库的“两张样图确认 -> 批量生成”能力仍属于第二阶段，当前 MVP 先交付上传 zip 和选择素材库。

## 最近修改文件
- `PROJECT_STATE.md`
- `docs/superpowers/specs/2026-07-24-3004-partner-stickman-workflow-design.md`
- `docs/superpowers/plans/2026-07-24-3004-partner-stickman-workflow-mvp.md`
- `deploy/manim-v2-3004.conf`
- `deploy/manim-v2-3004-backend.service`
- `deploy/manim-v2-3004-worker.service`
- `deploy/manim-v2-3004-ai-video-render.service`
- `deploy/env.backend.3004.example`
- `deploy/env.frontend.3004.example`
- `deploy/deploy-v2-3004.sh`
- `backend/app/models/partner.py`
- `backend/app/models/user.py`
- `backend/app/models/subscription.py`
- `backend/app/models/__init__.py`
- `backend/app/schemas/user.py`
- `backend/app/main.py`
- `backend/tests/test_partner_models_import.py`
- `backend/app/services/partner_program.py`
- `backend/app/api/partner.py`
- `backend/app/api/auth.py`
- `backend/app/api/payment.py`
- `backend/app/api/admin.py`
- `backend/tests/test_partner_program_service.py`
- `backend/app/services/stickman_workflow_assets.py`
- `backend/app/api/stickman_workflow.py`
- `backend/tests/test_stickman_workflow_assets.py`
- `backend/app/services/stickman_workflow_limits.py`
- `backend/tests/test_stickman_workflow_limits.py`
- `frontend/src/services/partner.ts`
- `frontend/src/services/admin.ts`
- `frontend/src/services/stickmanWorkflow.ts`
- `frontend/src/stores/authStore.ts`
- `frontend/src/App.tsx`
- `frontend/src/components/Layout/MainLayout.tsx`
- `frontend/src/components/Layout/AdminLayout.tsx`
- `frontend/src/pages/PartnerDashboard.tsx`
- `frontend/src/pages/admin/AdminPartners.tsx`
- `frontend/src/pages/admin/AdminStickmanWorkflowLibraries.tsx`
- `frontend/src/pages/StickmanWorkflow/index.tsx`
- `frontend/src/pages/StickmanWorkflow/StickmanWorkflow.css`
- `backend/app/services/ai_video.py`
- `backend/tests/test_ai_video_sc1_material_urls.py`
- `deploy/manim-v2-3004-backend.service`
- `deploy/manim-v2-3004-worker.service`
- `deploy/env.backend.3004.example`

## 重要技术决策
- 3004 必须隔离部署，不能修改或重启现有 3003 服务。
- 合作者不使用管理员账号，新增非敏感的 `partner` 角色和 `/partner` 工作台。
- 用户微信付款后优先自动开通；线下收款用邀请码/兑换码开通，邀请码绑定套餐、期限、模式、额度和推荐人。
- `/stickman-workflow` 使用专用素材库系统，后台接口命名为 `/admin/stickman-workflow/material-libraries`，前台配置接口命名为 `/stickman-workflow/config`。
- 自定义文案和选择视频时长互斥：用户输入文案时由文案和 TTS 估算/校准时长；用户选择时长时只能 AI 生成文案。
- 套餐能力区分素材库模式和实时生图模式；素材库模式下实时生图能力对用户透明且不可见。
- 后台素材库生成采用“两张样图确认 -> 批量生成完整素材库 -> 生成 material.json -> 后台启用”的流程。
- Dayun Manbo 是默认参考音色；如果 Dayun 接口 429 或不可用，3004 生成链路允许透明降级到现有开源 CosyVoice zero-shot 参考音色路径，优先保证平台一键成片完成。

## 不要重复做
- 不要把 `/admin/stickman-v2/scene-style-libraries` 当作 `/stickman-workflow` 的后台素材库上传。
- 不要直接修改、部署或重启 3003。
- 不要提交密钥、生成成片、上传缓存、storage、uploads 或临时构建产物。
- 不要让合作者进入 `/admin` 或看到全局用户、收入、密钥、系统配置。
- 不要在未更新 `PROJECT_STATE.md` 的情况下进行远程同步、部署或上下文交接。

## 下一步
1. 提交 open-source CosyVoice zero-shot curl 客户端修复和本状态记录。
2. 同步 `backend/app/services/ai_video.py`、`backend/tests/test_ai_video_sc1_material_urls.py`、`PROJECT_STATE.md` 到 3004，并仅重启 3004 backend/worker。
3. 重新创建 3004 `/stickman-workflow` 标题生成任务 `job_8`，优先使用 `dayun_manbo` 声音和 `sc1_outputs` 素材库。
4. 下载成功 MP4，使用 ffmpeg/ffprobe 检查音频流和视频流，抽取关键帧确认场景图、字幕、总结和标签布局，并记录 job id、输出路径、验证结论。
