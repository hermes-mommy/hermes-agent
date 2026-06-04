#!/bin/bash
# Guinevere Backup Monitoring — Prometheus Textfile Collector — P8-020
# Reads the backup success sentinel from /var/log/guinevere/last-backup-success
# and writes a Prometheus gauge metric for node-exporter textfile collection.
# Run via cron: */5 * * * * /home/guinevere/guinevere/monitoring/scripts/backup-metric-collector.sh
#
# ObsSpec §4.9: Backup metrics must include last_success timestamp for freshness checks.
# ADR-025: Daily backup is BLOCKING. Stale backup >26h triggers SEV2 alert.

set -euo pipefail

SENTINEL="/var/log/guinevere/last-backup-success"
OUTPUT="/home/guinevere/guinevere/monitoring/node-exporter/textfile/backup.prom"
TMP_OUTPUT="${OUTPUT}.tmp"

# Determine metric value: timestamp of sentinel or 0 if missing
VALUE=0
if [ -f "$SENTINEL" ]; then
    VALUE=$(stat -c %Y "$SENTINEL" 2>/dev/null || echo 0)
fi

# Write Prometheus textfile format
# # HELP and # TYPE comments are MANDATORY for textfile collector (otherwise metrics are silently ignored)
cat > "$TMP_OUTPUT" << METRICS
# HELP guinevere_backup_last_success_timestamp Unix timestamp of last successful backup (0 = never or missing)
# TYPE guinevere_backup_last_success_timestamp gauge
guinevere_backup_last_success_timestamp ${VALUE}
METRICS

# Atomic rename to avoid partial reads by node-exporter
mv "$TMP_OUTPUT" "$OUTPUT"