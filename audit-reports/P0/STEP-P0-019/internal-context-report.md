# Pre-Implementation Context Report --- P0-019 (PgBouncer Connection Pooling)

**Date:** 2026-05-31
**Auditor:** Guinevere
**Source Task:** STEP-P0-019
**File:** audit-reports/P0/STEP-P0-019/internal-context-report.md

---

## 1. Scope Definition

### Step Identity
- **Step ID:** P0-019
- **Type:** Database
- **Status:** Not Started
- **Risk:** Medium
- **Estimated Time:** 2 hours
- **Cost Impact:** $0/month (Docker container, same VPS)
- **Phase:** P0 Infrastructure Foundation (step 19 of 29)

### Goal (from StepPrompts.md line 1994)
Install PgBouncer for connection pooling, reducing PostgreSQL connection overhead.

### CRITICAL SCOPE DEVIATION: Docker vs Bare-Metal
StepPrompts lines 2009-2094 implement PgBouncer via **bare-metal apt + systemd** (sudo apt install -y pgbouncer, systemctl enable pgbouncer). However:
- PostgreSQL is itself a Docker container (guinevere-postgres on guinevere-net, 172.28.0.2:5432, exposed as 127.0.0.1:5433)
- Operator Faiz explicitly requires PgBouncer as Docker container on guinevere-net, listening at port **5434**
- ADR-014 allows selective containerization
- PgBouncer on guinevere-net can resolve the PostgreSQL container via Docker DNS (guinevere-postgres:5432) instead of loopback

**This report fully adopts the Docker adaptation per user directive. All bare-metal StepPrompts commands are superseded.**

---

## 2. Dependency Graph

### Upstream (MUST be complete)
| Step | Dependency | Status | Risk if Missing |
|---|---|---|---|
| P0-010 | Docker network guinevere-net (172.28.0.0/16) | [x] COMPLETE | Container has no network |
| P0-014 | PostgreSQL 16 Docker container on guinevere-net | [x] COMPLETE | No backend to pool |
| P0-017 | PG users (core, surveillance, scheduler, readonly, backup) | [ ] NOT STARTED | userlist.txt has no entries to authenticate |
| P0-018 | PG hardening (pg_hba.conf, SSL, connection limits) | [ ] NOT STARTED | PgBouncer must connect via scram-sha-256 through hardened pg_hba |

### Downstream (BLOCKED by P0-019)
| Step | What It Needs |
|---|---|
| P0-028 | Pre-flight verification, pooler connection test OK (CHECKLIST.md line 119) |
| P1-xx | All Hermes/LLM services connect through pooled port 5434 |
| P5-xx | Agent loop services connect through pooled port 5434 |
| P7-xx | Surveillance services connect through pooled port 5434 |

### Parallel Opportunity
P0-019 is parallel-safe with P0-020 (Redis 7). No shared config files, no port collision (5434 vs 6380).

---

## 3. Definition of Done

### From StepPrompts Verification (DOCKER ADAPTED)
- [ ] PgBouncer running: docker ps shows Up (healthy)
- [ ] Listening on 5434: docker port shows 5434/tcp
- [ ] Connection through pool works: psql via port 5434 returns result
- [ ] Pool stats available: SHOW POOLS returns stats
- [ ] Transaction pool mode confirmed
- [ ] Aizanta untouched: Aizanta containers still 5/5 healthy

### From CHECKLIST.md (line 119) DOCKER ADAPTED
- [ ] docker ps --filter name=guinevere-pgbouncer shows Up (healthy)
- [ ] Pooler connection test via psql -h 127.0.0.1 -p 5434 returns SELECT 1

### Extended DoD (from AGENTS.md)
- [ ] Auditor gate: independent report PASS
- [ ] No Aizanta impact, no consent/safety violation
- [ ] No plaintext passwords in evidence files
- [ ] Evidence files at docs/setup-evidence/P0/STEP-P0-019/

---

## 4. ADR References & Binding Decisions

| ADR | Title | Relevance |
|---|---|---|
| ADR-014 | VPS and Container Architecture | Selective containerization allowed |
| ADR-027 | Self-Hosted PostgreSQL | Explicitly requires PgBouncer |
| ADR-031 | Database Naming Convention | Database name = guinevere |
| ADR-005 | Agent Loop and Delegation | Agent loop services connect via pooled port 5434 |
| ADR-018 | Security Architecture | scram-sha-256 auth, no public ports |

### Port Assignments
| Service | Aizanta | Guinevere (actual) |
|---|---|---|
| PostgreSQL | 5432 | 5433 (loopback) / 5432 (container-internal) |
| PgBouncer | 5433 | **5434** (target) |
| Redis | 6379 | 6380 (future P0-020) |

---

## 5. Acceptance Criteria References

| AC ID | Description | Relevance |
|---|---|---|
| AC-CORE-001 | systemd-managed core daemon | PgBouncer is Docker-managed; ADR-014 allows this |
| AC-CORE-002 | Service resilience | Docker restart policy + health check |
| AC-SEC-001 | RBAC/ABAC default deny | PgBouncer binds 127.0.0.1:5434 only |
| AC-SEC-007 | Audit logs complete | log_connections, log_disconnections enabled |

---

## 6. Evidence Paths

### StepPrompts Evidence Path (adapted for Docker)
docs/setup-evidence/P0/STEP-P0-019/
- pgbouncer-status.txt - docker ps, port mapping, health check
- pgbouncer.ini - Docker-adapted config (template in section 10)
- pool-test.txt - psql connection test output
- aizanta-post-check.md - Aizanta containers unaffected
- p0-019-summary.md - Human-readable summary
- verification.md - Full verification artifact

---

## 7. Shared Writers and Collision Scan

### Shared Files
| File | P0-019 Action | Other Writers | Risk |
|---|---|---|---|
| secrets/guinevere-secrets.yaml | READ only | P0-017 writes here | LOW |
| guinevere-net Docker network | pgbouncer joins | P0-014, P0-020, P8 | LOW |

### Port Collision
| Port | Owner | Action |
|---|---|---|
| 5432 | Aizanta PostgreSQL | MUST NOT TOUCH |
| 5433 | Guinevere PostgreSQL | MUST NOT TOUCH |
| **5434** | **P0-019 Target** | Verify free before bind |
| 6379 | Aizanta Redis | MUST NOT TOUCH |

### Docker DNS
On guinevere-net, guinevere-postgres resolves to 172.28.0.2. PgBouncer connects via host=guinevere-postgres port=5432.

---

## 8. Blockers

### CRITICAL
**B1: P0-017 NOT COMPLETE** - PG users dont exist yet.
**B2: P0-018 NOT COMPLETE** - pg_hba.conf must allow 172.28.0.0/16.

### MEDIUM
**B3: db-passwords.yaml does not exist** - SOPS extraction path unknown until P0-017.
**B4: CHECKLIST.md line 119 references systemctl** - Must update to Docker equivalent.
**B5: StepPrompts references apt install** - Entire section superseded.

### LOW
**B6: pgbouncer/pgbouncer image may not include psql** - Use admin console or bitnami image.

---

## 9. Contradictions and Anomalies

### C1: Bare-Metal StepPrompts vs Docker Reality (CRITICAL)
All StepPrompts commands (lines 2009-2065) are superseded by Docker equivalents.

### C2: P0-018 pg_hba.conf Subnet Conflict (CRITICAL)
P0-018 StepPrompts pg_hba.conf only allows 127.0.0.1/32. PgBouncer on guinevere-net connects from 172.28.0.x. P0-018 must add 172.28.0.0/16 entries for all service users.

### C3: SOPS Password Path Mismatch
StepPrompts references secrets/db-passwords.yaml. No such file exists. Must verify after P0-017.

---

## 10. Proposed Docker Deployment

### 10.1 Image Recommendation
**Primary:** pgbouncer/pgbouncer:latest (~8MB, official). Add explicit --health-cmd.
**Alternative:** bitnami/pgbouncer:latest (~200MB, includes psql, built-in health check).

### 10.2 Docker Networking
| Detail | Value |
|---|---|
| Network | guinevere-net (172.28.0.0/16) |
| Container name | guinevere-pgbouncer |
| PostgreSQL host | guinevere-postgres (Docker DNS resolves to 172.28.0.2) |
| PostgreSQL port | 5432 (container-internal) |
| PgBouncer listen | 0.0.0.0:5434 |
| Host bind | 127.0.0.1:5434:5434 |

### 10.3 Bind Mounts
| Host Path | Container Path |
|---|---|
| /home/guinevere/config/pgbouncer/pgbouncer.ini | /etc/pgbouncer/pgbouncer.ini |
| /home/guinevere/config/pgbouncer/userlist.txt | /etc/pgbouncer/userlist.txt |

### 10.4 pgbouncer.ini (Docker-adapted)

```ini; pgbouncer.ini
[databases]
guinevere = host=guinevere-postgres port=5432 dbname=guinevere

[pgbouncer]
listen_addr = 0.0.0.0
listen_port = 5434
auth_type = scram-sha-256
auth_file = /etc/pgbouncer/userlist.txt
auth_user = guinevere_core
pool_mode = transaction
max_client_conn = 200
default_pool_size = 25
min_pool_size = 5
reserve_pool_size = 5
reserve_pool_timeout = 3.0
server_round_robin = 1
log_connections = 1
log_disconnections = 1
log_pooler_errors = 1
stats_period = 60
dns_max_ttl = 15.0
dns_nxdomain_ttl = 15.0
server_idle_timeout = 600
client_idle_timeout = 0
query_timeout = 0
query_wait_timeout = 10
```

### 10.5 Docker Run Command

'''bash; docker run command (template)
mkdir -p /home/guinevere/config/pgbouncer

# NOTE: SOPS key path depends on P0-017 output
CORE_PASS=$(sops -d /home/guinevere/secrets/guinevere-secrets.yaml | yq eval '.database.users.guinevere_core.password')

# Write userlist.txt
cat > /home/guinevere/config/pgbouncer/userlist.txt << EOF
"guinevere_core" "${CORE_PASS}"
"guinevere_surveillance" "${SURV_PASS}"
"guinevere_scheduler" "${SCHED_PASS}"
"guinevere_readonly" "${READONLY_PASS}"
"guinevere_backup" "${BACKUP_PASS}"
EOF

chmod 640 /home/guinevere/config/pgbouncer/userlist.txt

# Run container
docker run -d \
  --name guinevere-pgbouncer \
  --network guinevere-net \
  --restart unless-stopped \
  --cpus="0.5" \
  --memory="256m" \
  -p 127.0.0.1:5434:5434 \
  -v /home/guinevere/config/pgbouncer/pgbouncer.ini:/etc/pgbouncer/pgbouncer.ini:ro \
  -v /home/guinevere/config/pgbouncer/userlist.txt:/etc/pgbouncer/userlist.txt:ro \
  --health-cmd="psql -h 127.0.0.1 -p 5434 -U guinevere_core -d guinevere -c 'SELECT 1;' 2>/dev/null || exit 1" \
  --health-interval=15s \
  --health-timeout=5s \
  --health-retries=3 \
  --health-start-period=10s \
  --label "guinevere.component=pgbouncer" \
  --label "guinevere.phase=P0" \
  --label "guinevere.step=P0-019" \
  pgbouncer/pgbouncer:latest
'''

### 10.6 Verification

'''bash; verification commands (Docker-adapted)
docker ps --filter name=guinevere-pgbouncer
docker port guinevere-pgbouncer
docker inspect --format='{{json .State.Health}}' guinevere-pgbouncer
psql -h 127.0.0.1 -p 5434 -U guinevere_core -d guinevere -c "SELECT 1;"
psql -h 127.0.0.1 -p 5434 -U guinevere_core -d guinevere -c "SHOW POOLS;"
docker ps --filter name=aizanta
'''

### 10.7 Rollback
'''bash; rollback commands
docker stop guinevere-pgbouncer
docker rm guinevere-pgbouncer
# Config lives on host at /home/guinevere/config/pgbouncer
# Remove if desired, or preserve for re-deployment
'''

---

## 11. Risk Assessment

| Risk | Prob | Impact | Mitigation |
|---|---|---|---|
| P0-017 not done | HIGH | BLOCKING | Cannot proceed until P0-017 |
| P0-018 pg_hba.conf lacks 172.28.0.0/16 | HIGH | BLOCKING | PgBouncer connects from 172.28.0.x |
| db-passwords.yaml doesnt exist | HIGH | BLOCKING | SOPS extraction path unknown |
| CHECKLIST.md still references systemctl | MEDIUM | LOW | Update after implementation |
| pgbouncer image has no psql | MEDIUM | MEDIUM | Use admin console or bitnami/pgbouncer |
| Container IP overlap | LOW | LOW | Docker auto-assigns |

---

## 12. Execution Recommendations

1. **Block P0-019 until P0-017 and P0-018 are complete**
2. **Update P0-018** to add 172.28.0.0/16 scram-sha-256 entries for all service users
3. **Resolve SOPS password path** - verify P0-017 output structure
4. **Use auth_user = guinevere_core** mode - reduces userlist.txt sync burden
5. **Consider bitnami/pgbouncer** if psql is needed for health checks
6. **Update CHECKLIST.md** line 119 from systemctl to Docker equivalent

---

## Report Summary

| Metric | Value |
|---|---|
| Files analyzed | 8+ (StepPrompts P0-019/018/017, PROGRESS, CHECKLIST, ADR-027, docker-network.txt, P0-014 evidence) |
| Contradictions | 1 critical (bare-metal vs Docker), 2 medium (pg_hba.conf subnet, SOPS path) |
| Blockers | 2 critical (P0-017, P0-018 not done), 3 medium |
| Docker adaptation | Full rewrite |
| Report file | audit-reports/P0/STEP-P0-019/internal-context-report.md |

*Generated by Guinevere for STEP-P0-019 pre-implementation context. P0-019 cannot proceed until P0-017 and P0-018 are complete.*