# 3002/3003 ???????

???????????????????????????????????????????

## 1. ????????

??????????????????

```bash
systemctl show manim-v2-backend.service -p WorkingDirectory -p ExecStart -p Environment --no-pager
systemctl show manim-v2-worker.service -p WorkingDirectory -p ExecStart -p Environment --no-pager
systemctl show manim-v2-3003-backend.service -p WorkingDirectory -p ExecStart -p Environment --no-pager
systemctl show manim-v2-3003-worker.service -p WorkingDirectory -p ExecStart -p Environment --no-pager
```

???? nginx ???

```bash
grep -R "root .*dist\|3002\|3003\|8002\|8003" -n /etc/nginx/sites-enabled /etc/nginx/conf.d 2>/dev/null
```

?? Git ???

```bash
cd /opt/manim-v2
git branch --show-current
git rev-parse HEAD
git status --short
```

## 2. ?????

- ???????? 3003 ???
- ???????????????????????
- ??????????????????
- ????? 3002 ???

## 3. ?? 3003

??? 3003 ?????

```bash
backup_dir="/opt/manim-v2-3003-backups/deploy_$(date +%Y%m%d_%H%M%S)"
mkdir -p "$backup_dir"
rsync -a --delete --exclude storage --exclude videos --exclude app/videos /opt/manim-v2-3003-snapshot/backend/ "$backup_dir/backend/"
rsync -a --delete /opt/manim-v2-3003-repro-3002-current/frontend/dist/ "$backup_dir/frontend-dist/"
cp /opt/manim-v2-3003-snapshot/backend/.env "$backup_dir/backend.env" 2>/dev/null || true
```

????? 3003 ???

```text
PORT=8003
CELERY_QUEUE=manim_v2_3003
DATABASE_URL=sqlite:////opt/manim/backend/manim.db
```

???

```bash
systemctl daemon-reload
systemctl restart manim-v2-3003-backend.service manim-v2-3003-worker.service
```

???

```bash
curl -s -o /dev/null -w '3003:%{http_code}\n' http://127.0.0.1:3003/
curl -s -o /dev/null -w '8003docs:%{http_code}\n' http://127.0.0.1:8003/docs
systemctl is-active manim-v2-3003-backend.service manim-v2-3003-worker.service
```

## 4. ?? 3003 ? 3002 ??

???????????????????????????

```bash
cd /opt/manim-v2
git switch -c repro/3002-current-YYYYMMDD
```

??????

```bash
python3 - <<'PY'
import sqlite3, json, pathlib
con = sqlite3.connect('/opt/manim/backend/manim.db')
con.row_factory = sqlite3.Row
rows = [dict(r) for r in con.execute('select * from templates order by id')]
out = pathlib.Path('docs/deployments/templates_3002_YYYYMMDD.json')
out.write_text(json.dumps(rows, ensure_ascii=False, indent=2), encoding='utf-8')
print('exported templates', len(rows), 'to', out)
PY
```

???????

```text
docs/deployments/3002-current-YYYYMMDD.md
```

?????????????

```bash
git add backend frontend/src docs/deployments deploy
# ??????????????????????? dist
git add -f frontend/dist
git reset -- frontend/tsconfig.tsbuildinfo || true
git commit -m "snapshot: current 3002 deployed state YYYY-MM-DD"
git push -u origin repro/3002-current-YYYYMMDD
```

## 5. ? 3003 ??? 3002

????? 3003 ?????

```bash
front_dist=$(awk '/^[[:space:]]*root[[:space:]]/ {gsub(/;/, "", $2); print $2; exit}' /etc/nginx/sites-enabled/manim-v2-3003.conf)
back_dir=$(systemctl show manim-v2-3003-backend.service -p WorkingDirectory --value)
echo "$front_dist"
echo "$back_dir"
```

?? 3002?

```bash
backup_dir="/opt/manim_backups/deploy_3003_to_3002_$(date +%Y%m%d_%H%M%S)"
mkdir -p "$backup_dir"
rsync -a --delete --exclude node_modules --exclude dist --exclude videos --exclude app/videos --exclude __pycache__ /opt/manim-v2/backend/ "$backup_dir/backend/"
rsync -a --delete --exclude node_modules --exclude dist /opt/manim-v2/frontend/ "$backup_dir/frontend/"
cp /opt/manim-v2/backend/.env "$backup_dir/backend.env" 2>/dev/null || true
```

????? 3002 ???

```bash
cp /opt/manim-v2/backend/.env /tmp/manim-v2-3002.env.deploy-preserve
systemctl stop manim-v2-worker.service manim-v2-backend.service
rsync -a --delete --exclude .env --exclude storage --exclude videos --exclude app/videos --exclude __pycache__ --exclude '*.pyc' "$back_dir/" /opt/manim-v2/backend/
cp /tmp/manim-v2-3002.env.deploy-preserve /opt/manim-v2/backend/.env
rsync -a --delete "$front_dist/" /opt/manim-v2/frontend/dist/
systemctl daemon-reload
systemctl start manim-v2-backend.service
systemctl start manim-v2-worker.service
```

3002 ???????

```text
PORT=8002 ? uvicorn --port 8002
CELERY_QUEUE=manim_v2
DATABASE_URL=sqlite:////opt/manim/backend/manim.db
```

## 6. ?? 3002

```bash
curl -k -s -L -o /tmp/check.out -w 'home:%{http_code}\n' https://www.lazymedia.cn/
curl -k -s -L -o /tmp/check.out -w 'login:%{http_code}\n' https://www.lazymedia.cn/login
curl -k -s -L -o /tmp/check.out -w 'creator:%{http_code}\n' https://www.lazymedia.cn/creator
systemctl is-active nginx manim-v2-backend.service manim-v2-worker.service
```

???????

```bash
for id in 26 53 57 67 72 77 78; do
  curl -s -o /dev/null -w "template_$id:%{http_code} %{content_type}\n" \
    "http://127.0.0.1:3002/api/videos/template_examples/template_${id}_preview.mp4"
done
```

????????

```bash
python3 - <<'PY'
import sqlite3
con=sqlite3.connect('/opt/manim/backend/manim.db')
cur=con.cursor()
for sql,label in [
 ('select count(*) from templates', 'total'),
 ('select count(*) from templates where is_active=1 and is_visible=1', 'active_visible'),
 ("select count(*) from templates where is_active=1 and is_visible=1 and example_video_url is not null and example_video_url != ''", 'with_preview'),
]:
    print(label, cur.execute(sql).fetchone()[0])
PY
```

## 7. ??

??????

1. ?????????????? commit?
2. ??????????
3. ??????????????????????

????????????????????

## 8. ????????

- ????? commit?
- ??????????
- ?????
- ???? URL?????????
- ??????????????????
