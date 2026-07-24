# Vibe Coding 过程约束

## 目标
允许快速用 AI 协作开发，但不允许项目失控。每次改动都必须可追溯、可验证、可回滚，并继续贴近 SC1 参考视频。

## 编码前必须做
- 读取 `AGENTS.md`、`PROJECT_STATE.md`、`rules/quality-gates.md`、`rules/skill-usage.md`。
- 如果是产品行为、成片效果或生成链路变化，同时读取 `specs/sc1-stickman-workflow-spec.md`。
- 先搜索现有实现，再决定修改位置。
- 优先修现有平台链路，不新增一次性脚本替代平台能力。
- 明确本次变更属于哪一类：文档、前端、后端、TTS、Remotion、部署、验证。

## 状态管理
- 不依赖聊天上下文保存项目记忆。
- 远程同步、部署、上下文压缩或交接前，必须更新 `PROJECT_STATE.md`。
- `PROJECT_STATE.md` 至少记录：
  - 当前任务
  - 已完成内容
  - 当前问题
  - 最近修改文件
  - 下一步计划
  - 重要技术决策
  - 不要重复做的事情
  - 当前分支、提交、部署目录、验证 job id 和输出路径

## 改动范围
- 优先做最小修复。
- 不为一个局部问题重写整条工作流。
- 不新增重复的“临时生成流程”来绕过平台。
- 不提交密钥、token、密码、`.env` 私密配置、上传文件、缓存、生成媒体或部署压缩包。
- 不用硬编码兜底假装成功。
- 不用占位文案、空字幕、静音音频或伪造状态掩盖问题。

## 视频质量约束
- 最终判断必须看实际成片或抽帧。
- 用户问“平台是否可用”时，必须尽量通过 3003 平台完整生成验证。
- 检查首段、中段、尾段和之前失败过的 cue 边界。
- 检查音频、中文字幕、英文字幕、场景图、总结关键词是否共用同一套 cue 时间线。
- 检查场景图是否居中、完整、无白底框、无被横线/字幕/面板遮挡。
- 检查总结关键词是否为 2-4 个字情绪标签，而不是字幕截取。

## 编码风格
- 遵循现有 Python、TypeScript、CSS、Remotion 写法。
- 后端编排优先放在 `backend/app/services/ai_video.py`，除非已有清晰拆分点。
- 最终视频表现优先放在 `Sc1StickmanVideo.jsx`。
- 命名要贴近 SC1 领域：`captionCues`、`summaryLabel`、`assetImages`、`durationFrames`、`audioScenes`。
- 只在非显而易见的时间线、素材清理、同步或部署逻辑旁加简短注释。

## 测试与验证
- Python 修改后至少运行：`python -m py_compile backend/app/services/ai_video.py`。
- 提交前运行：`git diff --check`。
- 渲染相关修改后，必须生成新平台任务并抽帧。
- 成片必须确认存在音频流。
- 面向用户的结果放 `outputs/`；临时分析和脚本放 `work/`。

## 提交与同步
- 一个提交只做一组相关事情。
- 推荐提交信息：
  - `fix: align sc1 cue timing`
  - `fix: prevent scene image clipping`
  - `docs: update sc1 workflow rules`
  - `chore: record 3003 deploy state`
- 远程部署前必须先更新并提交 `PROJECT_STATE.md`。
- 远程部署后必须记录服务状态、部署提交、平台 job id 和成片路径。

## 不确定时
- 保留参考视频要求。
- 保留素材库路径。
- 保留单张居中场景图设计。
- 只在缺失信息会改变用户可见输出、部署目标或不可逆操作时询问用户。
