# 3004 合作者与火柴人工作流设计规格

## 背景
现有 3003 平台已经有 `/stickman-workflow` 独立火柴人一键成片入口，用户输入标题后生成 SC1 心理学火柴人成片。现在要在不影响 3003 的前提下，在 3004 上扩展商业化和生成可控性：

- 合作者推荐用户并获得分佣。
- 微信付款或线下收款后用户能自动开通，不再全部依赖人工审核。
- `/stickman-workflow` 支持自定义文案、视频时长、背景、素材库和素材/实时生图模式。
- 后台能管理 `/stickman-workflow` 专用素材库，而不是误用 `stickman-v2` 素材库配置。
- 后台支持从参考图生成新素材库，先出两张样图确认，再批量生成完整素材库。
- 3004 独立部署验证，不能影响 3003。

## 不可混淆边界
`/admin/stickman-v2/scene-style-libraries` 是现有增强讲解 `stickman_v2` 工作室链路的配置，不等于 `/stickman-workflow` 一键火柴人模块。

本次新增的是 `/stickman-workflow` 专用素材库系统：

- 后台管理接口：`/admin/stickman-workflow/material-libraries`
- 用户可见配置接口：`/stickman-workflow/config`
- 生成任务接口继续使用：`/stickman-workflow/jobs`
- 默认素材库仍指向本地 `E:\ai\火柴人工作流\outputs` 和远程 `/opt/manim_assets/sc1-outputs`

## 推荐方案
采用“合作者账号 + 推荐码/兑换码 + 自动开通 + 专用工作台”的方案，而不是给合作者开子级管理员账号。

原因：

- 合作者只需要管理自己推荐来的用户和佣金，不应该拥有后台敏感权限。
- 邀请码/兑换码可以同时支持线上微信支付和线下 wx 收款。
- 后台仍然保留全局管理权，可以看所有用户来源、订单、佣金和套餐能力。
- 这个方案能复用现有用户、订单、订阅和模块权限模型，改动边界更清晰。

## 角色与权限
### 管理员
管理员继续使用现有 `/admin`，可以：

- 创建和管理合作者。
- 查看所有用户、订单、订阅、分佣和素材库。
- 创建邀请码/兑换码。
- 上传 `/stickman-workflow` 专用素材库 zip。
- 上传背景图和背景风格。
- 发起参考图生成素材库任务。
- 设置套餐、额度、素材模式和实时生图模式。

### 合作者
合作者使用独立 `/partner` 工作台，可以：

- 查看自己的推荐码、邀请码、推广链接。
- 查看自己推荐来的用户列表。
- 查看自己推荐订单、开通状态和预计佣金。
- 给已付款用户发放由后台授权范围内的邀请码/兑换码。

合作者不能：

- 进入 `/admin`。
- 查看全局用户、全局收入、系统配置、密钥、日志。
- 修改套餐价格、全局素材库或模型配置。
- 给非自己推荐的用户开通权限。

### 普通用户
普通用户可以：

- 通过推荐链接注册并自动绑定推荐人。
- 微信支付后自动开通。
- 使用兑换码开通对应套餐。
- 在 `/stickman-workflow` 默认只输入标题生成成片。
- 按套餐能力使用高级选项。

## 推荐与开通流程
### 线上支付流程
1. 用户通过合作者链接进入平台，链接包含 `ref`。
2. 用户注册后记录 `referred_by_partner_id` 和 `referral_code`。
3. 用户选择套餐并微信支付。
4. 支付成功回调更新订单、订阅、模块权限和分佣台账。
5. 用户立即可用，无需人工审核。

### 线下收款流程
1. 管理员或合作者在授权范围内生成兑换码。
2. 兑换码绑定套餐、期限、每日/每月额度、素材模式、视频时长上限和推荐人。
3. 用户付款给 wx 后拿到兑换码。
4. 用户登录后输入兑换码，系统自动开通。
5. 兑换码使用后记录使用人、使用时间、推荐人和分佣状态。

## 套餐与成本模式
套餐需要同时控制：

- 每日视频数量上限。
- 单条视频最大时长。
- 每月总视频数量或总分钟数。
- 可用素材库列表。
- 是否允许用户上传背景图。
- 是否允许选择背景风格。
- 是否允许自定义文案。
- 是否允许实时生成场景图。

模式定义：

- `material_only`：只允许素材库匹配，默认模式，用户看不到实时生图入口。
- `ai_image`：允许按文案实时生成场景图，成本更高。
- `hybrid`：默认素材库匹配，素材缺口时后台可自动补图，但对用户保持透明。

## `/stickman-workflow` 生成配置
默认流程保持不变：用户输入一个标题即可生成完整成片。

高级选项可折叠展示：

- 生成模式：标题生成、用户自定义文案。
- 视频时长：15 秒、30 秒、45 秒、60 秒、自定义套餐上限内时长。
- 背景：默认背景、后台背景风格、用户上传背景图。
- 素材库：后台启用且用户套餐允许的素材库。
- 音色：默认 `dayun_manbo`，可选后台开放音色。

互斥规则：

- 用户输入自定义文案时，不允许同时选择目标时长。
- 用户选择视频时长时，系统必须 AI 生成文案并控制文案长度。

## 时长判断方案
采用两阶段判断：

### 快速预估
在用户提交前或创建任务前，用中文字符数、标点停顿和音色语速估算时长。

建议公式：

- 中文基础语速：每秒 4.2 到 5.2 个汉字。
- 逗号、顿号、分号增加 0.12 秒停顿。
- 句号、问号、感叹号增加 0.25 秒停顿。
- 换行增加 0.35 秒停顿。
- 不同音色可配置 `speed_factor`。

### 实际校准
TTS 生成后用 `ffprobe` 读取音频真实时长。真实时长驱动最终字幕、场景图、关键词和视频时长。

如果自定义文案超出套餐上限：

- 创建任务前能预估超限时直接拦截。
- TTS 后真实超限时任务失败并返回明确提示，后续可支持自动压缩文案。

## `/stickman-workflow` 专用素材库
### zip 上传
后台新增素材库列表和上传能力。zip 必须包含：

- 图片文件：`png`、`jpg`、`jpeg` 或 `webp`
- 清单文件：`material.json` 或 `materials.json`

清单结构要求：

```json
[
  {
    "file_name": "anxiety_001.png",
    "image_path": "images/anxiety_001.png",
    "title": "焦虑内耗",
    "keywords": ["焦虑", "内耗", "关系"],
    "emotion": "anxious",
    "scene": "relationship",
    "description": "一个火柴人被复杂想法包围"
  }
]
```

上传后系统要：

- 解压到专用目录。
- 校验清单和图片是否匹配。
- 生成规范化 `materials.normalized.json`。
- 统计图片数和条目数。
- 提取封面图。
- 保存素材库元数据。
- 支持启用、停用、排序、隐藏。

### 默认素材库
默认素材库不复制进仓库。它只作为配置项存在：

- 本地路径：`E:\ai\火柴人工作流\outputs`
- 远程路径：`/opt/manim_assets/sc1-outputs`
- key：`sc1_outputs`

## 参考图生成素材库
后台支持上传一张参考图并生成素材库：

1. 管理员上传参考图。
2. 系统生成风格描述和素材库规划。
3. 系统先生成两张样图。
4. 管理员确认样图风格一致。
5. 系统批量生成指定数量素材图。
6. 系统自动生成 `material.json`。
7. 管理员验收后启用素材库。

生成素材库必须符合现有 SC1 素材库使用要求：用有限数量的图表达常见心理、情绪和场景，能够通过 json 与文案语义匹配。

## 数据模型
新增或扩展的数据对象：

- `PartnerProfile`：合作者资料、佣金比例、状态、结算信息。
- `ReferralCode`：推荐码，绑定合作者，用于注册归因。
- `InviteCode`：兑换码，绑定套餐、权限、有效期、使用次数和合作者。
- `CommissionLedger`：分佣台账，记录订单、用户、合作者、金额、比例、状态。
- `StickmanWorkflowMaterialLibrary`：`/stickman-workflow` 专用素材库元数据。
- `StickmanWorkflowMaterialGenerationJob`：参考图生成素材库任务。

现有 `User` 需要扩展：

- `role`：`user`、`partner`、`admin`。
- `referred_by_partner_id`
- `referral_code`

现有 `Order` 需要扩展：

- `partner_id`
- `referral_code`
- `commission_amount`
- `commission_status`

## API 设计
### 合作者
- `GET /partner/profile`
- `GET /partner/referrals`
- `GET /partner/orders`
- `GET /partner/commissions`
- `POST /partner/invite-codes`

### 管理后台
- `GET /admin/partners`
- `POST /admin/partners`
- `PUT /admin/partners/{partner_id}`
- `GET /admin/referrals`
- `GET /admin/commissions`
- `POST /admin/invite-codes`
- `GET /admin/stickman-workflow/material-libraries`
- `POST /admin/stickman-workflow/material-libraries`
- `POST /admin/stickman-workflow/material-libraries/{library_key}/package`
- `POST /admin/stickman-workflow/material-libraries/{library_key}/generate-from-reference`
- `POST /admin/stickman-workflow/material-generation-jobs/{job_id}/approve-samples`

### 用户端
- `GET /stickman-workflow/config`
- `POST /stickman-workflow/jobs`
- `POST /payment/redeem-code`

## 3004 隔离部署
3004 必须使用独立路径和服务：

- 远程目录：`/opt/manim-v2-3004-snapshot`
- 前端端口：`3004`
- 后端端口：`8004`
- Remotion 渲染端口：`18788`
- 后端服务：`manim-v2-3004-backend.service`
- worker 服务：`manim-v2-3004-worker.service`
- 渲染服务：`manim-v2-3004-ai-video-render.service`
- Celery 队列：`manim_v2_3004`
- Nginx 配置：`manim-v2-3004.conf`

3004 部署脚本不能重启 3003 服务，不能覆盖 `/opt/manim-v2-3003-snapshot`。

## 验收标准
- 访问 `http://152.136.218.74:3004` 不影响 `http://152.136.218.74:3003`。
- 管理员能创建合作者、查看推荐用户和佣金。
- 合作者不能进入 `/admin`，只能进入 `/partner`。
- 用户通过推荐链接注册后能记录来源。
- 用户支付或兑换码开通后无需人工审核即可使用。
- `/stickman-workflow/config` 返回专用素材库、背景和声音配置。
- `/stickman-workflow` 默认只输入标题仍可生成成片。
- 自定义文案与选择时长互斥。
- 用户套餐限制能拦截超长视频或不可用模式。
- 后台能上传 `/stickman-workflow` 专用素材库 zip 并在前台选择。
- 上传参考图后能生成两张样图，确认后再批量生成素材库。
- 3004 平台完整生成任务能完成，输出 MP4 包含音频流和视频流。

## 递进交付
第一阶段交付 3004 MVP：

- 3004 隔离部署配置。
- 合作者、推荐码、兑换码和佣金台账基础模型。
- `/stickman-workflow` 专用素材库上传和配置接口。
- 前台支持自定义文案、目标时长互斥、背景/素材库选择。
- 套餐能力控制素材模式和时长上限。
- 3004 平台完成一次标题生成成片验证。

第二阶段交付增强能力：

- 合作者工作台完整统计。
- 参考图生成两张样图并确认。
- 批量生成素材库和 material.json。
- 佣金结算状态和导出。

## 自检结论
- 本规格明确区分了 `stickman-v2` 与 `/stickman-workflow`，避免复用错误后台配置。
- 本规格限定 3004 隔离部署，避免影响 3003。
- 本规格把大需求拆成 MVP 与增强阶段，避免一次性过度开发。
- 本规格没有依赖未确认的密钥或外部支付后台细节；支付沿用现有微信支付回调和订单模型扩展。
