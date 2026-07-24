# 3003 开发流程文档实施计划

> **给后续 agent 的说明：** 实施本计划时应使用可逐步执行的计划流程。每个步骤使用复选框记录状态。

**目标：** 补齐项目长期记忆、vibe coding 约束、质量门禁、skill 使用规范和 SC1 工作流规格，让后续 agent 不依赖聊天记忆也能继续开发。

**架构：** 稳定项目规则放在 `AGENTS.md`，当前状态放在 `PROJECT_STATE.md`，日常约束放在 `rules/`，产品/技术规格放在 `specs/`，历史实施计划放在 `docs/superpowers/plans/`。这样可以把“固定规则”“当前进度”“验收标准”“执行计划”分开管理。

**技术栈：** Markdown 文档、现有 3003 Python 后端、React 前端、Remotion 渲染服务、systemd 远程部署。

## 全局约束

- 本地 SC1 素材库固定为 `E:\ai\火柴人工作流\outputs`。
- 远程 SC1 素材库固定为 `/opt/manim_assets/sc1-outputs`。
- 同一时间只保留一张居中场景图。
- 场景图出现后不能持续缩放。
- 字幕必须跟完整旁白同步，不能只展示场景标题。
- 总结关键词必须是中文情绪短词，通常 2-4 个字。
- 每次远程同步、部署或上下文交接前必须更新 `PROJECT_STATE.md`。

---

### 任务 1：补充项目级 agent 规则

**文件：**
- 新增/修改：`AGENTS.md`

**接口：**
- 输入：用户确认过的项目要求和当前 `PROJECT_STATE.md`。
- 输出：后续 agent 编码前必须读取的项目级规则。

- [x] **步骤 1：写入项目使命和固定约束**

记录 SC1 参考视频目标、素材路径、单张居中场景图、字幕同步、总结关键词、远程部署规则。

- [x] **步骤 2：写入上下文恢复流程**

要求未来 agent 在上下文重置后依次读取 `AGENTS.md`、`PROJECT_STATE.md`、`rules/` 和 `specs/`。

- [x] **步骤 3：明确自动读取边界**

说明不能假设每次编码前系统都会自动完整读取所有文件，agent 必须主动读取关键文档。

### 任务 2：补充 vibe coding 约束

**文件：**
- 新增/修改：`rules/vibe-coding.md`

**接口：**
- 输入：`AGENTS.md` 中的项目约束。
- 输出：日常 AI 协作编码纪律。

- [x] **步骤 1：写入编码前约束**

规定编码前要读哪些文件、如何确认任务类型、如何先搜索现有实现。

- [x] **步骤 2：写入状态管理和改动范围约束**

规定 `PROJECT_STATE.md` 的更新时机，禁止提交密钥、缓存、生成媒体和临时产物。

- [x] **步骤 3：写入视频质量约束**

规定平台生成、抽帧、音轨、字幕、场景图、总结关键词的验证要求。

### 任务 3：补充质量门禁

**文件：**
- 新增：`rules/quality-gates.md`

**接口：**
- 输入：项目开发流程和远程部署流程。
- 输出：编码前、提交前、部署前、部署后、成片验收、文档验收的门禁清单。

- [x] **步骤 1：写入编码前门禁**

要求读取关键文档、确认分支、确认工作树、确认是否需要 skill。

- [x] **步骤 2：写入提交和部署门禁**

要求检查密钥/缓存/生成物、运行必要检查、更新 `PROJECT_STATE.md`、记录部署信息。

- [x] **步骤 3：写入成片验收门禁**

要求检查场景图、字幕、音频、关键词、右上角标签、水印和参考视频贴近度。

### 任务 4：补充 skill 使用规范

**文件：**
- 新增：`rules/skill-usage.md`

**接口：**
- 输入：当前已安装 skill 和项目开发流程。
- 输出：哪些场景必须使用现成 skill，哪些项目专属 skill 建议创建。

- [x] **步骤 1：记录当前可用 skill**

记录 `writing-plans` 和 `byted-text-to-speech` 的使用场景。

- [x] **步骤 2：记录系统内置能力用法**

记录 `imagegen`、`skill-creator`、`skill-installer`、`openai-docs` 的项目内使用边界。

- [x] **步骤 3：推荐项目专属 skill**

推荐创建 `sc1-video-validation`、`3003-deploy-sync`、`sc1-requirements-check`。

### 任务 5：补充 SC1 工作流规格

**文件：**
- 新增/修改：`specs/sc1-stickman-workflow-spec.md`

**接口：**
- 输入：参考视频要求和现有平台架构。
- 输出：3003 一键成片工作流的产品和技术验收标准。

- [x] **步骤 1：写入用户流程和生成链路**

覆盖文案生成、语义分段、素材匹配、版式、字幕、关键词、声音、进度体验。

- [x] **步骤 2：写入验收标准和验证命令**

记录平台任务、MP4 音视频流、抽帧、cue 时间线、关键词累计展示等验收项。

### 任务 6：补充开发流程控制规格

**文件：**
- 新增：`specs/development-control-spec.md`

**接口：**
- 输入：项目文档分工、编码流程、验证流程、部署流程。
- 输出：需求进入、计划、编码、验证、部署、交接的闭环规格。

- [x] **步骤 1：写入文档分工**

明确 `AGENTS.md`、`PROJECT_STATE.md`、`rules/`、`specs/`、`docs/superpowers/plans/` 分别负责什么。

- [x] **步骤 2：写入任务进入流程**

把任务分成文档治理、局部修复、跨模块功能、平台验收、远程部署，并规定最低要求。

- [x] **步骤 3：写入可控性验收标准**

规定新 agent 能否恢复、部署能否追溯、成片修复是否有证据、复杂任务是否有计划。

### 任务 7：验证文档集合

**文件：**
- 读取：`AGENTS.md`
- 读取：`rules/vibe-coding.md`
- 读取：`rules/quality-gates.md`
- 读取：`rules/skill-usage.md`
- 读取：`specs/sc1-stickman-workflow-spec.md`
- 读取：`specs/development-control-spec.md`

**接口：**
- 输入：已完成的文档文件。
- 输出：可审阅、可提交的文档变更。

- [x] **步骤 1：检查文件可发现**

运行：

```powershell
rg --files -g AGENTS.md -g "rules/**" -g "specs/**" -g "docs/superpowers/plans/**"
```

期望：所有新增文档都能列出。

- [x] **步骤 2：检查文档占位词**

运行：

```powershell
$placeholderPattern = ([string]::Join('', [char[]](84,66,68))) + '|' + ([string]::Join('', [char[]](84,79,68,79))) + '|' + ([string]::Join('', [char[]](102,105,108,108,32,105,110))) + '|' + ([string]::Join('', [char[]](108,97,116,101,114)))
Select-String -Path AGENTS.md,rules/*.md,specs/*.md -Pattern $placeholderPattern
```

期望：没有真实占位内容。

- [x] **步骤 3：检查 Git diff**

运行：

```powershell
git diff --check
git diff -- AGENTS.md rules specs docs/superpowers/plans PROJECT_STATE.md
```

期望：只包含预期文档变更。
