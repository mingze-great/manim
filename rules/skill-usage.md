# Skill 使用规范

## 基本原则
Skill 不是聊天记忆的替代品，而是把固定工作方法沉淀成可复用流程。能用现成 skill 的工作，不要每次临时发挥。

进入项目后，不要假设 skill 会自动执行。需要使用 skill 时，必须先读取该 skill 的 `SKILL.md`，再按其中步骤执行。新安装的 skill 通常从下一轮对话开始稳定出现在可用列表中。

## 已安装的流程类 skills

### `brainstorming`
用途：需求分析、产品设计、方案探索。

必须使用场景：
- 用户提出一个新功能、新模块、新平台能力。
- 用户的需求还不够清晰，需要先明确目标、边界、成功标准。
- 需要在实现前给出 2-3 个方案并让用户确认。
- 涉及产品体验、交互流程、成片效果、商业化规则等非纯代码问题。

约束：
- 使用该 skill 时，不能直接写代码。
- 必须先形成设计说明并获得用户确认，再进入 `writing-plans`。

### `writing-plans`
用途：把已确认的规格拆成可执行实施计划。

必须使用场景：
- 新增或重做完整工作流。
- 修改会影响后端、前端、Remotion、TTS、部署中的两个以上模块。
- 需要让多个 agent 并行开发。
- 需要给未来 agent 留可执行计划。

输出位置：
- `docs/superpowers/plans/YYYY-MM-DD-<任务名>.md`

### `executing-plans`
用途：按计划在当前会话逐步执行。

使用场景：
- 已有计划文档。
- 任务之间耦合较强，不适合并行。
- 当前没有可用 subagent，或用户希望单线程稳妥执行。

### `subagent-driven-development`
用途：master agent 根据计划，把独立任务分发给多个子 agent 实施，并逐项 review。

必须使用场景：
- 用户明确要求多个 agent 并行开发。
- 计划中存在多个相互独立的任务。
- 任务能按文件、模块、接口或 worktree 边界拆开。

流程要求：
- master agent 只做需求澄清、计划、分发、review、集成、最终验收。
- 每个子 agent 只拿自己的任务说明、相关文件、验收条件，不继承 master 的全部聊天上下文。
- 每个子任务完成后必须单独验收。
- 最终整合后必须做整体验收。

### `dispatching-parallel-agents`
用途：把互不依赖的信息收集、验证或开发任务并行派发。

使用场景：
- 同时调查多个模块。
- 同时验证多个方案。
- 同时让多个 agent 检查不同文件或风险。
- master agent 需要快速收集多个独立结论。

限制：
- 不派发会互相修改同一文件的任务，除非先划分 worktree 或明确合并策略。

### `using-git-worktrees`
用途：为并行开发创建隔离工作区。

必须使用场景：
- 多个 agent 同时改代码。
- 一个需求可能破坏主工作树稳定性。
- 需要试验两个以上方案。

要求：
- 每个并行需求一个独立 worktree 或独立分支。
- master agent 最后统一 review 和合并。

### `requesting-code-review`
用途：请求独立代码评审。

必须使用场景：
- 每个子 agent 完成一个任务后。
- 重大功能完成后。
- 合并到主分支或部署前。
- 修改涉及鉴权、文件、远程执行、TTS、渲染、部署脚本等高风险区域。

### `receiving-code-review`
用途：处理 review 反馈。

必须使用场景：
- 收到 reviewer 或用户的多条修改意见。
- review 意见不清楚或可能不适合当前代码库。
- 需要逐条判断是否接受、反驳或延后。

要求：
- 不盲目接受 review。
- 每条反馈先理解、验证、判断，再修改。

### `verification-before-completion`
用途：完成前验证。

必须使用场景：
- 准备说“完成”“修好了”“可用”“通过”之前。
- 准备提交、部署、交付成片之前。
- 子 agent 声称完成后，master agent 独立验收前。

要求：
- 没有新鲜验证证据，不能声称完成。

### `finishing-a-development-branch`
用途：开发分支收尾。

使用场景：
- 一个功能分支或 worktree 准备合并。
- 多个子任务已完成，准备统一整理、验证、提交或交付。

### `test-driven-development`
用途：测试驱动开发。

使用场景：
- 修复明确 bug。
- 新增可单元测试的业务逻辑。
- 修改脚本分段、素材匹配、时间线计算、字幕清洗、关键词生成等纯逻辑。

要求：
- 能写测试时先写失败测试，再写最小实现。

### `systematic-debugging`
用途：系统化排查问题。

必须使用场景：
- 同一个问题反复出现。
- 不清楚根因，不能只靠猜。
- 涉及“字幕不同步”“场景图被挡住”“TTS 失败”“部署后平台不可用”等链路问题。

## 已安装的验证、设计和安全类 skills

### `playwright`
用途：真实浏览器自动化。

必须使用场景：
- 验证 3003 前端流程。
- 自动打开平台、登录、输入主题、点击生成、观察进度、截图。
- 调试前端交互、按钮、表单、预览区域。

### `screenshot`
用途：系统或应用截图。

使用场景：
- 用户要求截图。
- 浏览器/平台截图工具不适用，需要 OS 级截图。

### `notion-spec-to-implementation`
用途：从 Notion 规格转实施计划。

使用场景：
- 需求或产品规格来自 Notion。
- 需要把外部 spec 转为任务、计划、验收标准。

### `security-best-practices`
用途：安全最佳实践检查。

必须使用场景：
- 用户要求安全 review。
- 修改鉴权、登录、token、远程命令、文件上传、下载、路径处理、公开 API。
- 准备把新接口暴露给外部用户。

### `security-threat-model`
用途：威胁建模。

使用场景：
- 新增外网可访问能力。
- 新增用户上传、远程执行、凭据存储、多租户、支付、队列任务。
- 用户要求做 AppSec 或威胁分析。

### `byted-text-to-speech`
用途：文本转语音、配音、朗读、旁白、TTS 试音。

使用场景：
- 快速生成一段测试配音。
- 对比 TTS 音色、语速、情绪表现。
- 验证文本预处理是否适合语音合成。

注意：
- 本项目默认成片音色仍以平台配置为准。
- 使用该 skill 生成的音频如果要进入平台链路，必须记录来源和参数。

## 系统内置能力

### `imagegen`
用途：生成或编辑位图素材。

使用场景：
- 用户明确选择“实时生成场景图”档位。
- 需要制作透明背景 cutout 或参考图变体。

限制：
- 默认 SC1 工作流优先使用 `E:\ai\火柴人工作流\outputs` 素材库。
- 不要用新生成图片替代素材库匹配，除非用户明确要求。

### `skill-creator`
用途：创建项目专属 skill。

优先创建：
- `sc1-video-validation`
- `3003-deploy-sync`
- `sc1-requirements-check`
- `3003-master-agent-orchestration`

### `skill-installer`
用途：从网络安装已有 skill。

使用场景：
- 用户要求补充开发流程、review、安全、测试、部署等可复用技能。
- 当前项目缺少某个明确流程 skill。

### `openai-docs`
用途：查询 OpenAI/Codex/OpenAI API 官方最新文档。

限制：
- 本项目常规 3003 平台开发不需要调用它。
- 如果要改 Codex skill、OpenAI API 或模型选型，再使用它。

## 复杂开发推荐流程

### 单需求
1. `brainstorming`
2. `writing-plans`
3. `test-driven-development` 或直接实现
4. `verification-before-completion`
5. `requesting-code-review`
6. `finishing-a-development-branch`

### 多需求并行
1. master agent 使用 `brainstorming` 明确需求。
2. master agent 使用 `writing-plans` 写总计划和任务拆分。
3. master agent 使用 `using-git-worktrees` 为每个需求准备隔离工作区。
4. master agent 使用 `subagent-driven-development` 或 `dispatching-parallel-agents` 分发任务。
5. 每个子 agent 完成自己的开发和局部验证。
6. master agent 对每个子任务使用 `requesting-code-review`。
7. master agent 合并任务后使用 `verification-before-completion` 做整体验收。
8. 如涉及 3003 部署，按 `rules/quality-gates.md` 远程部署门禁执行。

## 建议创建的项目专属 skills

### `sc1-video-validation`
目标：固化“下载 MP4、检查音轨、抽关键帧、看字幕和场景图”的流程。

### `3003-deploy-sync`
目标：固化“更新状态、同步远程、重启服务、创建验证 job、记录结果”的流程。

### `sc1-requirements-check`
目标：编码前自动读取项目规则并输出本次任务验收条件。

### `3003-master-agent-orchestration`
目标：固化 master agent 的需求澄清、任务拆分、并行分发、逐项验收、统一整合、最终验收流程。
