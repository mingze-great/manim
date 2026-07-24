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
- 状态更新时间：`2026-07-24 23:42:00 +08:00`

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

## 当前问题
- 还没有实现 3004 部署配置、合作者分佣、邀请码开通、火柴人高级参数、专用素材库上传或平台验证。
- 还没有远程部署 3004。
- 还没有 3004 平台生成任务验证。

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

## 重要技术决策
- 3004 必须隔离部署，不能修改或重启现有 3003 服务。
- 合作者不使用管理员账号，新增非敏感的 `partner` 角色和 `/partner` 工作台。
- 用户微信付款后优先自动开通；线下收款用邀请码/兑换码开通，邀请码绑定套餐、期限、模式、额度和推荐人。
- `/stickman-workflow` 使用专用素材库系统，后台接口命名为 `/admin/stickman-workflow/material-libraries`，前台配置接口命名为 `/stickman-workflow/config`。
- 自定义文案和选择视频时长互斥：用户输入文案时由文案和 TTS 估算/校准时长；用户选择时长时只能 AI 生成文案。
- 套餐能力区分素材库模式和实时生图模式；素材库模式下实时生图能力对用户透明且不可见。
- 后台素材库生成采用“两张样图确认 -> 批量生成完整素材库 -> 生成 material.json -> 后台启用”的流程。

## 不要重复做
- 不要把 `/admin/stickman-v2/scene-style-libraries` 当作 `/stickman-workflow` 的后台素材库上传。
- 不要直接修改、部署或重启 3003。
- 不要提交密钥、生成成片、上传缓存、storage、uploads 或临时构建产物。
- 不要让合作者进入 `/admin` 或看到全局用户、收入、密钥、系统配置。
- 不要在未更新 `PROJECT_STATE.md` 的情况下进行远程同步、部署或上下文交接。

## 下一步
1. 提交合作者 API、后台邀请码和兑换码开通接口。
2. 开始实现 `/stickman-workflow` 专用素材库服务、后台上传接口和用户配置接口。
3. 按计划实现并验证，最后部署到 3004。
