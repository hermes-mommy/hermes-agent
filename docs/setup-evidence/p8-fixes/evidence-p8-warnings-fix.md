# P8 Warnings Fix — Evidence 2026-06-09

## W-01: node_exporter textfile collector ✅ FIXED

| Issue | Fix |
|---|---|
| Script path wrong | `backup-metric-collector.sh` path fixed from `/home/guinevere/guinevere/...` to `/home/guinevere/code/guinevere/...` |
| Metric name mismatch | `backup_status.prom` updated from `guinevere_backup_last_success_timestamp_seconds` to `guinevere_backup_last_success_timestamp` |
| Verification | `curl localhost:9100/metrics | grep guinevere_backup` → metric visible ✅ |

## W-02: Alertmanager webhook endpoint ✅ CODE WRITTEN (pending restart)

| Issue | Fix |
|---|---|
| All alertmanager receivers pointed to non-existent endpoint | Created `POST /internal/alertmanager/webhook` in `src/core/api/routes.py` |
| Endpoint | Parses alertmanager JSON, builds severity-colored Discord embeds, forwards via REST API |
| Router registered | `internal_router` added to `src/core/main.py` |
| **Pending** | Service restart needed: `sudo systemctl restart guinevere-core` |

## W-03: Backup sentinel stale ✅ FIXED

| Issue | Fix |
|---|---|
| rclone binary was broken symlink | Installed rclone v1.69.1 at `~/.hermes/bin/rclone` |
| Backup failed at 02:00 | Manual backup ran successfully, snapshot `3d257ca2` in S3 |
| Prometheus metric stale | Updated `backup_status.prom` with fresh timestamp |
| Hermes cron job | `guinevere-daily-backup` active, next run: tomorrow 02:00 WIB |

## Files Modified

- `monitoring/scripts/backup-metric-collector.sh` — path fix
- `monitoring/node-exporter/textfile/backup_status.prom` — metric name alignment
- `src/core/api/routes.py` — alertmanager webhook endpoint (+137 lines)
- `src/core/main.py` — internal_router registration
- `/home/guinevere/.hermes/bin/rclone` — replaced broken symlink
