#!/usr/bin/env bash
set -euo pipefail

DST="/opt/manim-v2-3003-snapshot"
BRANCH="feature/ai-video-module-on-3003"
TS="$(date +%Y%m%d_%H%M%S)"
BACKUP="/opt/manim_backups/manim-v2-3003-before-ai-video-${TS}.tar.gz"

echo "BACKUP=${BACKUP}"
test -d "${DST}/.git"

tar -czf "${BACKUP}" \
  --exclude='manim-v2-3003-snapshot/backend/uploads' \
  --exclude='manim-v2-3003-snapshot/backend/videos' \
  --exclude='manim-v2-3003-snapshot/backend/logs' \
  --exclude='manim-v2-3003-snapshot/storage/ai-video' \
  --exclude='manim-v2-3003-snapshot/.git' \
  -C /opt manim-v2-3003-snapshot

cd "${DST}"
git fetch origin "${BRANCH}" --depth=1
git checkout -B "${BRANCH}" FETCH_HEAD -f

echo "--- preserve 3003 env/runtime files ---"
git status --short --branch | head -80
git log -1 --format='%H%n%h%n%ci%n%D%n%s'

echo "--- setup ai video render service ---"
cd "${DST}/video-render-service/remotion-mind-video"
npm install --omit=dev
node -e "import('@remotion/renderer').then(async ({ensureBrowser}) => { await ensureBrowser({chromeMode: 'headless-shell', logLevel: 'info'}); })"
cp "${DST}/deploy/manim-v2-3003-ai-video-render.service" /etc/systemd/system/manim-v2-3003-ai-video-render.service
systemctl daemon-reload
systemctl enable manim-v2-3003-ai-video-render.service
systemctl restart manim-v2-3003-ai-video-render.service
sleep 4
curl -s --max-time 10 http://127.0.0.1:18787/api/health || true
echo

echo "--- restart 3003 only ---"
cd "${DST}"
systemctl restart manim-v2-3003-backend.service
systemctl restart manim-v2-3003-worker.service
systemctl reload nginx
sleep 8

echo "--- health ---"
curl -I -s --max-time 10 http://127.0.0.1:3003/ | head -20 || true
curl -s --max-time 10 http://127.0.0.1:8003/health || true
echo

echo "--- ai-video route smoke ---"
curl -I -s --max-time 10 http://127.0.0.1:3003/ai-video/dashboard | head -20 || true

echo "--- ports ---"
(ss -ltnp 2>/dev/null || netstat -ltnp 2>/dev/null) | grep -E ':(3002|3003|8002|8003)\b' || true

echo "--- service status ---"
systemctl is-active manim-v2-3003-ai-video-render.service manim-v2-3003-backend.service manim-v2-3003-worker.service
