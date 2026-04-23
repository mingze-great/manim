#!/bin/bash
set -euo pipefail

APP_ROOT="${APP_ROOT:-/opt/manim-v2}"
BRANCH="${BRANCH:-feature/chat-style-and-reference-code}"
REMOTE="${REMOTE:-origin}"
BACKEND_SERVICE="${BACKEND_SERVICE:-manim-v2-backend.service}"
WORKER_SERVICE="${WORKER_SERVICE:-manim-v2-worker.service}"
NGINX_CONF_SRC="${NGINX_CONF_SRC:-$APP_ROOT/manim-v2.conf}"
NGINX_CONF_DST="${NGINX_CONF_DST:-/etc/nginx/sites-available/manim-v2.conf}"

echo "==> Deploying v2 from git"
echo "APP_ROOT=$APP_ROOT"
echo "BRANCH=$BRANCH"

cd "$APP_ROOT"

if [ -n "$(git status --porcelain)" ]; then
  echo "Worktree is dirty. Please commit/stash server-local changes before deploy."
  git status --short
  exit 1
fi

git fetch "$REMOTE" "$BRANCH"
git checkout "$BRANCH"
git pull --ff-only "$REMOTE" "$BRANCH"

cd "$APP_ROOT/frontend"
npm ci
npm run build

if [ -f "$NGINX_CONF_SRC" ]; then
  cp "$NGINX_CONF_SRC" "$NGINX_CONF_DST"
fi

systemctl restart "$BACKEND_SERVICE"
systemctl restart "$WORKER_SERVICE"
nginx -t
systemctl reload nginx

sleep 5
curl -fsS http://127.0.0.1:8002/health

echo "==> Deploy complete"
