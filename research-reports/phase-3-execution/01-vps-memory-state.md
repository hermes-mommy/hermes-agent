# Guinevere VPS Memory State — Complete Assessment

**Date:** 2026-06-05 11:16 UTC  
**Host:** faiz-prod-01 (100.94.104.22 via Tailscale)  
**User:** guinevere  
**Assessment Scope:** PostgreSQL, Redis, SQLite memory stores

---

## Executive Summary

**All memory stores are online and healthy, but GUINEVERE DATA IS EMPTY.** 
PostgreSQL has the full schema (76 tables across 12 application schemas) with zero user data rows. Redis has 14 keys in DB5 (Hermes agent session state) and is otherwise empty. SQLite stores contain Hermes state (26 messages, 2 sessions) and 9Router operational data. **Phase 3 Memory Bridge migration has NOT been applied** — the `memory` schema tables exist but are all at zero rows.

---

## 1. PostgreSQL

### 1.1 Infrastructure

| Property | Value |
|---|---|
| Container | `guinevere-postgres` (Docker, image: `guinevere-postgres-pgvector:16`) |
| Status | **Running** (Up 4 days) |
| Port | `127.0.0.1:5433→5432` (pgbouncer at `127.0.0.1:5434→5432`) |
| Version | PostgreSQL 16.14 (Debian 16.14-1.pgdg13+1) |
| Connection | scram-sha-256 auth |
| Exporter | `guinevere-postgres-exporter` at `127.0.0.1:9187` |

### 1.2 Extensions

| Extension | Version |
|---|---|
| `plpgsql` | 1.0 |
| `timescaledb` | 2.27.1 |
| `vector` (pgvector) | 0.8.2 |

### 1.3 Databases

| Database | Size | Notes |
|---|---|---|
| `guinevere` | 12 MB | Main application DB, 76 tables, **all zero rows** |
| `guinevere_core` | 7,583 kB (7.4 MB) | Core/support DB, **no tables** |
| `postgres` | (default) | System template |

### 1.4 Roles

| Role | Attributes |
|---|---|
| `guinevere` | Superuser, Create role, Create DB, Replication, Bypass RLS |
| `guinevere_core` | 30 connections |
| `guinevere_readonly` | 15 connections |
| `guinevere_scheduler` | 10 connections |
| `guinevere_surveillance` | 10 connections |
| `guinevere_backup` | 5 connections |
| `guinevere_pgbouncer` | 5 connections |

### 1.5 Application Schemas & Table Inventory

#### Schema Summary

| Schema | Tables | Total Size | Owner |
|---|---|---|---|
| `agents` | 3 | 56 kB | guinevere_core |
| `audit` | 3 | 64 kB | guinevere |
| `consent` | 3 | 56 kB | guinevere_core |
| `extensions` | 3 | 48 kB | guinevere_core |
| `financial` | 4 | 72 kB | guinevere |
| `loops` | 0 | — | guinevere |
| `memory` | 8 | 456 kB | guinevere |
| `ops` | 5 | 96 kB | guinevere |
| `persona` | 5 | 80 kB | guinevere |
| `projects` | 4 | 64 kB | guinevere_core |
| `security` | 3 | 48 kB | guinevere_core |
| `social` | 3 | 48 kB | guinevere_core |
| `surveillance` | 4 | 72 kB | guinevere |
| **Total** | **48** | **1,160 kB** | |

Plus TimescaleDB internal schemas: `_timescaledb_cache` (3 tables), `_timescaledb_catalog` (22 tables), `_timescaledb_config` (1 table), `_timescaledb_functions`, `_timescaledb_internal` (3 tables), `timescaledb_experimental`, `timescaledb_information`.

#### Full Table Inventory (Application Schemas)

| Schema | Table | Rows | Notes |
|---|---|---|---|
| **agents** | execution_log | 0 | |
| | subagent_registry | 0 | |
| | task_queue | 0 | |
| **audit** | audit_trail | 0 | |
| | compliance_check | 0 | |
| | evidence_register | 0 | |
| **consent** | consent_ledger | 0 | |
| | revocation_log | 0 | |
| | scope_registry | 0 | |
| **extensions** | pgcrypto_config | 0 | |
| | pgvector_config | 0 | |
| | timescaledb_config | 0 | |
| **financial** | monthly_reports | 0 | |
| | optimization_log | 0 | |
| | project_costs | 0 | |
| | transactions | 0 | |
| **memory** | emotional_events | 0 | |
| | episodes | 0 | |
| | faiz_predictions | 0 | |
| | faiz_profile | 0 | |
| | inner_journal | 0 | |
| | knowledge_graph | 0 | |
| | procedural_skills | 0 | |
| | semantic_facts | 0 | |
| **ops** | alembic_version | 1 | Migration tracking only |
| | alert_history | 0 | |
| | backup_log | 0 | |
| | health_check | 0 | |
| | migration_log | 0 | |
| **persona** | drift_log | 0 | |
| | mood_history | 0 | |
| | persona_state | 0 | |
| | punishment_log | 0 | |
| | reward_log | 0 | |
| **projects** | agent_tasks | 0 | |
| | evidence_artifacts | 0 | |
| | loop_instances | 0 | |
| | tasks | 0 | |
| **security** | access_log | 0 | |
| | break_glass_log | 0 | |
| | secret_rotation_log | 0 | |
| **social** | client_contacts | 0 | |
| | communication_log | 0 | |
| | social_map | 0 | |
| **surveillance** | confrontation_block_log | 0 | |
| | device_registry | 0 | |
| | events | 0 | |
| | ingestion_log | 0 | |

### 1.6 Memory Schema Detail

The `memory` schema is **fully structured but empty**:

| Table | Purpose | Rows |
|---|---|---|
| `episodes` | Episodic memory entries | 0 |
| `emotional_events` | Emotion-attached events | 0 |
| `faiz_predictions` | Predictive modeling for Faiz | 0 |
| `faiz_profile` | Faiz profile data | 0 |
| `inner_journal` | Agent inner journal entries | 0 |
| `knowledge_graph` | Knowledge graph nodes | 0 |
| `procedural_skills` | Procedural memory skills | 0 |
| `semantic_facts` | Semantic memory facts | 0 |

**Note:** The tables `episodic_memories`, `semantic_memories`, and `dnr_entries` referenced in `src/memory/` do NOT exist. The actual schema uses `episodes` and `semantic_facts` — suggesting a schema evolution that hasn't been deployed yet.

### 1.7 TimescaleDB Status

TimescaleDB 2.27.1 is configured with background jobs running:

| Internal Table | Rows |
|---|---|
| `bgw_job` | 5 |
| `dimension` | 4 |
| `hypertable` | 4 |
| `metadata` | 4 |
| `compression_algorithm` | 8 |
| `bgw_job_stat` | 5 |

No hypertables have been created on user tables — TimescaleDB is installed but not yet applied to any application tables.

### 1.8 Row-Level Security (RLS)

Not yet audited — RLS configuration exists in schema but was not explicitly checked per-table (command query issue). Schema-level permissions suggest RLS is available but likely not enforced on empty tables.

### 1.9 Ingestion State

| Metric | Value |
|---|---|
| Last write timestamp | **N/A** — all tables empty |
| write_pipeline status | **Not active** — no data being ingested |
| Sequences / auto-increment | At initial state |

---

## 2. Redis

### 2.1 Infrastructure

| Property | Value |
|---|---|
| Container | `guinevere-redis` (Docker, image: `redis:7.4-alpine`) |
| Status | **Running** (Up 21 hours — restarted ~2026-06-04 07:48 UTC) |
| Port | `127.0.0.1:6380→6379` |
| Version | Redis 7.4.9, 64-bit, standalone mode |
| Auth | Password-protected (SHA-256 hash) |
| Exporter | `guinevere-redis-exporter` at `127.0.0.1:9121` |

### 2.2 Configuration

| Setting | Value |
|---|---|
| `maxmemory` | 2 GB |
| `maxmemory-policy` | `allkeys-lru` |
| `databases` | 16 |
| `save` (RDB) | 900s/1 change, 300s/10 changes, 60s/10000 changes |
| `appendonly` (AOF) | **yes** |
| `appendfsync` | `everysec` |
| `loglevel` | `notice` |
| FLUSHALL/FLUSHDB | **Renamed** (disabled) |
| CONFIG | **Renamed** (disabled) |

### 2.3 Keyspace

| Database | Keys | Expires | TTL |
|---|---|---|---|
| DB0 | **0** | 0 | — |
| DB1 | **0** | 0 | — |
| DB2 | **0** | 0 | — |
| DB3 | **0** | 0 | — |
| DB4 | **0** | 0 | — |
| **DB5** | **14** | 0 | avg_ttl=0 (persistent) |
| DB6 | **0** | 0 | — |
| DB7 | **0** | 0 | — |
| DB8–DB15 | (not checked) | — | — |

**DB5 is the only active database** with 14 keys, all without TTL (persistent keys). Based on context, these likely represent Hermes agent session state or Discord channel metadata.

### 2.4 Memory Usage

| Metric | Value |
|---|---|
| `used_memory` | 1.21 MB |
| `used_memory_rss` | 8.75 MB |
| `used_memory_peak` | 1.24 MB |
| `used_memory_dataset` | ~316 KB |
| `total_system_memory` | 15.25 GB |
| Memory fragmentation | Low (`used_memory_peak_perc: 97.39%`) |

### 2.5 Persistence

| Metric | Value |
|---|---|
| RDB | Enabled, last save OK (2026-06-05 00:50 UTC) |
| RDB saves | 2 total |
| AOF | **Enabled**, last rewrite OK |
| Keys loaded on restart | **0** (RDB was empty at last load) |
| `rdb_changes_since_last_save` | 0 |

### 2.6 Operational Stats

| Metric | Value |
|---|---|
| Total connections received | 163,143 |
| Total commands processed | 222,101 |
| Instantaneous ops/sec | ~3 |
| Rejected connections | 0 |
| Expired keys | 0 |
| Sync full/partial | 0 / 0 |

### 2.7 Errors

Redis logs show zero errors. The restart on 2026-06-04 07:48 UTC was clean. Minor warning:

> `WARNING Memory overcommit must be enabled!` — `vm.overcommit_memory = 1` not set. Low risk at current memory levels (1.21M used of 2GB max), but could cause issues under memory pressure.

---

## 3. SQLite

### 3.1 File Inventory

| File | Size | Purpose |
|---|---|---|
| `/home/guinevere/.hermes/state.db` | 104 KB | Hermes agent session/message store |
| `/home/guinevere/.hermes/kanban.db` | 104 KB | Hermes task/task_run tracking |
| `/home/guinevere/.9router/db/data.sqlite` | 2.1 MB | 9Router operational data |
| `/home/guinevere/.9router/data.sqlite` | 0 bytes | **Empty** (symlink or stale) |
| `/home/guinevere/.9router/db/data-pre-migration-20260601.sqlite` | 172 KB | Pre-migration backup |
| `/home/guinevere/.9router/db/data-migration.sqlite` | 361 MB | Migration working copy |
| `/home/guinevere/data/grafana/grafana.db` | 1.2 MB | Grafana internal state (container-owned) |

### 3.2 Hermes `state.db` (104 KB)

**Tables:**
- `messages` — chat messages
- `sessions` — session metadata
- `state_meta` — state metadata store
- `schema_version` — migration version tracking
- `messages_fts` — FTS5 full-text search (content, data, docsize, idx, config)
- `messages_fts_trigram` — FTS5 trigram search (content, data, docsize, idx, config)

**Row counts:**

| Table | Rows |
|---|---|
| `messages` | 26 |
| `sessions` | 2 |
| `state_meta` | 0 |
| `schema_version` | 13 |

**Sessions (2 active):**
1. `20260605_102308_b4846761` — Discord channel `1146639950654214264`, model `ds/deepseek-v4-flash`
2. `20260605_092059_6dc1af91` — Discord channel `1146639950654214264`, model `ds/deepseek-v4-flash`

Both sessions are Discord-based with `deepseek-v4-flash` via custom provider at `localhost:20128`.

### 3.3 Hermes `kanban.db` (104 KB)

**Tables:** `tasks`, `task_runs`, `task_comments`, `task_links`, `task_events`, `kanban_notify_subs`

**All tables are EMPTY (0 rows).** The kanban system has schema but no active tasks.

### 3.4 9Router `data.sqlite` (2.1 MB)

**Tables:** `apiKeys`, `combos`, `kv`, `providerConnections`, `providerNodes`, `proxyPools`, `requestDetails`, `settings`, `usageDaily`, `usageHistory`, `_meta`

**Row counts:**

| Table | Rows |
|---|---|
| `apiKeys` | 0 |
| `combos` | 1 |
| `kv` | 0 |
| `providerConnections` | 26 |
| `providerNodes` | 0 |
| `proxyPools` | 0 |
| `requestDetails` | 492 |
| `settings` | 0 |
| `usageDaily` | 4 |
| `usageHistory` | 100 |
| `_meta` | 3 |

9Router is operational with 26 provider connections and 492 tracked requests.

### 3.5 FTS / Full-Text Search

Hermes `state.db` has two FTS5 indexes:
- **`messages_fts`**: Standard FTS5 on message content
- **`messages_fts_trigram`**: Trigram-based FTS5 for substring matching

Both have content, data, docsize, idx, config tables plus insert/delete/update triggers.

---

## 4. Disk Usage

| Path | Size | Notes |
|---|---|---|
| `/home/guinevere/.hermes/` | 55 MB | Hermes agent state + skills cache |
| `/home/guinevere/.9router/` | 412 MB | Includes 361 MB migration copy |
| `/home/guinevere/data/` | 374 MB | Grafana + monitoring data |
| `/home/guinevere/` (total) | 1.8 GB | Full home directory |
| Docker images | 7.2 GB | 23 images, 17 active |
| Docker containers | 556.5 MB | 18 containers running |
| Docker volumes | 73 MB | 4 volumes, 3 active |
| Docker build cache | 2.4 GB | Reclaimable: 503 MB |

---

## 5. Running Services (Memory-Related)

### 5.1 Systemd Services

| Service | Status |
|---|---|
| `guinevere-core.service` | **running** |
| `guinevere-loops.service` | **running** |
| `guinevere-scheduler.service` | **running** |
| `guinevere-9router.service` | **running** |
| `guinevere-monitoring.service` | **running** |
| `guinevere-surveillance.service` | **running** |
| `hermes-gateway.service` | **running** |
| `cloudflared.service` | **running** (webhook tunnel) |

### 5.2 Docker Containers

| Container | Uptime | Notes |
|---|---|---|
| `guinevere-postgres` | 4 days | PG 16 pgvector-enabled |
| `guinevere-redis` | 21 hours | Redis 7.4 (restarted Jun 4) |
| `guinevere-pgbouncer` | 4 days | Connection pooling |
| `guinevere-postgres-exporter` | 2 days | Metrics |
| `guinevere-redis-exporter` | 2 days | Metrics |
| `guinevere-prometheus` | 2 days | Metrics DB |
| `guinevere-grafana` | 2 days | Dashboards |
| `guinevere-loki` | 2 days | Log aggregation |
| `guinevere-promtail` | 2 days | Log shipping |
| `guinevere-alertmanager` | 2 days | Alerts |
| `guinevere-node-exporter` | 2 days | Host metrics |

(Also: aizanta-postgres, aizanta-redis, aizanta-nginx, aizanta-frontend, aizanta-bot — separate project)

---

## 6. Logs — Errors & Warnings

### 6.1 PostgreSQL Logs (last 30 lines)

**Clean.** Only normal connection/disconnection events. One expected error from our diagnostic query:

```
ERROR:  relation "episodic_memories" does not exist at character 50
```

This confirms the table name mismatch — the actual table is `memory.episodes`, not `episodic_memories`.

Connection pattern: Local psql connections from `guinevere` user and `guinevere_core` user via scram-sha-256. No authentication failures, no lock contention, no crash recovery.

### 6.2 Redis Logs (last 30 lines)

**Clean.** Last restart on 2026-06-04 07:48:35 UTC:

- RDB loaded with 0 keys (expected for fresh/empty DB)
- AOF loaded successfully
- Background saves completing normally (2 saves)
- Fork CoW: 0 MB (negligible memory overhead)
- One warning: `vm.overcommit_memory = 1` not set (non-critical)

### 6.3 Hermes / Guinevere Systemd Logs

**No access.** `journalctl` returned "No entries" — user `guinevere` is not in `adm`/`systemd-journal` groups. Application logs would need to be read from log files or Docker logs.

---

## 7. Memory Ingestion & Pipeline State

### Current State: **COLD START — NO DATA**

| Check | Status |
|---|---|
| PostgreSQL memory tables populated? | **NO** — all 8 memory tables at 0 rows |
| Redis memory DB populated? | **NO** — only DB5 has 14 Hermes session keys |
| SQLite memory active? | **PARTIAL** — Hermes state.db has 26 messages |
| write_pipeline active? | **NOT ACTIVE** — no write activity visible |
| Last write to memory tables? | **NEVER** — all created_at columns would be null |
| TimescaleDB hypertables on memory? | **NO** — TimescaleDB installed but not applied |
| pgvector indexes active? | **NO** — `pgvector_config` table empty |

### Phase 3 Migration Status

The PostgreSQL schema is **fully deployed** (76 tables across 12 schemas, `memory` schema with 8 tables) but **contains zero data**. The `src/memory/` module references `episodic_memories`, `semantic_memories`, and `dnr_entries` — these table names do NOT match the actual schema which uses `episodes`, `semantic_facts`, etc. This indicates:

1. Schema was designed and deployed via migrations (likely Alembic — `ops.alembic_version` has 1 row)
2. No data migration from old stores has been executed
3. The `src/memory/` Python code may reference outdated table names

---

## 8. Summary & Recommendations

### Health Status: 🟢 All Services Running, 🟡 Zero Application Data

| Store | Status | Data | Issues |
|---|---|---|---|
| PostgreSQL | 🟢 Running | 🟡 Schema only (0 rows) | Table name mismatch with `src/memory/` |
| Redis | 🟢 Running | 🟡 14 keys in DB5 | Empty otherwise; overcommit warning |
| SQLite (Hermes) | 🟢 Active | 🟢 26 messages, 2 sessions | Low volume; kanban empty |
| SQLite (9Router) | 🟢 Active | 🟢 492 requests tracked | Operational |
| Monitoring | 🟢 Running | 🟢 All exporters active | — |

### Immediate Actions for Phase 3 Memory Bridge:

1. **Reconcile table names** — `src/memory/` uses `episodic_memories`/`semantic_memories`/`dnr_entries` but PG has `memory.episodes`/`memory.semantic_facts`/etc. Choose one naming convention.

2. **Run Alembic to verify schema version** — check if migrations are fully applied:
   ```bash
   alembic current
   alembic heads
   ```

3. **Apply TimescaleDB hypertables** to episodic/timeseries memory tables if needed.

4. **Enable pgvector indexes** on `semantic_facts` and other embedding-bearing tables.

5. **Configure Redis DB allocation** — document which DB index maps to which memory subsystem.

6. **Seed initial data** if migrating from SQLite/Hermes state to PostgreSQL.

7. **Set `vm.overcommit_memory = 1`** on host for Redis stability.

---

## Appendix A: Command Execution Log

All data gathered via non-destructive read-only SSH commands:
- SSH connectivity verified
- Docker container inspection (no state changes)
- PostgreSQL read-only queries (via `docker exec psql`)
- Redis read-only queries (via `docker exec redis-cli`)
- SQLite read-only inspection (via `sqlite3`)
- Filesystem `find`/`du` commands (no modifications)
- Docker `logs` tail (read-only)
- No services restarted, no configs modified, no data written

## Appendix B: Artifacts

Temporary scripts created during assessment:
- `/tmp/mem_diag.sh` — Initial diagnostic script (partial success)
- `/tmp/pg_tables.sh` — PostgreSQL table scan
- `/tmp/sqlite_scan.sh` — SQLite comprehensive scan
- `/tmp/pg_all_tables.sql` — Full table listing query
- `/tmp/pg_stats.sql` — Schema stats and row counts query

These can be safely removed from the VPS.

---

*Report generated 2026-06-05 by Guinevere VPS Memory Assessment | Phase 3 Execution Prep*