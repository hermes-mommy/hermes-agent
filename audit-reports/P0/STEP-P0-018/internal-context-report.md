# Pre-Implementation Context Report — P0-018 (PostgreSQL Security Hardening)

**Date:** 2026-05-31
**Auditor:** Guinevere
**Source Task:** STEP-P0-018
**File:** `audit-reports/P0/STEP-P0-018/internal-context-report.md`

---

## 1. Scope Definition

### Step Identity
- **Step ID:** P0-018
- **Type:** Security — PostgreSQL Hardening
- **Status:** Not Started
- **Risk:** High
- **Estimated Time:** 2 hours
- **Cost Impact:** $0/month
- **Phase:** P0 Infrastructure Foundation (step 18 of 29)
- **Git Commit:** `chore(P0): pending`

### Goal (from StepPrompts.md lines 1883-1984)
Harden PostgreSQL configuration with connection restrictions, SSL, and audit logging. Replace default pg_hba.conf with scram-sha-256 only, restrict to localhost, set connection limits per user, reject all else.

### CRITICAL ADAPTATION: Docker vs Bare-Metal
**StepPrompts assumes bare-metal Debian/Ubuntu** (`/etc/postgresql/16/main/pg_hba.conf`, `systemctl restart postgresql`, `sudo -u postgres psql`).

**Actual deployment**: Docker container `guinevere-postgres` (postgres:16-trixie base, with pgvector 0.8.2 + TimescaleDB 2.27.1 installed via apt inside the container).

| Aspect | Bare-Metal (assumed) | Docker (actual) |
|---|---|---|
| pg_hba.conf path | `/etc/postgresql/16/main/pg_hba.conf` | Inside container PGDATA — determined by `SHOW hba_file` |
| Config method | `guinevere.conf` in `conf.d/` | CLI `-c` flags + default `postgresql.conf` + `postgresql.auto.conf` (TimescaleDB) |
| Restart | `systemctl restart postgresql` | `docker restart guinevere-postgres` or `pg_reload_conf()` |
| psql access | `sudo -u postgres psql` | `docker exec -it guinevere-postgres psql -U guinevere -d guinevere` |
| superuser connection | `sudo -u postgres psql` | `docker exec -it guinevere-postgres psql -U postgres` |

---

## 2. Current Container State (from P0-014/P0-015/P0-016 evidence)

### Container Parameters
| Parameter | Value |
|---|---|
| Container name | `guinevere-postgres` |
| Image | `postgres:16` (resolved `16.14-trixie`; pgvector 0.8.2 + TimescaleDB 2.27.1 installed in writable layer) |
| Network | `guinevere-net` (172.28.0.2/16) |
| Port | `127.0.0.1:5433:5432` (loopback only) |
| Volume mount | `/home/guinevere/data/postgres` -> `/var/lib/postgresql/data` (bind mount) |
| Health check | `pg_isready -U guinevere -d guinevere` (10s, 5 retries, 30s start period) |
| Config method | `docker run -c` CLI args |
| PGDATA | Default: `/var/lib/postgresql/data` |
| Volume structure | `ls /home/guinevere/data/postgres/` -> `pgdata/` subdirectory exists |

### Extensions Installed (writable layer — CRITICAL)
- `plpgsql` 1.0
- `vector` 0.8.2 (pgvector, from P0-015)
- `timescaledb` 2.27.1 (TimescaleDB Community Edition, from P0-016)

**WARNING**: Extensions are installed via `apt` inside the running container (writable layer). `docker rm` + `docker run` will LOSE both extensions. P0-018 must NEVER recreate the container.

### No Custom Config Mount
The P0-014 auditor report (Finding #1) confirms: **No `guinevere.conf` file was actually created on the host.** Config was applied via `docker run -c` CLI flags. P0-018 must either:
1. Edit pg_hba.conf directly inside PGDATA (via `docker exec`), OR
2. Mount a custom pg_hba.conf from host into container (requires `docker rm` + recreate — risky due to extensions)

---

## 3. Dependency Graph

### Upstream (MUST be complete)
| Step | Dependency | Status | Risk if Missing |
|---|---|---|---|
| **P0-017** | PostgreSQL users created (guinevere_core, surveillance, scheduler, readonly, backup) | **NOT COMPLETE** | pg_hba.conf references users that don't exist; ALTER USER CONNECTION LIMIT fails |
| P0-014 | PostgreSQL 16 running | COMPLETE | Container must be running |
| P0-015 | pgvector 0.8.2 | COMPLETE | Must preserve |
| P0-016 | TimescaleDB 2.27.1 | COMPLETE | Must preserve |

### CRITICAL: P0-017 is NOT Complete
- PROGRESS.md line 61: `[ ] P0-017 PostgreSQL users: guinevere_core, surveillance, scheduler`
- CHECKLIST.md lines 116-117: Both P0-017 verification items unchecked
- StepPrompts explicitly states: **"Dependencies: P0-017 (users created)"** (line 1891)
- pg_hba.conf references `guinevere_core`, `guinevere_surveillance`, `guinevere_scheduler`, `guinevere_readonly`, `guinevere_backup` — none exist yet
- ALTER USER CONNECTION LIMIT will fail if users don't exist

### Downstream (BLOCKED by P0-018)
| Step | What It Needs |
|---|---|
| P0-019 | PgBouncer connection pooling | Hardened pg_hba.conf for pooler auth |
| P3-001 | Alembic migrations | Secure connection from app service |
| P1-P8 | Application services | Secure, auditable DB connections |

---

## 4. pg_hba.conf Location — Docker Adaptation

### Finding the Exact Path
The actual pg_hba.conf path depends on PGDATA. Run these on the VPS:

```bash
# Method 1: Ask PostgreSQL directly (MOST RELIABLE)
docker exec guinevere-postgres psql -U guinevere -d guinevere -c "SHOW hba_file;"

# Method 2: Ask for config_file (to find PGDATA)
docker exec guinevere-postgres psql -U guinevere -d guinevere -c "SHOW config_file;"

# Method 3: Check PGDATA env var
docker exec guinevere-postgres sh -c "echo \$PGDATA"

# Method 4: List files in volume directly (host-side)
sudo ls -la /home/guinevere/data/postgres/pgdata/pg_hba.conf
```

### Expected Paths (from Volume Structure)
P0-014 evidence shows `pgdata/` subdirectory inside `/home/guinevere/data/postgres/`:

| Context | Expected Path |
|---|---|
| Inside container | `/var/lib/postgresql/data/pgdata/pg_hba.conf` |
| On host (VPS) | `/home/guinevere/data/postgres/pgdata/pg_hba.conf` |

### Container Backup Command
```bash
HBA_FILE=$(docker exec guinevere-postgres psql -U guinevere -d guinevere -tAc "SHOW hba_file")
docker exec guinevere-postgres cp "$HBA_FILE" "$HBA_FILE.bak"
```
Or via host volume:
```bash
sudo cp /home/guinevere/data/postgres/pgdata/pg_hba.conf /home/guinevere/data/postgres/pgdata/pg_hba.conf.bak
```

---

## 5. Full Docker Adaptation Map (Bare-Metal -> Docker)

### Command 1: Backup pg_hba.conf
**Bare-metal**: `sudo cp /etc/postgresql/16/main/pg_hba.conf /etc/postgresql/16/main/pg_hba.conf.bak`

**Docker**:
```bash
HBA_FILE=$(docker exec guinevere-postgres psql -U guinevere -d guinevere -tAc "SHOW hba_file")
echo "pg_hba.conf at: $HBA_FILE"
docker exec guinevere-postgres cp "$HBA_FILE" "$HBA_FILE.bak"
```

---

### Command 2: Create hardened pg_hba.conf
**Bare-metal**: `sudo tee /etc/postgresql/16/main/pg_hba.conf << 'EOF'`

**Docker Option A (RECOMMENDED — direct heredoc into container)**:
```bash
docker exec -i guinevere-postgres tee "$(docker exec guinevere-postgres psql -U guinevere -d guinevere -tAc "SHOW hba_file")" << 'EOF'
# TYPE  DATABASE        USER                    ADDRESS         METHOD
local   all             postgres                                peer
local   guinevere       guinevere_core                          scram-sha-256
local   guinevere       guinevere_surveillance                  scram-sha-256
local   guinevere       guinevere_scheduler                     scram-sha-256
local   guinevere       guinevere_readonly                      scram-sha-256
local   guinevere       guinevere_backup                        scram-sha-256
host    guinevere       guinevere_core          127.0.0.1/32    scram-sha-256
host    guinevere       guinevere_surveillance  127.0.0.1/32    scram-sha-256
host    guinevere       guinevere_scheduler     127.0.0.1/32    scram-sha-256
host    guinevere       guinevere_readonly      127.0.0.1/32    scram-sha-256
host    guinevere       guinevere_backup        127.0.0.1/32    scram-sha-256
host    guinevere       guinevere_core          ::1/128         scram-sha-256
host    guinevere       guinevere_surveillance  ::1/128         scram-sha-256
host    guinevere       guinevere_scheduler     ::1/128         scram-sha-256
host    guinevere       guinevere_readonly      ::1/128         scram-sha-256
host    guinevere       guinevere_backup        ::1/128         scram-sha-256
host    guinevere       guinevere_core          172.28.0.0/16   scram-sha-256
host    guinevere       guinevere_surveillance  172.28.0.0/16   scram-sha-256
host    guinevere       guinevere_scheduler     172.28.0.0/16   scram-sha-256
host    guinevere       guinevere_readonly      172.28.0.0/16   scram-sha-256
host    guinevere       guinevere_backup        172.28.0.0/16   scram-sha-256
host    all             all                     0.0.0.0/0       reject
host    all             all                     ::/0            reject
EOF
```

**Docker Option B (write on host, copy into container)**:
```bash
sudo tee /tmp/pg_hba.conf.hardened << 'EOF'
...
EOF
HBA_FILE=$(docker exec guinevere-postgres psql -U guinevere -d guinevere -tAc "SHOW hba_file")
docker cp /tmp/pg_hba.conf.hardened guinevere-postgres:"$HBA_FILE"
rm /tmp/pg_hba.conf.hardened
```

**Docker Option C (mount from host — NOT RECOMMENDED)**: Requires container recreation which loses pgvector + timescaledb extensions in writable layer. Avoid unless you rebuild a custom Docker image.

---

### Command 3: Reload PostgreSQL config
**Bare-metal**: `sudo systemctl restart postgresql`

**Docker (RECOMMENDED — zero downtime)**:
```bash
docker exec guinevere-postgres psql -U guinevere -d guinevere -c "SELECT pg_reload_conf();"
```

**Docker fallback (brief downtime ~2s)**:
```bash
docker restart guinevere-postgres
```

---

### Command 4: Set connection limits (ALTER USER)
**Bare-metal**: `sudo -u postgres psql -d guinevere << 'EOF' ... EOF`

**Docker**:
```bash
docker exec -i guinevere-postgres psql -U guinevere -d guinevere << 'EOF'
ALTER USER guinevere_core CONNECTION LIMIT 30;
ALTER USER guinevere_surveillance CONNECTION LIMIT 10;
ALTER USER guinevere_scheduler CONNECTION LIMIT 10;
ALTER USER guinevere_readonly CONNECTION LIMIT 15;
ALTER USER guinevere_backup CONNECTION LIMIT 5;
EOF
```

---

### Command 5: Verify connection limits
**Bare-metal**: `sudo -u postgres psql -d guinevere -c "SELECT usename, valuntil, useconfig FROM pg_user WHERE usename LIKE 'guinevere%';"`

**Docker**:
```bash
docker exec guinevere-postgres psql -U guinevere -d guinevere -c "SELECT usename, valuntil, useconfig FROM pg_user WHERE usename LIKE 'guinevere%';"
```

---

### Command 6: Verify password encryption
**Bare-metal**: `sudo -u postgres psql -d guinevere -c "SHOW password_encryption;"`

**Docker**:
```bash
docker exec guinevere-postgres psql -U guinevere -d guinevere -c "SHOW password_encryption;"
```

---

### Command 7: Check PostgreSQL status
**Bare-metal**: `systemctl status postgresql`

**Docker**:
```bash
docker ps --filter name=guinevere-postgres --format '{{.Names}} {{.Status}}'
```

---

### Command 8: Test core user connection
**Bare-metal**: `psql -U guinevere_core -d guinevere -h 127.0.0.1`

**Docker (inside container)**:
```bash
docker exec guinevere-postgres psql -U guinevere_core -d guinevere -h 127.0.0.1 -c "SELECT 1;"
```

**Docker (from host via mapped port)**:
```bash
PGPASSWORD=$(sops -d /home/guinevere/code/guinevere/secrets/db-passwords.yaml 2>/dev/null | grep core_password | awk '{print $2}') \
  psql -h 127.0.0.1 -p 5433 -U guinevere_core -d guinevere -c "SELECT 1;"
```

---

### Command 9: Rollback pg_hba.conf
**Bare-metal**: `sudo cp /etc/postgresql/16/main/pg_hba.conf.bak /etc/postgresql/16/main/pg_hba.conf && sudo systemctl restart postgresql`

**Docker**:
```bash
HBA_FILE=$(docker exec guinevere-postgres psql -U guinevere -d guinevere -tAc "SHOW hba_file")
docker exec guinevere-postgres cp "$HBA_FILE.bak" "$HBA_FILE"
docker exec guinevere-postgres psql -U guinevere -d guinevere -c "SELECT pg_reload_conf();"
```

---

## 6. Adapted pg_hba.conf — Full Content (with Docker Network Rules)

```apache
# TYPE  DATABASE        USER                    ADDRESS         METHOD

# Local Unix socket (inside container)
local   all             postgres                                peer
local   guinevere       guinevere_core                          scram-sha-256
local   guinevere       guinevere_surveillance                  scram-sha-256
local   guinevere       guinevere_scheduler                     scram-sha-256
local   guinevere       guinevere_readonly                      scram-sha-256
local   guinevere       guinevere_backup                        scram-sha-256

# IPv4 local connections (localhost only)
host    guinevere       guinevere_core          127.0.0.1/32    scram-sha-256
host    guinevere       guinevere_surveillance  127.0.0.1/32    scram-sha-256
host    guinevere       guinevere_scheduler     127.0.0.1/32    scram-sha-256
host    guinevere       guinevere_readonly      127.0.0.1/32    scram-sha-256
host    guinevere       guinevere_backup        127.0.0.1/32    scram-sha-256

# IPv6 local connections
host    guinevere       guinevere_core          ::1/128         scram-sha-256
host    guinevere       guinevere_surveillance  ::1/128         scram-sha-256
host    guinevere       guinevere_scheduler     ::1/128         scram-sha-256
host    guinevere       guinevere_readonly      ::1/128         scram-sha-256
host    guinevere       guinevere_backup        ::1/128         scram-sha-256

# Docker internal network (container-to-container on guinevere-net)
# NOTE: Using 'host' not 'hostssl' — SSL certs deferred. See Section 8.
host    guinevere       guinevere_core          172.28.0.0/16   scram-sha-256
host    guinevere       guinevere_surveillance  172.28.0.0/16   scram-sha-256
host    guinevere       guinevere_scheduler     172.28.0.0/16   scram-sha-256
host    guinevere       guinevere_readonly      172.28.0.0/16   scram-sha-256
host    guinevere       guinevere_backup        172.28.0.0/16   scram-sha-256

# Deny all other connections
host    all             all                     0.0.0.0/0       reject
host    all             all                     ::/0            reject
```

### Why Docker Network Rules (172.28.0.0/16) Are Needed
Future Guinevere containers (Hermes Agent, Discord bot, core app) will connect to PostgreSQL via Docker internal DNS (`guinevere-postgres:5432`) on `guinevere-net`. Without explicit rules for 172.28.0.0/16, container-to-container connections would hit the `reject` catch-all.

---

## 7. Connection Limits (Adapted)

```bash
docker exec -i guinevere-postgres psql -U guinevere -d guinevere << 'EOF'
ALTER USER guinevere_core CONNECTION LIMIT 30;
ALTER USER guinevere_surveillance CONNECTION LIMIT 10;
ALTER USER guinevere_scheduler CONNECTION LIMIT 10;
ALTER USER guinevere_readonly CONNECTION LIMIT 15;
ALTER USER guinevere_backup CONNECTION LIMIT 5;
EOF
```

**NOTE**: These will **FAIL** with `ERROR: role "guinevere_core" does not exist` if P0-017 has not been executed first.

---

## 8. SSL Feasibility Inside Docker PostgreSQL

### Current SSL Status
- PostgreSQL `postgres:16` Docker image includes SSL support out of the box
- At container init time, the image generates a self-signed cert if no `server.crt`/`server.key` exist in PGDATA
- Default: `ssl = off` unless explicitly enabled
- Check: `docker exec guinevere-postgres psql -U guinevere -d guinevere -c "SHOW ssl;"`

### What's Needed to Enable SSL
1. Verify `server.crt`/`server.key` exist in PGDATA (or generate them)
2. Set `ssl = on` (via `ALTER SYSTEM SET ssl = on;` + container restart)
3. Change pg_hba.conf entries from `host` to `hostssl`

### Self-Signed SSL Cert Generation (Inside Container)
```bash
docker exec guinevere-postgres sh -c "
  PGDATA=\$(psql -U postgres -tAc 'SHOW data_directory')
  openssl req -new -text -nodes -subj '/CN=guinevere-postgres' \
    -keyout \$PGDATA/server.key -out \$PGDATA/server.csr
  openssl x509 -req -in \$PGDATA/server.csr -text -days 365 \
    -signkey \$PGDATA/server.key -out \$PGDATA/server.crt
  chmod 600 \$PGDATA/server.key
  chown 999:999 \$PGDATA/server.key \$PGDATA/server.crt
  rm \$PGDATA/server.csr
"

# Enable SSL (requires container restart)
docker exec guinevere-postgres psql -U guinevere -d guinevere -c "ALTER SYSTEM SET ssl = on;"
docker restart guinevere-postgres

# Verify SSL
docker exec guinevere-postgres psql -U guinevere -d guinevere -c "SHOW ssl;"
```

### Verdict: Feasible but DEFER Recommended

| Factor | Assessment |
|---|---|
| Technical feasibility | Fully feasible. PostgreSQL Docker image supports SSL natively. |
| Effort | Low-medium (generate certs + ALTER SYSTEM + restart) |
| Risk | Low (self-signed cert for internal Docker network) |
| Value proposition | **Low** for current architecture. Container-to-container traffic is isolated on `guinevere-net` bridge network. No traffic traverses public network. |

**DEFER rationale** (consistent with StepPrompts line 1982: *"SSL certificates can be added later if remote access is needed via Tailscale."*):

1. All connections are either `127.0.0.1` (host-to-container) or `172.28.0.0/16` (container-to-container on isolated Docker bridge). Neither is public.
2. Tailscale (P0-022) will encrypt any remote connections to the VPS. SSL inside Docker on top of Tailscale is redundant.
3. PgBouncer (P0-019) may need its own SSL config — adding complexity now is premature.
4. Container restart risk: enabling SSL requires a restart. Each restart risks the writable-layer extensions.

**Action**: Use `host` (not `hostssl`) in pg_hba.conf. Defer SSL setup to P0-022 (Tailscale) or P10 (Hardening).

---

## 9. Definition of Done (Docker-Adapted)

### StepPrompts DoD (Adapted)
- [ ] pg_hba.conf backed up (`.bak` inside PGDATA)
- [ ] pg_hba.conf hardened: no `trust`, no `md5`, only `scram-sha-256`
- [ ] `SELECT pg_reload_conf()` executed successfully (zero downtime)
- [ ] pg_hba verification: `SELECT * FROM pg_hba_file_rules` shows only expected rules
- [ ] `SHOW password_encryption` returns `scram-sha-256`
- [ ] Connection limits set: `SELECT usename, useconfig FROM pg_user` shows limits for all 5 users
- [ ] Container healthy: `docker ps` shows `Up (healthy)`
- [ ] Core user connects: `docker exec ... psql -U guinevere_core -h 127.0.0.1 -c "SELECT 1"` returns 1
- [ ] Reject verified: wrong IP connection attempt fails
- [ ] Aizanta: 5/5 healthy, no restarts
- [ ] Evidence files in `docs/setup-evidence/P0/STEP-P0-018/`

---

## 10. Evidence Paths

| File | Description |
|---|---|
| `docs/setup-evidence/P0/STEP-P0-018/pg-hba.conf` | Content of hardened pg_hba.conf (copy) |
| `docs/setup-evidence/P0/STEP-P0-018/pg-security.txt` | Verification: SHOW password_encryption, pg_user, connection test |
| `docs/setup-evidence/P0/STEP-P0-018/connection-test.txt` | Core user connect test, reject verification |
| `audit-reports/P0/STEP-P0-018/step-p0-018-auditor-report.md` | Independent auditor report |

---

## 11. Shared Writers & Collision Scan

### Shared Files
| File | P0-018 Action | Other Writers | Risk |
|---|---|---|---|
| pg_hba.conf (inside PGDATA) | Edit/replace | None currently | LOW |
| `postgresql.auto.conf` (PGDATA) | Not touched | P0-016 (ALTER SYSTEM for timescaledb) | LOW |
| `guinevere` database | ALTER USER CONNECTION LIMIT | P0-015/016 (extensions), P0-017 (users), P3 (migrations) | MEDIUM — don't change existing objects |
| PROGRESS.md, CHECKLIST.md, StepPrompts.md | Status update | All P0 steps | MEDIUM — standard tracker sync |

### Container Collision
| Resource | Risk | Mitigation |
|---|---|---|
| `guinevere-postgres` container | **Must NOT be docker rm'd** (would lose pgvector + timescaledb) | Use `pg_reload_conf()`; never recreate container |
| pg_hba.conf | Sequential edits only | Parent handles |
| User passwords | P0-017 generates SOPS passwords | P0-018 reads from SOPS, does not regenerate |

---

## 12. Blockers

### CRITICAL
**B1: P0-017 NOT COMPLETE** — Users referenced in pg_hba.conf and ALTER USER commands don't exist. **P0-018 cannot proceed until P0-017 is executed.**

### MEDIUM
**B2: Container extensions in writable layer** — pgvector + TimescaleDB installed via `docker exec apt-get` will be LOST on any `docker rm` + `docker run`. P0-018 must use in-container editing only, never recreate the container.

**B3: No config mount exists** — Current container uses CLI `-c` flags. Adding a mounted pg_hba.conf requires recreating container (see B2). Must use `docker exec` editing instead.

### LOW
**B4: pg_hba.conf path is dynamic** — Must determine via `SHOW hba_file` at runtime. Cannot hardcode.

---

## 13. Security Implications of Docker Adaptation

### pg_hba.conf Editing Inside Container
- Editing via `docker exec` is safe — only root and docker group on VPS have access
- The bind mount makes the file also accessible at `/home/guinevere/data/postgres/pgdata/pg_hba.conf` on the host
- Post-reload verification: `SELECT * FROM pg_hba_file_rules` shows active rules

### scram-sha-256 Password Migration
- PostgreSQL 16 defaults to `scram-sha-256`. If P0-017 created users with `PASSWORD '...'` (no `ENCRYPTED PASSWORD`), passwords are already SCRAM-hashed
- Verify: `SELECT rolname, rolpassword ~ 'SCRAM-SHA-256' AS is_scram FROM pg_authid WHERE rolname LIKE 'guinevere%';`
- If any user uses `md5`, re-set: `ALTER USER ... PASSWORD '...';`

### Reject Rules
- The `reject` catch-all prevents connections from unexpected IPs
- Future Guinevere containers on `guinevere-net` will connect via Docker DNS (`guinevere-postgres:5432`) which resolves to 172.28.0.2 — allowed by the 172.28.0.0/16 rules
- Rejected connections generate: `LOG: no pg_hba.conf entry for ...`

---

## 14. Verification Commands (Docker-Adapted)

### Pre-Execution
```bash
# Verify P0-017 is complete
docker exec guinevere-postgres psql -U guinevere -d guinevere -c "\du" | grep guinevere_

# Verify pg_hba.conf location
docker exec guinevere-postgres psql -U guinevere -d guinevere -c "SHOW hba_file;"

# Backup baseline
docker exec guinevere-postgres psql -U guinevere -d guinevere -c "SELECT * FROM pg_hba_file_rules;"

# Container + Aizanta healthy
docker ps --filter name=guinevere-postgres --format '{{.Names}} {{.Status}}'
docker ps | grep aizanta
```

### Post-Execution
```bash
# No trust entries
docker exec guinevere-postgres psql -U guinevere -d guinevere \
  -c "SELECT * FROM pg_hba_file_rules WHERE auth_method = 'trust';"

# scram-sha-256 active
docker exec guinevere-postgres psql -U guinevere -d guinevere \
  -c "SHOW password_encryption;"

# Connection limits
docker exec guinevere-postgres psql -U guinevere -d guinevere \
  -c "SELECT usename, valuntil, useconfig FROM pg_user WHERE usename LIKE 'guinevere%';"

# Core user connects
docker exec guinevere-postgres psql -U guinevere_core -d guinevere -h 127.0.0.1 -c "SELECT 1;"

# Reject verified (wrong IP)
docker exec guinevere-postgres psql -U guinevere_core -d guinevere -h 172.28.0.99 -c "SELECT 1;" 2>&1 || echo "REJECT confirmed"

# Container healthy
docker ps --filter name=guinevere-postgres --format '{{.Names}} {{.Status}}'

# Aizanta healthy
docker ps | grep aizanta

# Extensions preserved
docker exec guinevere-postgres psql -U guinevere -d guinevere \
  -c "SELECT extname, extversion FROM pg_extension;"
```

---

## 15. Risk Assessment

| Risk | Prob | Impact | Mitigation |
|---|---|---|---|
| Container recreated (loses pgvector + timescaledb) | Low | Critical | Use `docker exec` editing only; never `docker rm` |
| P0-017 not done | High | Blocking | Complete P0-017 first, or inline users before P0-018 |
| pg_hba.conf path wrong | Low | Medium | Verify with `SHOW hba_file` before edits |
| pg_reload_conf() doesn't apply rules | Low | Low | Fallback to `docker restart` |
| scram-sha-256 password re-set needed | Medium | Medium | Test after reload; re-set if connections fail |
| Aizanta impact | Low | High | Pre/post Aizanta health check required |
| Container-to-container connections blocked | Med | Med | Include 172.28.0.0/16 rules in pg_hba.conf |

---

## 16. Execution Recommendations

1. **Complete P0-017 first** — P0-018 is blocked without users existing.

2. **Use in-container editing (Option A/B)** — Never `docker rm` + `docker run` (would lose pgvector + timescaledb).

3. **Use `pg_reload_conf()`** — Zero-downtime reload for pg_hba.conf changes. Avoid container restart unless necessary.

4. **Include Docker network rules** — Add `host guinevere <user> 172.28.0.0/16 scram-sha-256` entries for future container-to-container connections.

5. **Defer SSL** — Technically feasible but adds no value for isolated Docker network traffic. Defer to P0-022 (Tailscale) or P10.

6. **Verify extensions after changes** — Confirm `vector 0.8.2` and `timescaledb 2.27.1` are still present after any container operation.

---

## 17. Summary

| Metric | Value |
|---|---|
| Files analyzed | StepPrompts.md (1883-1984), PROGRESS.md, CHECKLIST.md, ADR-018, P0-014 evidence (4 files), P0-015 evidence, P0-016 evidence, P0-014 auditor report |
| Bare-metal -> Docker adaptations | 9 command mappings verified |
| Blockers | 1 critical (P0-017 not complete), 2 medium (extension loss risk, no config mount), 1 low (dynamic pg_hba.conf path) |
| SSL feasibility | Feasible — **DEFER recommended** |
| pg_hba.conf expected path | `/var/lib/postgresql/data/pgdata/pg_hba.conf` (container) / `/home/guinevere/data/postgres/pgdata/pg_hba.conf` (host) |
| Extension preservation | **CRITICAL** — Never recreate container |
| Recommended edit method | `docker exec -i tee` heredoc or `docker cp` |
| Recommended reload | `SELECT pg_reload_conf()` (zero downtime) |

---

| Field | Value |
|---|---|
| Report file | `audit-reports/P0/STEP-P0-018/internal-context-report.md` |
| Date | 2026-05-31 |
| Prepared by | Guinevere |
| Status for execution | **BLOCKED** — P0-017 must be completed first |

*Generated by Guinevere for STEP-P0-018 pre-implementation context. This report must be reviewed before any execution begins.*
