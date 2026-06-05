# Phase 6-7 Planning: Disaster Recovery & VPS Operational Documentation

**Status:** Draft  
**Version:** 1.0  
**Date:** 2026-06-05  
**Author:** Guinevere (Autonomous Agent)  
**Context:** ADR-035 Hermes Migration Preparation  
**Target Audience:** Faiz (Operator), Guinevere (Executor), Phase 7 Hardening Team  

---

## 1. Executive Summary

This document consolidates the operational topology, backup procedures, and disaster recovery (DR) scenarios for Project Guinevere in preparation for Phase 7 hardening (ADR-035 Hermes migration). The current infrastructure operates on a single 4C/16GB/120GB VPS (hostdata.id, Ubuntu 24.04) with strict resource limits, defense-in-depth security, and dual-repo encrypted backups (idcloudhost S3 primary, Cloudflare R2 secondary).

**Key Findings:**
- **Service Topology:** 8 systemd services + 8 Docker containers (monitoring stack). `guinevere-discord.service` is explicitly flagged for replacement by `hermes-gateway` in ADR-035.
- **Backup Integrity:** Dual-repo `restic` + `pg_dumpall` + `age` encryption. RPO < 5 minutes (WAL), RTO 4 hours (full stack).
- **Resource Constraints:** Strict `systemd` cgroups limit services to 512MB–2GB RAM and 100–200% CPU quota to prevent OOM on the 16GB host.

---

## 2. VPS Specifications & Capacity Planning

| Resource | Specification | Notes |
|---|---|---|
| **Provider** | hostdata.id (or equivalent) | Primary deployment target |
| **OS** | Ubuntu 24.04 LTS | CIS-hardened, non-root default |
| **CPU** | 4 Cores | Shared across systemd slices |
| **RAM** | 16 GB | Partitioned: 4GB Core, 4GB DB, 4GB Observability, 4GB OS/Buffer |
| **Disk** | 120 GB SSD | `vm.swappiness=10`, 8GB swap file configured |
| **Network** | Tailscale Mesh + Cloudflare Tunnel | Zero public ports; all internal traffic via `100.x.x.x` |

### Resource Allocation Baseline (systemd Slice: `guinevere.slice`)
- **guinevere-loops / mcp / scheduler**: `MemoryMax=2G`, `CPUQuota=200%`
- **guinevere-discord / surveillance**: `MemoryMax=1G` (or 768M), `CPUQuota=100%`
- **guinevere-obscura**: `MemoryMax=512M`, `CPUQuota=100%`
- **guinevere-shadow-monitor**: `MemoryMax=256M`, `CPUQuota=50%`

---

## 3. Service Topology Map

### 3.1 Systemd Services (Local Execution)
| Service Name | Type | Exec Command | Resource Limits | Dependencies | Hermes Migration Note |
|---|---|---|---|---|---|
| `guinevere-discord.service` | exec | `python -m src.discord.bot` | 1G RAM, 100% CPU | `guinevere-core` | **TO BE REPLACED** by `hermes-gateway` |
| `guinevere-loops.service` | exec | `python -m src.loops.manager` | 2G RAM, 200% CPU | `guinevere-core` | Retain or migrate to Hermes loop runner |
| `guinevere-mcp.service` | exec | `python -m src.mcp.manager` | 2G RAM, 200% CPU | `guinevere-core` | Evaluate Hermes MCP native integration |
| `guinevere-scheduler.service` | exec | `python -m src.loops.scheduler` | 2G RAM, 200% CPU | `guinevere-loops` | Retain for cron/ritual scheduling |
| `guinevere-surveillance.service`| exec | `python -m src.surveillance.consumer`| 768M RAM, 100% CPU | `guinevere-core`, `docker` | Retain for Android/Windows sync |
| `guinevere-obscura.service` | simple | `/usr/local/bin/obscura serve` | 512M RAM, 100% CPU | `network` | Retain for browser automation |
| `guinevere-shadow-monitor.service`| oneshot| `python -m src.discord.shadow_monitor`| 256M RAM, 50% CPU | `guinevere-discord` | Triggered by `guinevere-shadow-monitor.timer` (60s) |
| `guinevere-monitoring.service` | exec | `docker compose -f monitoring/compose.monitoring.yml up` | 1G RAM, 100% CPU | `docker` | Retain for observability |

### 3.2 Docker Compose Services
**File:** `monitoring/compose.monitoring.yml`  
**Network:** `guinevere-net` (external, bridge)  
**Port Binding:** All bound to `127.0.0.1` (Tailscale-only access).

| Service | Image | Port | Volume / Purpose |
|---|---|---|---|
| `prometheus` | `prom/prometheus:v3.3.0` | 9090 | `/home/guinevere/data/prometheus` (30d/15GB retention) |
| `grafana` | `grafana/grafana:11.5.0` | 3000 | `/home/guinevere/data/grafana` |
| `loki` | `grafana/loki:3.4.0` | 3100 | `/home/guinevere/data/loki` |
| `promtail` | `grafana/promtail:3.5.8` | N/A | Reads `/var/log/journal` (Note: v3.6.0+ drops journald) |
| `alertmanager`| `prom/alertmanager:v0.28.0`| 9093 | Routing to Discord/Gotify |
| `node-exporter`| `prom/node-exporter:v1.9.0`| 9100 | Host metrics + textfile collector |
| `postgres-exporter`| `prometheuscommunity/postgres-exporter:v0.17.1` | 9187 | DB metrics via `host.docker.internal:5433` |
| `redis-exporter` | `oliver006/redis_exporter:v1.67.0` | 9121 | Redis metrics via `host.docker.internal:6380` |

**Additional:** `docs/setup-evidence/P2/STEP-P2-020/docker-compose.yml` defines `gotify` (port 8081) for emergency push notifications.

---

## 4. Database Configuration

### 4.1 PostgreSQL (Self-Hosted, ADR-027)
- **Port:** 5433 (non-standard, documented in backup scripts) or 5432 (Docker default).
- **Connection Pooling:** PgBouncer configured between application and PostgreSQL.
- **Tuning (16GB RAM):** `shared_buffers=2GB`, `effective_cache_size=6GB`, `max_connections=200`, `wal_buffers=64MB`.
- **WAL Archiving:** `archive_mode=on`, `archive_timeout=900s` (forces segment every 15 min for RPO < 5 min).
- **Extensions:** `pgvector` (HNSW indexes), `timescaledb` (hypertables for episodes/events).

### 4.2 Redis (ADR-030 Canonical Assignments)
- **Port:** 6380 (or 6379 in some legacy configs; standardize to 6380 for Hermes).
- **Memory:** `maxmemory 1gb`, `maxmemory-policy allkeys-lru` (or `noeviction` for critical DBs).
- **Persistence:** `appendfsync everysec` (1-second RPO), `save 900 1`, `aof-use-rdb-preamble yes`.
- **Database Assignments:**
  - **DB0:** Rate limiting, persona state, consent grants (`noeviction`)
  - **DB1:** Memory recall cache (`allkeys-lru`)
  - **DB2:** Surveillance buffer, consent cache (`allkeys-lfu`)
  - **DB3:** Agent loop state, task metadata (`noeviction`)
  - **DB4:** Hermes session storage, Discord state (`volatile-lru`, 2hr TTL)
  - **DB5:** Cost tracking, `guinevere_safety` plugin state (`noeviction`)

---

## 5. Backup Procedures

### 5.1 Backup Architecture (ADR-025, ADR-032)
- **Primary Storage:** idcloudhost S3 (Indonesia region, low latency).
- **Secondary Storage:** Cloudflare R2 (Geo-redundant, zero egress fees).
- **Encryption:** `age` encryption applied *before* upload. Keys managed via SOPS.
- **Schedule:** Daily at 02:00 WIB (via `guinevere-backup.timer`), preceding the 03:00 WIB self-deploy window.

### 5.2 Backup Script Flow (`scripts/guinevere-backup.sh`)
1. **PostgreSQL Dump:** `pg_dumpall` (or `pg_dump -Fc`) → `gzip` compression → validate header.
2. **Primary Backup:** `sops exec-env` decrypts credentials → `restic backup` to idcloudhost S3 (tag: `primary`).
3. **Primary Retention:** `restic forget --prune --keep-daily 7 --keep-weekly 4 --keep-monthly 3`.
4. **Primary Verification:** `restic check --read-data-subset=5%`.
5. **Secondary Backup:** `restic backup` to Cloudflare R2 (tag: `secondary`).
6. **Secondary Retention:** `restic forget --prune --keep-daily 14 --keep-weekly 8 --keep-monthly 6`.
7. **Success Marker:** Writes ISO-8601 timestamp to `/var/log/guinevere/last-backup-success`.
8. **Cleanup:** Removes local plaintext dump file.

### 5.3 Monitoring Integration
- `monitoring/scripts/backup-metric-collector.sh` runs via cron every 5 minutes.
- Reads `/var/log/guinevere/last-backup-success` and writes `guinevere_backup_last_success_timestamp` to `/home/guinevere/guinevere/monitoring/node-exporter/textfile/backup.prom`.
- Prometheus alerts if timestamp is > 26 hours old (SEV2 alert).

---

## 6. Disaster Recovery Scenarios (RTO/RPO)

| Scenario | RPO | RTO | Recovery Method | Verification |
|---|---|---|---|---|
| **1. Full VPS Loss** | < 5 min (WAL) | 4 hours | Provision new VPS → install deps → restore `pg_dump` + WAL replay → restore `restic` configs → restart services. | Full stack health check (37-item checklist), Merkle chain hash continuity. |
| **2. PostgreSQL Data Corruption** | < 5 min (WAL) | 15 min | Stop services → `pg_restore` from latest valid daily dump → WAL replay to specific `recovery_target_time`. | `pg_amcheck`, row count validation, HNSW index rebuild (`CONCURRENTLY`). |
| **3. Redis Data Loss** | 1 sec (AOF) | 5 min | Stop Redis → restore `dump.rdb` + `appendonly.aof` from `restic` → restart → cache warming from PostgreSQL. | `DBSIZE` comparison, cache hit rate normalization within 30 min. |
| **4. SOPS/age Key Compromise** | N/A | 30 min | Isolate services → generate new age key → re-encrypt all `.env.sops` files → rotate all external API keys. | Audit trail review, successful decrypt of all secrets, service restart. |
| **5. guinevere-discord Service Failure** | N/A (stateless) | 10 min | `systemctl restart guinevere-discord` → verify gateway READY event. *(Post-Hermes: restart `hermes-gateway`)* | Discord bot responds to `/ping`, gateway connection stable. |
| **6. Surveillance Pipeline Backpressure** | < 5 min (DB2 buffer) | 10 min | Restart `guinevere-surveillance` → drain Redis DB2 buffer → verify ingestion lag < 1 min. | Prometheus metric `guinevere_surveillance_ingestion_lag_seconds` < 60. |
| **7. Disk Full / OOM Killer Event** | N/A | 15 min | Autonomous cleanup: log rotation, temp purge, old backup cleanup → restart killed service by priority. | `df -h` < 85%, `free -m` stable, service `active (running)`. |

---

## 7. Operational Runbook Outline

### 7.1 Daily Operations (Autonomous)
- **02:00 WIB:** `guinevere-backup.timer` triggers encrypted dual-repo backup.
- **03:00 WIB:** `guinevere-selfdeploy.timer` checks git, runs `uv sync`, `pytest`, and restarts services if healthy.
- **07:00 WIB:** Morning Ritual: Health check all 17+ services, review overnight alerts, verify backup success marker, check cost burn rate.
- **Continuous:** Loop Guardian (30s heartbeat), Prometheus scraping (15s), safe-word detection.

### 7.2 Weekly Operations (Every Monday)
- **08:00 WIB:** Week-in-review metrics compilation (SLO averages, SEV counts, cost burn).
- **Backlog Grooming:** Reassess task priority scores, identify blockers.
- **Dependency Review:** `uv pip audit`, `npm audit`, check for CVEs >= 7.0.

### 7.3 Monthly Operations (1st of Month)
- **06:00 WIB:** SLO Scorecard generation (`evidence/slo/YYYY-MM/scorecard.md`).
- **08:00 WIB:** Partial DR Drill (rotating scope: e.g., January = PostgreSQL full restore, February = Redis state reconstruction).
- **09:00 WIB:** Evidence audit (verify SHA-256 hashes, retention compliance).

### 7.4 Quarterly Operations
- **Full DR Drill:** Complete restore cycle on isolated environment or new VPS. Target duration: 4 hours.
- **Red-Team Exercise:** Simulate SEV0 scenarios (e.g., key compromise, persona drift).
- **Capacity Planning Review:** Analyze 3-month resource trends, project growth against 16GB RAM / 120GB disk limits.

---

## 8. Phase 7 Hardening Action Items (ADR-035)

1. **Deprecate `guinevere-discord.service`:** Ensure `hermes-gateway` systemd unit is created with equivalent or stricter resource limits (`MemoryMax=1G`, `CPUQuota=100%`) and security hardening (`ProtectSystem=strict`, `NoNewPrivileges=true`).
2. **Standardize Database Ports:** Resolve discrepancy between documentation (5432) and backup scripts (5433 for PostgreSQL, 6380 for Redis). Update all `systemd` `EnvironmentFile` and `docker-compose` references to match the Hermes configuration.
3. **Enhance Backup Verification:** Automate the weekly partial restore test. Currently, it is a manual/semi-automated step in the monthly runbook. Integrate a `restic restore` + `pg_restore --dry-run` into the `guinevere-backup.sh` script with a `DRY_RUN=1` flag for weekly execution.
4. **Redis DB Isolation for Hermes:** Confirm that Hermes session storage (DB4) and safety plugin state (DB5) are correctly isolated and that `guinevere_safety` plugin has `noeviction` policy enforced at the Redis config level for those specific databases (requires Redis 7.0+ `memory` per-DB limits or application-level guards).
5. **Update DR Plan Cross-References:** Ensure `43-DisasterRecoveryPlan_v1.0.md` explicitly references `hermes-gateway` instead of `guinevere-discord` in all recovery procedures and priority order lists.

---

## 9. Evidence & Artifacts

- **Backup Scripts:** `/scripts/guinevere-backup.sh`, `/scripts/guinevere-backup-docker.sh`
- **Systemd Units:** `/systemd/guinevere-*.service`, `/systemd/guinevere-*.timer`
- **Monitoring Config:** `/monitoring/compose.monitoring.yml`
- **Governance:** `adr/ADR-025-backup-disaster-recovery-strategy.md`, `adr/ADR-030-redis-db-assignments.md`, `adr/ADR-035-hermes-migration.md`
- **Operations:** `docs/40-operations/43-DisasterRecoveryPlan_v1.0.md`, `docs/40-operations/45-InternalOpsManual_v1.0.md`

---
*Generated by Guinevere for Phase 6-7 Planning. Strictly Private & Confidential.*
