# 3003 知识 IP 工作流字幕同步修复记录（2026-07-11）

## 修复目标

修复 3003 知识 IP 自动包装工作流中的两个问题：

- 顶部进度条不能使用固定栏目名，必须根据当前视频文案总结章节。
- 中间字幕必须与真人音频一致，不能使用章节标题代替字幕；同时保留英文字幕。

## 部署来源

- 服务器：152.136.218.74
- 目录：/opt/manim-v2-3003-snapshot
- 分支：codex/3003-knowledge-ip-workflow-20260710
- 提交：3413c778
- 提交信息：fix: sync knowledge IP captions with ASR and dynamic tabs

## 实现说明

- KnowledgeIpPackage.jsx：顶部四栏改为 props 驱动的 	opTabs，支持按时间高亮；不再写死固定栏目。
- prepare-knowledge-ip-job.js：支持从 Paraformer/阿里 ASR 的逐字时间戳生成真实字幕。
- 字幕切分逻辑：优先按标点切分；无标点句子不从中间硬切。
- 双语字幕：支持 --caption-translations 输入，每条 ASR 中文字幕按顺序绑定英文翻译。

## 本次验证

- 重新生成 knowledge-ip-test-prepared props：67 条 ASR 中文字幕，67 条英文字幕，缺失英文数量为 0。
- 渲染 25 秒双语同步预览，视频流 25.000s，音频流 25.045s。
- 关键帧验证：
  - 0.5s：无字幕，避免无声音先出字幕。
  - 4s：显示第一句中文和英文，对应真人音频。
  - 12s：字幕切换到后续 ASR 句子。
  - 20s：字幕继续与音频时间轴一致。
- 静帧验证：4s、30s、70s、130s、结尾帧均可访问，用于检查顶部章节高亮和字幕展示。

## 验收链接

- 双语 25 秒预览：http://152.136.218.74:3003/renders/knowledge-ip-preview-bilingual-sync.mp4
- 静帧目录示例：
  - http://152.136.218.74:3003/renders/knowledge-ip-stills/frame-120.png
  - http://152.136.218.74:3003/renders/knowledge-ip-stills/frame-900.png
  - http://152.136.218.74:3003/renders/knowledge-ip-stills/frame-2100.png
  - http://152.136.218.74:3003/renders/knowledge-ip-stills/frame-3900.png
  - http://152.136.218.74:3003/renders/knowledge-ip-stills/frame-5081.png

## 注意事项

当前测试样片的英文翻译文件位于运行资产目录，不纳入 Git。产品化时应在上传视频工作流中由翻译模型生成 caption_translations.json，再调用 prepare-knowledge-ip-job.js --caption-translations=...。
