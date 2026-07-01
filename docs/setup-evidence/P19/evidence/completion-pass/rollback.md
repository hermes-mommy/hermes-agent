# P19 Completion Pass — Rollback

**Date:** 2026-06-27 16:09 WIB

---

## Instant Rollback (flag only, no restart)

```bash
# Heartbeat reads from db6
redis-cli -p 6380 -a <pw> -n 6 DEL feature:projects:enabled
# Consistency in db0
redis-cli -p 6380 -a <pw> -n 0 DEL feature:projects:enabled
```
Runtime re-reads flag next heartbeat cycle → P19 transparent, P20 byte-identical.

## File Rollback (restore pre-completion VPS files)

```bash
# Restore 4 files from backup
cp /tmp/p19_completion_backup/*.py /home/guinevere/code/guinevere/src/life_kernel/
cp /tmp/p19_completion_backup/*.py /home/guinevere/code/guinevere/src/core/
cp /tmp/p19_completion_backup/*.py /home/guinevere/code/guinevere/src/discord/
sudo systemctl restart guinevere-core.service
sudo systemctl restart guinevere-discord.service
```

Backup files: `/tmp/p19_completion_backup/` (journal.py, graph.py, main.py, _entrypoint.py).

## Full Rollback (restore to P19-012 schema-only state)

1. Flag rollback: `DEL feature:projects:enabled` (db0+db6)
2. Remove `LIFE_KERNEL_PROJECT_ID` from `.env.core`
3. Restore backup files + restart core + discord
4. Verify P20 healthy (brain, dashboard, hard_stop)

## Footer

| Field | Value |
|---|---|
| Rollback tested | No (not executed — destructive operation) |
| Rollback path | Instant flag DEL + file restore |