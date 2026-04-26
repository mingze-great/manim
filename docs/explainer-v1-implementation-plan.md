# 讲解型视频 V1 实施方案

## 目标

- 基于当前已部署且已验证一致的分支 `feature/stickman-v2-on-3003`，新增一个独立一级模块 `讲解型视频`。
- 在产品层面和路由层面上，将它与 `思维可视化`、`火柴人视频`、`公众号文章` 明确区分。
- 在工程实现上，优先复用现有 `Project` 承载模型以及当前 `stickman` 生成链路中的可复用能力。
- 落地 `E:\ai\agent_v2_recover_3003\docs\V2_EXPLAINER_MODULE_DESIGN.md` 中定义的 V1 MVP，不引入超出范围的高级编辑功能。

## 分支策略

- 当前确认部署来源分支：`feature/v2-next-optimization-on-3003`
- 当前确认部署 commit：`d0679e4d3a587dc604f6e02e5506cb2446c5652c`
- 正式实现时，必须先从远程拉取 `feature/v2-next-optimization-on-3003` 作为基线，再从该基线创建 explainer 实现分支。
- 建议实现分支：`feature/explainer-v1-on-3003`
- 必须在独立 worktree 中开发，不直接在当前工作目录内混做。
- 后续所有实现、联调、部署验证都应在新分支与独立 worktree 中完成，再决定是否合入。

### 工作区要求

本需求后续实现必须遵守以下工作区要求：

1. 使用独立 `git worktree`。
2. worktree 基线必须来自远程最新的 `feature/v2-next-optimization-on-3003`。
3. 不在已有脏工作区上直接开发 explainer 功能。
4. 开发过程中保持“本地实现分支”和“远程实现分支”尽量同步。

### 推送策略

开发过程中采用“按功能块推送”，而不是“按单个小修改推送”。

要求：

1. 完成一大块可独立验证的功能后推送一次远程。
2. 不要求每个小功能都立刻推送。
3. 如果出现多次推送失败，不阻塞后续开发，但必须明确当前有哪些改动尚未同步远程。
4. 每次推送前后都要清楚本地与远程差异，确保后续可补推。
5. 最终交付前，必须保证本地工作区与远程实现分支状态清晰可追溯。

## 需求分析

### 产品定位

`讲解型视频` 不是对 `火柴人视频` 的改名，也不是 `思维可视化` 的变体。

它是一个新的独立模块，适用于：

- 情绪表达类内容
- 观点输出类内容
- 心理 / 成长 / 关系类内容
- 科普讲解类内容
- 任何可以拆分成连续分镜进行表达的文案型内容

### V1 必须具备的能力

第一版必须支持：

1. 创作首页新增模块入口。
2. `module_type = 'explainer'`。
3. 横版视频输出。
4. 强吸引力开头生成。
5. 8 到 15 个分镜脚本。
6. 每个分镜一张图。
7. 自动字幕。
8. 自动配音。
9. 一键合成。
10. 修改分镜文案。
11. 重生单张图片。
12. 修改开头。

### V1 明确不做的内容

第一版明确不做：

1. 高级时间轴编辑器。
2. 复杂转场模板库。
3. 多角色连续动作系统。
4. 局部重绘 / 局部修图。
5. 精细到逐镜头级别的复杂动画编辑。

### 质量预期

成片效果应更接近现代短视频讲解内容，而不是几何动画，也不是简单的 PPT 式切页。

关键特征：

- 文案驱动
- 分镜驱动
- 插画驱动
- 字幕驱动
- 轻镜头运动
- 前 3 秒抓人
- 横版信息清晰、字幕可读

### 抖音爆款效果目标

用户已经明确希望成片更接近“抖音爆款讲解视频”的表达效果，因此 V1 目标不能只停留在“能生成讲解视频”，而要尽量逼近短视频平台上的高留存表达方式。

第一版应重点追求以下效果：

1. 前 1 到 3 秒必须有明显钩子。
2. 标题、字幕、画面冲突点要同时服务于“停留”和“看下去”。
3. 分镜节奏要明显快于传统课件式讲解视频。
4. 文案要更像短视频口播，不像说明书或论文摘要。
5. 每个镜头都要有“信息推进”或“情绪推进”，不能只是换一张背景图。
6. 结尾要有收束感、反转感或观点拔高，避免平淡结束。

从实现角度，所谓“抖音爆款效果”在 V1 中应被拆成可执行规则，而不是抽象审美目标：

- 强钩子开头
- 高频信息密度
- 短句字幕
- 明确冲突词和情绪词
- 2 到 5 秒为主的镜头节奏
- 更强的标题化表达
- 更少解释腔，更强口语感

## 当前代码现状分析

### 已有可复用结构

当前仓库已经具备多个非常适合复用的基础能力：

1. `Project` 已具备 V1 所需的大部分承载字段。
   参考：`backend/app/models/project.py`
2. 项目 schema 已将这些字段暴露给前后端。
   参考：`backend/app/schemas/project.py`
3. 现有 `stickman` 模块已经具备完整链路：
   - 项目创建
   - 分镜生成
   - 图片生成
   - 配音生成
   - 视频合成
   - 任务进度流式返回
4. 现有前端已经有可直接借鉴的页面模式：
   - 创作首页模块入口
   - 分步创作页
   - 任务进度 / 结果页
   - 历史作品分类页

### `Project` 中可直接复用的字段

以下字段已经足够支撑 V1：

- `module_type`
- `storyboard_json`
- `image_assets_json`
- `generation_flags`
- `voice_source`
- `tts_provider`
- `tts_voice`
- `tts_rate`
- `video_url`
- `error_message`

这意味着 V1 不需要新增独立主表。

### 最接近的技术基线

当前最适合作为实现基线的是 `stickman`，不是 `manim`。

原因：

- `manim` 的核心是代码生成与渲染。
- `讲解型视频` 需要的是 `分镜 -> 出图 -> 字幕 -> TTS -> 合成` 这条链路。
- `stickman` 已经具备这条链路，并且已经支持：
  - 分镜 JSON
  - 字幕生成
  - 镜头运动 preset
  - 场景转场
  - 图片资产管理
  - 基于已有素材再次合成

### 当前实现的缺口

当前代码库尚未把 `explainer` 当成一等模块支持，缺口主要在：

1. 模块类型定义。
2. 创作首页切换入口。
3. explainer 专属页面与路由。
4. 后端 explainer API 语义层。
5. explainer 的任务流接口。
6. 历史作品分类与继续编辑跳转。
7. 用户权限与配额。
8. 后台统计维度。
9. 页面文案与产品命名。
10. 与参考风格匹配的默认 prompt / 风格系统。

## 设计原则

### 产品原则

用户使用时，必须明确感知到 `讲解型视频` 是一个独立模块，而不是 `火柴人视频` 的隐藏模式。

### 工程原则

实现层面应最大化复用现有 `stickman` 生成链路，但不能把 `stickman` 的产品语义直接暴露到 `explainer` 模块中。

### 最小正确改动原则

V1 应该新增：

- 新模块语义
- 新路由
- 新 prompt
- 新页面流转
- 新权限 / 统计维度

V1 应避免：

- 新建数据库主表
- 重写整套视频引擎
- 对无关模块进行大规模重构

## 总体方案

### 推荐实现路线

将 `explainer` 作为一个新的模块类型实现，并为其增加独立的：

- 路由
- 页面组件
- 后端接口
- 任务流名称
- 权限键
- 历史分类
- 后台统计桶

同时，第一版尽可能复用现有 `stickman` 的内部生成能力。

### 采用该路线的原因

这条路线在产品正确性和交付速度之间最平衡。

优点：

- 实现风险更低
- 相比重写视频引擎，改动量更小
- 相比把所有功能硬塞进 `stickman`，产品语义更清晰
- 后续如果 `explainer` 需要独立生成器，也更容易平滑演进

## 数据模型设计

### 模块类型

新增支持：

`module_type = 'explainer'`

影响范围包括：

- 后端 Pydantic schema 类型
- 前端 TypeScript 类型
- 创作页表单
- 历史页筛选
- 路由分流
- 后端模块校验辅助函数

### 主存储策略

继续使用 `Project` 作为主承载对象。

V1 不新增独立主表。

### 分镜 Schema 策略

设计文档中已经给出了 explainer 方向的分镜结构。实现时应尽量遵循该结构，同时允许与现有 stickman 合成引擎兼容。

建议的 explainer V1 分镜结构：

```json
{
  "scene_index": 1,
  "scene_title": "第一镜头标题",
  "hook_level": "high",
  "narration_text": "配音文案",
  "subtitle_text": "字幕文案",
  "visual_description": "画面描述",
  "camera_motion": "slow_zoom_in",
  "transition_type": "fade",
  "emotion_tone": "sad",
  "duration": 4.0,
  "image_url": null
}
```

### 兼容映射层

现有合成引擎更习惯使用 `narration`、`scene_description`、`motion_preset`、`subtitle_lines` 等字段，因此 explainer 实现中建议加入一层映射。

建议内部映射关系：

- `scene_index -> scene_id`
- `narration_text -> narration`
- `subtitle_text -> subtitle_lines`
- `visual_description -> scene_description`
- `camera_motion -> motion_preset`

这样可以避免对现有合成逻辑进行深度重写。

### `generation_flags` 预留字段

建议为 explainer V1 预留以下字段：

- `visual_style_key`
- `opening_hook_mode`
- `scene_count`
- `target_duration`
- `has_voice`
- `has_music`
- `subtitle_mode`
- `cover_title`
- `cover_image_mode`

## 后端 API 设计

### 接口分组策略

新增独立的 explainer 接口组，统一放在 `/projects/{id}/explainer/...` 下。

建议接口：

1. `POST /api/projects`
   创建项目，传入 `module_type='explainer'`
2. `POST /api/projects/{id}/explainer/storyboard`
   生成开头与分镜脚本
3. `PUT /api/projects/{id}/explainer/storyboard`
   更新分镜脚本
4. `POST /api/projects/{id}/explainer/images`
   生成全部分镜图
5. `POST /api/projects/{id}/explainer/images/{scene_index}/regenerate`
   重生单张图片
6. `POST /api/projects/{id}/explainer/voice`
   可选：单独生成或刷新配音
7. `POST /api/projects/{id}/explainer/compose`
   基于当前素材执行合成

### 模块校验辅助函数

建议新增一个与 `_get_stickman_project(...)` 对等的函数：

- `_get_explainer_project(...)`

这样可以保证模块校验清晰，不把 stickman 专用逻辑直接套到 explainer 上。

### 任务流接口

建议新增与 stickman 平行的 SSE 任务流：

1. `GET /api/tasks/{project_id}/explainer-generate`
2. `GET /api/tasks/{project_id}/explainer-compose`

建议 task type：

- `explainer_generate`
- `explainer_compose`

## 后端生成服务设计

### 生成器策略

建议新增 `ExplainerGenerator`，但第一版实现为对现有 stickman 能力的包装与重组，而不是完全独立重写。

建议职责：

1. `generate_storyboard(...)`
2. `generate_images(...)`
3. `compose_from_assets(...)`
4. `generate(...)` 用于一键全流程生成

### 可复用边界

可直接复用当前 stickman 的能力：

- TTS 生成
- 字幕切分与时间轴字幕生成
- 轻镜头运动 preset
- 转场处理
- ffmpeg 合成链路
- 图片资产输出结构

不能直接复用 stickman 的产品文案、接口命名、页面文案。

### Prompt 重构

当前 stickman 的 prompt 仍然是围绕 `火柴人科普短视频` 设计的，不适合直接作为 explainer 的默认策略。

explainer V1 需要自己的 prompt 系统，用于：

1. 输入理解
2. 开头 hook 生成
3. 分镜脚本生成
4. 单镜头视觉 prompt 生成

prompt 必须明确优化以下目标：

- 强开头
- 情绪化 / 观点化表达
- 8 到 15 个镜头
- 每镜头只表达一个点
- 前 1 到 3 镜头承担抓人职责
- 尾段负责升华或收束

### 爆款导向 Prompt 规则

如果目标是尽量做出抖音爆款讲解视频效果，那么 explainer prompt 需要显式加入“高留存短视频文案规则”，不能只让模型自由发挥。

建议加入以下规则：

1. 第一幕必须出现冲突、反差、反问、扎心判断、反常识结论或数字爆点中的至少一种。
2. 开头标题必须避免空泛，如“关于成长的思考”这类标题应被视为低质量结果。
3. 每个镜头文案优先使用短句、口语句、断句清晰的表达。
4. 每 2 到 3 个镜头必须推进一次新的信息点，避免连续解释同一层意思。
5. 字幕文本必须适合逐句上屏，而不是一整段长文压缩展示。
6. 收尾必须包含观点升维、情绪收束、行动建议或反转总结中的至少一种。

建议生成链路增加以下中间产物，以便提高稳定性：

- `hook_title`
- `hook_subtitle`
- `hook_conflict_point`
- `core_takeaways`
- `ending_payoff`

## 风格系统设计

### 默认视觉方向

V1 默认风格应从当前较通用的 stickman 教育插画方向，切换到更贴近设计文档要求的 explainer 风格。

目标特征：

- 深蓝底
- 白线稿人物 / 道具 / 场景
- 局部高亮色
- 情绪化或观点化标题
- 横版构图宽松
- 固定字幕安全区

除了设计文档中的基础风格要求，还应补充“短视频平台观感”的视觉目标：

- 首屏中心信息必须更集中，不能散
- 主体与字幕区必须明确分层
- 第一幕构图必须更像封面帧，具备停留感
- 高亮元素要服务于观点，不只是装饰
- 连续镜头之间要有节奏差，不能每幕都同构图同能量

### 三层 Prompt 结构

explainer 的图像 prompt 建议拆成三层：

1. 全局风格模板
2. 角色 / 场景一致性层
3. 分镜级 prompt 层

### 全局风格模板

应统一定义：

- 基础背景色调
- 线条语言
- 高亮色体系
- 字幕安全区构图
- 整体情绪方向

### 一致性层

应统一定义：

- 主角气质
- 主角外观描述
- 场景调性
- 道具风格
- 复用环境元素

### 分镜层

每个镜头单独定义：

- 动作
- 道具
- 情绪
- 环境
- 构图 / 机位感受

同时需要补充一组“爆款节奏字段”，建议体现在 scene 数据中或在生成时计算得出：

- `attention_goal`：该镜头承担抓人、解释、递进还是收束
- `punch_phrase`：该镜头字幕里的核心击中句
- `energy_level`：低 / 中 / 高，用于控制节奏起伏
- `beat_type`：hook / expand / turn / payoff

这样后续在 prompt、字幕和镜头运动上都可以更有针对性地做爆款节奏控制。

### 分镜节奏规则

为了更接近抖音爆款视频效果，建议第一版增加明确的分镜节奏规则：

1. 第 1 镜头：必须承担停留任务，优先展示冲突、结论、反问或大情绪。
2. 第 2 到 3 镜头：必须快速解释“为什么值得继续看”。
3. 中段镜头：每镜头推进一个点，不允许同义重复。
4. 尾段镜头：必须完成收束、拔高、反转或行动建议。
5. 单镜头时长默认应优先落在 2 到 5 秒，而不是平均拉长。
6. 如果某个镜头文案过长，应优先拆镜，而不是硬塞进单镜头。

## 字幕与口播策略

### 字幕策略

如果目标是抖音爆款效果，字幕不能只是“配音文字的被动展示”，而要成为留存工具。

建议规则：

1. 字幕优先短句。
2. 每条字幕最好只承载一个击中点。
3. 高冲突词、高情绪词、高价值词可以考虑做局部高亮。
4. 避免大段完整书面句连续上屏。
5. 第一幕字幕必须比普通镜头更短、更硬、更抓人。

### 口播策略

配音文案应更像短视频真人口播，而不是说明文。

建议规则：

1. 多用短句。
2. 允许适度口语化。
3. 避免连续抽象名词堆叠。
4. 每一幕旁白都要尽量带推进感，而不是平铺描述。
5. 第一幕和最后一幕的语气要明显强于中段普通解释镜头。

## 前端设计

### 创作首页入口

在 `frontend/src/pages/Creator/index.tsx` 中新增第四个模块入口 `讲解型视频`。

创作表单建议支持：

- 主题输入或长文输入
- 风格选择
- 目标时长
- 分镜数量
- 配音配置

### 新页面

建议新增两个专属页面：

1. `frontend/src/pages/ExplainerStudio.tsx`
2. `frontend/src/pages/ExplainerTask.tsx`

### 页面职责划分

`ExplainerStudio.tsx`：

- 创建项目
- 编辑主题或原始长文
- 配置风格 / 时长 / 分镜数
- 生成开头与分镜脚本
- 展示开头钩子质量与爆款导向提示

`ExplainerTask.tsx`：

- 展示分镜列表
- 预览当前图片或视频
- 编辑分镜文案
- 重生单图
- 修改开头标题 / 封面 / 首镜文案
- 合成并预览最终视频
- 标记哪些镜头承担 hook / 递进 / 收束职责

### 路由策略

建议新增路由：

- `/project/:id/explainer`

同时保留 `/project/:id/task` 作为共享任务入口，并在页面内部根据 `module_type` 分流。

推荐分流方式：

- `ProjectTask` 中，`explainer` 项目走 `ExplainerTask`
- `stickman` 项目继续走 `StickmanProjectTask`
- `manim` 项目保持现有逻辑不变

### 交互布局

建议 `ExplainerTask` 页面布局：

1. 左栏：分镜列表
2. 中栏：当前图 / 视频预览
3. 右栏：标题、字幕、文案编辑、单图重生、配音、合成操作

建议在 UI 上额外体现以下信息，方便用户朝“爆款效果”调优：

- 当前开头类型
- 当前镜头角色：hook / expand / payoff
- 当前镜头时长
- 当前镜头字幕是否过长
- 是否存在节奏拖沓风险提示

## 编辑能力设计

### 必须支持的编辑动作

V1 必须支持三类编辑：

1. 分镜文案编辑
2. 单张图片重生
3. 开头编辑

### 分镜文案编辑

用户至少应能修改：

- `subtitle_text`
- `narration_text`

保存时只更新 `storyboard_json`，不要求其他镜头重新生成。

### 单张图片重生

用户应能只重生某一个镜头的图片，不影响其他镜头。

这是设计文档中明确提出的产品能力，因此不能照搬当前 stickman 中“正式分镜图仅管理员可重生”的限制。

### 开头编辑

用户应能修改：

- 开头标题
- 封面图
- 第一镜头文案

第一版可以将这些数据存放在：

- `generation_flags`
- 首镜头 scene 对象

对于 V1 来说，这种实现是可接受的。

## 历史作品、权限与后台设计

### 历史作品接入

在作品页中新增 `explainer` 分类，与以下分类并列：

- `manim`
- `stickman`
- `article`

“继续编辑” 跳转逻辑也必须识别 explainer 项目并跳到正确页面。

### 权限键策略

建议新增独立权限键：

`explainer`

不要直接复用 `stickman` 的配额。

原因：

- 后台控制更清晰
- 运营统计更清晰
- 未来定价更灵活
- 支持排查更容易

### 用户权限扩展

以下前后端结构都需要补上 `explainer`：

- 默认模块权限
- 后台权限模板
- 前端权限标签
- 批量权限更新
- 用户详情展示

### 后台统计

在模块统计中新增 `explainer` 作为独立统计桶。

建议统计维度：

- 总数
- 今日新增
- 成功数
- 失败数
- 成功率

## 实施方案

### 第一阶段：类型与权限基础设施

预计涉及文件：

- `backend/app/schemas/project.py`
- `frontend/src/services/project.ts`
- `backend/app/models/user.py`
- `frontend/src/stores/authStore.ts`
- `frontend/src/pages/admin/AdminUsers.tsx`
- `backend/app/api/admin.py`

任务：

1. 给模块类型定义补上 `explainer`。
2. 给默认权限与后台模板补上 `explainer`。
3. 给后台模块统计输出补上 `explainer`。

### 第二阶段：后端 explainer API 骨架

预计涉及文件：

- `backend/app/api/projects.py`
- `backend/app/api/tasks.py`
- 新增 `backend/app/services/explainer_generator.py`

任务：

1. 新增 `_get_explainer_project(...)`
2. 新增 explainer 分镜接口
3. 新增 explainer 图片接口
4. 新增 explainer 合成接口
5. 新增 explainer 任务流接口

### 第三阶段：生成器实现

预计涉及文件：

- 新增 `backend/app/services/explainer_generator.py`
- 必要时从 `stickman_generator.py` 中少量抽离通用辅助逻辑

任务：

1. 实现 explainer 专属分镜生成 prompt
2. 实现分镜 schema 到现有合成链路的映射
3. 复用现有出图、字幕、TTS、合成能力
4. 补充 explainer 专属 `generation_flags`
5. 增加爆款导向的 hook / 节奏 / 收尾规则

### 第四阶段：前端入口与路由

预计涉及文件：

- `frontend/src/pages/Creator/index.tsx`
- `frontend/src/App.tsx`
- `frontend/src/components/Layout/MainLayout.tsx`

任务：

1. 新增 `讲解型视频` 模块入口
2. 新增 explainer 路由
3. 根据需要补充页标题逻辑

### 第五阶段：前端 explainer 页面

预计涉及文件：

- 新增 `frontend/src/pages/ExplainerStudio.tsx`
- 新增 `frontend/src/pages/ExplainerTask.tsx`
- `frontend/src/pages/ProjectTask.tsx`

任务：

1. 构建 studio 页面，用于分镜生成与参数配置
2. 构建 task 页面，用于分镜编辑、单图重生、预览与合成
3. 在 `ProjectTask` 中增加 `explainer` 分流

### 第六阶段：历史作品接入

预计涉及文件：

- `frontend/src/pages/History/index.tsx`

任务：

1. 新增 explainer 分类 tab
2. 新增 continue-edit 跳转逻辑
3. 保持播放与项目详情行为一致

### 第七阶段：验证与部署准备

任务：

1. 验证项目创建
2. 验证分镜数量与结构
3. 验证图片生成
4. 验证单图重生
5. 验证合成流程
6. 验证历史页跳转
7. 验证权限检查与后台统计
8. 验证前 3 秒钩子是否明显
9. 验证中段是否存在拖沓或同义重复
10. 验证结尾是否有明确收束或拔高

## 文件级改动地图

### 后端

- `backend/app/models/project.py`
  V1 大概率无需新增列。
- `backend/app/schemas/project.py`
  扩展模块类型支持。
- `backend/app/api/projects.py`
  增加 explainer 接口与模块校验函数。
- `backend/app/api/tasks.py`
  增加 explainer SSE 生成与合成任务。
- `backend/app/services/explainer_generator.py`
  新增 explainer 服务包装层。
- `backend/app/models/user.py`
  增加 explainer 默认权限与使用计数逻辑。
- `backend/app/api/admin.py`
  增加 explainer 统计与权限规范化支持。

### 前端

- `frontend/src/services/project.ts`
  增加 explainer 类型与 API 定义。
- `frontend/src/pages/Creator/index.tsx`
  增加新模块入口与创建流程。
- `frontend/src/App.tsx`
  增加路由。
- `frontend/src/pages/ProjectTask.tsx`
  增加 explainer 分流。
- `frontend/src/pages/ExplainerStudio.tsx`
  新页面。
- `frontend/src/pages/ExplainerTask.tsx`
  新页面。
- `frontend/src/pages/History/index.tsx`
  增加分类与跳转逻辑。
- `frontend/src/pages/admin/AdminUsers.tsx`
  增加权限配置支持。
- `frontend/src/stores/authStore.ts`
  扩展权限类型定义。

## 风险评估

### 高风险

1. 如果 prompt 约束不够强，视觉一致性可能仍然不稳定。
2. 如果直接大量复用 stickman prompt，成片很可能只是“换了名字的火柴人流程”，达不到讲解型视频定位。
3. 如果分镜 schema 与现有合成字段的映射分散在多个地方，后续修改文案和单图重生容易出现不同步问题。
4. 如果没有显式加入爆款导向规则，模型很容易生成“结构完整但不抓人”的平庸结果。

### 中风险

1. 字幕安全区可能与主体构图冲突。
2. 如果旁白切分过于机械，音画节奏可能不协调。
3. 如果开头标题、首镜文案、封面信息存储位置不统一，后续修改可能产生状态不一致。
4. 如果镜头普遍过长，整体会失去短视频留存感。

### 低风险

1. 创作首页新入口接入。
2. 历史页分类接入。
3. 后台模块统计新增一项。

## 验收标准

### 功能验收

1. 用户可以创建讲解型视频项目。
2. 用户可以输入主题或长文。
3. 系统可以生成有吸引力的开头。
4. 系统可以生成 8 到 15 个分镜脚本。
5. 系统可以生成统一风格插画。
6. 系统可以生成配音并完成视频合成。
7. 用户可以修改单个分镜文案。
8. 用户可以重生单张图片。
9. 用户可以修改开头后重新合成。

### 质量验收

1. 成片视觉风格明显更接近参考讲解型视频方向。
2. 前 3 秒具备抓人效果。
3. 分镜节奏清晰。
4. 字幕清晰可读。
5. 画面运动不死板，不是单纯切页式播放。
6. 标题与首屏具备明显短视频停留感。
7. 中段内容没有明显拖沓感，信息推进自然。
8. 结尾具备观点收束、情绪收束或行动收束。

### 回归与视频验收要求

本需求不是“功能实现即结束”，而是“达到目标效果才结束”。

因此最终阶段必须补做以下验收动作：

1. 对讲解型视频模块相关功能做完整回归测试。
2. 确认新增模块没有破坏现有 `manim`、`stickman`、`article` 流程。
3. 对生成的视频进行逐帧或细粒度逐段检查，而不是只看最终能播放。
4. 检查前 3 秒是否具备抖音风格的停留感和钩子感。
5. 检查字幕节奏、镜头节奏、画面焦点、情绪推进是否满足爆款目标。
6. 如果结果不满足要求，必须继续优化 prompt、分镜、字幕、镜头运动或合成逻辑，再次生成并复验。
7. 只有在功能正确且视频效果满足目标要求后，才算该需求完成。

## 推荐交付顺序

1. 先确认并保留本实施文档。
2. 从远程更新 `feature/v2-next-optimization-on-3003`。
3. 基于该远程基线创建 `feature/explainer-v1-on-3003`。
4. 为该分支创建独立 worktree。
5. 补齐类型、权限、后台统计基础设施。
6. 搭建后端 explainer API 骨架。
7. 实现 `ExplainerGenerator` 与字段映射。
8. 增加创作首页入口与 explainer 路由。
9. 实现 `ExplainerStudio`。
10. 实现 `ExplainerTask`。
11. 接入历史作品页。
12. 每完成一大块功能就推送远程一次。
13. 完成端到端联调、回归测试和视频逐帧验收。
14. 若效果未达标，则继续优化并重复验证。
15. 验证通过后再基于新分支部署。

## 最终建议

`讲解型视频` V1 的正确落地方式是：

- 产品层独立成模块
- 工程层复用现有视频生成骨架
- 数据层复用 `Project` 主表
- 权限、历史、统计全部显式支持 `explainer`
- 在 prompt 与默认风格上做专属设计
- 在开头、节奏、字幕和口播层面显式按抖音爆款规则做约束
- 在独立 worktree 中开发，并按功能块同步远程
- 最终以“回归通过 + 视频逐帧验收通过”为完成标准

这样可以以最小的风险，最快速地交付一个真正独立、可迭代的讲解型视频模块，而不是把已有火柴人流程简单换皮。
