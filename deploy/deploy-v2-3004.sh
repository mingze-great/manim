#!/bin/bash
set -euo pipefail

APP_ROOT="${APP_ROOT:-/opt/manim-v2-3004-snapshot}"
BRANCH="${BRANCH:-codex/3004-partner-stickman-platform-20260724}"
REMOTE="${REMOTE:-origin}"
BACKEND_SERVICE="${BACKEND_SERVICE:-manim-v2-3004-backend.service}"
WORKER_SERVICE="${WORKER_SERVICE:-manim-v2-3004-worker.service}"
RENDER_SERVICE="${RENDER_SERVICE:-manim-v2-3004-ai-video-render.service}"
NGINX_CONF_SRC="${NGINX_CONF_SRC:-$APP_ROOT/deploy/manim-v2-3004.conf}"
NGINX_CONF_DST="${NGINX_CONF_DST:-/etc/nginx/sites-available/manim-v2-3004.conf}"
BACKEND_ENV_SRC="${BACKEND_ENV_SRC:-$APP_ROOT/deploy/env.backend.3004.example}"
FRONTEND_ENV_SRC="${FRONTEND_ENV_SRC:-$APP_ROOT/deploy/env.frontend.3004.example}"
PYTHON_BIN="${PYTHON_BIN:-/root/miniconda3/envs/manim311/bin/python3.11}"
NPM_BIN="${NPM_BIN:-$(command -v npm || true)}"
BACKEND_ENV_BACKUP="/tmp/manim-v2-3004-backend.env.bak"
FRONTEND_ENV_BACKUP="/tmp/manim-v2-3004-frontend.env.bak"

echo "==> Deploying v2 3004 from git"
echo "APP_ROOT=$APP_ROOT"
echo "BRANCH=$BRANCH"

if [ ! -d "$APP_ROOT/.git" ]; then
  git clone --branch "$BRANCH" --single-branch https://github.com/mingze-great/manim.git "$APP_ROOT"
fi

if [ -f "$APP_ROOT/backend/.env" ]; then
  cp "$APP_ROOT/backend/.env" "$BACKEND_ENV_BACKUP"
fi

if [ -f "$APP_ROOT/frontend/.env.production.local" ]; then
  cp "$APP_ROOT/frontend/.env.production.local" "$FRONTEND_ENV_BACKUP"
fi

cd "$APP_ROOT"
git fetch "$REMOTE" "$BRANCH"
git checkout "$BRANCH"
git reset --hard "$REMOTE/$BRANCH"
git clean -fd

if [ -f "$BACKEND_ENV_BACKUP" ]; then
  cp "$BACKEND_ENV_BACKUP" "$APP_ROOT/backend/.env"
elif [ -f "$BACKEND_ENV_SRC" ] && [ ! -f "$APP_ROOT/backend/.env" ]; then
  cp "$BACKEND_ENV_SRC" "$APP_ROOT/backend/.env"
fi

if [ -f "$FRONTEND_ENV_BACKUP" ]; then
  cp "$FRONTEND_ENV_BACKUP" "$APP_ROOT/frontend/.env.production.local"
elif [ -f "$FRONTEND_ENV_SRC" ]; then
  cp "$FRONTEND_ENV_SRC" "$APP_ROOT/frontend/.env.production.local"
fi

if [ -z "$NPM_BIN" ]; then
  echo "npm not found. Install Node.js or set NPM_BIN before deploy."
  exit 1
fi

cd "$APP_ROOT/frontend"
"$NPM_BIN" ci
NODE_OPTIONS=--max-old-space-size=4096 "$NPM_BIN" run build

cd "$APP_ROOT/video-render-service/remotion-mind-video"
"$NPM_BIN" ci

cd "$APP_ROOT"
cp "$NGINX_CONF_SRC" "$NGINX_CONF_DST"
ln -sf "$NGINX_CONF_DST" /etc/nginx/sites-enabled/manim-v2-3004.conf

cp "$APP_ROOT/deploy/manim-v2-3004-backend.service" "/etc/systemd/system/$BACKEND_SERVICE"
cp "$APP_ROOT/deploy/manim-v2-3004-worker.service" "/etc/systemd/system/$WORKER_SERVICE"
cp "$APP_ROOT/deploy/manim-v2-3004-ai-video-render.service" "/etc/systemd/system/$RENDER_SERVICE"

systemctl stop "$BACKEND_SERVICE" 2>/dev/null || true
systemctl stop "$WORKER_SERVICE" 2>/dev/null || true
systemctl stop "$RENDER_SERVICE" 2>/dev/null || true
systemctl reset-failed "$BACKEND_SERVICE" 2>/dev/null || true
systemctl reset-failed "$WORKER_SERVICE" 2>/dev/null || true
systemctl reset-failed "$RENDER_SERVICE" 2>/dev/null || true

systemctl daemon-reload
systemctl enable "$BACKEND_SERVICE" "$WORKER_SERVICE" "$RENDER_SERVICE" || true
systemctl restart "$RENDER_SERVICE"
systemctl restart "$BACKEND_SERVICE"
systemctl restart "$WORKER_SERVICE"

nginx -t
systemctl reload nginx

sleep 5
curl -fsS http://127.0.0.1:8004/health
curl -I -fsS http://127.0.0.1:3004/ >/dev/null
systemctl is-active "$BACKEND_SERVICE" >/dev/null
systemctl is-active "$WORKER_SERVICE" >/dev/null
systemctl is-active "$RENDER_SERVICE" >/dev/null

echo "==> Deploy complete"
