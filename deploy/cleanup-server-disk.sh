#!/usr/bin/env bash
set -euo pipefail

MANIM_BACKUPS_DIR="${MANIM_BACKUPS_DIR:-/opt/manim_backups}"
DEPLOY_TMP_DIR="${DEPLOY_TMP_DIR:-/opt/manim_backups/deploy_tmp}"
KEEP_BACKUP_DAYS="${KEEP_BACKUP_DAYS:-3}"
KEEP_DEPLOY_TMP_DAYS="${KEEP_DEPLOY_TMP_DAYS:-3}"
JOURNAL_VACUUM_TIME="${JOURNAL_VACUUM_TIME:-3d}"
JOURNAL_VACUUM_SIZE="${JOURNAL_VACUUM_SIZE:-300M}"

echo "[cleanup] start $(date '+%F %T')"

if [ -d "$DEPLOY_TMP_DIR" ]; then
  find "$DEPLOY_TMP_DIR" -type f -mtime +"$KEEP_DEPLOY_TMP_DAYS" -delete 2>/dev/null || true
fi

if [ -d "$MANIM_BACKUPS_DIR" ]; then
  find "$MANIM_BACKUPS_DIR" -maxdepth 1 -type f -name 'manim-v2*.tar.gz' -mtime +"$KEEP_BACKUP_DAYS" -delete 2>/dev/null || true
  find "$MANIM_BACKUPS_DIR" -maxdepth 1 -type f -name 'manim-v2_frontend_only_*.tar.gz' -mtime +"$KEEP_BACKUP_DAYS" -delete 2>/dev/null || true
  find "$MANIM_BACKUPS_DIR" -maxdepth 1 -type f -name 'backend_3003_env_before_*' -mtime +"$KEEP_BACKUP_DAYS" -delete 2>/dev/null || true
  find "$MANIM_BACKUPS_DIR" -maxdepth 1 -type f -name 'check_3003_*' -mtime +"$KEEP_BACKUP_DAYS" -delete 2>/dev/null || true
  find "$MANIM_BACKUPS_DIR" -maxdepth 1 -type f -name 'manim-v2.conf.*.bak' -mtime +"$KEEP_BACKUP_DAYS" -delete 2>/dev/null || true
  find "$MANIM_BACKUPS_DIR" -maxdepth 1 -type d -name 'deploy_tmp_3003_*' -mtime +"$KEEP_BACKUP_DAYS" -exec rm -rf {} + 2>/dev/null || true
  find "$MANIM_BACKUPS_DIR" -maxdepth 1 -type d -name 'manim-v2-3003-*' -mtime +"$KEEP_BACKUP_DAYS" -exec rm -rf {} + 2>/dev/null || true
fi

journalctl --vacuum-time="$JOURNAL_VACUUM_TIME" || true
journalctl --vacuum-size="$JOURNAL_VACUUM_SIZE" || true

rm -rf /root/.npm/_cacache/* 2>/dev/null || true
find /tmp -maxdepth 1 -type f -name 'tmp*.mp4' -delete 2>/dev/null || true

echo "[cleanup] done $(date '+%F %T')"
df -h /
