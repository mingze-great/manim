# Skill 使用规范

## 基本原则
Skill 不是聊天记忆的替代品，而是把固定工作方法沉淀成可复用流程。能用现成 skill 的工作，不要每次临时发挥。

进入项目后，不要假设 skill 会自动执行。需要使用 skill 时，必须先读取该 skill 的 `SKILL.md`，再按其中步骤执行。

## 当前已安装且应使用的 skill

### `writing-plans`
用途：当任务涉及多步骤规格、架构、流程、重构、部署或验收方案时使用。

必须使用场景：
- 新增或重做一段完整工作流。
- 用户给出一组复杂要求，需要拆成实施步骤。
- 修改会影响后端、前端、Remotion、部署中的两个以上模块。
- 需要给未来 agent 留实施计划。

输出位置：
- `docs/superpowers/plans/YYYY-MM-DD-<任务名>.md`

### `byted-text-to-speech`
用途：文本转语音、配音、朗读、旁白、TTS 试音。

适合使用场景：
- 需要快速生成一段测试配音。
- 对比 TTS 音色、语速、情绪表现。
- 验证文本预处理是否适合语音合成。

注意：
- 本项目默认成片音色仍以平台配置为准。
- 使用该 skill 生成的音频如果要进入平台链路，必须记录来源和参数。

## 系统内置能力的推荐用法

### `imagegen`
用途：生成或编辑位图素材。

适合使用场景：
- 用户明确选择“实时生成场景图”档位。
- 需要制作透明背景 cutout 或参考图变体。

限制：
- 默认 SC1 工作流优先使用 `E:\ai\火柴人工作流\outputs` 素材库。
- 不要用新生成图片替代素材库匹配，除非用户明确要求。

### `skill-creator`
用途：创建项目专属 skill。

建议创建的项目专属 skill：
- `sc1-video-validation`：自动读取成片、抽帧、检查音轨、输出验证摘要。
- `3003-deploy-sync`：更新 `PROJECT_STATE.md`、同步远程、重启服务、创建验证 job。
- `sc1-script-segmentation`：按 1-3 cue 语义分段并生成 2-4 字总结关键词。

### `skill-installer`
用途：安装已有 skill。

建议安装或补齐的 skill 类型：
- git worktree 管理 skill：用于安全创建隔离工作区。
- 执行计划 skill：用于按计划逐步执行并打勾。
- 子任务开发 skill：用于复杂任务拆分给独立子 agent。
- 代码评审 skill：用于提交前专门找 bug、回归风险和测试缺口。
- 浏览器验证 skill：用于自动打开平台、点击生成、截图、检查 UI。

### `openai-docs`
用途：只在涉及 OpenAI/Codex/OpenAI API 的最新官方文档时使用。

限制：
- 本项目常规 3003 平台开发不需要调用它。
- 如果要改 Codex skill、OpenAI API 或模型选型，再使用它。

## 建议补充的项目专属 skill

### 必须优先创建：`sc1-video-validation`
目标：把当前手工做的“下载 MP4、检查音轨、抽关键帧、看字幕和场景图”固化。

应包含：
- 输入：MP4 路径、job id、参考视频路径。
- 检查：视频流、音频流、时长、分辨率、关键帧。
- 抽帧：首段、中段、尾段、已知失败 cue。
- 输出：验证摘要和抽帧路径。

### 第二优先级：`3003-deploy-sync`
目标：把远程同步流程标准化。

应包含：
- 更新 `PROJECT_STATE.md`。
- 检查本地分支、提交、工作树。
- 上传指定文件或推送分支。
- 重启必要 systemd 服务。
- 创建平台验证任务。
- 记录部署 HEAD、job id、输出路径。

### 第三优先级：`sc1-requirements-check`
目标：在修改前自动检查需求是否覆盖。

应包含：
- 读取 `AGENTS.md`、`rules/`、`specs/`。
- 输出本次任务必须满足的验收条件。
- 标记是否需要平台级验证。

## 使用顺序建议
复杂开发任务推荐顺序：

1. `sc1-requirements-check`
2. `writing-plans`
3. 编码实现
4. `sc1-video-validation`
5. `3003-deploy-sync`
6. 代码评审 skill

当前这些项目专属 skill 还未创建时，必须按对应文档手工执行同等流程。
