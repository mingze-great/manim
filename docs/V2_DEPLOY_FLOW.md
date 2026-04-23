# V2 Deploy Flow

新版分支：`feature/chat-style-and-reference-code`

推荐流程：

1. 本地开发并验证
2. 提交到 `feature/chat-style-and-reference-code`
3. 推送到远程：`git push origin feature/chat-style-and-reference-code`
4. 服务器进入 `/opt/manim-v2`
5. 执行 `scripts/deploy_v2_from_git.sh`

服务器要求：

- 代码目录：`/opt/manim-v2`
- 新版前端入口：`3002`
- 新版后端：`8002`
- 后端服务：`manim-v2-backend.service`
- Worker：`manim-v2-worker.service`

为什么不用本地直接上传：

- 生产实际代码可追溯
- 服务器状态和远程仓库一致
- 回滚更简单，只需切回上一个 commit
- 避免本地产物、临时脚本、脏目录混入生产

建议：

- 只把源码、配置、部署脚本纳入 git
- 打包产物、zip、tar、日志、临时目录全部忽略
- 生产部署统一走 `git pull` + build + restart
