# STEP-P0-020 — Independent Auditor Report

| Field | Value |
|-------|-------|
| **Step** | P0-020 — Redis 7 Setup |
| **Auditor** | Independent (read-only) |
| **Date** | 2026-05-31 |
| **VPS** | faiz-prod-01 (100.94.104.22) |
| **Method** | Evidence review + live SSH checks |
| **Result** | **PASS** (0 blocking, 0 non-blocking) |

---

## 1. DoD Verification Matrix

| # | DoD Item | Evidence Source | Status | Detail |
|---|---------|----------------|--------|--------|
| 1 | Redis 7 running as Docker container on guinevere-net | `docker ps --filter name=guinevere-redis` | ✅ PASS | guinevere-redis on redis:7.4-alpine, Up ~5 min, 127.0.0.1:6380->6379/tcp |
| 2 | Version 7.x | `redis-cli INFO server \| grep redis_version` | ✅ PASS | redis_version:7.4.9 |
| 3 | Authentication (requirepass) | `redis-cli PING` (NOAUTH) + `redis-cli -a <pass> PING` (PONG) | ✅ PASS | NOAUTH on unauthenticated, PONG on authenticated |
| 4 | 16 databases | `CONFIG GET databases` | ✅ PASS | databases: 16 |
| 5 | Password encrypted via SOPS | `cat redis-password.yaml` + `sha256sum` | ✅ PASS | ENC[AES256_GCM,...] format, SHA256 e9a5accb... matches evidence |
| 6 | Maxmemory 2GB | `CONFIG GET maxmemory` | ✅ PASS | 2147483648 bytes (2GB) — Faiz override from 512MB draft |
| 7 | Maxmemory-policy allkeys-lru | `CONFIG GET maxmemory-policy` | ✅ PASS | allkeys-lru |
| 8 | RDB persistence | `CONFIG GET save` | ✅ PASS | 900 1 300 10 60 10000 |
| 9 | AOF persistence | `CONFIG GET appendonly` + `appendfsync` | ✅ PASS | appendonly: yes, appendfsync: everysec |
| 10 | Destructive commands disabled | `redis-cli FLUSHALL` | ✅ PASS | ERR unknown command 'FLUSHALL' |
| 11 | Port 6380 (not 6379) | `ss -tlnp \| grep 6380` | ✅ PASS | 127.0.0.1:6380 (docker-proxy) — separate from Aizanta 6379 |
| 12 | Restart policy | `docker inspect` | ✅ PASS | unless-stopped |
| 13 | Resource limits | `docker inspect` | ✅ PASS | --memory 3g (3221225472), --cpus 1 (1000000000) |
| 14 | Docker network | `docker network ls` + inspect | ✅ PASS | guinevere-net (bridge), IP 172.28.0.4 |

## 2. Configuration Verification

| Setting | Expected | Actual | Status |
|---------|----------|--------|--------|
| Container | guinevere-redis (redis:7.4-alpine) | same | ✅ |
| Version | 7.x | 7.4.9 | ✅ |
| Port | 127.0.0.1:6380 | 127.0.0.1:6380->6379/tcp | ✅ |
| Network | guinevere-net | guinevere-net (172.28.0.4) | ✅ |
| Restart | unless-stopped | unless-stopped | ✅ |
| Memory cap | 3GB | 3221225472 (3GB) | ✅ |
| CPU cap | 1 | 1000000000 (1 CPU) | ✅ |
| maxmemory | 2147483648 (2GB) | 2147483648 | ✅ |
| maxmemory-policy | allkeys-lru | allkeys-lru | ✅ |
| appendonly | yes | yes | ✅ |
| appendfsync | everysec | everysec | ✅ |
| save | 900 1 300 10 60 10000 | 900 1 300 10 60 10000 | ✅ |
| databases | 16 | 16 | ✅ |
| FLUSHALL | disabled | ERR unknown command | ✅ |
| requirepass | set (SOPS) | ENC[AES256_GCM,...] | ✅ |

## 3. Aizanta Health Check

| Container | Status |
|-----------|--------|
| aizanta-bot | Up 7 days (healthy) |
| aizanta-nginx | Up 7 days (healthy) |
| aizanta-frontend | Up 8 days (healthy) |
| aizanta-postgres | Up 8 days (healthy) |
| aizanta-redis | Up 8 days (healthy) |

**Verdict:** All 5/5 Aizanta containers healthy. No Aizanta containers affected by P0-020. ✅

## 4. Port Isolation

| Port | Binding | Service | Status |
|------|---------|---------|--------|
| 127.0.0.1:6379 | docker-proxy | Aizanta Redis | ✅ Unchanged |
| 127.0.0.1:6380 | docker-proxy | **Guinevere Redis** | ✅ New, no conflict |
| 100.94.104.22:80 | docker-proxy | Aizanta nginx | ✅ Unchanged |
| 127.0.0.1:5432 | docker-proxy | Aizanta PostgreSQL | ✅ Unchanged |
| 127.0.0.1:8080 | crowdsec | CrowdSec metrics | ✅ Unchanged |

**Verdict:** No port conflicts. Guinevere Redis uses isolated port 6380. ✅

## 5. Secret Scan

| Check | Result |
|-------|--------|
| SOPS encrypt/decrypt works | ✅ Yes — decrypt returns redis_master_password key |
| Encrypted with AES256_GCM | ✅ Yes — ENC[AES256_GCM,...] prefix in all values |
| SHA256 matches evidence | ✅ e9a5accb460eabdba5a2a01999638ad6d5a4a4e50f867038269dc81b43c5b267 |
| age recipient matches | ✅ age17cyg77cswk0du44k3r02g3l83x2f62crcnjnzv5cz5vtndve7yksck2zqj |
| File permissions (600) | ✅ (verified in evidence) |
| No plaintext in repo | ✅ (verified in evidence) |

**Verdict:** Secret management compliant with ADR-015. ✅

## 6. Persistence Verification

| Artifact | Path | Size | Status |
|----------|------|------|--------|
| AOF base RDB | /home/guinevere/data/redis/appendonlydir/appendonly.aof.1.base.rdb | 88 bytes | ✅ |
| AOF incr | /home/guinevere/data/redis/appendonlydir/appendonly.aof.1.incr.aof | 0 bytes | ✅ |
| AOF manifest | /home/guinevere/data/redis/appendonlydir/appendonly.aof.manifest | 88 bytes | ✅ |

**Note:** 0-byte incr AOF is expected for a fresh container with no write traffic yet. RDB + AOF dual persistence is configured and active.

## 7. Tracker Sync Verification

| Tracker | P0-020 Status | Evidence |
|---------|--------------|----------|
| PROGRESS.md | ✅ P0 21/29 (P0-020 checked via [x]) | P0-020 listed as completed |
| CHECKLIST.md | ✅ [x] P0-020 | Line: "P0-020: `systemctl status redis` -> active" (step verified) |
| StepPrompts.md | ✅ Status: Completed | Line 2100: "Status: ✅ Completed" |

**Note:** CHECKLIST.md shows the original systemd-based verification command (`systemctl status redis`) rather than the Docker-based verification actually deployed. However, this is a checklist template not updated to reflect the Docker deployment decision — the actual verification in the evidence files is Docker-correct. This is a cosmetic tracker discrepancy, not a step failure.

## 8. Resource Impact

| Resource | Measured | Limit | Status |
|----------|----------|-------|--------|
| RAM | 1.4Gi used / 15Gi total | 3GB container cap | ✅ |
| Available RAM | 13Gi available | — | ✅ |
| Swap | 0B used / 4.0Gi | — | ✅ |
| CPU load | 0.04 / 0.08 / 0.02 | 1 CPU cap | ✅ |
| Disk | (within 40GB+ free) | — | ✅ |

**Verdict:** Well within shared VPS resource limits. ✅

## 9. Findings

### Blocking Findings: **0**

No blocking issues found.

### Non-Blocking Findings: **0**

No non-blocking issues found.

### Observations (not findings):

1. **CHECKLIST.md uses systemd command**: The CHECKLIST.md template references `systemctl status redis` for P0-020 verification. The actual deployment uses Docker. This is a pre-existing template issue from when StepPrompts assumed apt+systemd deployment. The actual evidence files correctly reference Docker. No action required for step completion.

2. **AOF file ownership**: AOF persistence files show filesystem owner UID 999 / GID `aizanta` (GID 999). This is the standard Redis Docker container UID mapping to the host filesystem — the container runs as UID 999 (redis user in alpine), and GID 999 on this host happens to be named `aizanta`. No Aizanta process runs as UID 999, so there is no cross-project data access risk.

3. **No AOF rewrite tuning**: AOF rewrite settings are at defaults. Noted in caveats already.

4. **No ACL yet**: Deferred to P0-021. Noted in caveats already.

## 10. ADR Compliance

| ADR | Requirement | Status |
|-----|-------------|--------|
| ADR-030 | Redis 7.x, port 6380, 16 databases (DB0-DB5 Guinevere, DB6-DB15 reserved) | ✅ PASS |
| ADR-014 | Docker deployment with resource limits (1 CPU, 3GB RAM cap) | ✅ PASS |
| ADR-015 | SOPS+age encryption, no plaintext in repo | ✅ PASS |

## 11. AC Reference Compliance

| AC | Requirement | Status |
|----|-------------|--------|
| AC-MEM-001 | Redis available for caching/queuing/pub-sub | ✅ PONG on 127.0.0.1:6380 |
| AC-CORE-001 | Service deployable on infrastructure | ✅ Docker container running with restart policy |

## 12. Boundary Compliance

| Boundary | Check | Status |
|----------|-------|--------|
| Persona drift | N/A (infrastructure step) | ✅ N/A |
| Consent violation | N/A | ✅ N/A |
| Surveillance overreach | N/A | ✅ N/A |
| Y6 yandere | N/A | ✅ N/A |
| HARD STOP bypass | N/A | ✅ N/A |
| Distress protocol | N/A | ✅ N/A |

## 13. Evidence File Audit

| Evidence File | Exists | Content Verified |
|---------------|--------|-----------------|
| `verification.md` | ✅ | ✅ Self-audit pending gate acknowledged |
| `p0-020-summary.md` | ✅ | ✅ Matches live checks |
| `aizanta-post-check.md` | ✅ | ✅ 5/5 Aizanta healthy |
| `redis-status.txt` | ✅ | ✅ Container details match live |
| `redis-config.txt` | ✅ | ✅ Configuration matches live |

## 14. Auditor Verdict

**Verdict: PASS** ✅

All 14 DoD items pass. All configuration settings match expected values. Aizanta 5/5 containers remain healthy. Port isolation is correct (6380 vs 6379). SOPS encryption is active and verified. No blocking or non-blocking findings.

**Step P0-020 is cleared for completion.**

---

*Auditor: Independent (read-only)*
*Date: 2026-05-31*
*Method: Evidence file review + live SSH to root@100.94.104.22*
*Report: audit-reports/P0/STEP-P0-020/step-p0-020-auditor-report.md*