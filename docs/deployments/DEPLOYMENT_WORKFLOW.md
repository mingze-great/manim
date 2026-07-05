# 3002/3003 部署与回退流程

本流程用于避免“忘记当前服务是哪个分支、哪个提交、远程和本地不同步、无法回退”的问题。

## 1. 查看当前运行状态

先看远程真实运行状态，不要只看本地。

```bash
systemctl show manim-v2-backend.service -p WorkingDirectory -p ExecStart -p Environment --no-pager
systemctl show manim-v2-worker.service -p WorkingDirectory -p ExecStart -p Environment --no-pager
systemctl show manim-v2-3003-backend.service -p WorkingDirectory -p ExecStart -p Environment --no-pager
systemctl show manim-v2-3003-worker.service -p WorkingDirectory -p ExecStart -p Environment --no-pager
grep -R "root .*dist\|3002\|3003\|8002\|8003" -n /etc/nginx/sites-enabled /etc/nginx/conf.d 2>/dev/null
cd /opt/manim-v2 && git branch --show-current && git rev-parse HEAD && git status --short
```

## 2. 开发新功能

- 新功能先在本地或 3003 开发。
- 优先复用已有模块和成熟开源方案，不重复造轮子。
- 不确定的能力先做最小验证，再产品化。
- 不直接修改 3002 试错。

## 3. 部署 3003

部署到 3003 前先备份：

```bash
backup_dir="/opt/manim-v2-3003-backups/deploy_$(date +%Y%m%d_%H%M%S)"
mkdir -p "$backup_dir"
rsync -a --delete --exclude storage --exclude videos --exclude app/videos /opt/manim-v2-3003-snapshot/backend/ "$backup_dir/backend/"
rsync -a --delete /opt/manim-v2-3003-repro-3002-current/frontend/dist/ "$backup_dir/frontend-dist/"
cp /opt/manim-v2-3003-snapshot/backend/.env "$backup_dir/backend.env" 2>/dev/null || true
```

3003 环境必须保持：

```text
PORT=8003
CELERY_QUEUE=manim_v2_3003
DATABASE_URL=sqlite:////opt/manim/backend/manim.db
```

重启并验证：

```bash
systemctl daemon-reload
systemctl restart manim-v2-3003-backend.service manim-v2-3003-worker.service
curl -s -o /dev/null -w '3003:%{http_code}\n' http://127.0.0.1:3003/
curl -s -o /dev/null -w '8003docs:%{http_code}\n' http://127.0.0.1:8003/docs
systemctl is-active manim-v2-3003-backend.service manim-v2-3003-worker.service
```

## 4. 固化快照

如果要把当前运行状态作为可回退版本，必须创建快照分支、导出模板表、写入部署文档并推送远程。

```bash
cd /opt/manim-v2
git switch -c repro/3002-current-YYYYMMDD
python3 - <<'PY'
import sqlite3, json, pathlib
con = sqlite3.connect('/opt/manim/backend/manim.db')
con.row_factory = sqlite3.Row
rows = [dict(r) for r in con.execute('select * from templates order by id')]
out = pathlib.Path('docs/deployments/templates_3002_YYYYMMDD.json')
out.write_text(json.dumps(rows, ensure_ascii=False, indent=2), encoding='utf-8')
print('exported templates', len(rows), 'to', out)
PY
git add backend frontend/src docs/deployments deploy
git add -f frontend/dist
git reset -- frontend/tsconfig.tsbuildinfo || true
git commit -m "snapshot: current 3002 deployed state YYYY-MM-DD"
git push -u origin repro/3002-current-YYYYMMDD
```

## 5. 从 3003 同步到 3002

同步前确认 3003 实际来源：

```bash
front_dist=$(awk '/^[[:space:]]*root[[:space:]]/ {gsub(/;/, "", $2); print $2; exit}' /etc/nginx/sites-enabled/manim-v2-3003.conf)
back_dir=$(systemctl show manim-v2-3003-backend.service -p WorkingDirectory --value)
echo "$front_dist"
echo "$back_dir"
```

备份 3002 并同步，必须保留 3002 `.env`：

```bash
backup_dir="/opt/manim_backups/deploy_3003_to_3002_$(date +%Y%m%d_%H%M%S)"
mkdir -p "$backup_dir"
rsync -a --delete --exclude node_modules --exclude dist --exclude videos --exclude app/videos --exclude __pycache__ /opt/manim-v2/backend/ "$backup_dir/backend/"
rsync -a --delete --exclude node_modules --exclude dist /opt/manim-v2/frontend/ "$backup_dir/frontend/"
cp /opt/manim-v2/backend/.env "$backup_dir/backend.env" 2>/dev/null || true
cp /opt/manim-v2/backend/.env /tmp/manim-v2-3002.env.deploy-preserve
systemctl stop manim-v2-worker.service manim-v2-backend.service
rsync -a --delete --exclude .env --exclude storage --exclude videos --exclude app/videos --exclude __pycache__ --exclude '*.pyc' "$back_dir/" /opt/manim-v2/backend/
cp /tmp/manim-v2-3002.env.deploy-preserve /opt/manim-v2/backend/.env
rsync -a --delete "$front_dist/" /opt/manim-v2/frontend/dist/
systemctl daemon-reload
systemctl start manim-v2-backend.service
systemctl start manim-v2-worker.service
```

3002 环境必须保持：`8002`、`CELERY_QUEUE=manim_v2`、`DATABASE_URL=sqlite:////opt/manim/backend/manim.db`。

## 6. 验证 3002

```bash
curl -k -s -L -o /tmp/check.out -w 'home:%{http_code}\n' https://www.lazymedia.cn/
curl -k -s -L -o /tmp/check.out -w 'login:%{http_code}\n' https://www.lazymedia.cn/login
curl -k -s -L -o /tmp/check.out -w 'creator:%{http_code}\n' https://www.lazymedia.cn/creator
systemctl is-active nginx manim-v2-backend.service manim-v2-worker.service
for id in 26 53 57 67 72 77 78; do
  curl -s -o /dev/null -w "template_$id:%{http_code} %{content_type}\n" "http://127.0.0.1:3002/api/videos/template_examples/template_${id}_preview.mp4"
done
```

## 7. 回退

回退优先级：

1. 使用部署文档记录的快照分支和 commit。
2. 使用部署前备份目录。
3. 使用数据库模板导出或数据库备份恢复模板状态。

回退前同样要备份当前现场，不能直接覆盖。

## 8. 最终交付必须说明

- 来源分支和 commit。
- 部署目标和服务路径。
- 备份目录。
- 验证过的 URL、服务和模板预览。
- 哪些运行时文件被刻意排除。