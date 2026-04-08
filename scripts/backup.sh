#!/bin/bash

DATE=$(date +%Y%m%d_%H%M%S)
BACKUP_DIR="/opt/backups"
mkdir -p $BACKUP_DIR

echo "📦 开始备份..."

# 备份 PostgreSQL
docker exec manim-postgres-prod pg_dump -U postgres manim_prod > $BACKUP_DIR/db_prod_$DATE.sql

# 备份视频文件
tar -czf $BACKUP_DIR/videos_prod_$DATE.tar.gz ./videos/prod/

# 清理旧备份（保留7天）
find $BACKUP_DIR -name "*.sql" -mtime +7 -delete
find $BACKUP_DIR -name "*.tar.gz" -mtime +7 -delete

echo "✅ 备份完成：$BACKUP_DIR"
