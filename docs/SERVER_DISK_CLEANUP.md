# Server Disk Cleanup

## Scope

This cleanup only targets safe operational files:

- old backup tarballs under `/opt/manim_backups`
- old deploy temp files under `/opt/manim_backups/deploy_tmp`
- old debug helper files under `/opt/manim_backups`
- old systemd journal archives
- npm cache and throwaway temp mp4 files

It does **not** remove:

- `/opt/manim-v2`
- `/opt/manim-v2-3003-snapshot`
- shared template videos
- active databases

## Script

- `deploy/cleanup-server-disk.sh`

## Suggested Schedule

Run once per day at `03:20`.

Example cron entry:

```cron
20 3 * * * /opt/manim-v2/deploy/cleanup-server-disk.sh >> /var/log/manim-disk-cleanup.log 2>&1
```

## Retention

Defaults:

- backup tarballs: keep 3 days
- deploy temp files: keep 3 days
- journal: keep 3 days and cap to 300MB

Environment overrides are supported:

- `KEEP_BACKUP_DAYS`
- `KEEP_DEPLOY_TMP_DAYS`
- `JOURNAL_VACUUM_TIME`
- `JOURNAL_VACUUM_SIZE`
