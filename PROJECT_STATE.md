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
- 当前待部署客户端修复提交：`7c3c74bdaef302d8794d727602d74bd97928fe7a`
- 当前待部署客户端修复：`backend/app/services/ai_video.py` 将开源 CosyVoice zero-shot 改为受控 `curl --max-time` 下载 PCM，避免 Python `requests` 等待流关闭导致 worker 卡住。
- 状态更新时间：`2026-07-25 02:21:40 +08:00`

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
- 已同步并部署 3004 配置提交 `8e776f5bb7fa79a33710910b759476f9822ad08d`：backend/worker 显式设置 `AI_VIDEO_COSYVOICE_TIMEOUT=180`，并将 zero-shot prompt 固定为 `/opt/manim-v2-3004-snapshot/outputs/cosyvoice_zero_shot_sample.wav`。
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

## 2026-07-25 20:05 CosyVoice 事故复盘与预防
- 当前分支：`codex/3004-partner-stickman-platform-20260724`
- 当前本地 HEAD：`b37e1bbcc67d9767766efac809f6bd1c9a199bb3`（`docs: record interrupted 3004 deployment`）
- 3004 当前部署标记：远程 `.deployed-ref` 曾确认 `codex/3004-partner-stickman-platform-20260724@e8683916d7b386cbac2629b28ca42a15fe970d9c`，`source_commit=a30bd440e00ec3d27273447cf05281fd27fdd475`。
- 已完成平台验证：3004 登录、`/api/stickman-workflow/config`、`/api/stickman-workflow/duration-estimate`、`/api/platform-assistant/chat` 均已在平台真实接口验证通过；助手回答能引导用户进入 `/stickman-workflow`。
- 新建 3004 验收用户：`codex_3004_verify_193716`，仅用于 3004 平台闭环测试；已在 3004 SQLite 标记审核通过。
- 新建平台任务：`job_10`，由 3004 `/stickman-workflow/jobs` 创建，任务失败于 `tts_generating`。
- 根因：`job_10` 使用 `dayun_manbo` 时 Dayun 接口不可用/限流后降级到本机 open-source CosyVoice；服务器重启后 `manim-v2-3003-cosyvoice.service` 未可用，随后发现其配置模型目录 `/opt/cosyvoice-3003/pretrained_models/CosyVoice-300M` 缺少 `llm.pt`。
- 事故放大原因：CosyVoice systemd 配置为失败自动重启，启动时反复加载大模型并访问 ModelScope/wetext，导致腾讯云小规格主机出现高 I/O/CPU/用户态卡顿；表现为 ICMP 和 TCP 端口可达，但 SSH 卡在 banner exchange，3003/3004 HTTP 应用层无响应。
- 已尝试恢复动作：向远程发送 `systemctl disable --now manim-v2-3003-cosyvoice.service` 与 `pkill -9` 残留进程命令；由于当时 SSH stdout 不可靠，不能确认完全生效。
- 当前阻塞：用户重启后，公网 `3003` 和 `3004` 仍 HTTP 超时；`22` 与 `3004` TCP 握手成功，但 SSH banner exchange 仍超时。说明系统仍处于用户态/I/O 卡住或重启未完全恢复状态，暂不能继续部署或创建生成任务。
- 必须预防：
  1. 服务器恢复后第一步确认并禁用 `manim-v2-3003-cosyvoice.service` 自动启动，除非模型文件完整且健康检查稳定。
  2. 3004 平台代码不得在生成任务中隐式拉起或依赖这个本机 CosyVoice 服务；调用前必须做短超时健康检查。
  3. `dayun_manbo` 失败时，3004 应优先使用轻量、外部、可超时的 TTS fallback；如果无可用 TTS，任务要快速失败并提示“音频服务不可用”，不能触发大模型本地服务导致整机不可用。
  4. CosyVoice 如后续继续使用，必须独立 3004 服务名、独立端口、`Restart=on-failure` 限制重启频率、`StartLimitBurst`、`MemoryMax`、健康检查和完整模型文件校验。
- 本地防护实现：`backend/app/services/ai_video.py` 已新增 open-source CosyVoice 健康闸门，任何 SFT/zero-shot 调用前先请求 `/docs`，默认 2 秒超时；不健康时快速失败，避免触发本机重型 TTS fallback。
- 本地防护实现：`dayun_manbo` 或 DashScope 失败后优先降级到轻量 `edge_tts` 并输出真实 wav；只有 Edge TTS 也失败时才尝试经过健康闸门的本机 open-source CosyVoice。
- 本地回归测试：`backend/tests/test_ai_video_sc1_material_urls.py` 已新增健康失败用例、Edge 优先 fallback 用例、Edge 失败后才尝试本机 CosyVoice 用例。
- 本地验证：`PYTHONPATH=backend pytest backend/tests/test_ai_video_sc1_material_urls.py -q` -> `16 passed`；`python -m py_compile backend/app/services/ai_video.py` 通过；`git diff --check` 通过。
- 本地扩展验证：`PYTHONPATH=backend pytest backend/tests/test_platform_assistant.py backend/tests/test_image_gen_service.py backend/tests/test_material_library_generation.py backend/tests/test_ai_video_sc1_material_urls.py backend/tests/test_partner_models_import.py backend/tests/test_partner_program_service.py backend/tests/test_stickman_workflow_assets.py backend/tests/test_stickman_workflow_limits.py -q` -> `39 passed`。
- 本地提交：`0bd033d`（`fix: guard local cosyvoice fallback health`）、`555a829`（`fix: prefer edge tts fallback before local cosyvoice`）、`90d3872`（`docs: record cosyvoice fallback safeguards`）。
- GitHub 同步：`git push origin codex/3004-partner-stickman-platform-20260724` 在 180 秒后超时，不能确认远程分支已更新；服务器恢复后优先使用 `git archive`/SFTP 方式同步到 3004 部署目录。
- 2026-07-25 22:20 恢复后已确认：`manim-v2-3003-cosyvoice.service` 为 `disabled/inactive`，50000 未监听；3003/3004 主服务均 active；3004 已部署到 `be28bd759066e45c8a2aa981259483f9aad9de8d`。
- 平台任务 `job_11` 创建成功但失败于 TTS：Dayun 不可用、Edge TTS 返回 403、本机 CosyVoice 被健康闸门拒绝。此失败没有拖垮服务器，证明健康闸门有效。
- 本地新增修复：安全 TTS fallback 顺序改为 `DashScope CosyVoice -> Edge TTS -> 健康的本机 CosyVoice`。DashScope 使用服务器环境变量，不写代码、不提交密钥。
- 本地验证：`PYTHONPATH=backend pytest backend/tests/test_ai_video_sc1_material_urls.py -q` -> `16 passed`；`python -m py_compile backend/app/services/ai_video.py` 通过；`git diff --check` 通过。
- 3004 已配置 DashScope TTS 环境变量到 systemd drop-in，只在服务器环境保存，代码和提交不包含密钥；已部署 `b4c2d6c1d43d663e3d07e4c402c1ac2860db3f7b`。
- 平台任务 `job_12` 已推进到渲染前素材预检，失败原因为远程素材库实际存在 `materials.generated.json` 和 `psychology-stickman-18-*.png` 命名文件，但配置传入缺失的 `material.json`，导致代码回退到 `18.png` 等兜底文件名。
- 本地新增修复：`_sc1_material_paths` 在显式 manifest 不存在时，会回退同目录 `materials.generated.json`、`materials.json`、`material.json`；新增回归测试覆盖该路径。
- 本地验证：`PYTHONPATH=backend pytest backend/tests/test_ai_video_sc1_material_urls.py -q` -> `17 passed`；`python -m py_compile backend/app/services/ai_video.py` 通过；`git diff --check` 通过。
- 3004 已部署素材 manifest 修复提交：`a4598d0e22fbb36552d491220b9579219163539a`，部署时间 `2026-07-25T22:35:19+08:00`，只重启 3004 backend/worker，3003 未重启。
- 平台闭环成功任务：`job_13`，状态 `completed`，输出 URL `/api/ai-video/files/13/output/video.mp4`。
- 本地下载成片：`C:\Users\Administrator\Documents\Codex\2026-07-18\300\outputs\3004_job_13_validation\job_13.mp4`，大小 `1806529` 字节。
- ffmpeg 验证：视频时长 `00:00:24.68`；视频流 H.264 1920x1080 30fps；音频流 AAC 48000Hz stereo，确认有视频流和音频流。
- 抽帧验证：`frame_01s.png`、`frame_08s.png`、`frame_16s.png`、`frame_24s.png` 均显示单张居中完整场景图，没有被横线/字幕/白色面板遮挡；右上角 `心理分享 | 认知突破` 可见；无 `@Sc1火柴人`；字幕居中；总结为 2-4 字短词并在段内累计展示。
- 当前可访问平台：`http://152.136.218.74:3004`；3003 验证仍返回 200，未做 3003 部署。
- 当前本地状态提交：`589c467`（`docs: record 3004 job 13 validation`）。
- GitHub 同步：再次执行 `git push origin codex/3004-partner-stickman-platform-20260724`，180 秒后超时，不能确认 GitHub 远程分支已更新；当前可复现锚点以本地 worktree 与 3004 `.deployed-ref` 为准。

## 2026-07-25 3004 数据库迁移修复
- 用户反馈：3004 登录不上，怀疑未迁移 3003 数据库。
- 排查结论：3004 `.env` 指向 `/opt/manim-v2-3004-snapshot/backend/manim_platform_3004.db`，该库只有 3 个测试用户；3003 实际服务使用 `/opt/manim/backend/manim.db`，不是 3003 快照目录里的空库。
- 3003 实际库用户数：`56`，包含原 `admin`、`myoung` 等账号。
- 修复计划：只停止/重启 3004 backend 与 worker；备份当前 3004 SQLite；用 SQLite online backup 从 `/opt/manim/backend/manim.db` 复制到 3004 数据库路径；启动 3004 后由当前代码自动补齐合作者、邀请码、素材库、AI 助手、火柴人控制等新增表和字段；不修改、不重启 3003。
- 已执行迁移：停止 3004 backend/worker，备份旧 3004 库为 `/opt/manim-v2-3004-snapshot/backend/manim_platform_3004.pre-3003-migration.20260725_225135.db`，使用 SQLite `.backup` 从 `/opt/manim/backend/manim.db` 复制到 `/opt/manim-v2-3004-snapshot/backend/manim_platform_3004.db`，再启动 3004 backend/worker。
- 迁移后验证：3004 数据库用户数为 `56`；`users` 已补齐 `role`、`is_approved`、`module_permissions_json`、`referred_by_partner_id`、`referral_code` 等新字段；合作者/邀请码/佣金表 `partner_profiles`、`referral_codes`、`invite_codes`、`commission_ledgers` 存在；素材库生成表 `material_library_generations` 存在。
- 服务验证：3004 backend/worker/render 均 `active`；`http://152.136.218.74:3004` 返回 200；`http://152.136.218.74:3003` 返回 200；3003 未部署、未重启。
- 注意：3004 现在继承 3003 账号状态，只有 `is_active=1` 且 `is_approved=1` 的账号可登录；未审核账号仍会按平台规则被拦截。
- 下一步恢复顺序：
  1. 等腾讯云 SSH banner 恢复或由控制台强制关机开机。
  2. 先确认 `manim-v2-3003-cosyvoice.service` disabled/inactive，杀掉所有 `cosyvoice3003` 残留进程。
  3. 确认 3003/3004 HTTP 恢复，且 3003 不做业务部署。
  4. 提交本地防护代码并部署到 3004。
  5. 部署到 3004 后重新创建平台任务，完成 MP4 下载、ffprobe 和抽帧验收。

## 2026-07-25 16:10 远程卡顿排查与清理
- 当前分支：`codex/3004-partner-stickman-platform-20260724`
- 当前本地 HEAD：`7c3c74bdaef302d8794d727602d74bd97928fe7a`
- 远程排查：`/` 分区 40GB 中已用 37GB，最初仅剩 832MB，确认接近满盘，是任务生成、Remotion 渲染和构建卡住的高风险原因。
- 已清理：`/tmp` 旧 `pymp-*`、Remotion 临时包、旧 frame 目录、apt/pip/npm/conda/journal 缓存、`/var/lib/snapd/cache`。
- 已清理：旧服务 `/opt/manim-v2/backend/videos` 中 7 天前历史生成视频 1020 个，释放约 3166.0MB；保留最近 7 天 16 个视频。
- 清理后验证：`/` 分区可用空间提升到 5.6GB，使用率降到 86%，inode 使用率 25%。
- 服务验证：3004 backend、worker、ai-video-render 均为 active；`http://127.0.0.1:8004/health` 和 `http://127.0.0.1:18788/api/health` 正常。
- 3003 保护验证：3003 backend、worker 正常；3003 render 健康接口正常。未修改 3003 部署代码。
- 发现问题：3004 render 的 `/sc1-materials/*` 响应缺少 CORS 头，日志存在 Remotion 加载素材图被 CORS 拦截，可能导致成片场景图缺失或任务卡住。
- 本地修复：`video-render-service/remotion-mind-video/server.js` 新增全局 CORS 中间件，准备同步到 3004，不触碰 3003 部署逻辑。

## 2026-07-25 16:25 3004 CORS 热修同步验证
- 已同步到远程：`/opt/manim-v2-3004-snapshot/video-render-service/remotion-mind-video/server.js`
- 已重启服务：`manim-v2-3004-ai-video-render.service`
- 验证结果：3004 render service 为 `active`，`/api/health` 正常。
- 验证结果：`/sc1-materials/psychology-stickman-14-digital-overload.png` 已返回 `Access-Control-Allow-Origin: *`、`Access-Control-Allow-Methods: GET,POST,OPTIONS`、`Access-Control-Allow-Headers: Content-Type, Authorization`。
- 验证结果：3004 backend、worker、render 均为 `active`；公网 `http://152.136.218.74:3004` 返回 200。
- 当前磁盘：`/` 分区 40GB，已用 32GB，可用 5.6GB，使用率 86%。
- 注意：本次只热修 3004 render CORS 和清理服务器空间；未重启 3003，未删除 3003/3004 部署目录或素材库。

## 2026-07-25 16:45 3004 平台助手与本地验证
- 当前分支：`codex/3004-partner-stickman-platform-20260724`
- 提交前 HEAD：`7c3c74bdaef302d8794d727602d74bd97928fe7a`
- 已完成：新增后端平台助手接口 `/api/platform-assistant/chat` 与文档知识库检索服务。
- 已完成：新增登录后全局悬浮 AI 助手，支持当前页面 path、快捷问题、来源标签、平台入口按钮和兜底回答。
- 已完成：补充 `rules/quality-gates.md` 与 `rules/vibe-coding.md`，明确面向用户需求必须通过平台闭环验证，不能只用本地脚本替代。
- 已完成：保留 3004 火柴人高级控制、合作者/邀请码、素材库、背景、AI 生图 payload、CORS 热修等改动，不触碰 3003。
- 本地验证：`pytest backend/tests/test_platform_assistant.py backend/tests/test_image_gen_service.py backend/tests/test_ai_video_sc1_material_urls.py backend/tests/test_partner_models_import.py backend/tests/test_partner_program_service.py backend/tests/test_stickman_workflow_assets.py backend/tests/test_stickman_workflow_limits.py -q` -> 21 passed, 7 warnings。
- 本地验证：`python -m py_compile ...` 覆盖新增后端与相关 API/service 文件 -> 通过。
- 本地验证：`npm run build` in `frontend` -> 通过；仅 Vite chunk size warning。
- 本地验证：`git diff --check` -> 通过；仅换行符提示。
- 密钥检查：提交 diff 未发现 `sk-` 形式密钥；`work/` 临时目录不提交。
- 下一步：提交本地改动，同步 3004 部署目录，只重启 3004 backend/worker/render，随后验证助手问答与 `/stickman-workflow` 平台成片。

## 2026-07-25 3004 第二阶段部署前记录
- 当前工作区：`C:\Users\Administrator\Documents\Codex\2026-07-18\300\work\3004-partner-stickman-worktree`
- 当前分支：`codex/3004-partner-stickman-platform-20260724`
- 提交前 HEAD：`00fa442502503ad2807db0cdc3518cccb66af264`
- 3004 当前部署锚点：`codex/3004-partner-stickman-platform-20260724@00fa442502503ad2807db0cdc3518cccb66af264`，部署时间 `2026-07-25T16:38:00+08:00`。
- 本次待部署：修复 CosyVoice 残缺 PCM 接受、输出全部字幕 cue、全片总结关键词去重、素材缺失预检；新增参考图生成两张样图、确认后批量生成素材库及 `materials.json`；新增自定义文案动态时长估算；补充 AI 助手对推荐归属、分佣、图片套餐和素材库生成流程的知识。
- 本地测试：`pytest backend/tests/test_platform_assistant.py backend/tests/test_image_gen_service.py backend/tests/test_material_library_generation.py backend/tests/test_ai_video_sc1_material_urls.py backend/tests/test_partner_models_import.py backend/tests/test_partner_program_service.py backend/tests/test_stickman_workflow_assets.py backend/tests/test_stickman_workflow_limits.py -q` -> `37 passed`。
- 本地检查：相关后端文件 `python -m py_compile` 通过；`frontend npm run build` 通过，仅有既有 Vite chunk size warning；`git diff --check` 通过；提交差异未发现密钥、服务器密码或用户提供的 API Key。
- 远程部署前体检：根分区可用 5.6GB；3004 backend、worker、render 均为 active；8004 和 18788 健康接口正常。
- 部署边界：只同步 `/opt/manim-v2-3004-snapshot`，只重启 `manim-v2-3004-backend.service`、`manim-v2-3004-worker.service`、`manim-v2-3004-ai-video-render.service`，不修改、不重启 3003。
- 部署后必须完成：确认 Celery 注册 `app.tasks.generate_material_library_celery`；平台登录后验证助手、时长估算、合作者和邀请码；从 `/stickman-workflow` 创建新成片并完成 ffprobe 与关键帧验收。
- 代码审查修复：渲染素材按 job 子目录隔离，避免同名图片跨素材库覆盖；素材库封面 URL 按 library key 隔离；生成样图接口增加管理员鉴权和样图白名单；120 张串行生成任务时限提高为 soft 15000 秒、hard 15600 秒；总结关键词不再从旁白任意截取，改用情绪短词及唯一组合池。
- 本地清理：已删除工作树 `work/` 下旧部署 zip/tar 和一次性探针脚本，并在 `.gitignore` 增加 `/work/`；这些包含环境快照的临时文件未进入提交。
- 本次功能源码提交：`a30bd440e00ec3d27273447cf05281fd27fdd475`（`feat: complete 3004 stickman platform workflow`）。该提交包含成片同步修复、素材库自动生成、动态时长、助手知识和审查整改，是本轮 3004 部署的源码锚点。

## 2026-07-25 远程部署中断记录
- 当前本地 HEAD：`e8683916d7b386cbac2629b28ca42a15fe970d9c`（`docs: record 3004 workflow source anchor`），工作树干净。
- GitHub 推送 `codex/3004-partner-stickman-platform-20260724` 在 120 秒后超时，不能确认 GitHub 远程分支已更新。
- 已将提交 `e8683916d7b386cbac2629b28ca42a15fe970d9c` 的 `git archive` 上传为远程 `/tmp/manim-3004-e868391.tar`。
- 已发起 3004 专用部署命令，内容为：备份 3004 SQLite、解压归档、构建前端、编译检查、仅重启 3004 backend/worker/render、写入 `.deployed-ref`。命令连接随后丢失，未获得可采信 stdout，不能声明部署成功。
- 当前主机网络层可达：ICMP 稳定约 33ms，22/80/3003/3004 均能完成 TCP 握手；但 SSH 持续卡在 banner exchange，3003/3004 HTTP 均无应用层响应，等待数分钟仍未恢复。判断为整机 userland 过载或 I/O/内存卡死，不是单独 3004 路由问题。
- 阿里云控制台浏览器没有登录会话，本机没有阿里云 CLI 或实例控制凭据。未经用户明确允许不能重启整台实例，因为会影响 3003。
- 恢复后第一步：检查 `/opt/manim-v2-3004-snapshot/.deployed-ref`、进程/内存/I/O、构建进程和三个 3004 服务；同时确认 3003 健康。若部署未完成，先终止残留 3004 构建进程，再按提交 `e868391` 重部署。
- 仍未完成：3004 合作者/邀请码真实数据验收、参考图两张样图闭环、AI 助手页面验收、平台创建成片、ffprobe 和抽帧验收。

## 2026-07-25 3004 手机登录、合作者链路、素材库上传与工作流首页优化编码前记录
- 当前任务：只在 3004 分支实现手机号/用户名兼容登录、合作者权限链路收紧、素材库 zip 上传持久化修复、首页/工作流入口结构优化，并完成 3004 平台闭环验收。
- 本地工作区：`C:\Users\Administrator\Documents\Codex\2026-07-18\300\work\3004-partner-stickman-worktree`
- 当前分支：`codex/3004-partner-stickman-platform-20260724`
- 编码前本地 HEAD：`04f0e91d34b6afd972f28c8b330415c43dd95db9`（`docs: record 3004 database migration`，提交时间 `2026-07-25T22:53:32+08:00`）
- 编码前 3004 部署锚点：`/opt/manim-v2-3004-snapshot/.deployed-ref` 记录 `codex/3004-partner-stickman-platform-20260724@a4598d0e22fbb36552d491220b9579219163539a`，部署时间 `2026-07-25T22:35:19+08:00`。
- 编码前远程状态：`/` 分区约 5.5G 可用，3004 backend/worker/render active，3003 backend/worker/render active。
- 部署边界：本轮只同步 `/opt/manim-v2-3004-snapshot`，只允许重启 `manim-v2-3004-backend.service`、`manim-v2-3004-worker.service`、`manim-v2-3004-ai-video-render.service`；不修改、不重启 3003。
- 回退要求：部署前必须备份 3004 SQLite 为 `manim_platform_3004.pre-phone-partner-ui.<timestamp>.db`，并保留上一版 3004 代码快照或 `.deployed-ref` 可恢复锚点。
- 本轮验收必须记录：本地测试/构建结果、部署提交、3004 服务状态、手机号登录验证、合作者授权与兑换码验证、素材库上传刷新验证、`/stickman-workflow` 平台成片 job id、MP4 输出路径和音视频流检查结果。

## 2026-07-25 3004 手机登录、合作者链路、素材库上传与工作流首页优化本地验证记录
- 当前分支：`codex/3004-partner-stickman-platform-20260724`
- 本地验证前 HEAD：`04f0e91d34b6afd972f28c8b330415c43dd95db9`
- 已完成本地改动：手机号/用户名兼容登录；重复手机号登录明确报错；admin 不再通过 partner API 或普通布局进入合作者工作台；合作者工作台仅 partner 角色可见；后台素材库 zip 上传支持自动创建/持久化并返回完整列表；首页新增工作流入口卡片；可选 SMTP 管理员通知服务。
- 本地测试：`PYTHONPATH=backend pytest backend/tests/test_platform_assistant.py backend/tests/test_image_gen_service.py backend/tests/test_material_library_generation.py backend/tests/test_ai_video_sc1_material_urls.py backend/tests/test_auth_partner_access.py backend/tests/test_partner_models_import.py backend/tests/test_partner_program_service.py backend/tests/test_stickman_workflow_assets.py backend/tests/test_stickman_workflow_limits.py backend/tests/test_stickman_workflow_upload_persistence.py -q` -> `45 passed`。
- 本地编译：`python -m py_compile backend/app/api/auth.py backend/app/api/partner.py backend/app/api/admin.py backend/app/api/payment.py backend/app/services/notifications.py` -> 通过。
- 前端构建：`npm run build` in `frontend` -> 通过，仅保留既有 Vite chunk size warning。
- 差异检查：`git diff --check` -> 通过，仅提示 `PROJECT_STATE.md` CRLF 将转 LF。
- 密钥检查：`rg` 仅命中测试用假密钥 `sk-secret` 和 env example 空字段，未发现真实密钥进入本轮 diff。
- 下一步：提交本地改动；部署前备份 3004 SQLite 和代码快照；只同步并重启 3004；在 3004 平台验证登录、合作者兑换码、素材库上传和 `/stickman-workflow` 成片。

## 2026-07-26 00:18 3004 job_91 成片复验与渲染小修
- 当前任务：继续 3004 平台闭环验收；通过真实 `/stickman-workflow` 平台接口创建成片，并修复验收发现的可见问题。
- 当前分支：`codex/3004-partner-stickman-platform-20260724`
- 修复前本地 HEAD：`31b95f9140c59392d2247de682f121e41d0438bf`（`fix: accept bom material manifests`）
- 3004 部署锚点：远程 `/opt/manim-v2-3004-snapshot/.deployed-ref` 记录 `codex/3004-partner-stickman-platform-20260724@31b95f93abf7f97b422ec5f7bbd4632a7c6ed629`，部署时间 `2026-07-26T00:07:33+08:00`。
- 远程状态：3004 backend/worker/render 均 `active`；`http://127.0.0.1:8004/health` 与 `http://127.0.0.1:18788/api/health` 正常；3003 health 返回 `200`，未修改、未重启 3003；根分区约 4.0G 可用。
- 平台任务：使用 3004 用户手机号 `13990040003` 创建 `/stickman-workflow` 任务 `job_91`，标题生成模式、`dayun_manbo`、`sc1_outputs`、`material_only`、目标约 20 秒。
- 平台结果：`job_91` 状态 `completed`，输出 URL `/api/ai-video/files/91/output/video.mp4`，远程路径 `/opt/manim-v2-3004-snapshot/backend/storage/ai-video/tasks/job_91/output/video.mp4`。
- 本地下载：`C:\Users\Administrator\Documents\Codex\2026-07-18\300\outputs\3004_job_91_validation\job_91.mp4`，大小 `1469346` 字节。
- ffprobe：视频 H.264，1920x1080，30fps；音频 AAC，48000Hz，2 声道；时长 `19.179` 秒。
- 抽帧：`frame_01s.png`、`frame_08s.png`、`frame_16s.png`。场景图单张居中完整，未被横线/字幕/白色面板遮挡；右上角 `心理分享 | 认知突破` 可见；无 `@Sc1火柴人`；总结关键词为 2-4 字短词并在分段内累计展示。
- 验收发现：左上角标题显示为 `???????????`，初步判断为本次 PowerShell API 请求体中文编码导致标题入库异常，但渲染层也应兜底；字幕 cue 首尾清洗漏掉中文/英文引号，`job_91` 中段字幕出现前导引号。
- 本地修复：`video-render-service/remotion-mind-video/src/remotion/Sc1StickmanVideo.jsx` 新增字幕首尾引号/标点清洗；左上标题对明显问号乱码使用 `心理火柴人` 兜底，避免平台输出出现乱码。
- 本地验证：`git diff --check` 通过；本地 Remotion 子项目缺 `node_modules`，`npm run build` 失败于 `vite` 不存在，需在 3004 远程部署目录用现有依赖验证构建。
- 下一步：提交本渲染小修，部署到 3004 render 服务，重新创建平台任务并抽帧确认标题不再乱码、字幕无首尾引号。

## 2026-07-26 00:25 3004 job_92 最终平台闭环记录
- 当前任务：完成手机号登录、合作者链路、素材库上传、工作流首页、AI 助手知识库和 SC1 火柴人成片能力在 3004 的平台闭环验收。
- 当前分支：`codex/3004-partner-stickman-platform-20260724`
- 渲染热修提交：`032fb939382d7a05d01ea87f52e1c10f45d50f6b`（`fix: clean sc1 header and subtitle text`）
- 3004 部署目录：`/opt/manim-v2-3004-snapshot`
- 3004 部署标记：`/opt/manim-v2-3004-snapshot/.deployed-ref` 已记录 `branch=codex/3004-partner-stickman-platform-20260724`、`commit=032fb939382d7a05d01ea87f52e1c10f45d50f6b`、`deployed_at=2026-07-26T00:20:00+08:00`。
- 部署动作：只同步 `video-render-service/remotion-mind-video/src/remotion/Sc1StickmanVideo.jsx` 和 `PROJECT_STATE.md` 到 3004；仅重启 `manim-v2-3004-ai-video-render.service`；未修改、未重启 3003。
- 远程构建：在 3004 部署目录执行 `npm run build` 通过，仅有既有 Vite chunk size warning。
- 服务状态：3004 backend/worker/render 均 `active`；`http://127.0.0.1:8004/health` 正常；`http://127.0.0.1:18788/api/health` 正常；3003 health 返回 `200`。
- 磁盘状态：`/` 分区约 3.9G 可用，使用率约 90%，后续批量渲染前仍建议继续清理旧生成物和缓存。
- AI 助手复验：使用 3004 admin 手机号 `13990040001` 登录后调用 `/api/platform-assistant/chat`，问题“我怎么生成心理学火柴人视频”，返回成功并带 `3` 个来源。
- 平台成片任务：使用 3004 用户手机号 `13990040003` 创建 `/stickman-workflow` 任务 `job_92`，标题生成模式、`dayun_manbo`、`sc1_outputs`、`material_only`、目标约 20 秒。
- 任务结果：`job_92` 状态 `completed`，输出 URL `/api/ai-video/files/92/output/video.mp4`，远程路径 `/opt/manim-v2-3004-snapshot/backend/storage/ai-video/tasks/job_92/output/video.mp4`。
- 本地交付文件：`C:\Users\Administrator\Documents\Codex\2026-07-18\300\outputs\3004_job_92_validation\job_92.mp4`，大小 `1466671` 字节。
- ffprobe：视频 H.264，1920x1080，30fps；音频 AAC，48000Hz，2 声道；时长 `19.179` 秒。
- 抽帧文件：`C:\Users\Administrator\Documents\Codex\2026-07-18\300\outputs\3004_job_92_validation\frame_01s.png`、`frame_08s.png`、`frame_16s.png`。
- 抽帧结论：左上角标题不再乱码，显示 `心理火柴人`；右上角 `心理分享 | 认知突破` 可见；场景图单张居中完整，未被横线/字幕/白色面板遮挡；字幕居中且无首尾多余引号/标点；总结关键词为 2-4 字短词并在分段内累计展示；无 `@Sc1火柴人`。
- 已验证的本轮平台能力：手机号/用户名兼容登录；合作者邀请码链路；素材库 zip 上传持久化；工作流首页入口；AI 助手知识库；火柴人标题一键生成成片。
- 远程同步：3004 服务器部署目录已同步；`git push origin codex/3004-partner-stickman-platform-20260724` 失败，错误为 `Recv failure: Connection was reset`，GitHub 远程分支不能确认已更新。
- 不要重复做：不要碰 3003；不要重启或重新启用 `manim-v2-3003-cosyvoice.service`；不要把 3004 的素材库后台接口与旧 `/admin/stickman-v2/scene-style-libraries` 混用。

## 2026-07-26 3004 后台素材库上传与合作者用户选择修复记录
- 当前任务：修复 3004 后台 `/admin/stickman-workflow-libraries` 新增素材库后上传 zip 卡片消失、已有素材库上传不更新，以及 `/admin/partners` 创建合作者时用户选择列表 no data、不能按用户名/手机号搜索的问题。
- 当前分支：`codex/3004-partner-stickman-platform-20260724`
- 修复前本地 HEAD：`8b99ff87d4ce38a082650131a042f4fd51c70a5d`
- 3004 部署前锚点：`/opt/manim-v2-3004-snapshot/.deployed-ref` 记录代码提交 `032fb939382d7a05d01ea87f52e1c10f45d50f6b`，状态提交 `8b99ff87d4ce38a082650131a042f4fd51c70a5d`。
- 根因 1：前端上传素材库 zip 前先调用保存配置；后端规范化素材库配置时会丢弃 `name` 为空的新素材库草稿，如果 zip 随后解析失败，页面会被后端旧列表覆盖，看起来“新增素材库消失”。
- 根因 2：素材库 zip 解析只识别 `material.json/materials.json` 和 `file_name/image_path`，不兼容常见的 `materials.generated.json`、`materials.normalized.json`、`fileName/imagePath` 或包裹在 `materials/items/data` 字段里的清单。
- 根因 3：合作者创建弹窗只依赖初次加载的用户列表，没有远程搜索；在列表为空、加载失败或用户不在前 500 条时，选择框显示 no data。
- 本地修复：`backend/app/services/stickman_workflow_assets.py` 允许空名称草稿以 key 作为名称保存；上传 zip 支持 `materials.generated.json`、`materials.normalized.json`、驼峰字段和对象包裹清单。
- 本地修复：`frontend/src/pages/admin/AdminStickmanWorkflowLibraries.tsx` 上传 zip 不再先保存并覆盖当前列表；上传成功后使用接口返回的完整列表刷新，失败时保留新增草稿。
- 本地修复：`frontend/src/pages/admin/AdminPartners.tsx` 创建合作者弹窗打开时加载候选用户，选择框支持按用户名/手机号远程搜索；`frontend/src/services/admin.ts` 修正用户列表返回类型兼容数组和包装对象。
- 本地验证：`PYTHONPATH=backend pytest backend/tests/test_stickman_workflow_upload_persistence.py -q` -> `4 passed`。
- 本地验证：`python -m py_compile backend/app/services/stickman_workflow_assets.py backend/app/api/admin.py` -> 通过。
- 本地验证：`npm run build` in `frontend` -> 通过，仅有既有 Vite chunk size warning。
- 本地验证：`git diff --check` -> 通过。
- 部署边界：只同步到 `/opt/manim-v2-3004-snapshot`，只重启 3004 backend；如前端 dist 更新由 nginx 静态文件直接生效，不重启 3003。
- 下一步：提交本轮修复，部署 3004，平台验证素材库新增 zip 上传刷新后仍存在、已有库上传计数更新、合作者创建弹窗搜索手机号/用户名有候选用户。

## 2026-07-26 3004 后台修复部署与 UI 验证补充
- 部署提交：`d663b62e1d84311680a2d44054fb3231e20b5d33` 已同步到 `/opt/manim-v2-3004-snapshot`；远程前端 `npm run build` 通过；3004 backend/worker/render 均 active；3004 health 正常；3003 health 返回 `200`。
- 3004 API 验证：上传包含 `materials.generated.json` 和 `fileName/imagePath` 的 zip 到新增素材库 `codex_probe_generated_260058` 返回 `200`，刷新 `/admin/stickman-workflow/material-libraries` 后能查到该素材库，`image_count=1`、`material_count=1`。
- 清理动作：验证用 `codex_probe_generated_*` 素材库已从 3004 配置中移除，避免污染后台列表。
- 3004 API 验证：`/api/admin/users?limit=50&search=13990040002` 和 `/api/admin/users?limit=50&search=codex3004_partner` 均能返回 `codex3004_partner_phone`。
- 浏览器 UI 验证：Playwright 登录 `http://152.136.218.74:3004`，进入 `/admin/partners`，点击“创建合作者”，输入手机号 `13990040002`，下拉可见 `codex3004_partner_phone · 13990040002`。
- 浏览器 UI 验证：进入 `/admin/stickman-workflow-libraries`，点击“新增素材库”，页面出现新的素材库草稿卡片，上传 zip 按钮仍存在；截图保存到 `C:\Users\Administrator\Documents\Codex\2026-07-18\300\outputs\3004_admin_fix_ui.png`。
- 额外发现：浏览器控制台出现 React #31，根因为部分后台接口错误 `detail` 可能是对象/数组，前端直接传给 `message.error` 渲染。
- 本地补充修复：`AdminStickmanWorkflowLibraries.tsx` 和 `AdminPartners.tsx` 新增错误消息格式化，保证对象/数组型错误被转成中文字符串。
- 本地验证：补充修复后 `npm run build` in `frontend` -> 通过，仅有既有 Vite chunk size warning；`git diff --check` -> 通过。
- 已部署补充前端修复：提交 `2e98a26bced0544ad31652c6b84da66075c13250` 已同步到 3004；远程前端 `npm run build` 通过；3004 health 正常；3003 health 返回 `200`。
- 浏览器复验：合作者搜索与素材库新增草稿仍通过，React #31 已消失；剩余发现为旧素材库封面 `/api/admin/stickman-workflow/assets/material-libraries/codex_verify_library_bom/scene.png` 经过公网 3004 返回 nginx 404。
- nginx 根因：3004 nginx `location /api` 会被后面的静态图片正则 location 抢走，导致 `/api/.../*.png` 未代理到 backend；backend 本地 `127.0.0.1:8004` 对同一路径返回 `200`。
- 本地修复：`deploy/manim-v2-3004.conf` 将 `location /api` 改为 `location ^~ /api`，确保 `/api` 下图片资源优先代理到 3004 backend；该修复只用于 3004。
- 已部署 nginx 配置修复：提交 `50fcf0933d29fcfb0fcec0010f44ddf2bcfa6790` 已同步 3004，`nginx -t` 通过并 reload；公网 3004 素材库封面 URL 返回 `200`；3004 health 正常；3003 health 返回 `200`。
- 最终 UI 复验又发现：`/admin/partners` 初始化调用 `/api/admin/users?limit=500`，但后端 `limit` 最大为 `100`，导致 422；这是创建合作者弹窗 no data 的直接原因之一。
- 本地修复：`AdminPartners.tsx` 初始化用户列表改为 `limit=100`，远程搜索仍按用户名/手机号查询；本地 `npm run build` 通过，`git diff --check` 通过。
- 下一步：提交并部署最终前端修复到 3004，再用浏览器确认合作者搜索、素材库新增草稿、素材封面和控制台错误均正常。

## 2026-07-26 01:25 3004 后台素材库与合作者最终验收
- 最终部署提交：`7e2b486aab7d6a9666247ae27e3e6332e9628f8d`（`fix: keep admin user lookup within api limits`）。
- 3004 部署标记：`/opt/manim-v2-3004-snapshot/.deployed-ref` 已记录 `commit=7e2b486aab7d6a9666247ae27e3e6332e9628f8d`，部署时间 `2026-07-26T01:23:00+08:00`。
- 远程构建：3004 前端 `npm run build` 通过，仅有既有 chunk size warning。
- 服务验证：3004 backend/worker/render 均 active；`http://127.0.0.1:8004/health` 正常；3003 health 返回 `200`，未部署或重启 3003。
- 素材库上传验证：3004 API 已验证新增素材库 zip 上传成功，支持 `materials.generated.json` 和 `fileName/imagePath`；刷新后素材库仍存在并有 `image_count=1`、`material_count=1`。
- 素材库预览验证：3004 nginx 已修复 `/api/.../*.png` 代理优先级，公网素材库封面 URL 返回 `200`。
- 合作者验证：浏览器登录 3004 admin 后进入 `/admin/partners`，点击“创建合作者”，输入手机号 `13990040002`，下拉可见 `codex3004_partner_phone · 13990040002`。
- 素材库 UI 验证：浏览器进入 `/admin/stickman-workflow-libraries`，点击“新增素材库”，新增草稿卡片可见且“上传素材库 zip”按钮仍存在，不再消失。
- 浏览器控制台验证：最终 Playwright 复验 `badResponses=[]`，`meaningfulConsoleErrors=[]`；截图保存到 `C:\Users\Administrator\Documents\Codex\2026-07-18\300\outputs\3004_admin_fix_ui_final_clean.png`。
- 注意：验证用 `codex_probe_generated_*` 素材库已清理；保留原 `codex_verify_library_bom` 测试库。
- GitHub 同步：`git push origin codex/3004-partner-stickman-platform-20260724` 执行 180 秒后超时，不能确认 GitHub 远程分支已更新；当前可复现锚点以本地 worktree 与 3004 `.deployed-ref` 为准。

# 2026-07-26 3004 用户详情、AI 助手动效、素材库 422 与模块可见性优化编码前记录

- 当前任务：只在 3004 分支和部署目录实施后台用户详情页、AI 助手卡通动效、素材库 FormData 422 修复、AI 视频导演/知识 IP admin-only 可见性；不修改、不部署、不重启 3003。
- 本地工作区：`C:\Users\Administrator\Documents\Codex\2026-07-18\300\work\3004-partner-stickman-worktree`。
- 本地分支：`codex/3004-partner-stickman-platform-20260724`。
- 编码前本地 HEAD：`e7b75f78798649ffd0bda5f96896d9e6926fedc2`。
- 编码前工作树：`git status --short` 为空。
- 3004 部署目录：`/opt/manim-v2-3004-snapshot`。
- 3004 编码前部署锚点：`.deployed-ref` 记录 `commit=7e2b486aab7d6a9666247ae27e3e6332e9628f8d`，`deployed_at=2026-07-26T01:23:00+08:00`，`project_state_commit=e7b75f78798649ffd0bda5f96896d9e6926fedc2`。
- 编码前 3004 健康：`http://127.0.0.1:8004/health` 返回 healthy；`manim-v2-3004-backend.service` active；根分区约 3.8G 可用。
- 下一步：先补后端合作者详情/设置接口测试，再实现接口；随后改 admin 用户列表和详情页、修复 `admin.ts` FormData header、改 AI 助手入口和 admin-only 路由；本地验证后备份 3004 DB/代码并部署 3004。

## 2026-07-26 3004 用户详情、AI 助手动效、素材库 422 与模块可见性优化本地验证记录

- 当前分支：`codex/3004-partner-stickman-platform-20260724`。
- 本地验证前 HEAD：`e7b75f78798649ffd0bda5f96896d9e6926fedc2`。
- 已完成本地改动：`/admin/users` 每行只保留“用户详情”；新增 `/admin/users/:id` 集中管理审核、启停、有效期、密码、前端版本、模块权限、配额、最近任务和合作者设置；新增 admin 用户详情页启用/停用合作者 API；`admin.ts` 对 FormData 上传删除 JSON Content-Type，避免素材库 zip 上传 422；AI 助手入口改为卡通人浮动动效；首页、主菜单和路由均限制 AI 视频导演与知识 IP 仅 admin 可见可进。
- 本地测试：`PYTHONPATH=backend pytest backend/tests/test_admin_user_partner_profile.py backend/tests/test_stickman_workflow_upload_persistence.py -q` -> `6 passed`。
- 本地编译：`python -m py_compile backend/app/api/admin.py backend/app/services/stickman_workflow_assets.py` -> 通过。
- 前端构建：`npm run build` in `frontend` -> 通过，仅有既有 Vite chunk size warning。
- 差异检查：`git diff --check` -> 通过，仅提示 `PROJECT_STATE.md` CRLF 将转 LF。
- 待部署边界：只部署到 `/opt/manim-v2-3004-snapshot`；只允许重启 3004 backend 和更新 3004 前端静态构建；不修改、不重启 3003。
- 部署前下一步：提交本地改动；备份 3004 SQLite 与代码快照；同步并部署 3004；平台验证用户详情设置合作者、素材库覆盖上传 `codex_verify_library_bom` 不再 422、普通用户看不到/进不去 admin-only 模块、AI 助手卡通入口可见可用。

## 2026-07-26 12:40 3004 用户详情、AI 助手动效、素材库 422 与模块可见性优化部署验收记录

- 功能提交：`33f27e6f9612ab2214bf3fbf15b9ab19eb82f6a0`（`feat: add admin user detail controls`）。
- 3004 部署目录：`/opt/manim-v2-3004-snapshot`。
- 3004 部署标记：`.deployed-ref` 已记录 `branch=codex/3004-partner-stickman-platform-20260724`、`commit=33f27e6f9612ab2214bf3fbf15b9ab19eb82f6a0`、`deployed_at=2026-07-26T12:34:12+08:00`。
- 部署前备份：SQLite 备份 `/opt/manim-v2-3004-backups/manim_platform_3004.pre-user-detail-ai-fab.20260726_122855.db`；代码快照 `/opt/manim-v2-3004-backups/manim-v2-3004.pre-user-detail-ai-fab.20260726_122855.tar.gz`。
- 部署动作：上传本地 git archive `/tmp/manim-3004-33f27e6.tar`，解包同步到 `/opt/manim-v2-3004-snapshot`；远程前端 `npm run build` 已生成 `frontend/dist/assets/main-C1KP00Vr.js`；仅重启 `manim-v2-3004-backend.service`，未修改、未重启 3003。
- 服务验证：`manim-v2-3004-backend.service`、`manim-v2-3004-worker.service`、`manim-v2-3004-ai-video-render.service` 均为 `active`；`http://127.0.0.1:8004/health` 返回 `200`；`http://127.0.0.1:18788/api/health` 返回 `200`；`http://127.0.0.1:3004/` 返回 `200`；`http://127.0.0.1:3003/` 返回 `200`。
- 验证账号：3004 专用测试账号 `13990049991 / Codex3004!`（admin）、`13990049992 / Codex3004!`（普通用户）、`13990049993 / Codex3004!`（合作者设置目标用户），均只用于 3004 验收。
- API 验证：admin 与普通用户手机号登录均返回 token；`/api/auth/me` 分别返回 `codex_admin_ui_verify` admin 和 `codex_user_ui_verify` 普通用户；普通用户访问 `/api/admin/users?limit=1` 返回 `403`。
- 用户详情合作者验证：admin 搜索手机号 `13990049993` 得到目标用户 `id=89`；调用 `PUT /api/admin/users/89/partner-profile` 返回 `enabled=true`、`commission_rate_bps=2500`、`status=active`、`referral_code=CODEXVER`，说明用户详情页对应的合作者设置 API 可用。
- 素材库覆盖上传验证：上传包含 BOM `materials.generated.json` 与 `fileName` 字段的 zip 到 `/api/admin/stickman-workflow/material-libraries/codex_verify_library_bom/package` 返回 `200`；响应列表中 `codex_verify_library_bom` 存在，`image_count=1`、`material_count=1`、`is_visible=True`，未再出现 `422`。
- 前端构建产物验证：`main-C1KP00Vr.js` 包含 `assistant-person`、`用户详情`、`合作者设置`；`main-CxirjtrL.css` 包含 `assistant-wave` 与 `assistant-float`，说明 AI 助手卡通入口和动效样式已进入 3004 静态包。
- admin-only 可见性验证：源码与构建均已包含 `/ai-video/*` 和 `/knowledge-ip` 的 `AdminRoute` 包裹，主菜单和首页工作流卡片按 `user.is_admin` 过滤；普通用户 admin API 403 已复验。浏览器自动化因本机 Playwright 包不可用未完成截图验证，后续如需视觉截图可在装好 Playwright 后补跑 `work/verify_3004_ui.js`。
- 磁盘状态：`/` 分区 40GB，已用约 34GB，可用约 3.8GB，使用率约 90%；后续批量渲染前仍建议清理旧任务与缓存。
- 不要重复做：本轮只部署 3004，不要回滚或重启 3003；不要把 `codex_verify_library_bom` 当作正式素材库，它是覆盖上传验证库。
- GitHub 同步：`git push origin codex/3004-partner-stickman-platform-20260724` 已成功，远程分支已创建/更新；PR 地址为 `https://github.com/mingze-great/manim/pull/new/codex/3004-partner-stickman-platform-20260724`。
- 补充说明：后续本地状态提交 `acba0a42a590f0491f85d476104c2a0bf7453e90` 已同步到 3004 服务器 `PROJECT_STATE.md` 和 `.deployed-ref`，但再次推送 GitHub 时网络 `Recv failure: Connection was reset`；GitHub 至少已包含功能部署记录提交 `1d985ef2a22d7f4b4e7bad2aef7c450a20b70a5b`。


## 2026-07-26 3004 ???????????????????????????????
- ??????? 3004 ???????????????????????? zip ???????????????????????????? 3003?
- ????????`C:\Users\Administrator\Documents\Codex\2026-07-18\300\work\3004-partner-stickman-worktree`?
- ?????`codex/3004-partner-stickman-platform-20260724`?
- ???/????? HEAD?`cd4d2899d1e7961cd9db83f95e79f702c2d2f42c`????? `2026-07-26 13:03:01 +0800`????? `docs: clarify 3004 git sync status`?
- 3004 ???????nginx error.log ? `2026-07-26 13:04:50` ???? `client intended to send too large body: 105229520 bytes`?????? `codex_verify_library_bom` zip ? 100.4MB?3004 nginx ????? `client_max_body_size`?????? nginx ????????? `net::ERR_CONNECTION_RESET`?
- ????????`deploy/manim-v2-3004.conf` ?? `client_max_body_size 300m` ?????????`backend/app/services/stickman_workflow_assets.py` ?????? zip??????????????????????????`backend/app/services/stickman_workflow_limits.py` ?????/???/????????????????????????`backend/app/api/stickman_workflow.py` ???????????????????????????? `sceneStyles`?`backend/app/api/admin.py` ?????????????`frontend/src/pages/StickmanWorkflow/index.tsx` ?????????????????????????? `materialLibrary` key?`frontend/src/pages/admin/AdminUserDetail.tsx` ?????????/??????
- ?????`PYTHONPATH=backend pytest backend/tests/test_stickman_workflow_upload_persistence.py backend/tests/test_stickman_workflow_limits.py -q` -> `15 passed`?`PYTHONPATH=backend pytest backend/tests/test_partner_program_service.py backend/tests/test_admin_user_partner_profile.py -q` -> `5 passed`?`python -m py_compile backend/app/services/stickman_workflow_assets.py backend/app/services/stickman_workflow_limits.py backend/app/api/stickman_workflow.py backend/app/api/admin.py` -> ???`npm run build` in `frontend` -> ?????? Vite chunk size warning?`git diff --check` -> ???? CRLF/LF ???
- ??????????????? 3004 SQLite ????????? `/opt/manim-v2-3004-snapshot`???? 3004 backend ? reload nginx???? 3003??? 3004 ?????????? reset???????????????????????admin ???????????????
- ????????? `/admin/stickman-v2/scene-style-libraries` ???? `/stickman-workflow` ??????????????????????? 3003?
# 项目状态

## 2026-07-26 3004 套餐、合作者发码、图片模式透明化与自定义文案完整性部署前记录

- 当前任务：只在 3004 分支 `codex/3004-partner-stickman-platform-20260724` 上继续完成火柴人套餐配置、合作者按套餐生成兑换码、金额佣金计算、用户端隐藏底层图片模式、自定义文案完整生成；不触碰 3003。
- 本地工作区：`C:\Users\Administrator\Documents\Codex\2026-07-18\300\work\3004-partner-stickman-worktree`。
- 部署目标：`/opt/manim-v2-3004-snapshot`，平台 URL `http://152.136.218.74:3004`。
- 编码前 HEAD：`d1b0121c07227b21455961e43f107c4e8a4e0ba2`，提交时间 `2026-07-26T13:41:50+08:00`，提交信息 `feat: add stickman quota plans and robust library upload`。
- 已完成本地改动：新增后台火柴人套餐配置；admin/partner 可按套餐生成兑换码并填写金额；佣金按金额乘合作者比例计算；用户兑换后写入素材/实时生图模式、素材库范围、每日/每月分钟限制、总视频次数和单条上限；用户端隐藏底层图片模式，仅显示场景图风格；自定义文案按最多 3 句一组扩展分镜，避免只生成前 12 秒。
- 最近修改文件：`backend/app/services/stickman_workflow_plans.py`、`backend/app/api/admin.py`、`backend/app/api/partner.py`、`backend/app/api/stickman_workflow.py`、`backend/app/services/partner_program.py`、`backend/app/services/ai_video.py`、`backend/app/models/partner.py`、`backend/app/main.py`、`frontend/src/pages/admin/AdminPartners.tsx`、`frontend/src/pages/PartnerDashboard.tsx`、`frontend/src/pages/StickmanWorkflow/index.tsx`、`frontend/src/services/admin.ts`、`frontend/src/services/partner.ts`、`backend/tests/test_stickman_workflow_plans.py`、`backend/tests/test_ai_video_user_script_completion.py`、`backend/tests/test_ai_video_sc1_material_urls.py`、`backend/tests/test_partner_program_service.py`。
- 本地验证：`python -m py_compile backend/app/services/stickman_workflow_plans.py backend/app/api/admin.py backend/app/api/partner.py backend/app/api/stickman_workflow.py backend/app/services/partner_program.py backend/app/services/ai_video.py backend/app/main.py` 通过；`PYTHONPATH=backend pytest backend/tests/test_ai_video_sc1_material_urls.py backend/tests/test_ai_video_user_script_completion.py backend/tests/test_stickman_workflow_plans.py backend/tests/test_partner_program_service.py backend/tests/test_stickman_workflow_limits.py backend/tests/test_stickman_workflow_upload_persistence.py backend/tests/test_admin_user_partner_profile.py -q` -> `42 passed`；`npm run build` in `frontend` 通过，仅有既有 Vite chunk size warning；`git diff --check` 通过，仅有 CRLF/LF 换行提示。
- 下一步：提交本地改动；部署前备份 3004 SQLite 和代码快照；同步到 `/opt/manim-v2-3004-snapshot`，构建前端，只重启 3004 backend/worker，必要时 reload nginx，不动 3003；平台验证 admin 套餐保存、合作者按套餐发码、佣金金额、用户兑换权限、用户端隐藏图片模式、长自定义文案生成完整成片。
- 不要重复做：不要回滚或重启 3003；不要把底层实时生图模式暴露给普通用户；不要只用本地脚本替代 3004 平台闭环。
## 2026-07-26 3004 套餐与自定义文案完整性部署验收记录

- 功能提交：`e3d5930`，提交信息 `feat: add stickman package plans and invite commissions`。
- 3004 部署目录：`/opt/manim-v2-3004-snapshot`。
- 3004 `.deployed-ref`：`branch=codex/3004-partner-stickman-platform-20260724`，`commit=e3d5930`，`deployed_at=2026-07-26T21:43:51+0800`。
- 部署前备份：
  - SQLite：`/opt/manim-v2-3004-backups/manim_platform_3004.pre-package-plans..db`
  - 代码快照：`/opt/manim-v2-3004-backups/manim-v2-3004.pre-package-plans..tar.gz`
  - 注：本轮备份命令第一次被 PowerShell 吃掉时间戳变量，因此文件名中时间戳为空，但备份文件已存在且可用于回退。
- 服务状态：`manim-v2-3004-backend.service` active，`manim-v2-3004-worker.service` active，`manim-v2-3004-ai-video-render.service` active；`http://127.0.0.1:8004/health` healthy；`http://127.0.0.1:3004/` 返回 200；`http://127.0.0.1:3003/` 返回 200，未修改或重启 3003。
- 平台 API 验收：
  - admin 手机号登录 `13990049991` 成功。
  - `POST /api/admin/stickman-workflow/plans` 保存成功，验证套餐 `codex_count_2x5m`：`quota_mode=count_package`，`total_video_limit=2`，`max_video_seconds=300`，`material_mode=ai_image`，`amount=200`。
  - admin 绑定合作者生成兑换码 `SC1-3OBHD1KB`，`amount=200`，`commission_amount=60`，`material_mode=ai_image`，证明佣金按金额乘合作者比例计算。
  - 普通用户 `13990049992` 的 `/api/stickman-workflow/config` 返回 `sceneStyles=2`，`materialMode=material_only`，`canUseAiImages=false`，前端页面源码不包含 `画面模式` 或 `实时生图`，说明底层图片模式对用户透明。
  - 合作者 `13990049993` 的 `/api/partner/stickman-plans` 可看到验证套餐 `codex_count_2x5m`，`material_mode=ai_image`，`amount=200`。
- 平台成片验收：
  - 通过 3004 `/api/stickman-workflow/jobs` 创建自定义文案任务 `job_96`，输出 `/api/ai-video/files/96/output/video.mp4`。
  - 远程输出文件：`/opt/manim-v2-3004-snapshot/backend/storage/ai-video/tasks/job_96/output/video.mp4`。
  - 本地下载与抽帧目录：`C:\Users\Administrator\Documents\Codex\2026-07-18\300\outputs\job_96_verify`。
  - `ffprobe` 确认 MP4 包含 `h264` 视频流和 `aac` 音频流，时长约 `29.31s`。
  - `project.json` 场景数为 `4`，完整包含用户文案第十句“第十句，是终于不用反复审判自己。”，证明不再只生成前几个分镜/前 12 秒。
  - 抽帧 `frame_02s.png`、`frame_08s.png`、`frame_16s.png` 目检：单张场景图居中完整，未被横线或白色面板遮挡；右上角 `心理分享 | 认知突破` 存在；无 `@Sc1火柴人`；字幕居中；总结关键词为 2-4 字短词并累计展示。
- 服务器空间：根分区约 `40G`，已用约 `35G`，可用约 `3.0G`，使用率约 `93%`；后续批量渲染前仍建议继续清理旧备份/缓存。
- 下一步建议：如果用户要保留 `codex_count_2x5m` 作为正式套餐，可在后台改名和金额；如果只是验证套餐，可在后台删除，避免污染正式套餐列表。

## 2026-07-26 3004 图片模式权限、长文案、历史作品与关键词相关性部署前记录

- 当前任务：只在 3004 分支 `codex/3004-partner-stickman-platform-20260724` 上继续优化火柴人图片模式可见权限、自定义文案长度限制、火柴人历史作品入口和方框总结关键词相关性；不触碰 3003。
- 本地工作区：`C:\Users\Administrator\Documents\Codex\2026-07-18\300\work\3004-partner-stickman-worktree`。
- 部署目标：`/opt/manim-v2-3004-snapshot`，平台 URL `http://152.136.218.74:3004`。
- 编码前 HEAD：`b5009c9a68eee09173a5efc10996af71f84c90cc`，提交时间 `2026-07-26 21:54:03 +0800`，提交信息 `docs: record 3004 package plan deployment`。
- 已完成本地改动：后台用户详情 `stickman_v2` 权限增加可见图片模式配置；admin 默认可见素材匹配和实时生图两种模式；合作者仅在自己有双模式权限时可给推荐用户选择图片模式，否则兑换码后端强制继承合作者单模式；火柴人自定义文案去掉 1200 字固定限制，改为只按预计时长/套餐上限判定；新增 `/api/stickman-workflow/jobs` 历史列表，前端 `/stickman-workflow` 增加“历史作品查看”按钮和下载入口；SC1 方框总结优先提取当前字幕中的强相关 2-4 字关键词，避免唯一性兜底漂移到不相关词。
- 最近修改文件：`backend/app/services/partner_program.py`、`backend/app/services/stickman_workflow_plans.py`、`backend/app/api/stickman_workflow.py`、`backend/app/api/partner.py`、`backend/app/api/admin.py`、`backend/app/services/ai_video.py`、`backend/tests/test_partner_program_service.py`、`backend/tests/test_stickman_workflow_limits.py`、`backend/tests/test_ai_video_sc1_material_urls.py`、`frontend/src/pages/admin/AdminUserDetail.tsx`、`frontend/src/pages/PartnerDashboard.tsx`、`frontend/src/pages/StickmanWorkflow/index.tsx`、`frontend/src/services/partner.ts`、`frontend/src/services/stickmanWorkflow.ts`。
- 本地验证：`python -m py_compile backend/app/services/partner_program.py backend/app/services/stickman_workflow_plans.py backend/app/api/stickman_workflow.py backend/app/api/partner.py backend/app/api/admin.py backend/app/services/ai_video.py` 通过；`PYTHONPATH=backend pytest backend/tests/test_partner_program_service.py backend/tests/test_stickman_workflow_limits.py backend/tests/test_ai_video_sc1_material_urls.py -q` -> `38 passed`；`npm run build` in `frontend` 通过，仅有既有 Vite chunk size warning；`git diff --check` 通过，仅有 CRLF/LF 换行提示。
- 下一步：提交本地改动；部署前备份 3004 SQLite 和代码快照；同步到 `/opt/manim-v2-3004-snapshot`，构建前端并只重启 3004 backend/worker；平台验证 admin 设置用户图片模式、合作者发码继承/可选逻辑、长文案无 1200 字上限、历史作品列表可刷新后查看下载、生成成片关键词与当前字幕强相关。
- 不要重复做：不要回滚、重启或覆盖 3003；不要把底层图片模式无条件暴露给普通用户；不要只用本地测试替代 3004 平台闭环验收。

### 2026-07-26 3004 TTS 平台闭环补充

- 3004 首次部署提交：`91ac13a97c7f6a456d6793119e3b31a60239769a`，已部署到 `/opt/manim-v2-3004-snapshot`，`.deployed-ref` 时间 `2026-07-26T22:26:57+0800`。
- 部署前备份：代码快照 `/opt/manim-v2-3004-backups/manim-v2-3004.pre-image-modes-history.20260726_222413.tar.gz`；SQLite 备份 `/opt/manim-v2-3004-backups/manim_platform_3004.pre-image-modes-history.20260726_222504.db`。
- 平台 API 验证已完成：admin 配置返回 `visibleImageModes=['material_only','ai_image']` 且可选择；普通用户 `13990049992` 已通过 admin 用户详情 API 设置为双模式，`/stickman-workflow/config` 返回双模式和 `materialMode=ai_image`；合作者 `13990049993` 当前只有素材模式，发码时即使请求 `ai_image`，后端生成兑换码仍强制 `material_only`，佣金按金额计算；长文案 `2700` 字符左右不再受 1200 字限制，估算 `293s/300s allowed=True`；火柴人历史列表返回 `job_96` 和 MP4 下载地址。
- 平台成片验证发现问题：新建 `job_98`、`job_99` 均失败于 `tts_generating`。根因不是图片模式/历史逻辑，而是服务器 IP 调 dayun manbo 外部接口返回 `HTTP 429`；DashScope SDK fallback 返回空音频或连接关闭；Edge TTS 返回 `403`；本机 CosyVoice 健康闸门拒绝调用，这是为防止再次拖垮服务器的预防措施。
- 本地补充修复：`backend/app/services/ai_video.py` 在 DashScope SDK 和 Edge TTS 失败后、进入本机 CosyVoice 前，新增轻量外部 `external_simple_tts` 兜底；实际优先使用服务器可访问的有道 `dictvoice`，Google Translate TTS 只作为次级尝试；不启动本机模型。如果外部 TTS 也失败，仍保持本机 CosyVoice 健康闸门。
- 本地补充测试：`PYTHONPATH=backend pytest backend/tests/test_partner_program_service.py backend/tests/test_stickman_workflow_limits.py backend/tests/test_ai_video_sc1_material_urls.py -q` -> `39 passed`；`python -m py_compile backend/app/services/partner_program.py backend/app/services/stickman_workflow_plans.py backend/app/api/stickman_workflow.py backend/app/api/partner.py backend/app/api/admin.py backend/app/services/ai_video.py` 通过；`npm run build` in `frontend` 通过；`git diff --check` 通过。
- 下一步：提交有道优先的 TTS 兜底修复并再次部署 3004，仅重启 3004 backend/worker；重新创建平台成片任务，下载 MP4 并用 ffprobe/抽帧验证音视频流、字幕/总结/场景图同步。
## 2026-07-26 3004 字幕编号前缀清理部署前记录

- 当前任务：继续只在 3004 分支 `codex/3004-partner-stickman-platform-20260724` 上完成火柴人自定义文案字幕清理，不触碰 3003。
- 本地工作区：`C:\Users\Administrator\Documents\Codex\2026-07-18\300\work\3004-partner-stickman-worktree`。
- 部署目标：`/opt/manim-v2-3004-snapshot`，平台 URL `http://152.136.218.74:3004`。
- 编码前 HEAD：`43e9a46ce4de518bd086d09b2e4d6809ab1dd93e`，提交时间 `2026-07-26 23:04:45 +0800`，提交信息 `fix: prefer accessible external tts fallback`。
- 当前改动：`backend/app/services/ai_video.py` 在 SC1 caption cue 切分时清理 `第一句/第二句/第三句` 等编号前缀，避免编号单独或带前缀出现在字幕中；`backend/tests/test_ai_video_sc1_material_urls.py` 增加回归测试。
- 下一步：运行目标 pytest、py_compile、git diff 检查；提交后只部署 3004 backend/worker，创建 3004 平台任务验证字幕、音频、场景图和总结同步。
- 不要重复做：不要改动、重启、覆盖 3003；不要只用本地测试替代 3004 平台成片闭环。
## 2026-07-27 3004 素材风格预览、声音试听、上传背景、套餐与助手图标部署前记录

- 当前任务：只在 3004 分支 `codex/3004-partner-stickman-platform-20260724` 上修复用户端新素材库不可见/不能实时刷新、场景图风格缺少预览、声音不能试听、上传背景未明显生效、合作者兑换码套餐固定为 399/599/799 三档，以及 AI 助手入口使用用户提供的机器人图标；不触碰 3003。
- 本地工作区：`C:\Users\Administrator\Documents\Codex\2026-07-18\300\work\3004-partner-stickman-worktree`。
- 部署目标：`/opt/manim-v2-3004-snapshot`，平台 URL `http://152.136.218.74:3004`。
- 编码前 HEAD：`2d7a4652f75b7517498f088523d38a265094ab43`，提交时间 `2026-07-26 23:22:59 +0800`，提交信息 `fix: clean numbered custom script captions`。
- 已完成本地改动：用户端素材库预览 URL 改为 `/api/stickman-workflow/assets/material-libraries/...` 并新增登录用户可访问的只读封面接口；火柴人 config 返回声音试听 URL、背景模板 preview 字段；用户端火柴人页面支持刷新场景图风格、展示素材示例图、声音试听、上传背景 16:9 提示和预览、背景模板预览；Remotion 上传背景透明度增强；默认/内置套餐强制包含 `399元40个视频`、`599元65个视频`、`799元90个视频`；AI 助手入口改用 `frontend/public/assistant-bot.png` 并保留动态提示。
- 最近修改文件：`backend/app/api/stickman_workflow.py`、`backend/app/services/stickman_workflow_assets.py`、`backend/app/services/stickman_workflow_plans.py`、`backend/tests/test_stickman_workflow_upload_persistence.py`、`frontend/src/pages/StickmanWorkflow/index.tsx`、`frontend/src/pages/StickmanWorkflow/StickmanWorkflow.css`、`frontend/src/services/stickmanWorkflow.ts`、`frontend/src/components/PlatformAssistant/PlatformAssistantWidget.tsx`、`frontend/src/components/PlatformAssistant/PlatformAssistantWidget.css`、`frontend/public/assistant-bot.png`、`video-render-service/remotion-mind-video/src/remotion/Sc1StickmanVideo.jsx`。
- 本地验证：`PYTHONPATH=backend pytest backend/tests/test_stickman_workflow_upload_persistence.py backend/tests/test_stickman_workflow_limits.py backend/tests/test_partner_program_service.py backend/tests/test_ai_video_sc1_material_urls.py -q` -> `48 passed`；`python -m py_compile backend/app/services/stickman_workflow_plans.py backend/app/services/stickman_workflow_assets.py backend/app/api/stickman_workflow.py backend/app/services/ai_video.py` 通过；`npm run build` in `frontend` 通过，仅有既有 Vite chunk size warning；`git diff --check` 通过，仅有 CRLF/LF 换行提示。
- 下一步：提交本地改动；部署前备份 3004 SQLite 和代码快照；同步到 `/opt/manim-v2-3004-snapshot`，重启 3004 backend/worker/render 或必要服务；平台验证 config 中新素材库封面 URL、用户端场景风格刷新/预览、声音试听、上传背景生成 payload/成片背景、合作者套餐三档、AI 助手机器人图标。
- 不要重复做：不要修改、回滚、重启或覆盖 3003；不要把后台 `/api/admin/...` 资源 URL 暴露给普通用户端预览；不要只用本地测试替代 3004 平台闭环。
## 2026-07-27 3004 场景图风格可见性二次修复记录

- 当前任务：3004 部署后平台验证发现普通用户 `/api/stickman-workflow/config` 仍只返回 `sc1_outputs`，根因是历史用户权限里的 `allowed_libraries` 过滤了后台新上传且前台可见的素材库；同时默认 SC1 没有预览图。
- 本地工作区：`C:\Users\Administrator\Documents\Codex\2026-07-18\300\work\3004-partner-stickman-worktree`。
- 当前已部署提交：`9af98cbe9dcd07067be61c49ac5af16250be3e1a`，部署目录 `/opt/manim-v2-3004-snapshot`。
- 本次补充改动：`backend/app/api/stickman_workflow.py` 改为用户端场景图风格展示所有后台启用且前台可见素材库，只有显式 `enforce_allowed_libraries` 时才限制；`backend/app/services/stickman_workflow_assets.py` 为默认 SC1 从 material.json 自动寻找第一张图作为预览；`backend/tests/test_stickman_workflow_limits.py` 更新并覆盖新行为。
- 本地验证：`PYTHONPATH=backend pytest backend/tests/test_stickman_workflow_upload_persistence.py backend/tests/test_stickman_workflow_limits.py backend/tests/test_partner_program_service.py backend/tests/test_ai_video_sc1_material_urls.py -q` -> `49 passed`；`python -m py_compile backend/app/services/stickman_workflow_assets.py backend/app/api/stickman_workflow.py` 通过；`git diff --check` 通过，仅有 CRLF/LF 换行提示。
- 下一步：提交并增量部署到 3004，重启 3004 backend/worker，重新验证普通用户 config 中 sceneStyles 数量和封面 URL。
- 不要重复做：不要通过要求用户手动改套餐 allowed_libraries 来解决新素材库不可见；后台可见素材库应自动成为用户端场景图风格。
## 2026-07-27 3004 默认场景预览和声音试听路径补充记录

- 当前任务：继续只修 3004。平台验证发现普通用户已能看到上传素材库，但默认 SC1 风格仍无预览图，声音试听接口返回 404。
- 根因：数据库中保存过 `sc1_outputs` 配置且 `cover_image_path` 为空，覆盖了代码默认库的自动封面；3004 试听文件实际在 `/opt/manim-v2-3004-snapshot/backend/storage/voice-references/`，试听接口候选路径未包含该目录。
- 本次补充改动：`backend/app/services/stickman_workflow_assets.py` 合并素材库配置时保留默认库自动识别的 base/manifest/cover 字段；`backend/app/api/stickman_workflow.py` 声音试听接口增加 `backend/storage/voice-references` 候选路径；`backend/tests/test_stickman_workflow_upload_persistence.py` 增加默认库空 cover 不覆盖自动预览测试。
- 本地验证：`PYTHONPATH=backend pytest backend/tests/test_stickman_workflow_upload_persistence.py backend/tests/test_stickman_workflow_limits.py -q` -> `23 passed`；`python -m py_compile backend/app/services/stickman_workflow_assets.py backend/app/api/stickman_workflow.py` 通过；`git diff --check` 通过，仅有 CRLF/LF 换行提示。
- 下一步：提交并增量部署 3004，验证普通用户 config 中默认 SC1 和上传库都有预览 URL，声音试听接口返回音频。
## 2026-07-27 3004 默认 SC1 manifest fallback 补充记录

- 当前任务：继续只修 3004。平台验证发现默认 SC1 风格仍没有预览图。
- 根因：远程默认库路径 `/opt/manim_assets/sc1-outputs/material.json` 不存在，真实索引文件是 `/opt/manim_assets/sc1-outputs/materials.generated.json`。
- 本次补充改动：`backend/app/services/stickman_workflow_assets.py` 在配置的默认 manifest 不存在时按 `material.json`、`materials.generated.json`、`materials.json`、`materials.normalized.json` 顺序寻找可用索引；`backend/tests/test_stickman_workflow_upload_persistence.py` 增加 fallback 测试。
- 本地验证：`PYTHONPATH=backend pytest backend/tests/test_stickman_workflow_upload_persistence.py -q` -> `10 passed`；`python -m py_compile backend/app/services/stickman_workflow_assets.py` 通过；`git diff --check` 通过，仅有 CRLF/LF 换行提示。
- 下一步：提交并增量部署 3004，复验默认 SC1 和上传素材库均有用户端预览图，声音试听接口返回 200 音频。
