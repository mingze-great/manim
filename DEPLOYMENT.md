# 部署文档

## 服务器架构

### 生产环境（新服务器）
- **服务器**: 152.136.218.74 (4核4G)
- **密码**: `010421`
- **状态**: ✅ 正常运行
- **域名**: manim.asia

### 开发环境（旧服务器）
- **服务器**: 106.52.166.109 (2核2G)
- **认证**: SSH 密钥登录
- **状态**: ✅ 已部署

## 端口分配

### 旧服务器 (106.52.166.109)

| 服务 | 端口 | 用途 | 状态 |
|------|------|------|------|
| Nginx (生产) | 80, 443 | 重定向到新服务器 | ✅ 运行中 |
| 渲染服务 | 8000 | Manim 视频渲染（服务于生产） | ✅ 运行中 |
| 开发后端 | 8001 | FastAPI 后端（开发测试） | ✅ 运行中 |
| 开发前端 | 3000 | React 前端（开发测试） | ✅ 运行中 |

### 新服务器 (152.136.218.74)
- 生产环境完整服务

## 开发环境访问

### 前端访问
```
http://106.52.166.109:3000
```

### API 访问
```
http://106.52.166.109:8001
http://106.52.166.109:3000/api (通过 Nginx 代理)
```

### API 文档
```
http://106.52.166.109:8001/docs
```

## 环境配置

### 后端配置 (/opt/manim-dev/backend/.env)
```env
DATABASE_URL=sqlite:///./manim_dev.db
DASHSCOPE_API_KEY=sk-cb3cf0d966b84924827b1000d33ee1f5
IMAGE_API_KEY=sk-cb3cf0d966b84924827b1000d33ee1f5
SECRET_KEY=dev-secret-key-123456
OLD_SERVER_URL=http://106.52.166.109:8000
NEW_SERVER_URL=http://106.52.166.109:3000
ENVIRONMENT=development
DEBUG=true
PORT=8001
```

### 前端构建
- **构建工具**: Vite
- **输出目录**: `/opt/manim-dev/frontend/dist`
- **API 代理**: Nginx 代理 `/api` 到 `localhost:8001`

## 服务管理

### 后端服务

启动后端：
```bash
cd /opt/manim-dev/backend
nohup /opt/manim-dev/backend/venv/bin/python -m uvicorn app.main:app --host 0.0.0.0 --port 8001 > /opt/manim-dev/logs/backend.log 2>&1 &
echo $! > /opt/manim-dev/logs/backend.pid
```

停止后端：
```bash
kill $(cat /opt/manim-dev/logs/backend.pid)
```

重启后端：
```bash
kill $(cat /opt/manim-dev/logs/backend.pid) 2>/dev/null
cd /opt/manim-dev/backend
nohup /opt/manim-dev/backend/venv/bin/python -m uvicorn app.main:app --host 0.0.0.0 --port 8001 > /opt/manim-dev/logs/backend.log 2>&1 &
echo $! > /opt/manim-dev/logs/backend.pid
```

查看日志：
```bash
tail -f /opt/manim-dev/logs/backend.log
```

### 前端更新

重新构建前端：
```bash
cd /opt/manim-dev/frontend
npm run build
```

重新加载 Nginx：
```bash
systemctl reload nginx
```

## 目录结构

### 旧服务器开发环境
```
/opt/manim-dev/
├── backend/
│   ├── venv/                  # Python 虚拟环境
│   ├── .env                   # 环境变量
│   ├── app/                   # 应用代码
│   │   ├── main.py           # 主应用（已修改：注释 start_scheduler）
│   │   └── tasks/
│   │       └── cleanup.py    # 简化版本（无 APScheduler）
│   ├── manim_dev.db          # SQLite 数据库
│   └── requirements.txt
├── frontend/
│   ├── dist/                  # 构建输出
│   ├── src/                   # 源代码
│   └── package.json
├── data/dev/                  # 数据目录
├── videos/dev/                # 视频目录
├── logs/
│   ├── backend.log           # 后端日志
│   └── backend.pid           # 后端进程 PID
└── backups/                   # 备份目录
```

## Git 分支管理

```
main                       # 生产分支
develop                    # 开发分支（当前工作分支）
feature/article-generation # 公众号功能（已保留）
```

## API 端点

### 健康检查
- 后端直接访问: `GET http://106.52.166.109:8001/health`
- 前端代理访问: `GET http://106.52.166.109:3000/api/` (需要实际 API 路径)

### 认证
- 登录: `POST http://106.52.166.109:3000/api/auth/login`
- 注册: `POST http://106.52.166.109:3000/api/auth/register`

## 注意事项

1. **不影响生产环境**: 旧服务器的 8000 端口继续为生产环境提供渲染服务
2. **资源限制**: 旧服务器只有 2核2G，避免使用 Docker 以节省资源
3. **APScheduler 已禁用**: 为避免依赖问题，定时任务已禁用
4. **数据库**: 开发环境使用 SQLite，生产环境使用 PostgreSQL

## 故障排查

### 后端无法启动
1. 检查日志: `tail -100 /opt/manim-dev/logs/backend.log`
2. 清理缓存: `find /opt/manim-dev/backend -type d -name '__pycache__' -exec rm -rf {} +`
3. 检查进程: `ps aux | grep uvicorn`
4. 检查端口: `netstat -tlnp | grep 8001`

### 前端无法访问
1. 检查 Nginx: `systemctl status nginx`
2. 检查端口: `netstat -tlnp | grep 3000`
3. 测试 Nginx 配置: `nginx -t`
4. 查看 Nginx 日志: `tail -f /var/log/nginx/error.log`

### API 代理失败
1. 检查后端运行: `curl http://localhost:8001/health`
2. 检查 Nginx 配置: `cat /etc/nginx/sites-enabled/manim-dev.conf`
3. 测试代理: `curl http://localhost:3000/api/auth/login`

## 部署历史

### 2026-04-07
- ✅ 在旧服务器创建开发环境目录结构
- ✅ 克隆 develop 分支代码
- ✅ 配置 Python 虚拟环境和依赖
- ✅ 禁用 APScheduler（创建简化版 cleanup.py）
- ✅ 配置后端 .env 文件
- ✅ 启动后端服务（端口 8001）
- ✅ 构建前端项目
- ✅ 配置 Nginx 托管前端（端口 3000）
- ✅ 验证服务可从外网访问