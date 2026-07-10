# 3003 首页恢复与知识 IP 入口部署记录（2026-07-11）

## 目标

在当前 3003 分支上恢复此前首页产品化优化，并新增知识 IP 自动包装工作流入口。

## 变更内容

- 从 `origin/codex/3003-knowledge-ip-workflow-snapshot-20260710` 合并首页优化：
  - 首页平台名保持“思维可视化”。
  - 首页包含“申请试用”入口。
  - Footer 增加 ICP 备案号 `蜀ICP备2026016040号-2`，链接至 `https://beian.miit.gov.cn/`。
  - 首页模板预览展示逻辑恢复。
- 新增前端路由：`/knowledge-ip`。
- 左侧菜单新增入口：`知识IP包装`。
- 新增知识 IP 自动包装工作台页面，用于展示当前 3003 已打通的完整成片链路和验收视频。

## 回退点

修改前备份目录：`/opt/manim_backups/3003_before_home_knowledge_ip_20260711_061715`

## 验证

- `frontend && npm run build` 成功。
- 构建产物中已包含：
  - `蜀ICP备2026016040号-2`
  - `申请试用`
  - `知识IP包装`
  - `知识IP自动包装`
- `http://127.0.0.1:3003/knowledge-ip` 返回 200。
- 完整成片链接恢复：`http://152.136.218.74:3003/renders/knowledge-ip-final-full-bilingual-sync.mp4`。

## 注意

当前知识 IP 页面已经有前端入口和验收视频展示。真正“上传视频后自动排队生成”的 API 还需要下一步接入后台任务队列。
