# Pre-Implementation Context Report — P0-014 (PostgreSQL 16 Setup)

**Date:** 2026-05-31
**Auditor:** Guinevere
**Source Task:** STEP-P0-014
**File:** audit-reports/P0/STEP-P0-014/internal-context-report.md

---

## 1. Scope Definition

### Step Identity
- **Step ID:** P0-014
- **Type:** Database
- **Status:** Not Started
- **Risk:** Medium
- **Estimated Time:** 3 hours
- **Cost Impact:** $0/month (self-hosted)
- **Phase:** P0 Infrastructure Foundation (step 14 of 29)

### Goal (from StepPrompts.md line 1450)
Install and configure PostgreSQL 16 as the primary database for Guinevere.

### Configuration Parameters (guinevere.conf)
| Parameter | Value | Notes |
|---|---|---|
| listen_addresses | localhost | No remote binds |
| port | **5433** | Offset from Aizanta (5432) |
| max_connections | 100 | Max concurrent connections |
| shared_buffers | **1GB** | ~12.5% of 8GB cgroup limit |
| effective_cache_size | **3GB** | ~37.5% of 8GB cgroup |
| work_mem | 16MB | Per-operation sort memory |
| maintenance_work_mem | 256MB | VACUUM, index builds |
| wal_level | replica | WAL archiving capable |
| max_wal_size/min_wal_size | 2GB / 512MB | WAL limits |
| checkpoint_completion_target | 0.9 | Spread checkpoints |
| random_page_cost | 1.1 | SSD-optimized |
| effective_io_concurrency | 200 | SSD-optimized |
| log_min_duration_statement | 1000ms | Slow query log |
| log_checkpoints | on | Audit trail |
| log_connections / log_disconnections | on | Connection audit |
| log_lock_waits | on | Contention detection |
| log_temp_files | 0 | Log all temp files |
| timezone | Asia/Jakarta | WIB |

### CRITICAL SCOPE AMBIGUITY: Docker vs systemd
The StepPrompts P0-014 uses **apt + systemd** (apt install -y postgresql-16, systemctl restart postgresql). However:
- P0-010 created `guinevere-net` Docker network (172.28.0.0/16) for Guinevere containers
- Deployment Guide (docs/40-operations/44-DeploymentGuide_v1.0.md) uses Docker for PostgreSQL
- User context explicitly says "Docker container on guinevere-net, port 5433, data at /home/guinevere/data/postgres/"
- Research reports discuss both approaches

**Must be resolved before execution.**

---

## 2. Dependency Graph

### Upstream (MUST be complete)
| Step | Dependency | Status | Risk if Missing |
|---|---|---|---|
| P0-003 | Directory structure | COMPLETE | PG data dir target missing |
| P0-009 | cgroup limits (8GB RAM, 2 CPU) | COMPLETE | PG could exceed resource limits |
| P0-010 | Docker network guinevere-net | COMPLETE | Container has no network (Docker path) |
| P0-000 | VPS audit | COMPLETE | Port conflict with Aizanta |

### Downstream (BLOCKED by P0-014)
| Step | What It Needs |
|---|---|
| P0-015 pgvector 0.7.0 | Running PG16 on guinevere database |
| P0-016 TimescaleDB 2.15 | Running PG16 on guinevere database |
| P0-017 PG users creation | Running PG on guinevere database |
| P0-018 PG hardening (pg_hba.conf) | PG installed, ports configured |
| P0-019 PgBouncer pooling | PG running on custom port |
| P3-001 Alembic migrations | 47 tables, pgvector + TimescaleDB |
| P7-007 TimescaleDB ingestion | TimescaleDB extension active |

---

## 3. Definition of Done

### From StepPrompts Verification (lines 1517-1524)
- PG 16 running: systemctl status postgresql shows active
- Version: psql --version shows 16.x
- Database: sudo -u postgres psql -l lists guinevere
- Config: SHOW shared_buffers returns 1GB
- Timezone: SHOW timezone returns Asia/Jakarta
- Localhost: SHOW listen_addresses returns localhost
- Port isolation: ss -tlnp | grep 5433 shows postgres on 5433
- Port 5432: NOT guinevere PG (Aizanta only)
- Evidence files in docs/setup-evidence/P0/STEP-P0-014/
- Aizanta: systemctl status aizanta-* all running

### From CHECKLIST.md (line 113)
- systemctl status postgresql active
- sudo -u postgres psql -c 'SELECT version()' shows PG 16.x

### Extended DoD (from AGENTS.md)
- Diagnostics clean on config files
- Auditor gate: independent report PASS
- Boundary: no Aizanta impact, no consent/safety violation

---

## 4. ADR References & Binding Decisions

| ADR | Title | Relevance |
|---|---|---|
| ADR-014 | VPS & Container Architecture | Single VPS, user isolation, cgroup limits |
| ADR-027 | Self-Hosted PostgreSQL | PG16 on VPS, pgvector + TimescaleDB, PgBouncer |
| ADR-031 | Database Naming Convention | Database name = guinevere (not guinevere_db) |
| ADR-009 | Memory Recall & Semantic Search | pgvector required, HNSW index mandatory |
| ADR-018 | Security Architecture | Localhost-only, scram-sha-256, connection limits |
| ADR-007 | Memory Storage Backend | PostgreSQL primary, no SQLite |

### Port Assignments (binding per StepPrompts)
| Service | Aizanta | Guinevere |
|---|---|---|
| PostgreSQL | 5432 | **5433** |
| PgBouncer | 5433 | **5434** |
| Redis | 6379 | **6380** |

---

## 5. Acceptance Criteria References

| AC ID | Description | P0-014 Relevance |
|---|---|---|
| AC-MEM-001 | PostgreSQL + Redis, no SQLite | PG primary store established |
| AC-CORE-001 | Core daemon runs as systemd | PG must be available for core |
| AC-CORE-002 | Zero public admin ports | PG binds localhost only |
| AC-SEC-001 | RBAC/ABAC default deny | listen_addresses=localhost |
| AC-SEC-007 | Audit logs complete | log_connections, log_disconnections |
| AC-DATA-001 | Classification metadata | Audit logging for data tracking |

---

## 6. Evidence Paths & Convention

### StepPrompts Path (currently active)
docs/setup-evidence/P0/STEP-P0-014/
- postgresql-status.txt
- postgresql-config.txt
- port-isolation.txt (recommended additional)
- aizanta-verification.txt (recommended additional)

### Path Convention Conflict
StepPrompts: docs/setup-evidence/P0/STEP-P0-014/
IMPLEMENTATION_GUIDE: evidence/phase-N/step-MMM/

Existing evidence (P0-009, P0-010) uses docs/setup-evidence/ convention, so this is the active one.

---

## 7. Shared Writers & Collision Scan

### Shared Files (collision risks)
| File | P0-014 Action | Other Writers | Risk |
|---|---|---|---|
| /etc/postgresql/16/main/conf.d/guinevere.conf | Creates | P0-015/016/018 modify | HIGH - sequential required |
| /etc/postgresql/16/main/postgresql.conf | Indirect | P0-016 timescaledb-tune overwrites | HIGH |
| guinevere database | createdb | P0-015/016 extensions, P0-017 users, P3 migrations | HIGH - shared resource |
| guinevere-net Docker network | If Docker path | P8 monitoring containers | MEDIUM |

### Port Collision Scan
| Port | Owner | P0-014 Action |
|---|---|---|
| 5432 | Aizanta PG | MUST NOT TOUCH |
| **5433** | **P0-014 Target** | Check free with ss -tlnp first |
| 5434 | PgBouncer (future P0-019) | Not yet in use |
| 6379 | Aizanta Redis | MUST NOT TOUCH |
| 6380 | Guinevere Redis (future) | Not yet in use |

### Network Collision Scan
| Network | Subnet | Conflict? |
|---|---|---|
| aizanta_aizanta-internal | 172.18.0.0/16 | No |
| bridge (default) | 172.17.0.0/16 | No |
| guinevere-net | **172.28.0.0/16** | No overlap |

### User/Process Collision
Both Aizanta and Guinevere share the postgres OS user (created by PG package). This is normal but requires separate data directories and ports if both run PG16.

---

## 8. Blockers

### CRITICAL
**B1: Docker vs systemd ambiguity** - StepPrompts uses apt/systemd; user context says Docker; deployment guide uses Docker. Must resolve before execution. Affects ALL commands in P0-014.

**B2: ADR-027 shared_buffers = 4GB conflicts with P0-009 cgroup 8GB limit** - ADR assumes full 16GB RAM. Stepprompt values (1GB shared_buffers, 3GB effective_cache_size) are correct. Use stepprompt values. ADR-027 must be updated.

### MEDIUM
**B3: Evidence path convention conflict** - docs/setup-evidence/ vs evidence/
**B4: Ubuntu 24.04 (Noble) PGDG repo availability** - May need codename mapping
**B5: Aizanta shares postgres system user** - Separate clusters must coexist

---

## 9. Contradictions & Anomalies

### C1: ADR-027 Memory Config vs Cgroup (CRITICAL)
ADR-027: shared_buffers=4GB, effective_cache_size=12GB (assumes 16GB total RAM)
P0-009 cgroup: MemoryMax=8G (Guinevere capped at 8GB)
StepPrompts (CORRECT): shared_buffers=1GB, effective_cache_size=3GB

**Verdict:** Use stepprompt values. Flag ADR-027 for correction.

### C2: Evidence Path Convention
StepPrompts: docs/setup-evidence/P0/STEP-P0-014/
IMPLEMENTATION_GUIDE: evidence/phase-N/step-MMM/
Active convention (from existing evidence): docs/setup-evidence/

### A1: Docker vs systemd (full ambiguity)
StepPrompts is systemd. User context is Docker. Deployment guide is Docker. Network was created for Docker. Data directory user specified is Docker. The stepprompt needs rewriting if Docker is chosen.

### A2: Data Directory Ambiguity
systemd path: /var/lib/postgresql/16/main/
Docker path: /home/guinevere/data/postgres/ (user-specified, in P0-003 structure)

### N1: timescaledb-tune overwrites P0-014 config
P0-016 runs timescaledb-tune --yes which auto-modifies shared_preload_libraries. May silently revert P0-014 settings. Document baseline before P0-016.

### N2: Port 5433 and Aizanta PgBouncer
StepPrompts port table shows Aizanta PgBouncer uses 5433. If Aizanta PgBouncer is running, 5433 is NOT available. Must verify with ss -tlnp.

### N3: Search for 256GB - Zero Results
No references to 256GB exist anywhere in the repo. VPS has 16GB RAM. maintenance_work_mem is 256MB (not GB). This clarifies there is no 256GB constraint.

---

## 10. Downstream Dependencies (P0-015, P0-016, P0-018)

### P0-015: pgvector 0.7.0 Extension
- Depends on: P0-014 (PG16 running on guinevere database)
- Build from source: git clone --branch v0.7.0, make, sudo make install
- Key risk: Requires postgresql-server-dev-16 and build tools
- Rollback: DROP EXTENSION vector CASCADE; rm extension files

### P0-016: TimescaleDB 2.15 Extension
- Depends on: P0-014 (PG16 running)
- Key risk: timescaledb-tune --yes auto-modifies shared_preload_libraries and may change P0-014 settings
- Rollback: DROP EXTENSION timescaledb CASCADE; apt purge; rm repo list

### P0-018: PostgreSQL Security Hardening
- Depends on: P0-017 (users created first)
- Key changes: Replace pg_hba.conf with scram-sha-256 only, localhost only, reject all else. Set connection limits per user (core=30, surv=10, sched=10, readonly=15, backup=5)
- Rollback: Restore pg_hba.conf.bak

---

## 11. Verification Commands

### Pre-Execution Checklist
```
ls -la /home/guinevere/data/postgres/        # P0-003 directory check
cat /sys/fs/cgroup/guinevere.slice/memory.max  # Expected: 8589934592 (8GB)
docker network ls | grep guinevere-net       # P0-010 check
ss -tlnp | grep 5433 || echo "PORT 5433 FREE"  # MUST be free
ss -tlnp | grep 5432                         # MUST show Aizanta, NOT guinevere
systemctl status aizanta-*                   # Aizanta services running
df -h /home                                  # >= 20GB free
```

### Post-Execution Checklist
```
systemctl status postgresql                   # active (running)
psql --version                                # PostgreSQL 16.x
sudo -u postgres psql -l | grep guinevere     # database exists
sudo -u postgres psql -d guinevere -c "SHOW shared_buffers;"    # 1GB
sudo -u postgres psql -d guinevere -c "SHOW port;"              # 5433
sudo -u postgres psql -d guinevere -c "SHOW listen_addresses;"  # localhost
sudo -u postgres psql -d guinevere -c "SHOW timezone;"          # Asia/Jakarta
sudo -u postgres psql -d guinevere -c "SHOW max_connections;"   # 100
ss -tlnp | grep 5433                         # postgres on 5433
ss -tlnp | grep 5432                         # NOT guinevere postgres
systemctl status aizanta-*                   # Aizanta unaffected
```

---

## 12. Rollback Safety

### StepPrompts Rollback Commands
```
sudo systemctl stop postgresql
sudo apt purge -y postgresql-16
sudo rm -rf /etc/postgresql/16
sudo rm -rf /var/lib/postgresql/16
sudo userdel postgres 2>/dev/null
```

### Destructiveness Assessment
| Action | Destructive | Reversible |
|---|---|---|
| systemctl stop | No | Yes (start) |
| apt purge | Yes | Reinstall needed |
| rm -rf /etc/postgresql/16 | Yes | Config lost |
| **rm -rf /var/lib/postgresql/16** | **DATA LOSS** | **NO - all databases destroyed** |
| userdel postgres | Yes | Recreatable by reinstall |

### Rollback Safety Rules
1. Never rollback if Aizanta is affected
2. Never rollback if P0-015/P0-016 ran (extension deps may break)
3. Document rollback in evidence if executed
4. Pre-execution backup recommended: cp -a /etc/postgresql /tmp/pg-config-backup-$(date +%Y%m%d)

---

## 13. Risk Assessment

| Risk | Prob | Impact | Mitigation |
|---|---|---|---|
| Port 5433 conflict (Aizanta PgBouncer) | Low | Critical | Check ss -tlnp before exec |
| Docker vs systemd ambiguity | High | Critical | Resolve before any command execution |
| shared_buffers 1GB low for pgvector | Med | Medium | Monitor; increase to 2GB if needed |
| Noble not in PGDG repo | Med | Medium | Use Jammy codename fallback |
| timescaledb-tune overwrites config | Med | Low | Document baseline, verify post-P0-016 |
| postgres user shared with Aizanta | Low | Medium | Separate data dirs, different ports |
| Disk space < 20GB | Low | Low | df -h before execution |

---

## 14. Execution Recommendations

### Priority 1: Resolve Docker vs systemd
**Option A (systemd - per StepPrompts):** apt install postgresql-16, configure via guinevere.conf, data at /var/lib/postgresql/16/main/
**Option B (Docker - per user context):** pgvector/pgvector:pg16 image, mount /home/guinevere/data/postgres/, map 5433:5432, network guinevere-net

If Docker is chosen, the stepprompt commands must be rewritten. The postgresql.conf path, data directory, restart commands, and verification commands all differ.

### Priority 2: Fix ADR-027 shared_buffers
Correct from shared_buffers=4GB, effective_cache_size=12GB to shared_buffers=1GB, effective_cache_size=3GB to match P0-009 cgroup limits.

### Priority 3: Pre-Execution Sequence
1. Confirm Docker or systemd approach
2. Verify ss -tlnp | grep 5433 is FREE
3. Verify Aizanta PG on 5432 is untouched
4. Verify df -h /home >= 20GB
5. Verify P0-003 directory exists
6. Verify P0-009 cgroup limits exist
7. Document Aizanta pre-state

### Priority 4: Post-Execution Sequence
1. Run all verification commands
2. Write evidence to docs/setup-evidence/P0/STEP-P0-014/
3. Verify Aizanta unaffected
4. Update PROGRESS.md (mark P0-014 complete)
5. Update CHECKLIST.md (line 113)
6. Create post-step auditor report
7. Git commit with message chore(P0): P0-014 PostgreSQL 16 setup

---

## Report Summary

| Metric | Value |
|---|---|
| Files analyzed | 11+ (StepPrompts, PROGRESS, CHECKLIST, IMPLEMENTATION_GUIDE, ADR-014, ADR-027, ADR-Index, docker-network.txt, guinevere-slice.conf, StepPrompts P0-015/016/018) |
| Cross-repo searches | 5 (pgvector=331 matches, TimescaleDB=358, postgresql.conf=16, pg_hba.conf=37, 256GB=0) |
| Contradictions found | 3 major (Docker vs systemd, ADR-027 shared_buffers, evidence path) |
| Blockers | 2 critical (B1 Docker/systemd, B2 ADR shared_buffers), 3 medium |
| Open questions | Docker or systemd? ADR-027 config correction needed? Evidence path to standardize? |
| Report file | audit-reports/P0/STEP-P0-014/internal-context-report.md |

*Generated by Guinevere for STEP-P0-014 pre-implementation context. This report must be reviewed before any execution begins.*
