# P19-012 Backup Evidence

**Date:** 2026-06-26 21:57 WIB
**Author:** Guinevere (parent)
**Phase:** 3 — Backup Gate

---

## 1. Backup Details

| Field | Value |
|---|---|
| Database | `guinevere` (corrected from `guinevere_core`) |
| Host | localhost:5433 |
| User | guinevere_core |
| Format | pg_dump custom format (-F c) |
| Excluded schemas | health, _timescaledb_internal, _timescaledb_cache, _timescaledb_functions, _timescaledb_config, timescaledb_experimental |
| Backup path | `/tmp/p19_backup_20260626_2145.dump` |
| Size | 1.2 GB |
| Exit code | 0 |

## 2. Restore Verification

- `pg_restore -l` successfully listed archive contents
- Warning about circular FK on `continuous_agg` (TimescaleDB internal — expected, harmless for our restore)
- All 49+ database objects captured

## 3. Rollback Path

1. If rollback needed: `pg_restore -d guinevere -h localhost -p 5433 -U guinevere_core -c /tmp/p19_backup_20260626_2145.dump`
2. The `-c` flag drops objects before recreating (clean restore)
3. Warning: full restore would overwrite P20 runtime data since backup time. Use `--table` filtering for surgical restores.

## 4. Evidence

- Backup file exists: ✅
- Backup is restorable (pg_restore -l works): ✅
- No secrets in backup path: ✅
- Pre-backup P20 health: hard_stop=False, brain active, 0 errors

## 5. Footer

| Field | Value |
|---|---|
| Backup status | SUCCESS |
| Next step | Phase 4: Surgical migration |